from app.schemas.copy import CopyAnalysisRequest
from app.schemas.generate import GenerateRequest
from app.services.copy_analysis import analyze_copy
from app.services.generation import generate_copy


def test_analyze_copy_returns_structured_result() -> None:
    result = analyze_copy(CopyAnalysisRequest(source_text="如果护肤没效果，先检查顺序。"))
    assert result.topic
    assert result.structure
    assert 0 <= result.confidence <= 1


def test_generate_copy_returns_requested_variants() -> None:
    result = generate_copy(GenerateRequest(product_name="课程", audience="新手", version_count=2))
    assert len(result.variants) == 2
    assert result.script
