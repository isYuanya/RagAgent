from fastapi.testclient import TestClient

from app.main import app
from app.schemas.copy import CopyAssetSummary
from app.services.copy_assets import delete_copy_asset_record, reset_copy_asset_store
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


def test_db_backed_raw_copy_delete_does_not_fall_back_to_cache_only(monkeypatch) -> None:
    asset = CopyAssetSummary(
        id="33333333-3333-3333-3333-333333333333",
        source_text="db backed cached raw copy",
        status="approved",
        storage_backend="postgres",
    )
    monkeypatch.setattr("app.services.copy_assets._soft_delete_db_asset", lambda asset_id: None)
    monkeypatch.setattr("app.services.copy_assets._get_redis_asset", lambda asset_id: asset)

    result = delete_copy_asset_record(asset.id)

    assert result == "unavailable"


def test_delete_raw_copy_returns_503_when_db_delete_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr("app.services.knowledge.delete_raw_copy", lambda raw_copy_id: "unavailable")

    response = client.delete("/api/knowledge/raw-copies/33333333-3333-3333-3333-333333333333")

    assert response.status_code == 503
    assert "Database is unavailable" in response.json()["detail"]


def test_template_crud_with_source_reference() -> None:
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


def test_fragment_vector_sync_on_create_update_delete(monkeypatch) -> None:
    upserted = []
    deleted = []
    monkeypatch.setattr("app.services.knowledge.upsert_fragment_vector", lambda document: upserted.append(document) or True)
    monkeypatch.setattr("app.services.knowledge.delete_fragment_vectors", lambda ids: deleted.extend(ids) or True)

    raw_response = client.post("/api/knowledge/raw-copies", json={"source_text": "vector source"})
    raw_id = raw_response.json()["id"]
    create_response = client.post(
        "/api/knowledge/fragments",
        json={
            "source_copy_id": raw_id,
            "sequence_order": 0,
            "fragment_text": "semantic fragment",
            "fragment_role": "hook",
            "position": "opening",
            "status": "approved",
            "confidence": 0.9,
        },
    )
    assert create_response.status_code == 200
    fragment_id = create_response.json()["id"]
    assert upserted[-1].metadata["fragment_id"] == fragment_id

    update_response = client.patch(
        f"/api/knowledge/fragments/{fragment_id}",
        json={"status": "pending_review"},
    )
    assert update_response.status_code == 200
    assert fragment_id in deleted

    delete_response = client.delete(f"/api/knowledge/fragments/{fragment_id}")
    assert delete_response.status_code == 204
    assert deleted.count(fragment_id) >= 2


