from fastapi import APIRouter, HTTPException, Query

from app.schemas.smart_composition import (
    SmartCompositionBriefPrefillRequest,
    SmartCompositionBriefPrefillResponse,
    SmartCompositionOptions,
    SmartCompositionRunCreate,
    SmartCompositionRunDetail,
    SmartCompositionRunListResponse,
)
from app.services import smart_composition

router = APIRouter()


def _page_query(default: int = 1) -> int:
    return Query(default=default, ge=1)


def _page_size_query(default: int = 20) -> int:
    return Query(default=default, ge=1, le=100)


@router.get("/options", response_model=SmartCompositionOptions)
def get_options() -> SmartCompositionOptions:
    return smart_composition.get_options()


@router.post("/brief-prefill", response_model=SmartCompositionBriefPrefillResponse)
def prefill_brief(
    payload: SmartCompositionBriefPrefillRequest,
) -> SmartCompositionBriefPrefillResponse:
    try:
        return smart_composition.prefill_brief(payload)
    except smart_composition.SmartCompositionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@router.post("/runs", response_model=SmartCompositionRunDetail)
def create_run(payload: SmartCompositionRunCreate) -> SmartCompositionRunDetail:
    try:
        return smart_composition.create_run(payload)
    except smart_composition.SmartCompositionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@router.get("/runs", response_model=SmartCompositionRunListResponse)
def list_runs(
    page: int = _page_query(),
    page_size: int = _page_size_query(),
) -> SmartCompositionRunListResponse:
    return smart_composition.list_runs(page=page, page_size=page_size)


@router.get("/runs/{run_id}", response_model=SmartCompositionRunDetail)
def get_run(run_id: str) -> SmartCompositionRunDetail:
    item = smart_composition.get_run(run_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Smart composition run not found")
    return item
