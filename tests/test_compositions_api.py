from fastapi.testclient import TestClient

from app.main import app
from app.services.compositions import reset_composition_store
from app.services.copy_assets import reset_copy_asset_store
from app.services.drafts import reset_draft_store
from app.services.knowledge import reset_knowledge_store
from app.workers import tasks


client = TestClient(app)


class FakeCompositionLLMClient:
    model = "fake-composition-model"

    def complete(self, prompt: str) -> str:
        return """{
            "candidates": [
                {
                    "title": "Routine launch A",
                    "strategy": "Use direct proof from approved fragments.",
                    "items": [
                        {
                            "role": "hook",
                            "position": "opening",
                            "text": "Check your routine before changing products.",
                            "quote_mode": "direct",
                            "reference_fragment_ids": ["FRAGMENT_ID"],
                            "reason": "Approved hook fits the brief."
                        },
                        {
                            "role": "pain_point",
                            "position": "body",
                            "text": "Many routines fail because the order is unclear.",
                            "quote_mode": "original",
                            "reference_fragment_ids": [],
                            "reason": "Summarizes the core pain."
                        },
                        {
                            "role": "solution",
                            "position": "body",
                            "text": "Put the hydrating step before the sealing step.",
                            "quote_mode": "original",
                            "reference_fragment_ids": [],
                            "reason": "Turns the point into action."
                        },
                        {
                            "role": "proof",
                            "position": "body",
                            "text": "The order can change how the same products feel.",
                            "quote_mode": "adapted",
                            "reference_fragment_ids": ["FRAGMENT_ID"],
                            "reason": "Adapts source proof."
                        },
                        {
                            "role": "cta",
                            "position": "ending",
                            "text": "Try checking the order tonight.",
                            "quote_mode": "original",
                            "reference_fragment_ids": [],
                            "reason": "Low-friction action."
                        }
                    ]
                }
            ]
        }""".replace("FRAGMENT_ID", _current_fragment_id)


class EmptyReferenceLLMClient:
    model = "fake-composition-model"

    def complete(self, prompt: str) -> str:
        return """{
            "candidates": [
                {
                    "title": "Fallback A",
                    "strategy": "Generate from brief only.",
                    "items": [
                        {"role": "hook", "position": "opening", "text": "Start from the brief.", "quote_mode": "original", "reference_fragment_ids": [], "reason": "No source."},
                        {"role": "pain_point", "position": "body", "text": "Name the pain.", "quote_mode": "original", "reference_fragment_ids": [], "reason": "No source."},
                        {"role": "solution", "position": "body", "text": "Show the solution.", "quote_mode": "original", "reference_fragment_ids": [], "reason": "No source."},
                        {"role": "proof", "position": "body", "text": "Make it credible.", "quote_mode": "original", "reference_fragment_ids": [], "reason": "No source."},
                        {"role": "cta", "position": "ending", "text": "Invite action.", "quote_mode": "original", "reference_fragment_ids": [], "reason": "No source."}
                    ]
                }
            ]
        }"""


_current_fragment_id = ""


def setup_function() -> None:
    global _current_fragment_id
    _current_fragment_id = ""
    tasks._TASKS.clear()
    reset_copy_asset_store()
    reset_knowledge_store()
    reset_draft_store()
    reset_composition_store()


def _brief() -> dict:
    return {
        "product": "routine",
        "audience": "new users",
        "platform": "xhs",
        "purpose": "conversion",
        "style": "practical",
        "key_selling_points": ["order"],
    }


def _create_approved_fragment() -> str:
    raw_response = client.post(
        "/api/knowledge/raw-copies",
        json={
            "source_text": "Check your routine before changing products.",
            "platform": "xhs",
            "audience": "new users",
            "purpose": "conversion",
        },
    )
    assert raw_response.status_code == 200
    fragment_response = client.post(
        "/api/knowledge/fragments",
        json={
            "source_copy_id": raw_response.json()["id"],
            "sequence_order": 0,
            "fragment_text": "Check your routine before changing products.",
            "fragment_role": "hook",
            "position": "opening",
            "platform": "xhs",
            "audience": "new users",
            "purpose": "conversion",
            "source_quality": "high",
            "risk_level": "low",
            "status": "approved",
            "confidence": 0.93,
        },
    )
    assert fragment_response.status_code == 200
    return fragment_response.json()["id"]


def _run_composition(monkeypatch, llm_client, brief: dict | None = None) -> dict:
    monkeypatch.setattr("app.services.compositions.get_llm_client", lambda: llm_client)
    monkeypatch.setattr(
        "app.api.routes.compositions.enqueue_auto_composition",
        lambda payload: __import__(
            "app.services.composition_jobs", fromlist=["run_auto_composition_task"]
        ).run_auto_composition_task(payload.model_dump()),
    )
    response = client.post("/api/compositions/auto-draft", json={"brief": brief or _brief()})
    assert response.status_code == 200
    task_payload = client.get(f"/api/tasks/{response.json()['task_id']}").json()
    assert task_payload["status"] == "finished"
    return task_payload


def test_auto_composition_task_returns_three_candidates_with_references(monkeypatch) -> None:
    global _current_fragment_id
    _current_fragment_id = _create_approved_fragment()

    task_payload = _run_composition(monkeypatch, FakeCompositionLLMClient())
    result = task_payload["result"]

    assert result["model"] == "fake-composition-model"
    assert result["fallback_reason"] is None
    assert len(result["candidates"]) == 3
    assert all(len(candidate["items"]) == 5 for candidate in result["candidates"])
    assert result["reference_fragments"][0]["id"] == _current_fragment_id
    assert result["candidates"][0]["items"][0]["quote_mode"] == "direct"
    assert result["candidates"][0]["items"][0]["reference_fragment_ids"] == [
        _current_fragment_id
    ]


