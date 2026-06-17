import csv
import json
from io import StringIO
from typing import Literal
from uuid import uuid4

from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.copy import CopyAnalysis, CopySource
from app.models.knowledge import KnowledgeCollection, copy_source_collections
from app.schemas.copy import (
    CopyAnalysisRequest,
    CopyAnalysisResponse,
    CopyAssetListResponse,
    CopyAssetReviewRequest,
    CopyAssetSummary,
    CopyImportResponse,
    CopyImportRowError,
)
from app.services.copy_analysis import analyze_copy


MAX_SYNC_IMPORT_ROWS = 50
METRIC_FIELDS = ("likes", "comments", "favorites", "shares")
AUTHOR_FOLLOWER_FIELD = "author_follower_count"

_copy_assets: dict[str, CopyAssetSummary] = {}
_db_available: bool | None = False if settings.app_env == "test" else None
_REDIS_ASSET_HASH = "ragagent:copy_assets"
_REDIS_ASSET_ORDER = "ragagent:copy_asset_order"


def reset_copy_asset_store() -> None:
    global _db_available
    _db_available = False if settings.app_env == "test" else None
    _copy_assets.clear()
    if _persistent_backends_disabled():
        return
    try:
        redis = _redis()
        redis.delete(_REDIS_ASSET_HASH, _REDIS_ASSET_ORDER)
    except RedisError:
        pass


def import_copy_assets(csv_text: str) -> CopyImportResponse:
    fieldnames, rows = read_copy_import_csv(csv_text)
    errors: list[CopyImportRowError] = []
    assets: list[CopyAssetSummary] = []

    if not fieldnames or "source_text" not in fieldnames:
        return CopyImportResponse(
            imported_count=0,
            failed_count=1,
            assets=[],
            errors=[CopyImportRowError(row_number=1, message="CSV 必须包含 source_text 表头。")],
        )

    if len(rows) > MAX_SYNC_IMPORT_ROWS:
        return CopyImportResponse(
            imported_count=0,
            failed_count=len(rows),
            assets=[],
            errors=[
                CopyImportRowError(
                    row_number=1,
                    message=f"同步导入最多支持 {MAX_SYNC_IMPORT_ROWS} 行，请拆分 CSV。",
                )
            ],
        )

    for index, row in enumerate(rows, start=2):
        payload = parse_copy_import_row(row, index)
        if isinstance(payload, CopyImportRowError):
            errors.append(payload)
            continue

        analysis = analyze_copy(payload)
        asset = create_copy_asset(payload, analysis)
        from app.services.copy_postprocess import sync_imported_asset_to_knowledge

        sync_imported_asset_to_knowledge(asset)
        assets.append(asset)

    return CopyImportResponse(
        imported_count=len(assets),
        failed_count=len(errors),
        assets=assets,
        errors=errors,
    )


def list_copy_assets(
    *,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    industry: str | None = None,
    platform: str | None = None,
    collection_id: str | None = None,
) -> CopyAssetListResponse:
    db_assets = _get_db_asset_items()
    redis_assets = _get_redis_asset_items()
    merged = _merge_asset_sources(
        db_assets if db_assets is not None else [],
        redis_assets if redis_assets is not None else [],
        _copy_assets.values(),
    )
    filtered = _filter_assets(
        merged,
        status=status,
        industry=industry,
        platform=platform,
        collection_id=collection_id,
    )
    start = (page - 1) * page_size
    end = start + page_size
    return CopyAssetListResponse(
        items=filtered[start:end],
        page=page,
        page_size=page_size,
        total=len(filtered),
    )


def get_copy_asset(asset_id: str) -> CopyAssetSummary | None:
    db_asset = _get_db_asset(asset_id)
    if db_asset is not None:
        return db_asset
    redis_asset = _get_redis_asset(asset_id)
    if redis_asset is not None:
        return redis_asset
    return _copy_assets.get(asset_id)


