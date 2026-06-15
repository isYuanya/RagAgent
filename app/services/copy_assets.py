import csv
import json
from io import StringIO
from uuid import uuid4

from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.copy import CopyAnalysis, CopySource
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
_db_available: bool | None = None
_REDIS_ASSET_HASH = "ragagent:copy_assets"
_REDIS_ASSET_ORDER = "ragagent:copy_asset_order"


def reset_copy_asset_store() -> None:
    _copy_assets.clear()
    try:
        redis = _redis()
        redis.delete(_REDIS_ASSET_HASH, _REDIS_ASSET_ORDER)
    except RedisError:
        pass


def import_copy_assets(csv_text: str) -> CopyImportResponse:
    reader = csv.DictReader(StringIO(csv_text))
    errors: list[CopyImportRowError] = []
    assets: list[CopyAssetSummary] = []

    if not reader.fieldnames or "source_text" not in reader.fieldnames:
        return CopyImportResponse(
            imported_count=0,
            failed_count=1,
            assets=[],
            errors=[CopyImportRowError(row_number=1, message="CSV 必须包含 source_text 表头。")],
        )

    rows = list(reader)
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
) -> CopyAssetListResponse:
    db_response = _list_db_assets(
        page=page,
        page_size=page_size,
        status=status,
        industry=industry,
        platform=platform,
    )
    redis_response = _list_redis_assets(
        page=page,
        page_size=page_size,
        status=status,
        industry=industry,
        platform=platform,
    )
    if db_response is not None and db_response.total > 0:
        return db_response
    if redis_response is not None:
        return redis_response
    if db_response is not None:
        return db_response

    filtered = [
        asset
        for asset in _copy_assets.values()
        if (status is None or asset.status == status)
        and (industry is None or asset.industry == industry)
        and (platform is None or asset.platform == platform)
    ]
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
        metrics=metric_result,
    )


def create_copy_asset(
    payload: CopyAnalysisRequest, analysis: CopyAnalysisResponse | None
) -> CopyAssetSummary:
    asset_id = str(uuid4())
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
        metrics=payload.metrics or {},
        status="pending_review",
        auto_analysis=analysis,
        reviewed_analysis=None,
    )
    _copy_assets[asset.id] = asset
    _save_redis_asset(asset)
    _persist_asset_to_db(asset)
    return asset


def _persist_asset_to_db(asset: CopyAssetSummary) -> None:
    if _db_available is False:
        return
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
        db.commit()
        _mark_db_available(True)
    except SQLAlchemyError:
        _mark_db_available(False)
        db.rollback()
    finally:
        db.close()


def _list_db_assets(
    *,
    page: int,
    page_size: int,
    status: str | None,
    industry: str | None,
    platform: str | None,
) -> CopyAssetListResponse | None:
    if _db_available is False:
        return None
    db = SessionLocal()
    try:
        sources = db.scalars(select(CopySource).order_by(CopySource.created_at.desc())).all()
        assets = [_source_to_asset(db, source) for source in sources]
        filtered = [
            asset
            for asset in assets
            if (status is None or asset.status == status)
            and (industry is None or asset.industry == industry)
            and (platform is None or asset.platform == platform)
        ]
        start = (page - 1) * page_size
        return CopyAssetListResponse(
            items=filtered[start : start + page_size],
            page=page,
            page_size=page_size,
            total=len(filtered),
        )
    except SQLAlchemyError:
        _mark_db_available(False)
        return None
    finally:
        db.close()


def _get_db_asset(asset_id: str) -> CopyAssetSummary | None:
    if _db_available is False:
        return None
    db = SessionLocal()
    try:
        source = db.get(CopySource, asset_id)
        if source is None:
            return None
        return _source_to_asset(db, source)
    except SQLAlchemyError:
        _mark_db_available(False)
        return None
    finally:
        db.close()


def _review_db_asset(asset_id: str, payload: CopyAssetReviewRequest) -> CopyAssetSummary | None:
    if _db_available is False:
        return None
    db = SessionLocal()
    try:
        source = db.get(CopySource, asset_id)
        if source is None:
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
        metrics=metadata.get("metrics") or {},
        status=metadata.get("status") or "pending_review",
        auto_analysis=auto_analysis,
        reviewed_analysis=CopyAnalysisResponse.model_validate(reviewed_raw)
        if isinstance(reviewed_raw, dict)
        else None,
    )


def _asset_metadata(asset: CopyAssetSummary) -> dict:
    return {
        "platform": asset.platform,
        "industry": asset.industry,
        "audience": asset.audience,
        "purpose": asset.purpose,
        "style": asset.style,
        "author_name": asset.author_name,
        "author_url": asset.author_url,
        "author_follower_count": asset.author_follower_count,
        "metrics": asset.metrics,
        "status": asset.status,
        "reviewed_analysis": asset.reviewed_analysis.model_dump(mode="json")
        if asset.reviewed_analysis
        else None,
    }


def _mark_db_available(value: bool) -> None:
    global _db_available
    _db_available = value


def _redis() -> Redis:
    return Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1)


def _save_redis_asset(asset: CopyAssetSummary) -> None:
    try:
        redis = _redis()
        redis.hset(_REDIS_ASSET_HASH, asset.id, json.dumps(asset.model_dump(mode="json"), ensure_ascii=False))
        if redis.lpos(_REDIS_ASSET_ORDER, asset.id) is None:
            redis.lpush(_REDIS_ASSET_ORDER, asset.id)
    except RedisError:
        pass


def _get_redis_asset(asset_id: str) -> CopyAssetSummary | None:
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
) -> CopyAssetListResponse | None:
    try:
        redis = _redis()
        ids = [item.decode("utf-8") for item in redis.lrange(_REDIS_ASSET_ORDER, 0, -1)]
        raw_assets = redis.hmget(_REDIS_ASSET_HASH, ids) if ids else []
    except RedisError:
        return None

    assets = [
        CopyAssetSummary.model_validate(json.loads(raw))
        for raw in raw_assets
        if raw is not None
    ]
    filtered = [
        asset
        for asset in assets
        if (status is None or asset.status == status)
        and (industry is None or asset.industry == industry)
        and (platform is None or asset.platform == platform)
    ]
    start = (page - 1) * page_size
    return CopyAssetListResponse(
        items=filtered[start : start + page_size],
        page=page,
        page_size=page_size,
        total=len(filtered),
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


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


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
