from pydantic import BaseModel, Field

from app.schemas.common import CopyContext, RiskWarning


class CopyAnalysisRequest(CopyContext):
    source_text: str = Field(min_length=1, description="待拆解的原始文案，不能为空。")
    source_url: str | None = Field(default=None, description="文案来源链接，可为空。")
    metrics: dict[str, int] | None = Field(
        default=None,
        description="文案表现数据，例如 likes、comments、favorites、shares。",
    )


class CopyAnalysisResponse(BaseModel):
    topic: str = Field(description="文案主题，这条内容主要讲什么。")
    target_user: str = Field(description="目标用户，内容说给谁听。")
    core_pain: str = Field(description="核心痛点，用户为什么会停留或行动。")
    emotion_buttons: list[str] = Field(description="情绪按钮，例如好奇、共鸣、危机感。")
    hook: str = Field(description="开头钩子，用于抓住注意力的一句话。")
    structure: list[str] = Field(description="内容结构步骤，例如提出问题、放大痛点、给出观点。")
    expression_skills: list[str] = Field(description="表达技巧，例如短句、反问、对比、数字化表达。")
    reusable_template: str = Field(description="可复用的文案模板或句式。")
    suitable_scenarios: list[str] = Field(description="适用场景，例如直播引流、私域成交、课程种草。")
    risk_warnings: list[RiskWarning] = Field(description="风险提示列表。")
    confidence: float = Field(ge=0, le=1, description="拆解结果置信度，范围为0到1。")


class CopyImportRequest(BaseModel):
    csv_text: str = Field(min_length=1, description="CSV 文件内容，由前端读取文件后提交。")


class CopyImportRowError(BaseModel):
    row_number: int = Field(ge=1, description="CSV 中出错的行号，包含表头行。")
    message: str = Field(description="这一行无法导入的原因。")


class CopyAssetSummary(CopyContext):
    id: str
    source_text: str
    source_url: str | None = None
    metrics: dict[str, int] = Field(default_factory=dict)
    status: str = Field(description="审核状态，例如 pending_review、approved、rejected。")
    auto_analysis: CopyAnalysisResponse | None = None
    reviewed_analysis: CopyAnalysisResponse | None = None


class CopyAssetListResponse(BaseModel):
    items: list[CopyAssetSummary]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)


class CopyImportResponse(BaseModel):
    imported_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    assets: list[CopyAssetSummary]
    errors: list[CopyImportRowError]


class CopyAssetReviewRequest(BaseModel):
    status: str = Field(pattern="^(pending_review|approved|rejected)$")
    reviewed_analysis: CopyAnalysisResponse