def delete_copy_asset(asset_id: str) -> Literal["deleted", "not_found", "conflict", "unavailable"]:
    db_result = _delete_db_asset(asset_id)
    if db_result == "deleted":
        _delete_redis_asset(asset_id)
        _copy_assets.pop(asset_id, None)
        return "deleted"
    if db_result == "conflict":
        return "conflict"

    redis_asset = _get_redis_asset(asset_id)
    if redis_asset is not None:
        if _asset_requires_db_delete(redis_asset):
            return "unavailable"
        if redis_asset.status != "pending_review":
            return "conflict"
        _delete_redis_asset(asset_id)
        _copy_assets.pop(asset_id, None)
        return "deleted"

    asset = _copy_assets.get(asset_id)
    if asset is None:
        return "not_found"
    if _asset_requires_db_delete(asset):
        return "unavailable"
    if asset.status != "pending_review":
        return "conflict"
    _copy_assets.pop(asset_id, None)
    return "deleted"


def review_copy_asset(asset_id: str, payload: CopyAssetReviewRequest) -> CopyAssetSummary | None:
    db_asset = _review_db_asset(asset_id, payload)
    if db_asset is not None:
        _save_redis_asset(db_asset)
        return db_asset

    redis_asset = _review_redis_asset(asset_id, payload)
    if redis_asset is not None:
        return redis_asset

    asset = _copy_assets.get(asset_id)
    if asset is None:
        return None
    updated = asset.model_copy(
        update={
            "status": payload.status,
            "reviewed_analysis": payload.reviewed_analysis,
        }
    )
    _copy_assets[asset_id] = updated
    _save_redis_asset(updated)
    return updated


def _parse_metrics(row: dict[str, str | None]) -> dict[str, int] | str:
    metrics: dict[str, int] = {}
    for field in METRIC_FIELDS:
        raw = (row.get(field) or "").strip()
        if not raw:
            continue
        try:
            metrics[field] = int(raw)
        except ValueError:
            return f"{field} 必须是整数。"
    return metrics


def parse_copy_import_row(
    row: dict[str, str | None], row_number: int
) -> CopyAnalysisRequest | CopyImportRowError:
    source_text = (row.get("source_text") or "").strip()
    if not source_text:
        return CopyImportRowError(row_number=row_number, message="source_text 不能为空。")

    metric_result = _parse_metrics(row)
    if isinstance(metric_result, str):
        return CopyImportRowError(row_number=row_number, message=metric_result)

    author_follower_count = _parse_optional_non_negative_int(row.get(AUTHOR_FOLLOWER_FIELD))
    if isinstance(author_follower_count, str):
        return CopyImportRowError(row_number=row_number, message=author_follower_count)

    return CopyAnalysisRequest(
        source_text=source_text,
        source_url=_blank_to_none(row.get("source_url")),
        author_name=_blank_to_none(row.get("author_name")),
        author_url=_blank_to_none(row.get("author_url")),
        author_follower_count=author_follower_count,
        platform=_blank_to_none(row.get("platform")),
        industry=_blank_to_none(row.get("industry")),
        audience=_blank_to_none(row.get("audience")),
        purpose=_blank_to_none(row.get("purpose")),
        style=_blank_to_none(row.get("style")),
        structure_type=_blank_to_none(row.get("structure_type")),
        content_type=_blank_to_none(row.get("content_type")),
        metrics=metric_result,
    )


def read_copy_import_csv(csv_text: str) -> tuple[list[str] | None, list[dict[str, str | None]]]:
    reader = csv.DictReader(StringIO(csv_text))
    if reader.fieldnames is not None:
        reader.fieldnames = [_normalize_csv_header(field) for field in reader.fieldnames]
    return reader.fieldnames, list(reader)


