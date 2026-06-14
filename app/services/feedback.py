from uuid import uuid4

from app.schemas.feedback import FeedbackRequest, FeedbackResponse


def record_feedback(payload: FeedbackRequest) -> FeedbackResponse:
    return FeedbackResponse(feedback_id=str(uuid4()))
