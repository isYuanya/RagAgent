from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.copy import CopyAnalysisResponse, CopyAssetSummary
from app.schemas.copy import BulkOperationResponse


SourceType = Literal["raw_copy", "analysis"]


class SourceReference(BaseModel):
    source_type: SourceType
    source_id: str
    source_display: str | None = None


class KnowledgeCollectionCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeCollectionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    description: str | None = None
    metadata: dict[str, Any] | None = None


class KnowledgeCollection(KnowledgeCollectionCreate):
    id: str


class KnowledgeCollectionListResponse(BaseModel):
    items: list[KnowledgeCollection]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)


class RawCopyCreate(BaseModel):
    source_text: str = Field(min_length=1)
    source_url: str | None = None
    author_name: str | None = None
    author_url: str | None = None
    author_follower_count: int | None = Field(default=None, ge=0)
    platform: str | None = None
    industry: str | None = None
    audience: str | None = None
    purpose: str | None = None
    style: str | None = None
    metrics: dict[str, int] = Field(default_factory=dict)
    collection_ids: list[str] = Field(default_factory=list)


class RawCopyUpdate(BaseModel):
    source_text: str | None = Field(default=None, min_length=1)
    source_url: str | None = None
    author_name: str | None = None
    author_url: str | None = None
    author_follower_count: int | None = Field(default=None, ge=0)
    platform: str | None = None
    industry: str | None = None
    audience: str | None = None
    purpose: str | None = None
    style: str | None = None
    metrics: dict[str, int] | None = None
    collection_ids: list[str] | None = None


class RawCopySummary(CopyAssetSummary):
    collection_ids: list[str] = Field(default_factory=list)
    collections: list[KnowledgeCollection] = Field(default_factory=list)


class RawCopyListResponse(BaseModel):
    items: list[RawCopySummary]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)


class AnalysisCreate(BaseModel):
    raw_copy_id: str
    auto_analysis: CopyAnalysisResponse | None = None
    reviewed_analysis: CopyAnalysisResponse | None = None
    status: str = Field(default="pending_review", pattern="^(pending_review|approved|rejected)$")


class AnalysisUpdate(BaseModel):
    auto_analysis: CopyAnalysisResponse | None = None
    reviewed_analysis: CopyAnalysisResponse | None = None
    status: str | None = Field(default=None, pattern="^(pending_review|approved|rejected)$")


class AnalysisSummary(BaseModel):
    id: str
    raw_copy_id: str
    auto_analysis: CopyAnalysisResponse | None = None
    reviewed_analysis: CopyAnalysisResponse | None = None
    status: str


class AnalysisListResponse(BaseModel):
    items: list[AnalysisSummary]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)


class TemplateCreate(BaseModel):
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    structure: list[str] = Field(default_factory=list)
    suitable_scenarios: list[str] = Field(default_factory=list)
    source: SourceReference | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TemplateUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    content: str | None = Field(default=None, min_length=1)
    structure: list[str] | None = None
    suitable_scenarios: list[str] | None = None
    source: SourceReference | None = None
    metadata: dict[str, Any] | None = None


class TemplateItem(TemplateCreate):
    id: str


class FragmentCreate(BaseModel):
    source_copy_id: str
    analysis_id: str | None = None
    sequence_order: int = Field(ge=0)
    previous_fragment: str | None = None
    next_fragment: str | None = None
    before_context: str | None = None
    after_context: str | None = None
    fragment_text: str = Field(min_length=1)
    fragment_role: str = Field(min_length=1)
    position: str = Field(min_length=1)
    industry: str | None = None
    platform: str | None = None
    purpose: str | None = None
    audience: str | None = None
    source_quality: Literal["unknown", "low", "medium", "high"] = "unknown"
    risk_level: Literal["low", "medium", "high"] = "low"
    status: Literal["pending_review", "approved", "rejected"] = "pending_review"
    confidence: float = Field(default=0, ge=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class FragmentUpdate(BaseModel):
    source_copy_id: str | None = None
    analysis_id: str | None = None
    sequence_order: int | None = Field(default=None, ge=0)
    previous_fragment: str | None = None
    next_fragment: str | None = None
    before_context: str | None = None
    after_context: str | None = None
    fragment_text: str | None = Field(default=None, min_length=1)
    fragment_role: str | None = Field(default=None, min_length=1)
    position: str | None = Field(default=None, min_length=1)
    industry: str | None = None
    platform: str | None = None
    purpose: str | None = None
    audience: str | None = None
    source_quality: Literal["unknown", "low", "medium", "high"] | None = None
    risk_level: Literal["low", "medium", "high"] | None = None
    status: Literal["pending_review", "approved", "rejected"] | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    metadata: dict[str, Any] | None = None


class FragmentItem(FragmentCreate):
    id: str


class FragmentExtractionResult(BaseModel):
    source_copy_id: str
    status: Literal["created", "skipped", "failed"]
    fragment_count: int = Field(default=0, ge=0)
    message: str | None = None


class FragmentExtractionBatchResponse(BaseModel):
    items: list[FragmentExtractionResult]
    processed_count: int = Field(ge=0)
    created_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)


class KnowledgeItemListResponse(BaseModel):
    items: list[TemplateItem | FragmentItem]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)


class KnowledgeStatsResponse(BaseModel):
    collections: int = Field(ge=0)
    raw_copies: int = Field(ge=0)
    analyses: int = Field(ge=0)
    templates: int = Field(ge=0)
    fragments: int = Field(ge=0)


class RawCopyBulkDeleteRequest(BaseModel):
    confirm: bool = False
    collection_id: str | None = None
    status: Literal["pending_review", "approved", "rejected"] | None = None
    industry: str | None = None
    platform: str | None = None
    raw_copy_ids: list[str] | None = None


class KnowledgeBulkOperationResponse(BulkOperationResponse):
    pass
