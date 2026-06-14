from fastapi import APIRouter

from app.schemas.feedback import FeedbackRequest, FeedbackResponse
from app.services.feedback import record_feedback

router = APIRouter()


@router.post("", response_model=FeedbackResponse)
def create_feedback(payload: FeedbackRequest) -> FeedbackResponse:
    return record_feedback(payload)
