from fastapi.testclient import TestClient

from app.main import app
from app.services.copy_assets import reset_copy_asset_store
from app.services.drafts import reset_draft_store
from app.services.knowledge import reset_knowledge_store
from app.workers import tasks


client = TestClient(app)


class FakeDiagnosticLLMClient:
    model = "fake-diagnostic-model"

    def complete(self, prompt: str) -> str:
        return """{
            "summary": "整体表达清楚，但开头吸引力和转化动作偏弱。",
            "overall_level": "fair",
            "dimensions": [
                {
                    "dimension": "opening_attractiveness",
                    "level": "weak",
                    "reason": "开头没有快速指出用户正在经历的问题。",
                    "suggestion": "先用更具体的场景切入。"
                },
                {
                    "dimension": "conversion_action",
                    "level": "fair",
                    "reason": "结尾有行动提示，但动作还不够低门槛。",
                    "suggestion": "把行动改成一个马上能做的小步骤。"
                }
            ],
            "sentence_issues": [
                {
                    "text": "这个方法绝对有效。",
                    "dimension": "compliance_risk",
                    "level": "high_risk",
                    "reason": "绝对化表达容易带来合规风险。",
                    "suggestion": "改成更审慎、可验证的表达。",
                    "replacement": "这个方法适合先作为检查思路。"
                }
            ],
            "rewrite_candidates": [
                {
                    "candidate_id": "safe",
                    "mode": "compliance_safe",
                    "title": "合规安全版",
                    "text": "如果你最近护肤效果不稳定，可以先检查步骤顺序。这个方法适合先作为检查思路。",
                    "reason": "弱化绝对承诺，并保留原始意图。"
                }
            ],
            "risk_warnings": [
                {
                    "level": "high",
                    "message": "包含绝对化表达。",
                    "suggestion": "替换为审慎表达。"
                }
            ]
        }"""


def setup_function() -> None:
    tasks._TASKS.clear()
    reset_copy_asset_store()
    reset_knowledge_store()
    reset_draft_store()


def _patch_sync_diagnostics(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.diagnostics.get_llm_client",
        lambda: FakeDiagnosticLLMClient(),
    )
    monkeypatch.setattr(
        "app.api.routes.diagnostics.enqueue_copy_diagnosis",
        lambda payload: __import__(
            "app.services.diagnostic_jobs", fromlist=["run_copy_diagnosis_task"]
        ).run_copy_diagnosis_task(payload.model_dump()),
    )


def test_copy_diagnosis_accepts_pasted_text_and_returns_structured_result(monkeypatch) -> None:
    _patch_sync_diagnostics(monkeypatch)

    response = client.post(
        "/api/diagnostics/copy",
        json={"text": "这个方法绝对有效。", "platform": "xhs", "purpose": "conversion"},
    )

    assert response.status_code == 200
    task_payload = client.get(f"/api/tasks/{response.json()['task_id']}").json()
    assert task_payload["status"] == "finished"
    assert task_payload["progress"]["phase"] == "finished"
    assert task_payload["progress"]["model"]

    result = task_payload["result"]
    assert result["source"]["source_type"] == "text"
    assert result["model"] == "fake-diagnostic-model"
    assert result["overall_level"] == "fair"
    assert result["dimensions"][0]["dimension"] == "opening_attractiveness"
    assert result["sentence_issues"][0]["replacement"] == "这个方法适合先作为检查思路。"
    assert result["rewrite_candidates"][0]["candidate_id"] == "safe"
    assert any(item["level"] == "high" for item in result["risk_warnings"])


def test_copy_diagnosis_can_read_existing_draft(monkeypatch) -> None:
    _patch_sync_diagnostics(monkeypatch)
    draft_response = client.post(
        "/api/drafts",
        json={"title": "诊断草稿", "platform": "xhs", "purpose": "conversion"},
    )
    draft_id = draft_response.json()["id"]
    client.post(
        f"/api/drafts/{draft_id}/items",
        json={"edited_text": "这个方法绝对有效。"},
    )

    response = client.post("/api/diagnostics/copy", json={"draft_id": draft_id})

    assert response.status_code == 200
    task_payload = client.get(f"/api/tasks/{response.json()['task_id']}").json()
    assert task_payload["status"] == "finished"
    assert task_payload["result"]["source"]["source_type"] == "draft"
    assert task_payload["result"]["source"]["draft_id"] == draft_id
    assert task_payload["result"]["source"]["text"] == "这个方法绝对有效。"


def test_copy_diagnosis_requires_text_or_draft_id() -> None:
    response = client.post("/api/diagnostics/copy", json={"platform": "xhs"})

    assert response.status_code == 422


def test_accept_diagnostic_rewrite_updates_draft_and_saves_version(monkeypatch) -> None:
    _patch_sync_diagnostics(monkeypatch)
    draft_response = client.post("/api/drafts", json={"title": "待改写草稿"})
    draft_id = draft_response.json()["id"]
    client.post(
        f"/api/drafts/{draft_id}/items",
        json={"edited_text": "这个方法绝对有效。"},
    )
    task_response = client.post("/api/diagnostics/copy", json={"draft_id": draft_id})

    accept_response = client.post(
        "/api/diagnostics/accepted-rewrite",
        json={
            "draft_id": draft_id,
            "task_id": task_response.json()["task_id"],
            "candidate_id": "safe",
        },
    )

    assert accept_response.status_code == 200
    payload = accept_response.json()
    assert payload["accepted"]["draft_id"] == draft_id
    assert payload["accepted"]["candidate_id"] == "safe"
    assert payload["draft"]["current_text"].startswith("如果你最近护肤效果不稳定")
    assert payload["draft"]["item_count"] == 1
    assert payload["version"]["current_text"].startswith("如果你最近护肤效果不稳定")
