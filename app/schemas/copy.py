from pydantic import BaseModel, Field

from app.schemas.common import CopyContext, RiskWarning


class CopyAnalysisRequest(CopyContext):
    source_text: str = Field(min_length=1)
    source_url: str | None = None
    metrics: dict[str, int] | None = None


class CopyAnalysisResponse(BaseModel):
    topic: str
    target_user: str
    core_pain: str
    emotion_buttons: list[str]
    hook: str
    structure: list[str]
    expression_skills: list[str]
    reusable_template: str
    suitable_scenarios: list[str]
    risk_warnings: list[RiskWarning]
    confidence: float = Field(ge=0, le=1)
