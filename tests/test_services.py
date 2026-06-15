from app.schemas.copy import CopyAnalysisRequest
from app.schemas.generate import GenerateRequest
from app.services.copy_assets import import_copy_assets, reset_copy_asset_store
from app.services.copy_analysis import analyze_copy
from app.services.generation import generate_copy


class FakeLLMClient:
    def complete(self, prompt: str) -> str:
        return """{
            "topic": "护肤顺序纠错",
            "target_user": "新手护肤用户",
            "core_pain": "护肤没有效果",
            "emotion_buttons": ["好奇", "危机感"],
            "hook": "先别急着换产品。",
            "structure": ["提出问题", "给出原因", "行动建议"],
            "expression_skills": ["短句", "对比"],
            "reusable_template": "如果你____，先检查____。",
            "suitable_scenarios": ["种草", "私域引流"],
            "risk_warnings": [],
            "confidence": 0.81
        }"""


def test_analyze_copy_returns_structured_result(monkeypatch) -> None:
    monkeypatch.setattr("app.services.copy_analysis.get_llm_client", lambda: FakeLLMClient())

    result = analyze_copy(CopyAnalysisRequest(source_text="如果护肤没效果，先检查顺序。"))
    assert result.topic == "护肤顺序纠错"
    assert result.structure == ["提出问题", "给出原因", "行动建议"]
    assert result.confidence == 0.81


def test_generate_copy_returns_requested_variants(monkeypatch) -> None:
    monkeypatch.setattr("app.services.generation.get_llm_client", lambda: FakeLLMClient())

    result = generate_copy(GenerateRequest(product_name="课程", audience="新手", version_count=2))
    assert len(result.variants) == 2
    assert result.script


def test_import_copy_assets_reports_row_errors_and_assets(monkeypatch) -> None:
    reset_copy_asset_store()
    monkeypatch.setattr("app.services.copy_analysis.get_llm_client", lambda: FakeLLMClient())

    csv_text = (
        "source_text,platform,industry,audience,purpose,style,likes\n"
        "如果护肤没效果，先检查顺序。,小红书,美妆,新手,引流,专业,120\n"
        ",抖音,教育,新手,涨粉,共情,5\n"
    )

    result = import_copy_assets(csv_text)

    assert result.imported_count == 1
    assert len(result.assets) == 1
    assert result.assets[0].status == "pending_review"
    assert result.errors[0].row_number == 3
