from pydantic import BaseModel, Field

from app.schemas.common import CopyContext, RiskWarning


class GenerateRequest(CopyContext):
    product_name: str | None = None
    selling_points: list[str] = Field(default_factory=list)
    user_pains: list[str] = Field(default_factory=list)
    reference_text: str | None = None
    version_count: int = Field(default=3, ge=1, le=10)


class GeneratedVariant(BaseModel):
    title: str
    hook: str
    script: str
    comment_guide: str


class GenerateResponse(BaseModel):
    topic_direction: str
    hooks: list[str]
    script: str
    shot_suggestions: list[str]
    titles: list[str]
    comment_guides: list[str]
    variants: list[GeneratedVariant]
    risk_warnings: list[RiskWarning]
