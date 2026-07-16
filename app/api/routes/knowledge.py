from fastapi import APIRouter, HTTPException, Query

from app.schemas.knowledge import (
    AnalysisCreate,
    AnalysisListResponse,
    AnalysisSummary,
    AnalysisUpdate,
    FragmentCreate,
    FragmentExtractionBatchResponse,
    FragmentExtractionResult,
    FragmentItem,
    FragmentUpdate,
    KnowledgeBulkOperationResponse,
    KnowledgeCollection,
    KnowledgeCollectionCreate,
    KnowledgeCollectionListResponse,
    KnowledgeCollectionUpdate,
    KnowledgeItemListResponse,
    KnowledgeStatsResponse,
    RawCopyCreate,
    RawCopyBulkDeleteRequest,
    RawCopyListResponse,
    RawCopySummary,
    RawCopyUpdate,
    TemplateCreate,
    TemplateItem,
    TemplateUpdate,
)
from app.services import knowledge
from app.services.fragment_extraction import (
    extract_fragments_for_approved_assets,
    extract_fragments_for_asset_id,
)

router = APIRouter()


def _page_query(default: int = 1) -> int:
    return Query(default=default, ge=1)


def _page_size_query(default: int = 20) -> int:
    return Query(default=default, ge=1, le=100)


@router.get("/stats", response_model=KnowledgeStatsResponse)
def get_knowledge_stats():
    return knowledge.get_knowledge_stats()


@router.get("/collections", response_model=KnowledgeCollectionListResponse)
def list_collections(page: int = _page_query(), page_size: int = _page_size_query()):
    return knowledge.list_collections(page=page, page_size=page_size)


@router.post("/collections", response_model=KnowledgeCollection)
def create_collection(payload: KnowledgeCollectionCreate):
    return knowledge.create_collection(payload)


