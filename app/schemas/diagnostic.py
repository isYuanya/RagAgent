from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import CopyContext, RiskWarning
from app.schemas.draft import DraftDetail, DraftVersionDetail


DiagnosticLevel = Literal["weak", "fair", "strong", "risk", "high_risk"]
RewriteMode = Literal["conservative", "conversion", "compliance_safe"]


class CopyDiagnosisRequest(CopyContext):
    text: str | None = Field(default=None, min_length=1)
    draft_id: str | None = None
    constraints: list[str] = Field(default_factory=list)
    rewrite_modes: list[RewriteMode] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_text_or_draft(self) -> "CopyDiagnosisRequest":
        if not self.text and not self.draft_id:
            raise ValueError("text or draft_id is required")
        return self


class DiagnosticSource(BaseModel):
    source_type: Literal["text", "draft"]
    text: str
    draft_id: str | None = None
    platform: str | None = None
    audience: str | None = None
    purpose: str | None = None
    style: str | None = None
    industry: str | None = None


class DimensionFinding(BaseModel):
    dimension: str
    level: DiagnosticLevel
    reason: str
    suggestion: str


class SentenceIssue(BaseModel):
    text: str
    dimension: str
    level: DiagnosticLevel
    reason: str
    suggestion: str
    replacement: str


class RewriteCandidate(BaseModel):
    candidate_id: str
    mode: RewriteMode
    title: str
    text: str = Field(min_length=1)
    reason: str


class CopyDiagnosisResult(BaseModel):
    source: DiagnosticSource
    summary: str
    overall_level: DiagnosticLevel
    dimensions: list[DimensionFinding]
    sentence_issues: list[SentenceIssue] = Field(default_factory=list)
    rewrite_candidates: list[RewriteCandidate]
    risk_warnings: list[RiskWarning] = Field(default_factory=list)
    model: str | None = None


class AcceptDiagnosticRewriteRequest(BaseModel):
    draft_id: str
    task_id: str
    candidate_id: str
    label: str | None = Field(default="AI 诊断改写")
    metadata: dict[str, Any] = Field(default_factory=dict)


class AcceptedDiagnosticRewrite(BaseModel):
    draft_id: str
    task_id: str
    candidate_id: str
    rewrite_text: str
    model: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AcceptDiagnosticRewriteResponse(BaseModel):
    accepted: AcceptedDiagnosticRewrite
    draft: DraftDetail
    version: DraftVersionDetail
