from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.draft import DraftDetail
from app.schemas.recommendation import ReferenceFragmentSummary


QuoteMode = Literal["direct", "adapted", "original"]


class AutoCompositionBrief(BaseModel):
    product: str = Field(min_length=1)
    audience: str = Field(min_length=1)
    platform: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    style: str = Field(min_length=1)
    key_selling_points: list[str] = Field(min_length=1)
    constraints: str | None = None
    target_length: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("key_selling_points")
    @classmethod
    def _strip_selling_points(cls, value: list[str]) -> list[str]:
        points = [item.strip() for item in value if item.strip()]
        if not points:
            raise ValueError("key_selling_points must contain at least one non-empty item")
        return points


class CompositionItemCandidate(BaseModel):
    role: Literal["hook", "pain_point", "solution", "proof", "cta"]
    position: str
    text: str = Field(min_length=1)
    quote_mode: QuoteMode = "original"
    reference_fragment_ids: list[str] = Field(default_factory=list)
    source_copy_id: str | None = None
    reason: str = ""


class CompositionCandidate(BaseModel):
    candidate_id: str
    title: str
    strategy: str = ""
    items: list[CompositionItemCandidate] = Field(min_length=5, max_length=5)
    reference_fragment_ids: list[str] = Field(default_factory=list)


class AutoCompositionRequest(BaseModel):
    brief: AutoCompositionBrief


class AutoCompositionResult(BaseModel):
    brief: AutoCompositionBrief
    model: str | None = None
    fallback_reason: str | None = None
    candidates: list[CompositionCandidate] = Field(min_length=3, max_length=3)
    reference_fragments: list[ReferenceFragmentSummary] = Field(default_factory=list)


class AcceptCompositionRequest(BaseModel):
    task_id: str
    candidate_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AcceptedCompositionItem(BaseModel):
    id: str
    task_id: str
    candidate_id: str
    draft_id: str
    brief: AutoCompositionBrief
    candidate_title: str
    model: str | None = None
    reference_fragment_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AcceptCompositionResponse(BaseModel):
    accepted: AcceptedCompositionItem
    draft: DraftDetail
