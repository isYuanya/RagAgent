from fastapi.testclient import TestClient

from app.main import app
from app.services.compositions import reset_composition_store
from app.services.copy_assets import reset_copy_asset_store
from app.services.drafts import reset_draft_store
from app.services.knowledge import reset_knowledge_store
from app.services.smart_composition import reset_smart_composition_store
from app.workers import tasks


client = TestClient(app)

_current_fragment_id = ""


class FakeCompositionLLMClient:
    model = "fake-composition-model"

    def complete(self, prompt: str) -> str:
        return """{
            "candidates": [
                {
                    "title": "Routine launch A",
                    "strategy": "Use source proof first.",
                    "items": [
                        {"role": "hook", "position": "opening", "text": "Check your routine before changing products.", "quote_mode": "direct", "reference_fragment_ids": ["FRAGMENT_ID"], "reason": "Strong matching hook."},
                        {"role": "pain_point", "position": "body", "text": "Many routines fail because the order is unclear.", "quote_mode": "original", "reference_fragment_ids": [], "reason": "Names the core pain."},
                        {"role": "solution", "position": "body", "text": "Put the hydrating step before the sealing step.", "quote_mode": "original", "reference_fragment_ids": [], "reason": "Gives an action."},
                        {"role": "proof", "position": "body", "text": "The same products can feel different when the order changes.", "quote_mode": "adapted", "reference_fragment_ids": ["FRAGMENT_ID"], "reason": "Adapts the proof."},
                        {"role": "cta", "position": "ending", "text": "Try checking the order tonight.", "quote_mode": "original", "reference_fragment_ids": [], "reason": "Low-friction CTA."}
                    ]
                },
                {
                    "title": "Routine launch B",
                    "strategy": "More direct conversion angle.",
                    "items": [
                        {"role": "hook", "position": "opening", "text": "Your routine may not need more products.", "quote_mode": "original", "reference_fragment_ids": [], "reason": "Contrarian hook."},
                        {"role": "pain_point", "position": "body", "text": "Buying more does not fix a confusing order.", "quote_mode": "original", "reference_fragment_ids": [], "reason": "Pain."},
                        {"role": "solution", "position": "body", "text": "Start by checking the order.", "quote_mode": "original", "reference_fragment_ids": [], "reason": "Solution."},
                        {"role": "proof", "position": "body", "text": "Order changes the experience.", "quote_mode": "original", "reference_fragment_ids": [], "reason": "Proof."},
                        {"role": "cta", "position": "ending", "text": "Save this checklist.", "quote_mode": "original", "reference_fragment_ids": [], "reason": "CTA."}
                    ]
                },
                {
                    "title": "Routine launch C",
                    "strategy": "Short version.",
                    "items": [
                        {"role": "hook", "position": "opening", "text": "Before replacing products, check the order.", "quote_mode": "original", "reference_fragment_ids": [], "reason": "Hook."},
                        {"role": "pain_point", "position": "body", "text": "The order is easy to miss.", "quote_mode": "original", "reference_fragment_ids": [], "reason": "Pain."},
                        {"role": "solution", "position": "body", "text": "Use a simple sequence.", "quote_mode": "original", "reference_fragment_ids": [], "reason": "Solution."},
                        {"role": "proof", "position": "body", "text": "Small changes are easier to test.", "quote_mode": "original", "reference_fragment_ids": [], "reason": "Proof."},
                        {"role": "cta", "position": "ending", "text": "Try it once.", "quote_mode": "original", "reference_fragment_ids": [], "reason": "CTA."}
                    ]
                }
            ]
        }""".replace("FRAGMENT_ID", _current_fragment_id)


