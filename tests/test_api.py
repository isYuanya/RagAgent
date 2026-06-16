from fastapi.testclient import TestClient

from app.main import app
from app.schemas.copy import CopyAssetSummary
from app.services.copy_assets import list_copy_assets, reset_copy_asset_store


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


def test_cors_allows_localhost_frontend_origins() -> None:
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://127.0.0.1:5174",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5174"


def test_cors_headers_are_present_on_get_responses() -> None:
    response = client.get("/api/health", headers={"Origin": "http://localhost:5173"})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_copy_analyze_endpoint(monkeypatch) -> None:
    monkeypatch.setattr("app.services.copy_analysis.get_llm_client", lambda: FakeLLMClient())

    response = client.post("/api/copy/analyze", json={"source_text": "先别急着换产品。"})

    assert response.status_code == 200
    assert response.json()["topic"] == "护肤顺序纠错"


def test_import_and_review_copy_asset(monkeypatch) -> None:
    reset_copy_asset_store()
    monkeypatch.setattr("app.services.copy_analysis.get_llm_client", lambda: FakeLLMClient())
    monkeypatch.setattr("app.api.routes.copy.enqueue_copy_import", lambda csv_text: __import__(
        "app.services.copy_import_jobs", fromlist=["run_copy_import_task"]
    ).run_copy_import_task(csv_text))

    response = client.post(
        "/api/copy/import",
        json={
            "csv_text": (
                "source_text,platform,industry,audience,purpose,style,likes,author_name,author_url,author_follower_count\n"
                "先别急着换产品。,小红书,美妆,新手,引流,专业,120,护肤研究员,https://example.com/author/1,52000\n"
            )
        },
    )

    assert response.status_code == 200
    task_payload = response.json()
    assert task_payload["task_id"]
    assert task_payload["progress"]["model"]
    assert task_payload["progress"]["percent"] == 100

    list_response = client.get("/api/copy/assets")
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert list_response.json()["items"][0]["author_name"] == "护肤研究员"
    assert list_response.json()["items"][0]["author_follower_count"] == 52000
    asset_id = list_response.json()["items"][0]["id"]

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


def test_import_plain_text_copy_asset(monkeypatch) -> None:
    reset_copy_asset_store()
    monkeypatch.setattr("app.services.copy_analysis.get_llm_client", lambda: FakeLLMClient())
    monkeypatch.setattr("app.api.routes.copy.enqueue_text_import", lambda text: __import__(
        "app.services.copy_import_jobs", fromlist=["run_text_import_task"]
    ).run_text_import_task(text))

    response = client.post(
        "/api/copy/import",
        json={"text": "plain text copy"},
    )

    assert response.status_code == 200
    assert response.json()["progress"]["percent"] == 100

    list_response = client.get("/api/copy/assets")
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    item = list_response.json()["items"][0]
    assert item["source_text"] == "plain text copy"
    assert item["auto_analysis"]["confidence"] == 0.8


def test_copy_asset_list_merges_db_and_redis_assets(monkeypatch) -> None:
    reset_copy_asset_store()
    db_asset = CopyAssetSummary(
        id="11111111-1111-1111-1111-111111111111",
        source_text="db copy",
        status="pending_review",
    )
    redis_asset = CopyAssetSummary(
        id="22222222-2222-2222-2222-222222222222",
        source_text="redis copy",
        status="pending_review",
    )

    monkeypatch.setattr(
        "app.services.copy_assets._get_db_asset_items",
        lambda: [db_asset],
    )
    monkeypatch.setattr(
        "app.services.copy_assets._get_redis_asset_items",
        lambda: [redis_asset],
    )

    response = list_copy_assets(status="pending_review")

    assert response.total == 2
    assert {item.id for item in response.items} == {db_asset.id, redis_asset.id}


def test_delete_pending_review_copy_asset(monkeypatch) -> None:
    reset_copy_asset_store()
    monkeypatch.setattr("app.services.copy_analysis.get_llm_client", lambda: FakeLLMClient())
    monkeypatch.setattr("app.api.routes.copy.enqueue_text_import", lambda text: __import__(
        "app.services.copy_import_jobs", fromlist=["run_text_import_task"]
    ).run_text_import_task(text))

    response = client.post("/api/copy/import", json={"text": "delete me"})
    assert response.status_code == 200
    asset_id = response.json()["result"]["asset_ids"][0]

    delete_response = client.delete(f"/api/copy/assets/{asset_id}")
    assert delete_response.status_code == 204

    get_response = client.get(f"/api/copy/assets/{asset_id}")
    assert get_response.status_code == 404

    list_response = client.get("/api/copy/assets")
    assert list_response.status_code == 200
    assert all(item["id"] != asset_id for item in list_response.json()["items"])


def test_import_requires_configured_llm(monkeypatch) -> None:
    reset_copy_asset_store()

    def raise_config_error():
        raise RuntimeError("OPENAI_API_KEY is not configured")

    monkeypatch.setattr("app.services.copy_analysis.get_llm_client", raise_config_error)
    monkeypatch.setattr("app.api.routes.copy.enqueue_copy_import", lambda csv_text: __import__(
        "app.services.copy_import_jobs", fromlist=["run_copy_import_task"]
    ).run_copy_import_task(csv_text))

    response = client.post(
        "/api/copy/import",
        json={"csv_text": "source_text\n先别急着换产品。\n"},
    )

    assert response.status_code == 200
    task_response = client.get(f"/api/tasks/{response.json()['task_id']}")
    assert task_response.status_code == 200
    assert task_response.json()["status"] == "failed"
    assert "OPENAI_API_KEY" in task_response.json()["error"]
