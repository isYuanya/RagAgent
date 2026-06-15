import csv
from io import StringIO
from uuid import uuid4

from app.schemas.copy import (
    CopyAnalysisRequest,
    CopyAssetListResponse,
    CopyAssetReviewRequest,
    CopyAssetSummary,
    CopyImportResponse,
    CopyImportRowError,
)
from app.services.copy_analysis import analyze_copy


MAX_SYNC_IMPORT_ROWS = 50
METRIC_FIELDS = ("likes", "comments", "favorites", "shares")

_copy_assets: dict[str, CopyAssetSummary] = {}


def reset_copy_asset_store() -> None:
    _copy_assets.clear()


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
        source_text = (row.get("source_text") or "").strip()
        if not source_text:
            errors.append(CopyImportRowError(row_number=index, message="source_text 不能为空。"))
            continue

        metric_result = _parse_metrics(row)
        if isinstance(metric_result, str):
            errors.append(CopyImportRowError(row_number=index, message=metric_result))
            continue

        payload = CopyAnalysisRequest(
            source_text=source_text,
            source_url=_blank_to_none(row.get("source_url")),
            platform=_blank_to_none(row.get("platform")),
            industry=_blank_to_none(row.get("industry")),
            audience=_blank_to_none(row.get("audience")),
            purpose=_blank_to_none(row.get("purpose")),
            style=_blank_to_none(row.get("style")),
            metrics=metric_result,
        )
        analysis = analyze_copy(payload)
        asset = CopyAssetSummary(
            id=str(uuid4()),
            source_text=source_text,
            source_url=payload.source_url,
            platform=payload.platform,
            industry=payload.industry,
            audience=payload.audience,
            purpose=payload.purpose,
            style=payload.style,
            metrics=metric_result,
            status="pending_review",
            auto_analysis=analysis,
            reviewed_analysis=None,
        )
        _copy_assets[asset.id] = asset
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
    return _copy_assets.get(asset_id)


def review_copy_asset(asset_id: str, payload: CopyAssetReviewRequest) -> CopyAssetSummary | None:
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


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