@router.get("/collections/{collection_id}", response_model=KnowledgeCollection)
def get_collection(collection_id: str):
    item = knowledge.get_collection(collection_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Knowledge collection not found")
    return item


@router.patch("/collections/{collection_id}", response_model=KnowledgeCollection)
def update_collection(collection_id: str, payload: KnowledgeCollectionUpdate):
    item = knowledge.update_collection(collection_id, payload)
    if item is None:
        raise HTTPException(status_code=404, detail="Knowledge collection not found")
    return item


@router.delete("/collections/{collection_id}", status_code=204)
def delete_collection(collection_id: str):
    if not knowledge.delete_collection(collection_id):
        raise HTTPException(status_code=404, detail="Knowledge collection not found")


@router.get("/raw-copies", response_model=RawCopyListResponse)
def list_raw_copies(
    page: int = _page_query(),
    page_size: int = _page_size_query(),
    collection_id: str | None = None,
):
    return knowledge.list_raw_copies(page=page, page_size=page_size, collection_id=collection_id)


@router.post("/raw-copies", response_model=RawCopySummary)
def create_raw_copy(payload: RawCopyCreate):
    return knowledge.create_raw_copy(payload)


@router.get("/raw-copies/{raw_copy_id}", response_model=RawCopySummary)
def get_raw_copy(raw_copy_id: str):
    item = knowledge.get_raw_copy(raw_copy_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Raw copy not found")
    return item


@router.patch("/raw-copies/{raw_copy_id}", response_model=RawCopySummary)
def update_raw_copy(raw_copy_id: str, payload: RawCopyUpdate):
    item = knowledge.update_raw_copy(raw_copy_id, payload)
    if item is None:
        raise HTTPException(status_code=404, detail="Raw copy not found")
    return item


@router.delete("/raw-copies/{raw_copy_id}", status_code=204)
def delete_raw_copy(raw_copy_id: str):
    result = knowledge.delete_raw_copy(raw_copy_id)
    if result == "not_found":
        raise HTTPException(status_code=404, detail="Raw copy not found")
    if result == "unavailable":
        raise HTTPException(status_code=503, detail="Database is unavailable; raw copy was not deleted")


@router.post("/raw-copies/bulk-delete", response_model=KnowledgeBulkOperationResponse)
def bulk_delete_raw_copies(payload: RawCopyBulkDeleteRequest):
    return knowledge.bulk_delete_raw_copies(payload)


@router.post("/raw-copies/bulk-delete/preview", response_model=KnowledgeBulkOperationResponse)
def preview_bulk_delete_raw_copies(payload: RawCopyBulkDeleteRequest):
    return knowledge.preview_bulk_delete_raw_copies(payload)


@router.get("/analyses", response_model=AnalysisListResponse)
def list_analyses(page: int = _page_query(), page_size: int = _page_size_query()):
    return knowledge.list_analyses(page=page, page_size=page_size)


@router.post("/analyses", response_model=AnalysisSummary)
def create_analysis(payload: AnalysisCreate):
    return knowledge.create_analysis(payload)


@router.get("/analyses/{analysis_id}", response_model=AnalysisSummary)
def get_analysis(analysis_id: str):
    item = knowledge.get_analysis(analysis_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return item


@router.patch("/analyses/{analysis_id}", response_model=AnalysisSummary)
def update_analysis(analysis_id: str, payload: AnalysisUpdate):
    item = knowledge.update_analysis(analysis_id, payload)
    if item is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return item


@router.delete("/analyses/{analysis_id}", status_code=204)
def delete_analysis(analysis_id: str):
    if not knowledge.delete_analysis(analysis_id):
        raise HTTPException(status_code=404, detail="Analysis not found")


@router.get("/templates", response_model=KnowledgeItemListResponse)
def list_templates(page: int = _page_query(), page_size: int = _page_size_query()):
    return knowledge.list_templates(page=page, page_size=page_size)


@router.post("/templates", response_model=TemplateItem)
def create_template(payload: TemplateCreate):
    return knowledge.create_template(payload)


@router.get("/templates/{item_id}", response_model=TemplateItem)
def get_template(item_id: str):
    return _get_or_404(knowledge.get_template(item_id), "Template not found")


@router.patch("/templates/{item_id}", response_model=TemplateItem)
def update_template(item_id: str, payload: TemplateUpdate):
    return _get_or_404(knowledge.update_template(item_id, payload), "Template not found")


@router.delete("/templates/{item_id}", status_code=204)
def delete_template(item_id: str):
    if not knowledge.delete_template(item_id):
        raise HTTPException(status_code=404, detail="Template not found")


@router.get("/fragments", response_model=KnowledgeItemListResponse)
def list_fragments(
    page: int = _page_query(),
    page_size: int = _page_size_query(),
    source_copy_id: str | None = None,
    fragment_role: str | None = None,
    position: str | None = None,
    industry: str | None = None,
    status: str | None = None,
    platform: str | None = None,
    purpose: str | None = None,
    audience: str | None = None,
    risk_level: str | None = None,
    q: str | None = None,
):
    return knowledge.list_fragments(
        page=page,
        page_size=page_size,
        source_copy_id=source_copy_id,
        fragment_role=fragment_role,
        position=position,
        industry=industry,
        status=status,
        platform=platform,
        purpose=purpose,
        audience=audience,
        risk_level=risk_level,
        q=q,
    )


@router.post("/fragments", response_model=FragmentItem)
def create_fragment(payload: FragmentCreate):
    return knowledge.create_fragment(payload)


@router.post("/fragments/extract-approved", response_model=FragmentExtractionBatchResponse)
def extract_approved_fragments(limit: int = Query(default=50, ge=1, le=100)):
    return extract_fragments_for_approved_assets(limit=limit)


@router.post("/fragments/extract/{source_copy_id}", response_model=FragmentExtractionResult)
def extract_fragments(source_copy_id: str):
    return extract_fragments_for_asset_id(source_copy_id)


@router.get("/fragments/{item_id}", response_model=FragmentItem)
def get_fragment(item_id: str):
    return _get_or_404(knowledge.get_fragment(item_id), "Fragment not found")


@router.patch("/fragments/{item_id}", response_model=FragmentItem)
def update_fragment(item_id: str, payload: FragmentUpdate):
    return _get_or_404(knowledge.update_fragment(item_id, payload), "Fragment not found")


@router.delete("/fragments/{item_id}", status_code=204)
def delete_fragment(item_id: str):
    if not knowledge.delete_fragment(item_id):
        raise HTTPException(status_code=404, detail="Fragment not found")


def _get_or_404(item, message: str):
    if item is None:
        raise HTTPException(status_code=404, detail=message)
    return item