class FakeDiagnosticLLMClient:
    model = "fake-diagnostic-model"

    def complete(self, prompt: str) -> str:
        return """{
            "summary": "Opening is clear, CTA can be stronger.",
            "overall_level": "fair",
            "dimensions": [
                {"dimension": "opening_attractiveness", "level": "strong", "reason": "Clear first sentence.", "suggestion": "Keep it concrete."},
                {"dimension": "conversion_action", "level": "fair", "reason": "CTA is usable but soft.", "suggestion": "Make the action more specific."}
            ],
            "sentence_issues": [],
            "rewrite_candidates": [
                {"candidate_id": "safe", "mode": "compliance_safe", "title": "Safe final", "text": "Final rewritten copy with a safer promise.", "reason": "Keeps the action clear."},
                {"candidate_id": "conversion", "mode": "conversion", "title": "Conversion final", "text": "Final rewritten copy with a stronger CTA.", "reason": "Stronger close."}
            ],
            "risk_warnings": []
        }"""


class FakeJudgeLLMClient:
    model = "fake-judge-model"

    def complete(self, prompt: str) -> str:
        if "best candidate" in prompt:
            return '{"selected_id":"missing","reason":"Uses source proof and complete structure."}'
        if "best rewrite" in prompt:
            return '{"selected_id":"safe","reason":"Safer final text."}'
        return """{
            "product": "routine",
            "audience": "new users",
            "platform": "xhs",
            "purpose": "conversion",
            "style": "practical",
            "key_selling_points": ["order"],
            "confidence": 0.8,
            "notes": ["Parsed from plain text."]
        }"""


def setup_function() -> None:
    global _current_fragment_id
    _current_fragment_id = ""
    tasks._TASKS.clear()
    reset_copy_asset_store()
    reset_knowledge_store()
    reset_draft_store()
    reset_composition_store()
    reset_smart_composition_store()


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


def test_auto_run_finishes_and_saves_initial_and_final_versions(monkeypatch) -> None:
    global _current_fragment_id
    _current_fragment_id = _create_approved_fragment()
    monkeypatch.setattr("app.services.compositions.get_llm_client", lambda: FakeCompositionLLMClient())
    monkeypatch.setattr("app.services.diagnostics.get_llm_client", lambda: FakeDiagnosticLLMClient())
    monkeypatch.setattr(
        "app.services.smart_composition.get_llm_client",
        lambda: FakeJudgeLLMClient(),
    )

    response = client.post("/api/assistant/runs", json={"mode": "auto", "brief": _brief()})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "finished"
    assert payload["draft_id"]
    assert payload["initial_version_id"]
    assert payload["final_version_id"]
    assert payload["result"]["draft"]["current_text"] == "Final rewritten copy with a safer promise."
    assert payload["result"]["composition"]["model"] == "fake-composition-model"
    assert payload["result"]["diagnosis"]["model"] == "fake-diagnostic-model"
    assert payload["result"]["rewrite_selection"]["method"] == "llm_judge"
    assert all(step["status"] == "completed" for step in payload["timeline"])

    versions = client.get(f"/api/drafts/{payload['draft_id']}/versions").json()
    assert len(versions) == 2
    version_ids = {item["id"] for item in versions}
    assert payload["final_version_id"] in version_ids
    assert payload["initial_version_id"] in version_ids

    list_response = client.get("/api/assistant/runs")
    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["id"] == payload["id"]


def test_guided_run_pauses_after_generating_composition(monkeypatch) -> None:
    global _current_fragment_id
    _current_fragment_id = _create_approved_fragment()
    monkeypatch.setattr("app.services.compositions.get_llm_client", lambda: FakeCompositionLLMClient())

    response = client.post("/api/assistant/runs", json={"mode": "guided", "brief": _brief()})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "waiting_for_user"
    assert payload["draft_id"] is None
    assert payload["result"]["composition"]["candidates"]
    assert any(step["status"] == "waiting_for_user" for step in payload["timeline"])


def test_brief_prefill_returns_structured_options(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.smart_composition.get_llm_client",
        lambda: FakeJudgeLLMClient(),
    )

    response = client.post(
        "/api/assistant/brief-prefill",
        json={"text": "For xhs, write a conversion post about routine order for new users."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["brief"]["product"] == "routine"
    assert payload["brief"]["key_selling_points"] == ["order"]
    assert payload["confidence"] == 0.8