def create_copy_asset(
    payload: CopyAnalysisRequest,
    analysis: CopyAnalysisResponse | None,
    collection_ids: list[str] | None = None,
) -> CopyAssetSummary:
    asset_id = str(uuid4())
    status = _initial_asset_status(analysis)
    asset = CopyAssetSummary(
        id=asset_id,
        source_text=payload.source_text,
        source_url=payload.source_url,
        author_name=payload.author_name,
        author_url=payload.author_url,
        author_follower_count=payload.author_follower_count,
        platform=payload.platform,
        industry=payload.industry,
        audience=payload.audience,
        purpose=payload.purpose,
        style=payload.style,
        structure_type=payload.structure_type,
        content_type=payload.content_type,
        metrics=payload.metrics or {},
        status=status,
        auto_analysis=analysis,
        reviewed_analysis=None,
        collection_ids=collection_ids or [],
    )
    db_persisted = _persist_asset_to_db(asset, collection_ids or [])
    if db_persisted:
        asset = asset.model_copy(update={"storage_backend": "postgres"})
    _copy_assets[asset.id] = asset
    _save_redis_asset(asset)
    return asset


def _persist_asset_to_db(asset: CopyAssetSummary, collection_ids: list[str]) -> bool:
    if _persistent_backends_disabled() or _db_available is False:
        return False
    db = SessionLocal()
    try:
        db.add(
            CopySource(
                id=asset.id,
                source_text=asset.source_text,
                source_url=asset.source_url,
                metadata_json=_asset_metadata(asset),
            )
        )
        if asset.auto_analysis is not None:
            db.add(
                CopyAnalysis(
                    copy_source_id=asset.id,
                    result_json=asset.auto_analysis.model_dump(mode="json"),
                    confidence=asset.auto_analysis.confidence,
                )
            )
        valid_collection_ids = _valid_db_collection_ids(db, collection_ids)
        if valid_collection_ids:
            db.execute(
                copy_source_collections.insert(),
                [
                    {"copy_source_id": asset.id, "collection_id": collection_id}
                    for collection_id in valid_collection_ids
                ],
            )
        db.commit()
        _mark_db_available(True)
        return True
    except SQLAlchemyError:
        _mark_db_available(False)
        db.rollback()
        return False
    finally:
        db.close()


def _list_db_assets(
    *,
    page: int,
    page_size: int,
    status: str | None,
    industry: str | None,
    platform: str | None,
    collection_id: str | None = None,
) -> CopyAssetListResponse | None:
    assets = _get_db_asset_items()
    if assets is None:
        return None
    filtered = _filter_assets(
        assets,
        status=status,
        industry=industry,
        platform=platform,
        collection_id=collection_id,
    )
    return _asset_list_response(filtered, page=page, page_size=page_size)


def _get_db_asset(asset_id: str) -> CopyAssetSummary | None:
    if _persistent_backends_disabled() or _db_available is False:
        return None
    db = SessionLocal()
    try:
        source = db.get(CopySource, asset_id)
        if source is None or _is_deleted_metadata(source.metadata_json or {}):
            return None
        return _source_to_asset(db, source)
    except SQLAlchemyError:
        _mark_db_available(False)
        return None
    finally:
        db.close()


def _review_db_asset(asset_id: str, payload: CopyAssetReviewRequest) -> CopyAssetSummary | None:
    if _persistent_backends_disabled() or _db_available is False:
        return None
    db = SessionLocal()
    try:
        source = db.get(CopySource, asset_id)
        if source is None or _is_deleted_metadata(source.metadata_json or {}):
            return None
        metadata = dict(source.metadata_json or {})
        metadata["status"] = payload.status
        metadata["reviewed_analysis"] = payload.reviewed_analysis.model_dump(mode="json")
        source.metadata_json = metadata
        db.commit()
        db.refresh(source)
        return _source_to_asset(db, source)
    except SQLAlchemyError:
        _mark_db_available(False)
        db.rollback()
        return None
    finally:
        db.close()


def _delete_db_asset(asset_id: str) -> Literal["deleted", "not_found", "conflict"] | None:
    if _persistent_backends_disabled() or _db_available is False:
        return None
    db = SessionLocal()
    try:
        source = db.get(CopySource, asset_id)
        if source is None or _is_deleted_metadata(source.metadata_json or {}):
            return "not_found"
        asset = _source_to_asset(db, source)
        if asset.status != "pending_review":
            return "conflict"
        metadata = dict(source.metadata_json or {})
        metadata["deleted"] = True
        source.metadata_json = metadata
        db.commit()
        return "deleted"
    except SQLAlchemyError:
        _mark_db_available(False)
        db.rollback()
        return None
    finally:
        db.close()


