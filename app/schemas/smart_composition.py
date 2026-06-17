from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.composition import (
    AutoCompositionBrief,
    AutoCompositionResult,
    CompositionCandidate,
)
from app.schemas.diagnostic import CopyDiagnosisResult, RewriteCandidate
from app.schemas.draft import DraftDetail, DraftVersionDetail
from app.schemas.knowledge import KnowledgeCollection
from app.schemas.recommendation import ReferenceFragmentSummary


SmartCompositionMode = Literal["auto", "guided"]
SmartCompositionStatus = Literal["pending", "running", "waiting_for_user", "finished", "failed"]
SmartCompositionStepStatus = Literal["pending", "running", "completed", "waiting_for_user", "failed"]
SmartCompositionStepId = Literal[
    "brief_prefill",
    "knowledge_retrieval",
    "composition_generation",
    "composition_selection",
    "initial_draft_save",
    "diagnosis",
    "rewrite_selection",
    "final_draft_save",
]


class SmartCompositionBrief(AutoCompositionBrief):
    collection_ids: list[str] = Field(default_factory=list)
    extra_notes: str | None = None


class SmartCompositionOption(BaseModel):
    value: str
    label: str
    description: str | None = None


class SmartCompositionOptions(BaseModel):
    collections: list[KnowledgeCollection] = Field(default_factory=list)
    platforms: list[SmartCompositionOption] = Field(default_factory=list)
    purposes: list[SmartCompositionOption] = Field(default_factory=list)
    audiences: list[SmartCompositionOption] = Field(default_factory=list)
    styles: list[SmartCompositionOption] = Field(default_factory=list)


class SmartCompositionBriefPrefillRequest(BaseModel):
    text: str = Field(min_length=1)


class SmartCompositionBriefPrefillResponse(BaseModel):
    brief: SmartCompositionBrief
    confidence: float = Field(ge=0, le=1)
    notes: list[str] = Field(default_factory=list)
    model: str | None = None


class SmartCompositionStep(BaseModel):
    step_id: SmartCompositionStepId
    label: str
    order: int = Field(ge=1)
    percent: int = Field(ge=0, le=100)
    status: SmartCompositionStepStatus = "pending"
    model: str | None = None
    message: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SmartCompositionSelection(BaseModel):
    selected_id: str
    method: Literal["llm_judge", "rule_fallback", "user"]
    score_signals: dict[str, float | int | str] = Field(default_factory=dict)
    judge_model: str | None = None
    reason: str | None = None
    fallback_reason: str | None = None


class SmartCompositionResult(BaseModel):
    composition: AutoCompositionResult | None = None
    diagnosis: CopyDiagnosisResult | None = None
    selected_candidate: CompositionCandidate | None = None
    selected_rewrite: RewriteCandidate | None = None
    composition_selection: SmartCompositionSelection | None = None
    rewrite_selection: SmartCompositionSelection | None = None
    materials: list[ReferenceFragmentSummary] = Field(default_factory=list)
    draft: DraftDetail | None = None
    initial_version: DraftVersionDetail | None = None
    final_version: DraftVersionDetail | None = None


class SmartCompositionRunCreate(BaseModel):
    mode: SmartCompositionMode = "auto"
    brief: SmartCompositionBrief
    metadata: dict[str, Any] = Field(default_factory=dict)


class SmartCompositionRunSummary(BaseModel):
    id: str
    mode: SmartCompositionMode
    status: SmartCompositionStatus
    brief: SmartCompositionBrief
    draft_id: str | None = None
    initial_version_id: str | None = None
    final_version_id: str | None = None
    selected_candidate_id: str | None = None
    selected_rewrite_id: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class SmartCompositionRunDetail(SmartCompositionRunSummary):
    timeline: list[SmartCompositionStep] = Field(default_factory=list)
    collection_ids: list[str] = Field(default_factory=list)
    material_ids: list[str] = Field(default_factory=list)
    result: SmartCompositionResult = Field(default_factory=SmartCompositionResult)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SmartCompositionRunListResponse(BaseModel):
    items: list[SmartCompositionRunSummary]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
