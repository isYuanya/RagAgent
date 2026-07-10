import pytest
from pydantic import ValidationError

from app.schemas.copy import CopyAnalysisRequest
from app.schemas.draft import DraftVideoExportPayload
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


def _valid_video_payload(**updates) -> dict:
    payload = {
        "title": "征信空白",
        "title_break": "征信空白\n贷款思路",
        "description": "用更稳妥的方式说明征信记录少时的贷款匹配思路。",
        "script": "如果你的信用记录比较少，先别急着乱申请。\n\n可以先看收入、负债和申请顺序，再选择更匹配的产品。",
        "tts_script": "如果你的信用记录比较少，先别急着乱申请。\n\n可以先看收入、负债和申请顺序，再选择更匹配的产品。",
        "hashtags": ["贷款", "#征信", " 信用记录 "],
    }
    payload.update(updates)
    return payload


def test_draft_video_export_payload_cleans_hashtags_without_hash() -> None:
    payload = DraftVideoExportPayload.model_validate(_valid_video_payload())
    assert payload.hashtags == ["贷款", "征信", "信用记录"]


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("title", "白户也能秒批"),
        ("title_break", "白户\n也能秒批"),
        ("description", "白户也能秒批，包过包下，百分百通过申请。"),
    ],
)
def test_draft_video_export_payload_rejects_high_risk_marketing_words(
    field_name: str,
    value: str,
) -> None:
    with pytest.raises(ValidationError):
        DraftVideoExportPayload.model_validate(_valid_video_payload(**{field_name: value}))


def test_draft_video_export_payload_rejects_too_many_title_break_lines() -> None:
    with pytest.raises(ValidationError):
        DraftVideoExportPayload.model_validate(
            _valid_video_payload(title_break="征信空白\n贷款\n思路")
        )


def test_draft_video_export_payload_rejects_script_pinyin_annotation() -> None:
    with pytest.raises(ValidationError):
        DraftVideoExportPayload.model_validate(
            _valid_video_payload(script="这个银行[háng]贷款要先看资质。")
        )


def test_draft_video_export_payload_rejects_interactive_script_ending() -> None:
    with pytest.raises(ValidationError):
        DraftVideoExportPayload.model_validate(
            _valid_video_payload(script="先看负债，再看收入。想了解的话评论区留言。")
        )


def test_draft_video_export_payload_rejects_tts_rewrite() -> None:
    with pytest.raises(ValidationError):
        DraftVideoExportPayload.model_validate(
            _valid_video_payload(tts_script="这是另一段配音稿，内容已经被改写。")
        )


def test_draft_video_export_payload_accepts_tts_pinyin_replacement() -> None:
    payload = DraftVideoExportPayload.model_validate(
        _valid_video_payload(
            script="你的选择越还越多，先别急着定。",
            tts_script="你的选择越[huán]越多，先别急着定。",
        )
    )

    assert payload.tts_script == "你的选择越[huán]越多，先别急着定。"


def test_draft_video_export_payload_rejects_tts_pinyin_after_character() -> None:
    with pytest.raises(ValidationError):
        DraftVideoExportPayload.model_validate(
            _valid_video_payload(
                script="你的选择越还越多，先别急着定。",
                tts_script="你的选择越还[huán]越多，先别急着定。",
            )
        )
