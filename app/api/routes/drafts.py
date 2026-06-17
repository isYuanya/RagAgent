from fastapi import APIRouter, HTTPException, Query

from app.schemas.draft import (
    DraftCreate,
    DraftDetail,
    DraftItemCreate,
    DraftItemReorderRequest,
    DraftItemUpdate,
    DraftListResponse,
    DraftStatus,
    DraftUpdate,
    DraftVersionCreate,
    DraftVersionDetail,
    DraftVersionSummary,
)
from app.services import drafts

router = APIRouter()


def _page_query(default: int = 1) -> int:
    return Query(default=default, ge=1)


def _page_size_query(default: int = 20) -> int:
    return Query(default=default, ge=1, le=100)


@router.get("", response_model=DraftListResponse)
def list_drafts(
    page: int = _page_query(),
    page_size: int = _page_size_query(),
    status: DraftStatus | None = "draft",
):
    return drafts.list_drafts(page=page, page_size=page_size, status=status)


@router.post("", response_model=DraftDetail)
def create_draft(payload: DraftCreate):
    return drafts.create_draft(payload)


@router.get("/{draft_id}", response_model=DraftDetail)
def get_draft(draft_id: str):
    item = drafts.get_draft(draft_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    return item


@router.patch("/{draft_id}", response_model=DraftDetail)
def update_draft(draft_id: str, payload: DraftUpdate):
    item = drafts.update_draft(draft_id, payload)
    if item is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    return item


@router.delete("/{draft_id}", status_code=204)
def archive_draft(draft_id: str):
    if not drafts.archive_draft(draft_id):
        raise HTTPException(status_code=404, detail="Draft not found")


@router.post("/{draft_id}/items", response_model=DraftDetail)
def add_draft_item(draft_id: str, payload: DraftItemCreate):
    try:
        return drafts.add_draft_item(draft_id, payload)
    except drafts.DraftNotFoundError:
        raise HTTPException(status_code=404, detail="Draft not found") from None
    except drafts.SourceFragmentNotFoundError:
        raise HTTPException(status_code=404, detail="Source fragment not found") from None


@router.patch("/{draft_id}/items/reorder", response_model=DraftDetail)
def reorder_draft_items(draft_id: str, payload: DraftItemReorderRequest):
    try:
        return drafts.reorder_draft_items(draft_id, payload)
    except drafts.DraftNotFoundError:
        raise HTTPException(status_code=404, detail="Draft not found") from None
    except drafts.DraftItemNotFoundError:
        raise HTTPException(status_code=404, detail="Draft item not found") from None


@router.patch("/{draft_id}/items/{item_id}", response_model=DraftDetail)
def update_draft_item(draft_id: str, item_id: str, payload: DraftItemUpdate):
    try:
        return drafts.update_draft_item(draft_id, item_id, payload)
    except drafts.DraftNotFoundError:
        raise HTTPException(status_code=404, detail="Draft not found") from None
    except drafts.DraftItemNotFoundError:
        raise HTTPException(status_code=404, detail="Draft item not found") from None


@router.delete("/{draft_id}/items/{item_id}", status_code=204)
def delete_draft_item(draft_id: str, item_id: str):
    try:
        drafts.delete_draft_item(draft_id, item_id)
    except drafts.DraftNotFoundError:
        raise HTTPException(status_code=404, detail="Draft not found") from None
    except drafts.DraftItemNotFoundError:
        raise HTTPException(status_code=404, detail="Draft item not found") from None


@router.post("/{draft_id}/versions", response_model=DraftVersionDetail)
def create_draft_version(draft_id: str, payload: DraftVersionCreate):
    try:
        return drafts.create_draft_version(draft_id, payload)
    except drafts.DraftNotFoundError:
        raise HTTPException(status_code=404, detail="Draft not found") from None


@router.get("/{draft_id}/versions", response_model=list[DraftVersionSummary])
def list_draft_versions(draft_id: str):
    try:
        return drafts.list_draft_versions(draft_id)
    except drafts.DraftNotFoundError:
        raise HTTPException(status_code=404, detail="Draft not found") from None


@router.get("/{draft_id}/versions/{version_id}", response_model=DraftVersionDetail)
def get_draft_version(draft_id: str, version_id: str):
    try:
        item = drafts.get_draft_version(draft_id, version_id)
    except drafts.DraftNotFoundError:
        raise HTTPException(status_code=404, detail="Draft not found") from None
    if item is None:
        raise HTTPException(status_code=404, detail="Draft version not found")
    return item
