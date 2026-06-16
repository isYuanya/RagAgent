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


class HighConfidenceLLMClient:
    def complete(self, prompt: str) -> str:
        return """{
            "topic": "skin care order",
            "target_user": "new skin care users",
            "core_pain": "routine has no effect",
            "emotion_buttons": ["curiosity"],
            "hook": "Check your routine before changing products.",
            "structure": ["raise problem", "give advice"],
            "expression_skills": ["short sentences"],
            "reusable_template": "If you feel ___, check ___ first.",
            "suitable_scenarios": ["education"],
            "risk_warnings": [],
            "confidence": 0.92
        }"""


class TextMetadataLLMClient:
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, prompt: str) -> str:
        self.calls += 1
        if self.calls == 1:
            return """{
            "source_text": "Check your skin care order before changing products.",
            "source_url": "https://example.com/post/metadata",
            "author_name": "Skin Researcher",
            "author_url": "https://example.com/author/skin",
            "author_follower_count": "52,000",
            "platform": "xiaohongshu",
            "industry": "beauty",
            "audience": "new users",
            "purpose": "education",
            "style": "professional",
            "metrics": {
                "likes": "120",
                "comments": "8",
                "favorites": "35",
                "shares": "4"
            }
        }"""
        return FakeLLMClient().complete(prompt)


class EmptyMetadataLLMClient:
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, prompt: str) -> str:
        self.calls += 1
        if self.calls == 1:
            return "{}"
        return FakeLLMClient().complete(prompt)


class FragmentExtractionLLMClient:
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, prompt: str) -> str:
        self.calls += 1
        if self.calls == 1:
            return """{
                "source_text": "Check your routine before changing products. The problem may be product order, not the product itself.",
                "platform": "xiaohongshu",
                "industry": "beauty",
                "audience": "new users",
                "purpose": "education",
                "style": "professional",
                "metrics": {}
            }"""
        if self.calls == 2:
            return FakeLLMClient().complete(prompt)
        return """{
            "fragments": [
                {
                    "fragment_text": "Check your routine before changing products.",
                    "fragment_role": "hook",
                    "position": "opening",
                    "reason": "Uses a direct recommendation to stop a common mistake.",
                    "source_quality": "high",
                    "risk_level": "low",
                    "confidence": 0.92
                },
                {
                    "fragment_text": "The problem may be product order, not the product itself.",
                    "fragment_role": "explanation",
                    "position": "middle",
                    "reason": "Explains the causal logic but needs review.",
                    "source_quality": "medium",
                    "risk_level": "low",
                    "confidence": 0.62
                }
            ]
        }"""


