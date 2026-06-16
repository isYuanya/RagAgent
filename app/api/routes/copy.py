from fastapi import APIRouter, HTTPException, Query

from app.schemas.copy import (
    CopyAnalysisRequest,
    CopyAnalysisResponse,
    CopyAssetListResponse,
    CopyAssetReviewRequest,
    CopyAssetSummary,
    CopyImportRequest,
)
from app.schemas.task import TaskResponse
from app.services.copy_assets import (
    get_copy_asset,
    list_copy_assets,
    review_copy_asset,
)
from app.workers.import_queue import enqueue_copy_import, enqueue_text_import
from app.workflows.copy_analysis import run_analysis_workflow

router = APIRouter()


@router.post("/analyze", response_model=CopyAnalysisResponse)
def analyze(payload: CopyAnalysisRequest) -> CopyAnalysisResponse:
    try:
        return run_analysis_workflow(payload)
    except RuntimeError as exc:
        raise _llm_http_error(exc) from exc


@router.post("/import", response_model=TaskResponse)
def import_assets(payload: CopyImportRequest) -> TaskResponse:
    if payload.text is not None:
        return enqueue_text_import(payload.text)
    return enqueue_copy_import(payload.csv_text or "")


@router.get("/assets", response_model=CopyAssetListResponse)
def list_assets(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = None,
    industry: str | None = None,
    platform: str | None = None,
) -> CopyAssetListResponse:
    return list_copy_assets(
        page=page,
        page_size=page_size,
        status=status,
        industry=industry,
        platform=platform,
    )


@router.get("/assets/{asset_id}", response_model=CopyAssetSummary)
def get_asset(asset_id: str) -> CopyAssetSummary:
    asset = get_copy_asset(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Copy asset not found")
    return asset


@router.patch("/assets/{asset_id}/review", response_model=CopyAssetSummary)
def review_asset(asset_id: str, payload: CopyAssetReviewRequest) -> CopyAssetSummary:
    asset = review_copy_asset(asset_id, payload)
    if asset is None:
        raise HTTPException(status_code=404, detail="Copy asset not found")
    return asset


def _llm_http_error(exc: RuntimeError) -> HTTPException:
    status_code = 503 if "OPENAI_API_KEY" in str(exc) or "LLM call failed" in str(exc) else 502
    return HTTPException(status_code=status_code, detail=str(exc))