def test_bulk_delete_raw_copies_cleans_fragments_and_templates(monkeypatch) -> None:
    deleted_vectors = []
    monkeypatch.setattr("app.services.knowledge.delete_fragment_vectors", lambda ids: deleted_vectors.extend(ids) or True)
    raw_response = client.post(
        "/api/knowledge/raw-copies",
        json={"source_text": "bulk raw", "platform": "xhs"},
    )
    raw_id = raw_response.json()["id"]
    fragment_response = client.post(
        "/api/knowledge/fragments",
        json={
            "source_copy_id": raw_id,
            "sequence_order": 0,
            "fragment_text": "bulk fragment",
            "fragment_role": "hook",
            "position": "opening",
            "status": "approved",
            "confidence": 0.9,
        },
    )
    fragment_id = fragment_response.json()["id"]
    template_response = client.post(
        "/api/knowledge/templates",
        json={
            "title": "source template",
            "content": "template",
            "source": {"source_type": "raw_copy", "source_id": raw_id},
        },
    )
    template_id = template_response.json()["id"]

    response = client.post(
        "/api/knowledge/raw-copies/bulk-delete",
        json={"confirm": True, "platform": "xhs", "raw_copy_ids": [raw_id]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["matched_count"] == 1
    assert payload["deleted_count"] == 1
    assert raw_id in payload["item_ids"]
    assert client.get(f"/api/knowledge/raw-copies/{raw_id}").status_code == 404
    assert client.get(f"/api/knowledge/fragments/{fragment_id}").status_code == 404
    assert client.get(f"/api/knowledge/templates/{template_id}").status_code == 404
    assert fragment_id in deleted_vectors


def test_knowledge_stats_counts_each_library() -> None:
    collection_response = client.post("/api/knowledge/collections", json={"name": "stats"})
    raw_response = client.post(
        "/api/knowledge/raw-copies",
        json={"source_text": "stats raw", "collection_ids": [collection_response.json()["id"]]},
    )
    raw_id = raw_response.json()["id"]
    client.post(
        "/api/knowledge/templates",
        json={"title": "stats template", "content": "template"},
    )
    client.post(
        "/api/knowledge/fragments",
        json={
            "source_copy_id": raw_id,
            "sequence_order": 0,
            "fragment_text": "stats fragment",
            "fragment_role": "hook",
            "position": "opening",
        },
    )

    response = client.get("/api/knowledge/stats")

    assert response.status_code == 200
    payload = response.json()
    assert payload["collections"] == 1
    assert payload["raw_copies"] == 1
    assert payload["templates"] == 1
    assert payload["fragments"] == 1


def test_bulk_delete_raw_copies_matches_beyond_first_100() -> None:
    created_ids = []
    for index in range(105):
        response = client.post(
            "/api/knowledge/raw-copies",
            json={"source_text": f"bulk raw {index}", "platform": "bulk-platform"},
        )
        assert response.status_code == 200
        created_ids.append(response.json()["id"])

    preview = client.post(
        "/api/knowledge/raw-copies/bulk-delete/preview",
        json={"platform": "bulk-platform"},
    )
    assert preview.status_code == 200
    assert preview.json()["matched_count"] == 105

    response = client.post(
        "/api/knowledge/raw-copies/bulk-delete",
        json={"confirm": True, "platform": "bulk-platform"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["matched_count"] == 105
    assert payload["deleted_count"] == 105
    assert client.get("/api/knowledge/raw-copies").json()["total"] == 0


def test_bulk_delete_raw_copies_rejects_unfiltered_delete_all() -> None:
    for index in range(3):
        response = client.post(
            "/api/knowledge/raw-copies",
            json={"source_text": f"safe raw {index}"},
        )
        assert response.status_code == 200

    preview = client.post(
        "/api/knowledge/raw-copies/bulk-delete/preview",
        json={},
    )
    assert preview.status_code == 200
    assert preview.json()["failed_count"] == 1
    assert preview.json()["matched_count"] == 0

    response = client.post(
        "/api/knowledge/raw-copies/bulk-delete",
        json={"confirm": True},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["failed_count"] == 1
    assert payload["deleted_count"] == 0
    assert client.get("/api/knowledge/raw-copies").json()["total"] == 3


def test_copy_import_populates_raw_copy_and_analysis_libraries(monkeypatch) -> None:
    monkeypatch.setattr("app.services.copy_analysis.get_llm_client", lambda: FakeLLMClient())
    monkeypatch.setattr("app.api.routes.copy.enqueue_copy_import", lambda csv_text, collection_ids=None: __import__(
        "app.services.copy_import_jobs", fromlist=["run_copy_import_task"]
    ).run_copy_import_task(csv_text, collection_ids=collection_ids or []))

    response = client.post(
        "/api/copy/import",
        json={"csv_text": "source_text,source_url\n先别急着换产品。,https://example.com/post/1\n"},
    )

    assert response.status_code == 200
    asset_id = response.json()["result"]["asset_ids"][0]

    asset_response = client.get(f"/api/copy/assets/{asset_id}")
    assert asset_response.status_code == 200
    asset_payload = asset_response.json()
    assert asset_payload["status"] == "pending_review"

    raw_response = client.get("/api/knowledge/raw-copies")
    assert raw_response.status_code == 200
    assert raw_response.json()["total"] == 1
    assert raw_response.json()["items"][0]["source_url"] == "https://example.com/post/1"

    analysis_response = client.get("/api/knowledge/analyses")
    assert analysis_response.status_code == 200
    assert analysis_response.json()["total"] == 1
    assert analysis_response.json()["items"][0]["auto_analysis"]["topic"] == "护肤顺序纠错"

    review_response = client.patch(
        f"/api/copy/assets/{asset_id}/review",
        json={"status": "approved", "reviewed_analysis": asset_payload["auto_analysis"]},
    )
    assert review_response.status_code == 200
    assert review_response.json()["status"] == "approved"


def test_delete_projected_asset_analysis_when_manual_analysis_row_is_missing(monkeypatch) -> None:
    monkeypatch.setattr("app.services.copy_analysis.get_llm_client", lambda: FakeLLMClient())
    monkeypatch.setattr("app.api.routes.copy.enqueue_copy_import", lambda csv_text, collection_ids=None: __import__(
        "app.services.copy_import_jobs", fromlist=["run_copy_import_task"]
    ).run_copy_import_task(csv_text, collection_ids=collection_ids or []))

    response = client.post(
        "/api/copy/import",
        json={"csv_text": "source_text\n鍏堝埆鎬ョ潃鎹骇鍝併€?\n"},
    )
    assert response.status_code == 200
    asset_id = response.json()["result"]["asset_ids"][0]

    analysis_response = client.get("/api/knowledge/analyses")
    assert analysis_response.status_code == 200
    assert analysis_response.json()["total"] == 1
    assert analysis_response.json()["items"][0]["id"] == asset_id

    monkeypatch.setattr("app.services.knowledge._db_delete_item", lambda *_args: False)
    delete_response = client.delete(f"/api/knowledge/analyses/{asset_id}")
    assert delete_response.status_code == 204

    assert client.get(f"/api/knowledge/analyses/{asset_id}").status_code == 404
    list_after_delete = client.get("/api/knowledge/analyses")
    assert list_after_delete.status_code == 200
    assert list_after_delete.json()["total"] == 0


def test_copy_import_assigns_assets_to_collection(monkeypatch) -> None:
    collection_response = client.post(
        "/api/knowledge/collections",
        json={"name": "导入集合"},
    )
    assert collection_response.status_code == 200
    collection_id = collection_response.json()["id"]

    monkeypatch.setattr("app.services.copy_analysis.get_llm_client", lambda: FakeLLMClient())
    monkeypatch.setattr("app.api.routes.copy.enqueue_text_import", lambda text, collection_ids=None: __import__(
        "app.services.copy_import_jobs", fromlist=["run_text_import_task"]
    ).run_text_import_task(text, collection_ids=collection_ids or []))

    response = client.post(
        "/api/copy/import",
        json={"text": "导入到指定集合的文案", "collection_ids": [collection_id]},
    )

    assert response.status_code == 200
    raw_response = client.get(f"/api/knowledge/raw-copies?collection_id={collection_id}")
    assert raw_response.status_code == 200
    assert raw_response.json()["total"] == 1
    assert raw_response.json()["items"][0]["collection_ids"] == [collection_id]

    asset_response = client.get(f"/api/copy/assets?collection_id={collection_id}")
    assert asset_response.status_code == 200
    assert asset_response.json()["total"] == 1
    assert asset_response.json()["items"][0]["collection_ids"] == [collection_id]