class BackfillFragmentExtractionLLMClient:
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, prompt: str) -> str:
        self.calls += 1
        if self.calls == 1:
            return """{
                "source_text": "Check your routine before changing products.",
                "platform": "xiaohongshu",
                "industry": "beauty",
                "audience": "new users",
                "purpose": "education",
                "style": "professional",
                "metrics": {}
            }"""
        if self.calls == 2:
            return HighConfidenceLLMClient().complete(prompt)
        return """{
            "fragments": [
                {
                    "fragment_text": "Check your routine before changing products.",
                    "fragment_role": "hook",
                    "position": "opening",
                    "source_quality": "high",
                    "risk_level": "low",
                    "confidence": 0.91
                }
            ]
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
    monkeypatch.setattr("app.api.routes.copy.enqueue_copy_import", lambda csv_text, collection_ids=None: __import__(
        "app.services.copy_import_jobs", fromlist=["run_copy_import_task"]
    ).run_copy_import_task(csv_text, collection_ids=collection_ids or []))

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
    assert task_payload["result"]["storage_backends"]

    list_response = client.get("/api/copy/assets")
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert list_response.json()["items"][0]["author_name"] == "护肤研究员"
    assert list_response.json()["items"][0]["author_follower_count"] == 52000
    assert list_response.json()["items"][0]["storage_backend"] in {"postgres", "redis", "memory"}
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
    monkeypatch.setattr("app.api.routes.copy.enqueue_text_import", lambda text, collection_ids=None: __import__(
        "app.services.copy_import_jobs", fromlist=["run_text_import_task"]
    ).run_text_import_task(text, collection_ids=collection_ids or []))

    response = client.post(
        "/api/copy/import",
        json={"text": "plain text copy"},
    )

    assert response.status_code == 200
    assert response.json()["progress"]["percent"] == 100
    assert response.json()["result"]["storage_backends"]

    list_response = client.get("/api/copy/assets")
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    item = list_response.json()["items"][0]
    assert item["source_text"] == "plain text copy"
    assert item["auto_analysis"]["confidence"] == 0.8
    assert item["storage_backend"] in {"postgres", "redis", "memory"}


def test_import_plain_text_extracts_embedded_metadata(monkeypatch) -> None:
    reset_copy_asset_store()
    llm_client = TextMetadataLLMClient()
    monkeypatch.setattr("app.services.copy_analysis.get_llm_client", lambda: llm_client)
    monkeypatch.setattr("app.api.routes.copy.enqueue_text_import", lambda text, collection_ids=None: __import__(
        "app.services.copy_import_jobs", fromlist=["run_text_import_task"]
    ).run_text_import_task(text, collection_ids=collection_ids or []))

    response = client.post(
        "/api/copy/import",
        json={
            "text": (
                "Platform: xiaohongshu\n"
                "Author: Skin Researcher\n"
                "Followers: 52,000\n"
                "Content: Check your skin care order before changing products."
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "finished"

    list_response = client.get("/api/copy/assets")
    assert list_response.status_code == 200
    item = list_response.json()["items"][0]
    assert item["source_text"] == "Check your skin care order before changing products."
    assert item["source_url"] == "https://example.com/post/metadata"
    assert item["author_name"] == "Skin Researcher"
    assert item["author_url"] == "https://example.com/author/skin"
    assert item["author_follower_count"] == 52000
    assert item["platform"] == "xiaohongshu"
    assert item["industry"] == "beauty"
    assert item["audience"] == "new users"
    assert item["purpose"] == "education"
    assert item["style"] == "professional"
    assert item["metrics"] == {"likes": 120, "comments": 8, "favorites": 35, "shares": 4}


def test_import_plain_text_falls_back_to_chinese_metadata_patterns(monkeypatch) -> None:
    reset_copy_asset_store()
    llm_client = EmptyMetadataLLMClient()
    monkeypatch.setattr("app.services.copy_analysis.get_llm_client", lambda: llm_client)
    monkeypatch.setattr("app.api.routes.copy.enqueue_text_import", lambda text, collection_ids=None: __import__(
        "app.services.copy_import_jobs", fromlist=["run_text_import_task"]
    ).run_text_import_task(text, collection_ids=collection_ids or []))

    response = client.post(
        "/api/copy/import",
        json={
            "text": (
                "平台：小红书\n"
                "作者：护肤研究员\n"
                "粉丝：5.2万\n"
                "行业：美妆\n"
                "目标人群：新手护肤用户\n"
                "目的：种草\n"
                "风格：专业\n"
                "指标：点赞120 评论8 收藏35 分享4\n"
                "正文：先别急着换产品，可能是护肤顺序错了。"
            )
        },
    )

    assert response.status_code == 200

    list_response = client.get("/api/copy/assets")
    assert list_response.status_code == 200
    item = list_response.json()["items"][0]
    assert item["source_text"] == "先别急着换产品，可能是护肤顺序错了。"
    assert item["author_name"] == "护肤研究员"
    assert item["author_follower_count"] == 52000
    assert item["platform"] == "小红书"
    assert item["industry"] == "美妆"
    assert item["audience"] == "新手护肤用户"
    assert item["purpose"] == "种草"
    assert item["style"] == "专业"
    assert item["metrics"] == {"likes": 120, "comments": 8, "favorites": 35, "shares": 4}


def test_import_csv_accepts_utf8_bom(monkeypatch) -> None:
    reset_copy_asset_store()
    monkeypatch.setattr("app.services.copy_analysis.get_llm_client", lambda: FakeLLMClient())
    monkeypatch.setattr("app.api.routes.copy.enqueue_copy_import", lambda csv_text, collection_ids=None: __import__(
        "app.services.copy_import_jobs", fromlist=["run_copy_import_task"]
    ).run_copy_import_task(csv_text, collection_ids=collection_ids or []))

    response = client.post(
        "/api/copy/import",
        json={"csv_text": "\ufeffsource_text,platform\nbom copy,xiaohongshu\n"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "finished"
    assert response.json()["result"]["imported_count"] == 1

    list_response = client.get("/api/copy/assets")
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert list_response.json()["items"][0]["source_text"] == "bom copy"


def test_high_confidence_import_is_auto_approved(monkeypatch) -> None:
    reset_copy_asset_store()
    monkeypatch.setattr("app.services.copy_analysis.get_llm_client", lambda: HighConfidenceLLMClient())
    monkeypatch.setattr("app.api.routes.copy.enqueue_text_import", lambda text, collection_ids=None: __import__(
        "app.services.copy_import_jobs", fromlist=["run_text_import_task"]
    ).run_text_import_task(text, collection_ids=collection_ids or []))

    response = client.post("/api/copy/import", json={"text": "auto approve me"})

    assert response.status_code == 200
    asset_id = response.json()["result"]["asset_ids"][0]

    asset_response = client.get(f"/api/copy/assets/{asset_id}")
    assert asset_response.status_code == 200
    assert asset_response.json()["status"] == "approved"

    delete_response = client.delete(f"/api/copy/assets/{asset_id}")
    assert delete_response.status_code == 409


def test_approving_copy_asset_auto_extracts_fragments(monkeypatch) -> None:
    reset_copy_asset_store()
    llm_client = FragmentExtractionLLMClient()
    monkeypatch.setattr("app.services.copy_analysis.get_llm_client", lambda: llm_client)
    monkeypatch.setattr("app.services.fragment_extraction.get_llm_client", lambda: llm_client)
    monkeypatch.setattr("app.api.routes.copy.enqueue_text_import", lambda text, collection_ids=None: __import__(
        "app.services.copy_import_jobs", fromlist=["run_text_import_task"]
    ).run_text_import_task(text, collection_ids=collection_ids or []))

    response = client.post(
        "/api/copy/import",
        json={
            "text": (
                "Check your routine before changing products.\n"
                "The problem may be product order, not the product itself."
            )
        },
    )
    assert response.status_code == 200
    asset_id = response.json()["result"]["asset_ids"][0]
    asset_response = client.get(f"/api/copy/assets/{asset_id}")
    asset_payload = asset_response.json()

    review_response = client.patch(
        f"/api/copy/assets/{asset_id}/review",
        json={"status": "approved", "reviewed_analysis": asset_payload["auto_analysis"]},
    )
    assert review_response.status_code == 200

    fragments_response = client.get(
        "/api/knowledge/fragments"
        "?fragment_role=hook&status=approved&platform=xiaohongshu"
        "&purpose=education&audience=new users&q=routine"
    )
    assert fragments_response.status_code == 200
    fragments_payload = fragments_response.json()
    assert fragments_payload["total"] == 1
    fragment = fragments_payload["items"][0]
    assert fragment["source_copy_id"] == asset_id
    assert fragment["status"] == "approved"
    assert fragment["confidence"] == 0.92
    assert fragment["platform"] == "xiaohongshu"
    assert fragment["purpose"] == "education"
    assert fragment["audience"] == "new users"

    pending_response = client.get("/api/knowledge/fragments?status=pending_review")
    assert pending_response.status_code == 200
    assert pending_response.json()["total"] == 1

    second_review_response = client.patch(
        f"/api/copy/assets/{asset_id}/review",
        json={"status": "approved", "reviewed_analysis": asset_payload["auto_analysis"]},
    )
    assert second_review_response.status_code == 200
    all_fragments_response = client.get(f"/api/knowledge/fragments?source_copy_id={asset_id}")
    assert all_fragments_response.json()["total"] == 2


def test_backfill_extracts_fragments_for_existing_approved_assets(monkeypatch) -> None:
    reset_copy_asset_store()
    llm_client = BackfillFragmentExtractionLLMClient()
    monkeypatch.setattr("app.services.copy_analysis.get_llm_client", lambda: llm_client)
    monkeypatch.setattr("app.services.fragment_extraction.get_llm_client", lambda: llm_client)
    monkeypatch.setattr("app.api.routes.copy.enqueue_text_import", lambda text, collection_ids=None: __import__(
        "app.services.copy_import_jobs", fromlist=["run_text_import_task"]
    ).run_text_import_task(text, collection_ids=collection_ids or []))

    response = client.post("/api/copy/import", json={"text": "auto approved old copy"})
    assert response.status_code == 200
    asset_id = response.json()["result"]["asset_ids"][0]
    asset_response = client.get(f"/api/copy/assets/{asset_id}")
    assert asset_response.json()["status"] == "approved"

    empty_fragments_response = client.get(f"/api/knowledge/fragments?source_copy_id={asset_id}")
    assert empty_fragments_response.status_code == 200
    assert empty_fragments_response.json()["total"] == 0

    backfill_response = client.post("/api/knowledge/fragments/extract-approved")
    assert backfill_response.status_code == 200
    backfill_payload = backfill_response.json()
    assert backfill_payload["processed_count"] == 1
    assert backfill_payload["created_count"] == 1
    assert backfill_payload["failed_count"] == 0

    fragments_response = client.get(f"/api/knowledge/fragments?source_copy_id={asset_id}")
    assert fragments_response.status_code == 200
    assert fragments_response.json()["total"] == 1


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
    monkeypatch.setattr("app.api.routes.copy.enqueue_text_import", lambda text, collection_ids=None: __import__(
        "app.services.copy_import_jobs", fromlist=["run_text_import_task"]
    ).run_text_import_task(text, collection_ids=collection_ids or []))

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
    monkeypatch.setattr("app.api.routes.copy.enqueue_copy_import", lambda csv_text, collection_ids=None: __import__(
        "app.services.copy_import_jobs", fromlist=["run_copy_import_task"]
    ).run_copy_import_task(csv_text, collection_ids=collection_ids or []))

    response = client.post(
        "/api/copy/import",
        json={"csv_text": "source_text\n先别急着换产品。\n"},
    )

    assert response.status_code == 200
    task_response = client.get(f"/api/tasks/{response.json()['task_id']}")
    assert task_response.status_code == 200
    assert task_response.json()["status"] == "failed"
    assert "OPENAI_API_KEY" in task_response.json()["error"]
