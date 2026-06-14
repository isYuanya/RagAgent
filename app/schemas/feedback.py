from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    artifact_id: str | None = None
    rating: int = Field(ge=1, le=5)
    comment: str | None = None
    selected_variant: str | None = None


class FeedbackResponse(BaseModel):
    feedback_id: str
    status: str = "recorded"
