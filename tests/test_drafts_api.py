from fastapi.testclient import TestClient

from app.main import app
from app.services import draft_video_export
from app.services.copy_assets import reset_copy_asset_store
from app.services.draft_video_export import reset_draft_video_export_store
from app.services.drafts import reset_draft_store
from app.services.knowledge import reset_knowledge_store


client = TestClient(app)


class _FragmentLLM:
    def complete(self, prompt: str) -> str:
        return (
            '{"fragments":['
            '{"fragment_text":"Approved hook","fragment_role":"hook","position":"opening",'
            '"reason":"strong opening","source_quality":"high","risk_level":"low","confidence":0.95},'
            '{"fragment_text":"Approved proof","fragment_role":"proof","position":"middle",'
            '"reason":"credible proof","source_quality":"high","risk_level":"low","confidence":0.9}'
            "]}"
        )


class _VideoExportLLM:
    model = "fake-video-export-model"

    def complete(self, prompt: str) -> str:
        return (
            '{"title":"护肤顺序","title_break":"护肤\\n顺序",'
            '"description":"先检查护肤顺序，再判断产品是否真的不适合。",'
            '"script":"如果你总觉得护肤没效果，先别急着换产品。\\n\\n很多时候问题不是产品，而是使用顺序。",'
            '"tts_script":"如果你总觉得护肤没效果，先别急着换产品。很多时候问题不是产品，而是使用顺序。",'
            '"hashtags":["护肤","护肤顺序"]}'
        )


class _InvalidVideoExportLLM:
    model = "fake-video-export-model"

    def complete(self, prompt: str) -> str:
        return '{"title":"这是一个超过十六个字的视频标题会失败","hashtags":[]}'


class _LegacyPinyinVideoExportLLM:
    model = "fake-video-export-model"

    def complete(self, prompt: str) -> str:
        return (
            '{"title":"还款节奏","title_break":"还款\\n节奏",'
            '"description":"先理清还款节奏，再根据自己的收入安排支出。",'
            '"script":"你的选择越还越多，先别急着定。",'
            '"tts_script":"你的选择越还[huán]越多，先别急着定。",'
            '"hashtags":["还款","资金规划"]}'
        )


def setup_function() -> None:
    reset_copy_asset_store()
    reset_draft_video_export_store()
    reset_knowledge_store()
    reset_draft_store()


def _create_fragment(text: str, role: str, order: int = 0) -> dict:
    raw_response = client.post(
        "/api/knowledge/raw-copies",
        json={"source_text": f"{text} source"},
    )
    assert raw_response.status_code == 200
    raw_id = raw_response.json()["id"]

    fragment_response = client.post(
        "/api/knowledge/fragments",
        json={
            "source_copy_id": raw_id,
            "sequence_order": order,
            "fragment_text": text,
            "fragment_role": role,
            "position": "opening" if order == 0 else "body",
            "industry": "beauty",
            "platform": "xhs",
            "purpose": "conversion",
            "audience": "new users",
            "source_quality": "high",
            "risk_level": "low",
            "status": "approved",
            "confidence": 0.9,
        },
    )
    assert fragment_response.status_code == 200
    return fragment_response.json()


