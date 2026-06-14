from app.schemas.copy import CopyAnalysisRequest
from app.schemas.feedback import FeedbackRequest
from app.schemas.generate import GenerateRequest


def test_copy_analysis_request_accepts_minimum_payload() -> None:
    payload = CopyAnalysisRequest(source_text="这是一条测试文案")
    assert payload.source_text == "这是一条测试文案"


def test_generate_request_bounds_version_count() -> None:
    payload = GenerateRequest(version_count=3)
    assert payload.version_count == 3


def test_feedback_rating_is_required_range() -> None:
    payload = FeedbackRequest(rating=5)
    assert payload.rating == 5
