from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    artifact_id: str | None = Field(default=None, description="被评价的产物ID，例如某次生成结果ID。")
    rating: int = Field(ge=1, le=5, description="用户评分，范围为1到5。")
    comment: str | None = Field(default=None, description="用户文字反馈。")
    selected_variant: str | None = Field(default=None, description="用户选择或偏好的版本ID或标题。")


class FeedbackResponse(BaseModel):
    feedback_id: str = Field(description="反馈记录ID。")
    status: str = Field(default="recorded", description="反馈记录状态。")