def _source_to_asset(db, source: CopySource) -> CopyAssetSummary:
    metadata = source.metadata_json or {}
    analysis = db.scalars(
        select(CopyAnalysis)
        .where(CopyAnalysis.copy_source_id == source.id)
        .order_by(CopyAnalysis.created_at.desc())
    ).first()
    auto_analysis = (
        CopyAnalysisResponse.model_validate(analysis.result_json)
        if analysis is not None and analysis.result_json
        else None
    )
    reviewed_raw = metadata.get("reviewed_analysis")
    collection_ids = _get_db_collection_ids(db, str(source.id))
    return CopyAssetSummary(
        id=str(source.id),
        source_text=source.source_text,
        source_url=source.source_url,
        author_name=metadata.get("author_name"),
        author_url=metadata.get("author_url"),
        author_follower_count=metadata.get("author_follower_count"),
        platform=metadata.get("platform"),
        industry=metadata.get("industry"),
        audience=metadata.get("audience"),
        purpose=metadata.get("purpose"),
        style=metadata.get("style"),
        structure_type=metadata.get("structure_type"),
        content_type=metadata.get("content_type"),
        metrics=metadata.get("metrics") or {},
        status=metadata.get("status") or "pending_review",
        auto_analysis=auto_analysis,
        reviewed_analysis=CopyAnalysisResponse.model_validate(reviewed_raw)
        if isinstance(reviewed_raw, dict)
        else None,
        storage_backend="postgres",
        collection_ids=collection_ids,
    )


def _merge_asset_sources(*sources) -> list[CopyAssetSummary]:
    merged: list[CopyAssetSummary] = []
    seen: set[str] = set()
    for source in sources:
        for asset in source:
            if asset.id in seen:
                continue
            seen.add(asset.id)
            merged.append(asset)
    return merged


def _filter_assets(
    assets: list[CopyAssetSummary],
    *,
    status: str | None,
    industry: str | None,
    platform: str | None,
    collection_id: str | None,
) -> list[CopyAssetSummary]:
    return [
        asset
        for asset in assets
        if (status is None or asset.status == status)
        and (industry is None or asset.industry == industry)
        and (platform is None or asset.platform == platform)
        and (collection_id is None or collection_id in asset.collection_ids)
    ]


def _asset_metadata(asset: CopyAssetSummary) -> dict:
    return {
        "platform": asset.platform,
        "industry": asset.industry,
        "audience": asset.audience,
        "purpose": asset.purpose,
        "style": asset.style,
        "structure_type": asset.structure_type,
        "content_type": asset.content_type,
        "author_name": asset.author_name,
        "author_url": asset.author_url,
        "author_follower_count": asset.author_follower_count,
        "metrics": asset.metrics,
        "status": asset.status,
        "reviewed_analysis": asset.reviewed_analysis.model_dump(mode="json")
        if asset.reviewed_analysis
        else None,
        "collection_ids": asset.collection_ids,
        "deleted": False,
    }


def _valid_db_collection_ids(db, collection_ids: list[str]) -> list[str]:
    if not collection_ids:
        return []
    rows = db.scalars(
        select(KnowledgeCollection.id).where(
            KnowledgeCollection.id.in_(collection_ids),
            KnowledgeCollection.is_deleted.is_(False),
        )
    ).all()
    return [str(row) for row in rows]


def _get_db_collection_ids(db, copy_source_id: str) -> list[str]:
    rows = db.execute(
        select(copy_source_collections.c.collection_id).where(
            copy_source_collections.c.copy_source_id == copy_source_id
        )
    ).all()
    return [str(row[0]) for row in rows]


def _mark_db_available(value: bool) -> None:
    global _db_available
    _db_available = value


def _normalize_csv_header(value: str | None) -> str:
    return (value or "").lstrip("\ufeff").strip()


def _initial_asset_status(analysis: CopyAnalysisResponse | None) -> str:
    if analysis is None:
        return "pending_review"
    if analysis.confidence >= settings.copy_auto_approve_min_confidence:
        return "approved"
    return "pending_review"


