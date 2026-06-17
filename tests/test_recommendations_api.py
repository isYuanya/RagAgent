from fastapi.testclient import TestClient

from app.main import app
from app.services.copy_assets import reset_copy_asset_store
from app.services.drafts import reset_draft_store
from app.services.knowledge import reset_knowledge_store
from app.services.recommendations import reset_recommendation_store


client = TestClient(app)


class FakeRecommendationLLMClient:
    model = "fake-recommendation-model"

    def complete(self, prompt: str) -> str:
        return """{
            "next_function": "proof",
            "candidates": [
                {
                    "text": "Show one concrete result so the reader knows what changed.",
                    "function": "proof",
                    "reason": "The draft has a pain point and now needs evidence.",
                    "tone": "specific and calm",
                    "suggested_order_index": 1,
                    "risk_warnings": [],
                    "reference_fragment_ids": []
                },
                {
                    "text": "Use a small before-after detail here, but avoid promising guaranteed results.",
                    "function": "proof",
                    "reason": "A before-after detail supports the claim without over-selling.",
                    "tone": "practical",
                    "suggested_order_index": 1,
                    "risk_warnings": [
                        {
                            "level": "medium",
                            "message": "Avoid guaranteed outcome wording.",
                            "suggestion": "Keep the result framed as an example."
                        }
                    ],
                    "reference_fragment_ids": []
                }
            ]
        }"""


def setup_function() -> None:
    reset_copy_asset_store()
    reset_knowledge_store()
    reset_draft_store()
    reset_recommendation_store()


def _create_draft_with_fragment() -> tuple[str, str]:
    raw_response = client.post(
        "/api/knowledge/raw-copies",
        json={
            "source_text": "Start with a pain point, then prove the reason with a concrete result.",
            "platform": "xhs",
            "audience": "new users",
            "purpose": "conversion",
        },
    )
    assert raw_response.status_code == 200
    raw_id = raw_response.json()["id"]

    fragment_response = client.post(
        "/api/knowledge/fragments",
        json={
            "source_copy_id": raw_id,
            "sequence_order": 0,
            "fragment_text": "Then prove the reason with one concrete result.",
            "fragment_role": "proof",
            "position": "body",
            "platform": "xhs",
            "audience": "new users",
            "purpose": "conversion",
            "source_quality": "high",
            "risk_level": "low",
            "status": "approved",
            "confidence": 0.91,
        },
    )
    assert fragment_response.status_code == 200
    fragment_id = fragment_response.json()["id"]

    draft_response = client.post(
        "/api/drafts",
        json={
            "title": "Recommendation draft",
            "audience": "new users",
            "platform": "xhs",
            "purpose": "conversion",
        },
    )
    assert draft_response.status_code == 200
    draft_id = draft_response.json()["id"]

    add_response = client.post(
        f"/api/drafts/{draft_id}/items",
        json={"edited_text": "If your routine feels useless, check the order first."},
    )
    assert add_response.status_code == 200
    return draft_id, fragment_id


def test_next_sentence_recommendation_task_returns_candidates(monkeypatch) -> None:
    draft_id, fragment_id = _create_draft_with_fragment()
    monkeypatch.setattr(
        "app.services.recommendations.get_llm_client",
        lambda: FakeRecommendationLLMClient(),
    )
    monkeypatch.setattr(
        "app.api.routes.recommendations.enqueue_next_sentence_recommendation",
        lambda payload: __import__(
            "app.services.recommendation_jobs", fromlist=["run_next_sentence_task"]
        ).run_next_sentence_task(payload.model_dump()),
    )

    response = client.post(
        "/api/recommendations/next-sentence",
        json={"draft_id": draft_id, "candidate_count": 2},
    )

    assert response.status_code == 200
    task_id = response.json()["task_id"]
    task_response = client.get(f"/api/tasks/{task_id}")
    assert task_response.status_code == 200
    task_payload = task_response.json()
    assert task_payload["status"] == "finished"
    assert task_payload["progress"]["phase"] == "finished"
    assert task_payload["progress"]["model"]

    result = task_payload["result"]
    assert result["draft_id"] == draft_id
    assert result["next_function"] == "proof"
    assert result["model"] == "fake-recommendation-model"
    assert len(result["candidates"]) == 2
    assert result["candidates"][0]["candidate_id"]
    assert result["candidates"][0]["text"].startswith("Show one concrete result")
    assert result["reference_fragments"][0]["id"] == fragment_id
    assert result["reference_fragments"][0]["text"] == "Then prove the reason with one concrete result."


def test_accept_recommendation_inserts_draft_item_and_records_acceptance(monkeypatch) -> None:
    draft_id, _fragment_id = _create_draft_with_fragment()
    monkeypatch.setattr(
        "app.services.recommendations.get_llm_client",
        lambda: FakeRecommendationLLMClient(),
    )
    monkeypatch.setattr(
        "app.api.routes.recommendations.enqueue_next_sentence_recommendation",
        lambda payload: __import__(
            "app.services.recommendation_jobs", fromlist=["run_next_sentence_task"]
        ).run_next_sentence_task(payload.model_dump()),
    )

    task_response = client.post(
        "/api/recommendations/next-sentence",
        json={"draft_id": draft_id, "candidate_count": 2},
    )
    result = client.get(f"/api/tasks/{task_response.json()['task_id']}").json()["result"]
    candidate_id = result["candidates"][0]["candidate_id"]

    accept_response = client.post(
        "/api/recommendations/accepted",
        json={
            "draft_id": draft_id,
            "task_id": task_response.json()["task_id"],
            "candidate_id": candidate_id,
        },
    )

    assert accept_response.status_code == 200
    payload = accept_response.json()
    assert payload["accepted"]["draft_id"] == draft_id
    assert payload["accepted"]["candidate_id"] == candidate_id
    assert payload["accepted"]["inserted_draft_item_id"]
    assert payload["draft"]["item_count"] == 2
    assert payload["draft"]["items"][1]["edited_text"].startswith("Show one concrete result")
