from fastapi import APIRouter, HTTPException, Query

from app.schemas.copy import (
    BulkOperationResponse,
    CopyAnalysisRequest,
    CopyAnalysisResponse,
    CopyAssetBulkDeleteRequest,
    CopyAssetListResponse,
    CopyAssetReviewRequest,
    CopyAssetSummary,
    CopyImportRequest,
)
from app.schemas.task import TaskResponse
from app.services.copy_assets import (
    bulk_delete_copy_assets,
    delete_copy_asset,
    get_copy_asset,
    list_copy_assets,
    review_copy_asset,
)
from app.services.fragment_extraction import extract_fragments_for_asset_id
from app.services import knowledge
from app.services.knowledge_sync import sync_asset_analysis_to_knowledge
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
        return enqueue_text_import(payload.text, payload.collection_ids)
    return enqueue_copy_import(payload.csv_text or "", payload.collection_ids)


@router.get("/assets", response_model=CopyAssetListResponse)
def list_assets(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = None,
    industry: str | None = None,
    platform: str | None = None,
    collection_id: str | None = None,
) -> CopyAssetListResponse:
    return list_copy_assets(
        page=page,
        page_size=page_size,
        status=status,
        industry=industry,
        platform=platform,
        collection_id=collection_id,
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
    sync_asset_analysis_to_knowledge(asset)
    if asset.status == "approved":
        extract_fragments_for_asset_id(asset.id)
    return asset


@router.delete("/assets/{asset_id}", status_code=204)
def delete_asset(asset_id: str) -> None:
    result = delete_copy_asset(asset_id)
    if result == "not_found":
        raise HTTPException(status_code=404, detail="Copy asset not found")
    if result == "conflict":
        raise HTTPException(status_code=409, detail="Only pending_review assets can be deleted")
    if result == "unavailable":
        raise HTTPException(status_code=503, detail="Database is unavailable; copy asset was not deleted")
    knowledge.cleanup_source_references(asset_id)


@router.post("/assets/bulk-delete", response_model=BulkOperationResponse)
def bulk_delete_assets(payload: CopyAssetBulkDeleteRequest) -> BulkOperationResponse:
    result = bulk_delete_copy_assets(payload)
    for asset_id in result.item_ids:
        knowledge.cleanup_source_references(asset_id)
    return result


def _llm_http_error(exc: RuntimeError) -> HTTPException:
    status_code = 503 if "OPENAI_API_KEY" in str(exc) or "LLM call failed" in str(exc) else 502
    return HTTPException(status_code=status_code, detail=str(exc))