def _redis() -> Redis:
    return Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1)


def _save_redis_asset(asset: CopyAssetSummary) -> None:
    if _persistent_backends_disabled():
        return
    try:
        redis = _redis()
        redis.hset(_REDIS_ASSET_HASH, asset.id, json.dumps(asset.model_dump(mode="json"), ensure_ascii=False))
        if redis.lpos(_REDIS_ASSET_ORDER, asset.id) is None:
            redis.lpush(_REDIS_ASSET_ORDER, asset.id)
    except RedisError:
        pass


def _get_redis_asset(asset_id: str) -> CopyAssetSummary | None:
    if _persistent_backends_disabled():
        return None
    try:
        raw = _redis().hget(_REDIS_ASSET_HASH, asset_id)
    except RedisError:
        return None
    if raw is None:
        return None
    return CopyAssetSummary.model_validate(json.loads(raw))


def _list_redis_assets(
    *,
    page: int,
    page_size: int,
    status: str | None,
    industry: str | None,
    platform: str | None,
    collection_id: str | None = None,
) -> CopyAssetListResponse | None:
    assets = _get_redis_asset_items()
    if assets is None:
        return None
    filtered = _filter_assets(
        assets,
        status=status,
        industry=industry,
        platform=platform,
        collection_id=collection_id,
    )
    return _asset_list_response(filtered, page=page, page_size=page_size)


def _get_db_asset_items() -> list[CopyAssetSummary] | None:
    if _persistent_backends_disabled() or _db_available is False:
        return None
    db = SessionLocal()
    try:
        sources = db.scalars(select(CopySource).order_by(CopySource.created_at.desc())).all()
        return [
            _source_to_asset(db, source)
            for source in sources
            if not _is_deleted_metadata(source.metadata_json or {})
        ]
    except SQLAlchemyError:
        _mark_db_available(False)
        return None
    finally:
        db.close()


def _get_redis_asset_items() -> list[CopyAssetSummary] | None:
    if _persistent_backends_disabled():
        return None
    try:
        redis = _redis()
        ids = [item.decode("utf-8") for item in redis.lrange(_REDIS_ASSET_ORDER, 0, -1)]
        raw_assets = redis.hmget(_REDIS_ASSET_HASH, ids) if ids else []
    except RedisError:
        return None

    return [
        CopyAssetSummary.model_validate(json.loads(raw))
        for raw in raw_assets
        if raw is not None
    ]


def _asset_list_response(
    assets: list[CopyAssetSummary], *, page: int, page_size: int
) -> CopyAssetListResponse:
    start = (page - 1) * page_size
    return CopyAssetListResponse(
        items=assets[start : start + page_size],
        page=page,
        page_size=page_size,
        total=len(assets),
    )


def _review_redis_asset(asset_id: str, payload: CopyAssetReviewRequest) -> CopyAssetSummary | None:
    asset = _get_redis_asset(asset_id)
    if asset is None:
        return None
    updated = asset.model_copy(
        update={
            "status": payload.status,
            "reviewed_analysis": payload.reviewed_analysis,
        }
    )
    _save_redis_asset(updated)
    return updated


def _delete_redis_asset(asset_id: str) -> None:
    if _persistent_backends_disabled():
        return
    try:
        redis = _redis()
        redis.hdel(_REDIS_ASSET_HASH, asset_id)
        redis.lrem(_REDIS_ASSET_ORDER, 0, asset_id)
    except RedisError:
        pass


def _is_deleted_metadata(metadata: dict) -> bool:
    return metadata.get("deleted") is True


def _asset_requires_db_delete(asset: CopyAssetSummary) -> bool:
    return asset.storage_backend == "postgres"


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _persistent_backends_disabled() -> bool:
    return settings.app_env == "test"


def _parse_optional_non_negative_int(value: str | None) -> int | None | str:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        parsed = int(raw)
    except ValueError:
        return "author_follower_count 必须是非负整数。"
    if parsed < 0:
        return "author_follower_count 必须是非负整数。"
    return parsed