def test_draft_workspace_flow_with_version_snapshot() -> None:
    hook_fragment = _create_fragment("Start with the pain", "hook", 0)
    proof_fragment = _create_fragment("Show one concrete proof", "proof", 1)

    create_response = client.post(
        "/api/drafts",
        json={
            "title": "Beauty launch draft",
            "goal": "Build a reviewable launch copy",
            "audience": "new users",
            "platform": "xhs",
            "purpose": "conversion",
        },
    )
    assert create_response.status_code == 200
    draft = create_response.json()
    draft_id = draft["id"]
    assert draft["status"] == "draft"
    assert draft["current_text"] == ""
    assert draft["items"] == []

    add_hook_response = client.post(
        f"/api/drafts/{draft_id}/items",
        json={"source_fragment_id": hook_fragment["id"]},
    )
    assert add_hook_response.status_code == 200
    draft = add_hook_response.json()
    hook_item = draft["items"][0]
    assert hook_item["edited_text"] == "Start with the pain"
    assert hook_item["original_fragment_text"] == "Start with the pain"
    assert hook_item["role"] == "hook"
    assert hook_item["source_copy_id"] == hook_fragment["source_copy_id"]

    add_proof_response = client.post(
        f"/api/drafts/{draft_id}/items",
        json={"source_fragment_id": proof_fragment["id"]},
    )
    assert add_proof_response.status_code == 200
    proof_item = add_proof_response.json()["items"][1]

    update_response = client.patch(
        f"/api/drafts/{draft_id}/items/{hook_item['id']}",
        json={"edited_text": "If skincare feels useless, check the order first"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["current_text"].startswith("If skincare feels useless")

    reorder_response = client.patch(
        f"/api/drafts/{draft_id}/items/reorder",
        json={
            "items": [
                {"item_id": hook_item["id"], "order_index": 1},
                {"item_id": proof_item["id"], "order_index": 0},
            ]
        },
    )
    assert reorder_response.status_code == 200
    assert reorder_response.json()["current_text"].startswith("Show one concrete proof")

    version_response = client.post(
        f"/api/drafts/{draft_id}/versions",
        json={"label": "first reviewable version"},
    )
    assert version_response.status_code == 200
    version = version_response.json()
    assert version["version_number"] == 1
    assert version["item_count"] == 2

    delete_item_response = client.delete(f"/api/drafts/{draft_id}/items/{proof_item['id']}")
    assert delete_item_response.status_code == 204
    current_response = client.get(f"/api/drafts/{draft_id}")
    assert current_response.status_code == 200
    assert current_response.json()["item_count"] == 1

    version_detail_response = client.get(f"/api/drafts/{draft_id}/versions/{version['id']}")
    assert version_detail_response.status_code == 200
    assert version_detail_response.json()["item_count"] == 2
    assert version_detail_response.json()["items"][0]["edited_text"] == "Show one concrete proof"

    archive_response = client.delete(f"/api/drafts/{draft_id}")
    assert archive_response.status_code == 204
    assert client.get("/api/drafts").json()["total"] == 0
    archived_response = client.get("/api/drafts?status=archived")
    assert archived_response.status_code == 200
    assert archived_response.json()["total"] == 1


def test_draft_item_requires_source_fragment_or_text() -> None:
    create_response = client.post("/api/drafts", json={"title": "Manual draft"})
    assert create_response.status_code == 200
    draft_id = create_response.json()["id"]

    invalid_response = client.post(f"/api/drafts/{draft_id}/items", json={})
    assert invalid_response.status_code == 422

    manual_response = client.post(
        f"/api/drafts/{draft_id}/items",
        json={"edited_text": "Manual sentence"},
    )
    assert manual_response.status_code == 200
    assert manual_response.json()["current_text"] == "Manual sentence"


def test_bulk_archive_drafts_preserves_history() -> None:
    first = client.post("/api/drafts", json={"title": "Archive one"}).json()
    second = client.post("/api/drafts", json={"title": "Archive two"}).json()
    client.post(f"/api/drafts/{first['id']}/items", json={"edited_text": "First text"})
    version_response = client.post(
        f"/api/drafts/{first['id']}/versions",
        json={"label": "before archive"},
    )
    assert version_response.status_code == 200

    response = client.post(
        "/api/drafts/bulk-archive",
        json={"confirm": True, "status": "draft", "draft_ids": [first["id"], second["id"]]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["matched_count"] == 2
    assert payload["archived_count"] == 2
    assert client.get("/api/drafts").json()["total"] == 0
    assert client.get("/api/drafts?status=archived").json()["total"] == 2
    detail_response = client.get(f"/api/drafts/{first['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["current_text"] == "First text"
    versions_response = client.get(f"/api/drafts/{first['id']}/versions")
    assert versions_response.status_code == 200
    assert len(versions_response.json()) == 1


def test_approve_draft_creates_raw_copy_and_fragments(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.fragment_extraction.get_llm_client",
        lambda: _FragmentLLM(),
    )
    create_response = client.post(
        "/api/drafts",
        json={
            "title": "Approved draft",
            "audience": "new users",
            "platform": "xhs",
            "purpose": "conversion",
        },
    )
    assert create_response.status_code == 200
    draft_id = create_response.json()["id"]
    add_response = client.post(
        f"/api/drafts/{draft_id}/items",
        json={"edited_text": "Approved hook\n\nApproved proof", "role": "hook", "position": "opening"},
    )
    assert add_response.status_code == 200

    approve_response = client.post(f"/api/drafts/{draft_id}/approve")
    assert approve_response.status_code == 200
    payload = approve_response.json()
    assert payload["draft"]["status"] == "ready"
    assert payload["raw_copy"]["status"] == "approved"
    assert payload["raw_copy"]["source_text"] == "Approved hook\n\nApproved proof"
    assert payload["raw_copy"]["metadata"]["source_type"] == "draft"
    assert payload["raw_copy"]["metadata"]["source_draft_id"] == draft_id
    assert payload["fragment_extraction"]["status"] == "created"
    assert payload["fragment_extraction"]["fragment_count"] == 2
    assert payload["draft"]["metadata"]["knowledge_ingest"]["raw_copy_id"] == payload["raw_copy"]["id"]

    raw_response = client.get("/api/knowledge/raw-copies")
    assert raw_response.status_code == 200
    assert raw_response.json()["total"] == 1

    fragments_response = client.get(
        f"/api/knowledge/fragments?source_copy_id={payload['raw_copy']['id']}"
    )
    assert fragments_response.status_code == 200
    assert fragments_response.json()["total"] == 2


def test_approve_draft_is_idempotent(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.fragment_extraction.get_llm_client",
        lambda: _FragmentLLM(),
    )
    draft = client.post("/api/drafts", json={"title": "Idempotent draft"}).json()
    draft_id = draft["id"]
    client.post(f"/api/drafts/{draft_id}/items", json={"edited_text": "Reusable approved text"})

    first = client.post(f"/api/drafts/{draft_id}/approve")
    second = client.post(f"/api/drafts/{draft_id}/approve")
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["raw_copy"]["id"] == first.json()["raw_copy"]["id"]
    assert second.json()["fragment_extraction"]["status"] == "skipped"
    assert client.get("/api/knowledge/raw-copies").json()["total"] == 1


def test_approve_empty_draft_fails() -> None:
    draft = client.post("/api/drafts", json={"title": "Empty draft"}).json()
    response = client.post(f"/api/drafts/{draft['id']}/approve")
    assert response.status_code == 409


def test_draft_video_export_task_persists_history(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.draft_video_export.get_llm_client",
        lambda: _VideoExportLLM(),
    )
    monkeypatch.setattr(
        "app.api.routes.drafts.enqueue_draft_video_export",
        lambda draft_id: __import__(
            "app.services.draft_video_export_jobs",
            fromlist=["run_draft_video_export_task"],
        ).run_draft_video_export_task({"draft_id": draft_id}),
    )
    draft = client.post("/api/drafts", json={"title": "视频草稿"}).json()
    draft_id = draft["id"]
    client.post(
        f"/api/drafts/{draft_id}/items",
        json={"edited_text": "如果你总觉得护肤没效果，先别急着换产品。"},
    )

    response = client.post(f"/api/drafts/{draft_id}/video-exports")
    assert response.status_code == 200
    task_payload = response.json()
    assert task_payload["status"] == "finished"
    assert task_payload["progress"]["phase"] == "finished"
    assert task_payload["progress"]["model"] == "fake-video-export-model"

    result = task_payload["result"]
    assert result["draft_id"] == draft_id
    assert result["model"] == "fake-video-export-model"
    assert result["result"] == {
        "title": "护肤顺序",
        "title_break": "护肤\n顺序",
        "description": "先检查护肤顺序，再判断产品是否真的不适合。",
        "script": "如果你总觉得护肤没效果，先别急着换产品。\n\n很多时候问题不是产品，而是使用顺序。",
        "tts_script": "如果你总觉得护肤没效果，先别急着换产品。很多时候问题不是产品，而是使用顺序。",
        "hashtags": ["护肤", "护肤顺序"],
    }

    history = client.get(f"/api/drafts/{draft_id}/video-exports")
    assert history.status_code == 200
    history_payload = history.json()
    assert history_payload["total"] == 1
    assert history_payload["items"][0]["id"] == result["id"]
    assert history_payload["items"][0]["result"]["title"] == "护肤顺序"


def test_draft_video_export_empty_draft_fails(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.routes.drafts.enqueue_draft_video_export",
        lambda draft_id: __import__(
            "app.services.draft_video_export_jobs",
            fromlist=["run_draft_video_export_task"],
        ).run_draft_video_export_task({"draft_id": draft_id}),
    )
    draft = client.post("/api/drafts", json={"title": "空草稿"}).json()

    response = client.post(f"/api/drafts/{draft['id']}/video-exports")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed"
    assert "Draft has no text" in payload["error"]


def test_draft_video_export_normalizes_legacy_tts_pinyin_format(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.draft_video_export.get_llm_client",
        lambda: _LegacyPinyinVideoExportLLM(),
    )
    monkeypatch.setattr(
        "app.api.routes.drafts.enqueue_draft_video_export",
        lambda draft_id: __import__(
            "app.services.draft_video_export_jobs",
            fromlist=["run_draft_video_export_task"],
        ).run_draft_video_export_task({"draft_id": draft_id}),
    )
    draft = client.post("/api/drafts", json={"title": "拼音草稿"}).json()
    client.post(
        f"/api/drafts/{draft['id']}/items",
        json={"edited_text": "你的选择越还越多，先别急着定。"},
    )

    response = client.post(f"/api/drafts/{draft['id']}/video-exports")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "finished"
    assert payload["result"]["result"]["tts_script"] == "你的选择越[huán]越多，先别急着定。"


def test_draft_video_export_invalid_llm_json_fails(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.draft_video_export.get_llm_client",
        lambda: _InvalidVideoExportLLM(),
    )
    monkeypatch.setattr(
        "app.api.routes.drafts.enqueue_draft_video_export",
        lambda draft_id: __import__(
            "app.services.draft_video_export_jobs",
            fromlist=["run_draft_video_export_task"],
        ).run_draft_video_export_task({"draft_id": draft_id}),
    )
    draft = client.post("/api/drafts", json={"title": "格式失败草稿"}).json()
    draft_id = draft["id"]
    client.post(f"/api/drafts/{draft_id}/items", json={"edited_text": "测试正文"})

    response = client.post(f"/api/drafts/{draft_id}/video-exports")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed"
    assert "invalid video export JSON" in payload["error"]
    assert client.get(f"/api/drafts/{draft_id}/video-exports").json()["total"] == 0


def test_invalid_persisted_video_export_history_record_is_skipped() -> None:
    class Row:
        id = "00000000-0000-0000-0000-000000000001"
        draft_id = "00000000-0000-0000-0000-000000000002"
        status = "finished"
        result_json = {
            "title": "Legacy",
            "title_break": "Legacy",
            "description": "Legacy persisted video export record.",
            "script": "Original script text",
            "tts_script": "Different TTS text",
            "hashtags": ["legacy"],
        }
        model = "legacy-model"
        error = None
        metadata_json = {}
        created_at = None
        updated_at = None

    assert draft_video_export._record_from_model(Row()) is None
