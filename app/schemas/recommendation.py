from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import RiskWarning
from app.schemas.draft import DraftDetail


class NextSentenceRecommendationRequest(BaseModel):
    draft_id: str
    candidate_count: int = Field(default=3, ge=1, le=5)
    cursor_item_id: str | None = None
    q: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReferenceFragmentSummary(BaseModel):
    id: str
    text: str
    role: str | None = None
    position: str | None = None
    source_copy_id: str | None = None
    source_display: str | None = None


class RecommendationCandidate(BaseModel):
    candidate_id: str
    text: str = Field(min_length=1)
    function: str
    reason: str
    tone: str
    suggested_order_index: int = Field(ge=0)
    risk_warnings: list[RiskWarning] = Field(default_factory=list)
    reference_fragment_ids: list[str] = Field(default_factory=list)
    reference_fragments: list[ReferenceFragmentSummary] = Field(default_factory=list)


class NextSentenceRecommendationResult(BaseModel):
    draft_id: str
    current_text: str
    next_function: str
    model: str | None = None
    candidates: list[RecommendationCandidate]
    reference_fragments: list[ReferenceFragmentSummary] = Field(default_factory=list)


class AcceptRecommendationRequest(BaseModel):
    draft_id: str
    task_id: str
    candidate_id: str
    order_index: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AcceptedRecommendationItem(BaseModel):
    id: str
    draft_id: str
    task_id: str
    candidate_id: str
    inserted_draft_item_id: str
    candidate_text: str
    function: str | None = None
    tone: str | None = None
    reason: str | None = None
    model: str | None = None
    reference_fragment_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AcceptRecommendationResponse(BaseModel):
    accepted: AcceptedRecommendationItem
    draft: DraftDetail