def test_auto_composition_prefers_semantic_fragment_retrieval(monkeypatch) -> None:
    global _current_fragment_id
    _current_fragment_id = _create_approved_fragment()

    class FakeRetriever:
        def retrieve(self, query, limit=5, filters=None):
            assert "routine" in query
            assert filters["status"] == "approved"
            return [
                type(
                    "Retrieved",
                    (),
                    {"metadata": {"fragment_id": _current_fragment_id}},
                )()
            ]

    monkeypatch.setattr("app.services.compositions.CopyKnowledgeRetriever", lambda: FakeRetriever())
    task_payload = _run_composition(monkeypatch, FakeCompositionLLMClient())

    assert task_payload["result"]["reference_fragments"][0]["id"] == _current_fragment_id


def test_auto_composition_backs_filled_reference_ids_when_llm_omits_them(monkeypatch) -> None:
    global _current_fragment_id
    _current_fragment_id = _create_approved_fragment()

    task_payload = _run_composition(monkeypatch, EmptyReferenceLLMClient())
    first_item = task_payload["result"]["candidates"][0]["items"][0]

    assert task_payload["result"]["fallback_reason"] is None
    assert task_payload["result"]["reference_fragments"][0]["id"] == _current_fragment_id
    assert first_item["quote_mode"] == "adapted"
    assert first_item["reference_fragment_ids"] == [_current_fragment_id]


def test_auto_composition_keyword_fallback_expands_chinese_brief(monkeypatch) -> None:
    global _current_fragment_id
    raw_response = client.post(
        "/api/knowledge/raw-copies",
        json={
            "source_text": "现在买房首付、贷款年限和还款方式都要提前算清楚。",
            "platform": "douyin",
            "audience": "expert_buyers",
            "purpose": "conversion",
        },
    )
    assert raw_response.status_code == 200
    fragment_response = client.post(
        "/api/knowledge/fragments",
        json={
            "source_copy_id": raw_response.json()["id"],
            "sequence_order": 0,
            "fragment_text": "现在买房首付是多付一点好还是少付一点好，贷款年限和还款方式都要提前算清楚。",
            "fragment_role": "hook",
            "position": "opening",
            "platform": "douyin",
            "audience": "expert_buyers",
            "purpose": "conversion",
            "source_quality": "high",
            "risk_level": "low",
            "status": "approved",
            "confidence": 0.93,
        },
    )
    assert fragment_response.status_code == 200
    _current_fragment_id = fragment_response.json()["id"]

    class EmptyRetriever:
        def retrieve(self, query, limit=5, filters=None):
            return []

    monkeypatch.setattr("app.services.compositions.CopyKnowledgeRetriever", lambda: EmptyRetriever())
    brief = {
        "product": "买房月供减压指南",
        "audience": "expert_buyers",
        "platform": "douyin",
        "purpose": "conversion",
        "style": "practical",
        "key_selling_points": ["识别隐藏成本", "选择利率方式", "安排还款方式"],
    }
    task_payload = _run_composition(monkeypatch, FakeCompositionLLMClient(), brief)

    assert task_payload["result"]["fallback_reason"] is None
    assert task_payload["result"]["reference_fragments"][0]["id"] == _current_fragment_id


def test_auto_composition_falls_back_without_matching_fragments(monkeypatch) -> None:
    task_payload = _run_composition(monkeypatch, EmptyReferenceLLMClient())
    result = task_payload["result"]

    assert result["fallback_reason"] == "no_matching_fragments"
    assert result["reference_fragments"] == []
    assert len(result["candidates"]) == 3
    for candidate in result["candidates"]:
        assert len(candidate["items"]) == 5
        assert all(item["quote_mode"] == "original" for item in candidate["items"])
        assert all(item["reference_fragment_ids"] == [] for item in candidate["items"])


def test_accept_composition_creates_draft_items_and_records_provenance(monkeypatch) -> None:
    global _current_fragment_id
    _current_fragment_id = _create_approved_fragment()
    task_payload = _run_composition(monkeypatch, FakeCompositionLLMClient())
    candidate_id = task_payload["result"]["candidates"][0]["candidate_id"]

    response = client.post(
        "/api/compositions/accepted",
        json={"task_id": task_payload["task_id"], "candidate_id": candidate_id},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"]["task_id"] == task_payload["task_id"]
    assert payload["accepted"]["candidate_id"] == candidate_id
    assert payload["draft"]["title"] == "Routine launch A"
    assert payload["draft"]["item_count"] == 5
    first_item = payload["draft"]["items"][0]
    assert first_item["source_fragment_id"] == _current_fragment_id
    assert first_item["source_copy_id"]
    assert first_item["metadata"]["quote_mode"] == "direct"
    assert first_item["metadata"]["generation_task_id"] == task_payload["task_id"]
    assert first_item["metadata"]["generation_candidate_id"] == candidate_id
    assert first_item["metadata"]["reference_fragment_ids"] == [_current_fragment_id]


def test_accept_composition_returns_404_for_missing_candidate(monkeypatch) -> None:
    task_payload = _run_composition(monkeypatch, EmptyReferenceLLMClient())

    response = client.post(
        "/api/compositions/accepted",
        json={"task_id": task_payload["task_id"], "candidate_id": "missing"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Composition candidate not found"
