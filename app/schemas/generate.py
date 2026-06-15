from pydantic import BaseModel, Field

from app.schemas.common import CopyContext, RiskWarning


class GenerateRequest(CopyContext):
    product_name: str | None = Field(default=None, description="产品、课程、服务或IP名称。")
    selling_points: list[str] = Field(default_factory=list, description="产品卖点列表。")
    user_pains: list[str] = Field(default_factory=list, description="目标用户痛点列表。")
    reference_text: str | None = Field(default=None, description="参考文案，用于生成风格或结构参考。")
    version_count: int = Field(default=3, ge=1, le=10, description="生成版本数量，范围为1到10。")


class GeneratedVariant(BaseModel):
    title: str = Field(description="该版本的标题。")
    hook: str = Field(description="该版本的开头钩子。")
    script: str = Field(description="该版本的完整口播文案。")
    comment_guide: str = Field(description="该版本的评论区引导话术。")


class GenerateResponse(BaseModel):
    topic_direction: str = Field(description="选题方向。")
    hooks: list[str] = Field(description="开头钩子候选列表。")
    script: str = Field(description="主版本完整口播文案。")
    shot_suggestions: list[str] = Field(description="分镜建议列表。")
    titles: list[str] = Field(description="标题候选列表。")
    comment_guides: list[str] = Field(description="评论区引导候选列表。")
    variants: list[GeneratedVariant] = Field(description="多个可替换生成版本。")
    risk_warnings: list[RiskWarning] = Field(description="风险提示列表。")
