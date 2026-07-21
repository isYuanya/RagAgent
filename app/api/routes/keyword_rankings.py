from fastapi import APIRouter, HTTPException, Query, Response, status

from app.schemas.keyword_rankings import (
    KeywordCrawlerRequest,
    KeywordGroupCreate,
    KeywordGroupItem,
    KeywordGroupListResponse,
    KeywordIndustryCreate,
    KeywordIndustryItem,
    KeywordIndustryListResponse,
    KeywordVideoImportRequest,
    KeywordVideoImportResponse,
    KeywordVideoListResponse,
)
from app.schemas.task import TaskResponse
from app.services import keyword_crawler_jobs, keyword_rankings


router = APIRouter()


def _page_query(default: int = 1) -> int:
    return Query(default=default, ge=1)


def _page_size_query(default: int = 20) -> int:
    return Query(default=default, ge=1, le=100)


@router.get("/keyword-industries", response_model=KeywordIndustryListResponse)
def list_keyword_industries(
    page: int = _page_query(),
    page_size: int = _page_size_query(),
):
    return keyword_rankings.list_industries(page=page, page_size=page_size)


@router.post("/keyword-industries", response_model=KeywordIndustryItem)
def create_keyword_industry(payload: KeywordIndustryCreate):
    try:
        return keyword_rankings.create_industry(payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/keyword-industries/{industry_id}", response_model=KeywordIndustryItem)
def get_keyword_industry(industry_id: str):
    item = keyword_rankings.get_industry(industry_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Keyword industry not found")
    return item


@router.delete("/keyword-industries/{industry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_keyword_industry(industry_id: str):
    deleted = keyword_rankings.delete_industry(industry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Keyword industry not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/keyword-industries/{industry_id}/keywords",
    response_model=KeywordGroupListResponse,
)
def list_keyword_groups(
    industry_id: str,
    page: int = _page_query(),
    page_size: int = _page_size_query(),
):
    items = keyword_rankings.list_keywords(industry_id, page=page, page_size=page_size)
    if items is None:
        raise HTTPException(status_code=404, detail="Keyword industry not found")
    return items


@router.post("/keywords", response_model=KeywordGroupItem)
def create_keyword_group(payload: KeywordGroupCreate):
    item = keyword_rankings.create_keyword(payload)
    if item is None:
        raise HTTPException(status_code=404, detail="Keyword industry not found")
    return item


@router.delete("/keywords/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_keyword_group(keyword_id: str):
    deleted = keyword_rankings.delete_keyword(keyword_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Keyword group not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/keywords/{keyword_id}/videos", response_model=KeywordVideoListResponse)
def list_keyword_videos(
    keyword_id: str,
    page: int = _page_query(),
    page_size: int = _page_size_query(default=50),
):
    items = keyword_rankings.list_videos(keyword_id, page=page, page_size=page_size)
    if items is None:
        raise HTTPException(status_code=404, detail="Keyword group not found")
    return items


@router.post("/keyword-videos/import", response_model=KeywordVideoImportResponse)
def import_keyword_videos(payload: KeywordVideoImportRequest):
    result = keyword_rankings.import_keyword_videos(payload)
    if result is None:
        raise HTTPException(status_code=404, detail="Keyword industry not found")
    return result


@router.post("/keyword-videos/crawl", response_model=TaskResponse)
def crawl_keyword_videos(payload: KeywordCrawlerRequest):
    return keyword_crawler_jobs.enqueue_keyword_crawl(payload)
