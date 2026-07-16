from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import CopyContext, RiskWarning


class CopyAnalysisRequest(CopyContext):
    source_text: str = Field(min_length=1, description="待拆解的原始文案，不能为空。")
    source_url: str | None = Field(default=None, description="文案来源链接，可为空。")
    author_name: str | None = Field(default=None, description="发布作者或账号名称。")
    author_url: str | None = Field(default=None, description="发布作者主页链接。")
    author_follower_count: int | None = Field(default=None, ge=0, description="作者粉丝数。")
    metrics: dict[str, int] | None = Field(
        default=None,
        description="文案表现数据，例如 likes、comments、favorites、shares。",
    )


class CopyAnalysisResponse(BaseModel):
    topic: str = Field(description="文案主题。")
    target_user: str = Field(description="目标用户。")
    core_pain: str = Field(description="核心痛点。")
    emotion_buttons: list[str] = Field(description="情绪按钮。")
    hook: str = Field(description="开头钩子。")
    structure: list[str] = Field(description="内容结构步骤。")
    expression_skills: list[str] = Field(description="表达技巧。")
    reusable_template: str = Field(description="可复用的文案模板或句式。")
    suitable_scenarios: list[str] = Field(description="适用场景。")
    risk_warnings: list[RiskWarning] = Field(description="风险提示列表。")
    confidence: float = Field(ge=0, le=1, description="拆解结果置信度，范围 0 到 1。")


class _LegacyCopyImportRequest(BaseModel):
    csv_text: str = Field(min_length=1, description="CSV 文件内容，由前端读取文件后提交。")


class CopyImportRowError(BaseModel):
    row_number: int = Field(ge=1, description="CSV 中出错的行号，包含表头行。")
    message: str = Field(description="这一行无法导入的原因。")


class CopyImportRequest(BaseModel):
    csv_text: str | None = Field(default=None, min_length=1)
    text: str | None = Field(default=None, min_length=1)
    collection_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_one_import_source(self) -> "CopyImportRequest":
        if bool(self.csv_text) == bool(self.text):
            raise ValueError("Provide exactly one of csv_text or text.")
        return self


class CopyAssetSummary(CopyContext):
    id: str
    source_text: str
    source_url: str | None = None
    author_name: str | None = None
    author_url: str | None = None
    author_follower_count: int | None = Field(default=None, ge=0)
    metrics: dict[str, int] = Field(default_factory=dict)
    status: str = Field(description="审核状态，例如 pending_review、approved、rejected。")
    auto_analysis: CopyAnalysisResponse | None = None
    reviewed_analysis: CopyAnalysisResponse | None = None
    storage_backend: str = Field(default="memory", description="当前资产来源：postgres、redis 或 memory。")
    collection_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


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


class CopyAssetBulkDeleteRequest(BaseModel):
    confirm: bool = False
    status: str | None = Field(default="pending_review", pattern="^(pending_review|approved|rejected)$")
    industry: str | None = None
    platform: str | None = None
    collection_id: str | None = None
    asset_ids: list[str] | None = None


class BulkOperationResponse(BaseModel):
    matched_count: int = Field(ge=0)
    deleted_count: int = Field(ge=0)
    archived_count: int = Field(default=0, ge=0)
    skipped_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    item_ids: list[str] = Field(default_factory=list)
    errors: list[dict[str, str]] = Field(default_factory=list)
