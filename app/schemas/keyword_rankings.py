from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


IndustryStatus = Literal["active", "inactive"]


class KeywordIndustryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    status: IndustryStatus = "active"


class KeywordIndustryItem(KeywordIndustryCreate):
    id: str
    keyword_count: int = Field(ge=0)
    video_count: int = Field(ge=0)
    last_updated_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class KeywordIndustryListResponse(BaseModel):
    items: list[KeywordIndustryItem]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)


class KeywordGroupCreate(BaseModel):
    industry_id: str
    keyword: str = Field(min_length=1, max_length=200)


class KeywordGroupItem(BaseModel):
    id: str
    industry_id: str
    keyword: str
    video_count: int = Field(ge=0)
    last_updated_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class KeywordGroupListResponse(BaseModel):
    items: list[KeywordGroupItem]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)


class KeywordVideoItem(BaseModel):
    id: str
    keyword_id: str
    rank: int = Field(ge=1)
    source_text: str
    source_url: str | None = None
    author_name: str | None = None
    author_url: str | None = None
    author_follower_count: int | None = Field(default=None, ge=0)
    platform: str | None = None
    industry: str | None = None
    audience: str | None = None
    purpose: str | None = None
    style: str | None = None
    likes: int = Field(ge=0)
    comments: int = Field(ge=0)
    favorites: int = Field(ge=0)
    shares: int = Field(ge=0)
    hot_score: float = Field(ge=0)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class KeywordVideoListResponse(BaseModel):
    items: list[KeywordVideoItem]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)


class KeywordVideoImportRequest(BaseModel):
    industry_id: str
    keyword: str = Field(min_length=1, max_length=200)
    csv_text: str = Field(min_length=1)


class KeywordVideoImportRowError(BaseModel):
    row_number: int = Field(ge=1)
    message: str


class KeywordVideoImportResponse(BaseModel):
    industry_id: str
    keyword_id: str
    keyword: str
    created_count: int = Field(ge=0)
    updated_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    video_count: int = Field(ge=0)
    errors: list[KeywordVideoImportRowError] = Field(default_factory=list)


class KeywordCrawlerRequest(BaseModel):
    keyword: str = Field(min_length=1, max_length=200)
    min_likes: int = Field(default=1000, ge=0)
    max_videos: int = Field(default=50, ge=1, le=200)
    industry_id: str | None = None
