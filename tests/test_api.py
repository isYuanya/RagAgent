from fastapi.testclient import TestClient

from app.main import app
from app.services.copy_assets import reset_copy_asset_store


client = TestClient(app)


class FakeLLMClient:
    def complete(self, prompt: str) -> str:
        return """{
            "topic": "护肤顺序纠错",
            "target_user": "新手护肤用户",
            "core_pain": "护肤没有效果",
            "emotion_buttons": ["好奇"],
            "hook": "先别急着换产品。",
            "structure": ["提出问题", "行动建议"],
            "expression_skills": ["短句"],
            "reusable_template": "如果你____，先检查____。",
            "suitable_scenarios": ["种草"],
            "risk_warnings": [],
            "confidence": 0.8
        }"""


def test_health_check() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_copy_analyze_endpoint(monkeypatch) -> None:
    monkeypatch.setattr("app.services.copy_analysis.get_llm_client", lambda: FakeLLMClient())

    response = client.post("/api/copy/analyze", json={"source_text": "先别急着换产品。"})

    assert response.status_code == 200
    assert response.json()["topic"] == "护肤顺序纠错"


def test_import_and_review_copy_asset(monkeypatch) -> None:
    reset_copy_asset_store()
    monkeypatch.setattr("app.services.copy_analysis.get_llm_client", lambda: FakeLLMClient())

    response = client.post(
        "/api/copy/import",
        json={
            "csv_text": (
                "source_text,platform,industry,audience,purpose,style,likes\n"
                "先别急着换产品。,小红书,美妆,新手,引流,专业,120\n"
            )
        },
    )

    assert response.status_code == 200
    asset_id = response.json()["assets"][0]["id"]

    list_response = client.get("/api/copy/assets")
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    review_response = client.patch(
        f"/api/copy/assets/{asset_id}/review",
        json={
            "status": "approved",
            "reviewed_analysis": {
                "topic": "校正后的主题",
                "target_user": "新手护肤用户",
                "core_pain": "护肤没有效果",
                "emotion_buttons": ["好奇"],
                "hook": "先别急着换产品。",
                "structure": ["提出问题", "行动建议"],
                "expression_skills": ["短句"],
                "reusable_template": "如果你____，先检查____。",
                "suitable_scenarios": ["种草"],
                "risk_warnings": [],
                "confidence": 0.9,
            },
        },
    )

    assert review_response.status_code == 200
    assert review_response.json()["status"] == "approved"
    assert review_response.json()["reviewed_analysis"]["topic"] == "校正后的主题"


def test_import_requires_configured_llm(monkeypatch) -> None:
    reset_copy_asset_store()

    def raise_config_error():
        raise RuntimeError("OPENAI_API_KEY is not configured")

    monkeypatch.setattr("app.services.copy_analysis.get_llm_client", raise_config_error)

    response = client.post(
        "/api/copy/import",
        json={"csv_text": "source_text\n先别急着换产品。\n"},
    )

    assert response.status_code == 503
