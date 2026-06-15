from fastapi.testclient import TestClient

from app.main import app
from app.services.copy_assets import reset_copy_asset_store
from app.services.knowledge import reset_knowledge_store


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


def setup_function() -> None:
    reset_copy_asset_store()
    reset_knowledge_store()


def test_collection_and_raw_copy_crud() -> None:
    collection_response = client.post(
        "/api/knowledge/collections",
        json={"name": "美妆库", "description": "美妆相关文案"},
    )
    assert collection_response.status_code == 200
    collection_id = collection_response.json()["id"]

    raw_response = client.post(
        "/api/knowledge/raw-copies",
        json={
            "source_text": "先别急着换产品，可能是护肤顺序错了。",
            "source_url": "https://example.com/post/1",
            "platform": "小红书",
            "collection_ids": [collection_id],
        },
    )
    assert raw_response.status_code == 200
    raw_payload = raw_response.json()
    assert raw_payload["collection_ids"] == [collection_id]
    assert raw_payload["collections"][0]["name"] == "美妆库"

    list_response = client.get(f"/api/knowledge/raw-copies?collection_id={collection_id}")
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    delete_response = client.delete(f"/api/knowledge/raw-copies/{raw_payload['id']}")
    assert delete_response.status_code == 204
    assert client.get(f"/api/knowledge/raw-copies/{raw_payload['id']}").status_code == 404


def test_template_tag_case_and_block_crud_with_source_reference() -> None:
    raw_response = client.post(
        "/api/knowledge/raw-copies",
        json={"source_text": "如果你总觉得没效果，先检查顺序。"},
    )
    raw_id = raw_response.json()["id"]

    template_response = client.post(
        "/api/knowledge/templates",
        json={
            "title": "问题反转模板",
            "content": "如果你总觉得____，先检查____。",
            "source": {"source_type": "raw_copy", "source_id": raw_id},
        },
    )
    assert template_response.status_code == 200
    template_id = template_response.json()["id"]
    assert template_response.json()["source"]["source_id"] == raw_id

    tag_response = client.post(
        "/api/knowledge/tags",
        json={
            "name": "共鸣",
            "category": "emotion",
            "source": {"source_type": "raw_copy", "source_id": raw_id},
        },
    )
    assert tag_response.status_code == 200

    case_response = client.post(
        "/api/knowledge/cases",
        json={
            "title": "高收藏护肤案例",
            "reason": "开头直接命中使用误区。",
            "source": {"source_type": "raw_copy", "source_id": raw_id},
        },
    )
    assert case_response.status_code == 200

    block_response = client.post(
        "/api/knowledge/blocks",
        json={
            "content": "百分百有效",
            "block_type": "violation",
            "reason": "绝对化承诺",
            "source": {"source_type": "raw_copy", "source_id": raw_id},
        },
    )
    assert block_response.status_code == 200

    update_response = client.patch(
        f"/api/knowledge/templates/{template_id}",
        json={"title": "更新后的模板"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "更新后的模板"

    delete_response = client.delete(f"/api/knowledge/templates/{template_id}")
    assert delete_response.status_code == 204
    assert client.get(f"/api/knowledge/templates/{template_id}").status_code == 404


def test_fragment_crud_and_filters() -> None:
    raw_response = client.post(
        "/api/knowledge/raw-copies",
        json={"source_text": "Start with the pain, then explain the reason."},
    )
    assert raw_response.status_code == 200
    raw_id = raw_response.json()["id"]

    create_response = client.post(
        "/api/knowledge/fragments",
        json={
            "source_copy_id": raw_id,
            "sequence_order": 1,
            "previous_fragment": "Start with the pain.",
            "next_fragment": "Then explain the reason.",
            "before_context": "Opening section",
            "after_context": "Reason section",
            "fragment_text": "Start with the pain",
            "fragment_role": "hook",
            "position": "opening",
            "industry": "beauty",
            "source_quality": "high",
            "risk_level": "low",
            "metadata": {"note": "manual split"},
        },
    )
    assert create_response.status_code == 200
    fragment = create_response.json()
    assert fragment["source_copy_id"] == raw_id
    assert fragment["fragment_role"] == "hook"

    list_response = client.get(f"/api/knowledge/fragments?source_copy_id={raw_id}&position=opening")
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    update_response = client.patch(
        f"/api/knowledge/fragments/{fragment['id']}",
        json={"fragment_role": "pain_point", "risk_level": "medium"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["fragment_role"] == "pain_point"
    assert update_response.json()["risk_level"] == "medium"

    empty_filter_response = client.get("/api/knowledge/fragments?fragment_role=hook")
    assert empty_filter_response.status_code == 200
    assert empty_filter_response.json()["total"] == 0

    delete_response = client.delete(f"/api/knowledge/fragments/{fragment['id']}")
    assert delete_response.status_code == 204
    assert client.get(f"/api/knowledge/fragments/{fragment['id']}").status_code == 404


def test_copy_import_populates_raw_copy_and_analysis_libraries(monkeypatch) -> None:
    monkeypatch.setattr("app.services.copy_analysis.get_llm_client", lambda: FakeLLMClient())
    monkeypatch.setattr("app.api.routes.copy.enqueue_copy_import", lambda csv_text: __import__(
        "app.services.copy_import_jobs", fromlist=["run_copy_import_task"]
    ).run_copy_import_task(csv_text))

    response = client.post(
        "/api/copy/import",
        json={"csv_text": "source_text,source_url\n先别急着换产品。,https://example.com/post/1\n"},
    )

    assert response.status_code == 200
    raw_response = client.get("/api/knowledge/raw-copies")
    assert raw_response.status_code == 200
    assert raw_response.json()["total"] == 1
    assert raw_response.json()["items"][0]["source_url"] == "https://example.com/post/1"

    analysis_response = client.get("/api/knowledge/analyses")
    assert analysis_response.status_code == 200
    assert analysis_response.json()["total"] == 1
    assert analysis_response.json()["items"][0]["auto_analysis"]["topic"] == "护肤顺序纠错"
