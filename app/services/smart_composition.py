import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command, interrupt

from app.core.config import settings
from app.core.llm import get_llm_client
from app.db.session import SessionLocal
from app.models.smart_composition import SmartCompositionRun as SmartCompositionRunModel
from app.schemas.composition import AutoCompositionBrief, AutoCompositionRequest, CompositionCandidate
from app.schemas.diagnostic import CopyDiagnosisRequest, RewriteCandidate
from app.schemas.draft import DraftCreate, DraftItemCreate, DraftVersionCreate
from app.schemas.smart_composition import (
    ConfirmCompositionRequest,
    ConfirmMaterialsRequest,
    ConfirmRewriteRequest,
    SmartCompositionBrief,
    SmartCompositionBriefPrefillRequest,
    SmartCompositionBriefPrefillResponse,
    SmartCompositionOption,
    SmartCompositionOptions,
    SmartCompositionRunCreate,
    SmartCompositionRunDetail,
    SmartCompositionRunListResponse,
    SmartCompositionRunSummary,
    SmartCompositionSelection,
    SmartCompositionStep,
    SmartCompositionStepId,
)
from app.services import compositions, diagnostics, drafts, knowledge
from app.workflows.smart_composition import (
    SmartCompositionGraphNodes,
    SmartCompositionGraphState,
    build_smart_composition_graph,
)


class SmartCompositionRunNotFoundError(Exception):
    pass


class SmartCompositionError(Exception):
    pass


class SmartCompositionInvalidResumeError(Exception):
    pass


class SmartCompositionInvalidSelectionError(Exception):
    pass


@dataclass
class _Store:
    runs: dict[str, SmartCompositionRunDetail] = field(default_factory=dict)


class _JudgeResponse(BaseModel):
    selected_id: str
    reason: str = ""


class _PrefillResponse(BaseModel):
    product: str = ""
    audience: str = ""
    platform: str = ""
    purpose: str = ""
    style: str = ""
    key_selling_points: list[str] = Field(default_factory=list)
    constraints: str | None = None
    target_length: str | None = None
    extra_notes: str | None = None
    confidence: float = Field(default=0.5, ge=0, le=1)
    notes: list[str] = Field(default_factory=list)


_store = _Store()
_db_available: bool | None = False if settings.app_env == "test" else None
_checkpointer = InMemorySaver()
_compiled_graph = None


STEP_DEFINITIONS: list[tuple[SmartCompositionStepId, str, int]] = [
    ("brief_prefill", "brief parsing", 5),
    ("knowledge_retrieval", "knowledge retrieval", 15),
    ("composition_generation", "composition candidate generation", 35),
    ("composition_selection", "composition candidate selection", 45),
    ("initial_draft_save", "initial draft version save", 55),
    ("diagnosis", "initial draft diagnosis", 70),
    ("rewrite_selection", "rewrite candidate selection", 85),
    ("final_draft_save", "final draft version save", 100),
]


def reset_smart_composition_store() -> None:
    global _checkpointer, _compiled_graph, _db_available, _store
    _store = _Store()
    _db_available = False if settings.app_env == "test" else None
    _checkpointer = InMemorySaver()
    _compiled_graph = None


def get_options() -> SmartCompositionOptions:
    collections = knowledge.list_collections(page=1, page_size=100).items
    return SmartCompositionOptions(
        collections=collections,
        platforms=[
            SmartCompositionOption(value="xhs", label="小红书"),
            SmartCompositionOption(value="douyin", label="抖音"),
            SmartCompositionOption(value="wechat", label="公众号"),
            SmartCompositionOption(value="video_account", label="视频号"),
        ],
        purposes=[
            SmartCompositionOption(value="conversion", label="转化"),
            SmartCompositionOption(value="traffic", label="引流"),
            SmartCompositionOption(value="engagement", label="互动"),
            SmartCompositionOption(value="brand", label="品牌心智"),
        ],
        audiences=[
            SmartCompositionOption(value="new_users", label="新用户"),
            SmartCompositionOption(value="returning_users", label="老用户"),
            SmartCompositionOption(value="price_sensitive", label="价格敏感人群"),
            SmartCompositionOption(value="expert_buyers", label="专业决策人群"),
        ],
        styles=[
            SmartCompositionOption(value="practical", label="干货型"),
            SmartCompositionOption(value="empathetic", label="共情型"),
            SmartCompositionOption(value="professional", label="专业型"),
            SmartCompositionOption(value="storytelling", label="故事型"),
        ],
    )


def prefill_brief(payload: SmartCompositionBriefPrefillRequest) -> SmartCompositionBriefPrefillResponse:
    llm = get_llm_client()
    raw = llm.complete(_build_prefill_prompt(payload.text))
    model = getattr(llm, "model", settings.openai_model)
    try:
        parsed = _PrefillResponse.model_validate(json.loads(_strip_json_fence(raw)))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise SmartCompositionError(f"LLM returned invalid brief prefill JSON: {exc}") from exc
    brief = SmartCompositionBrief(
        product=parsed.product or "待确认产品",
        audience=parsed.audience or "待确认人群",
        platform=parsed.platform or "xhs",
        purpose=parsed.purpose or "conversion",
        style=parsed.style or "practical",
        key_selling_points=parsed.key_selling_points or ["待确认卖点"],
        constraints=parsed.constraints,
        target_length=parsed.target_length,
        extra_notes=parsed.extra_notes,
    )
    return SmartCompositionBriefPrefillResponse(
        brief=brief,
        confidence=parsed.confidence,
        notes=parsed.notes,
        model=model,
    )


def create_run(payload: SmartCompositionRunCreate) -> SmartCompositionRunDetail:
    run = _new_run(payload)
    try:
        result = _invoke_graph(run.id, {"run": run.model_dump(mode="json")})
        next_run = _run_from_graph_result(result)
        return _save_run(_apply_graph_completion(next_run, result))
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)
        _mark_running_step_failed(run, str(exc))
        _save_run(run)
        raise


def confirm_materials(
    run_id: str,
    payload: ConfirmMaterialsRequest,
) -> SmartCompositionRunDetail:
    return _resume_run(run_id, "confirm_materials", payload.model_dump(mode="json"))


def confirm_composition(
    run_id: str,
    payload: ConfirmCompositionRequest,
) -> SmartCompositionRunDetail:
    return _resume_run(run_id, "confirm_composition", payload.model_dump(mode="json"))


def confirm_rewrite(
    run_id: str,
    payload: ConfirmRewriteRequest,
) -> SmartCompositionRunDetail:
    return _resume_run(run_id, "confirm_rewrite", payload.model_dump(mode="json"))


def list_runs(page: int = 1, page_size: int = 20) -> SmartCompositionRunListResponse:
    db_response = _db_list_runs(page, page_size)
    if db_response is not None:
        return db_response
    items = sorted(_store.runs.values(), key=lambda item: item.created_at, reverse=True)
    summaries = [_summary(item) for item in items]
    start = (page - 1) * page_size
    return SmartCompositionRunListResponse(
        items=summaries[start : start + page_size],
        page=page,
        page_size=page_size,
        total=len(summaries),
    )


def get_run(run_id: str) -> SmartCompositionRunDetail | None:
    db_item = _db_get_run(run_id)
    if db_item is not None:
        return db_item
    return _store.runs.get(run_id)


def _resume_run(
    run_id: str,
    expected_interrupt: str,
    resume_payload: dict,
) -> SmartCompositionRunDetail:
    run = get_run(run_id)
    if run is None:
        raise SmartCompositionRunNotFoundError()
    pending = run.metadata.get("pending_interrupt")
    if not isinstance(pending, dict) or pending.get("type") != expected_interrupt:
        raise SmartCompositionInvalidResumeError()
    try:
        result = _invoke_graph(run_id, Command(resume=resume_payload))
        next_run = _run_from_graph_result(result)
        return _save_run(_apply_graph_completion(next_run, result))
    except (SmartCompositionInvalidResumeError, SmartCompositionInvalidSelectionError):
        raise
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)
        _mark_running_step_failed(run, str(exc))
        _save_run(run)
        raise


def _invoke_graph(run_id: str, payload) -> dict:
    graph = _get_graph()
    config = {"configurable": {"thread_id": run_id}}
    return graph.invoke(payload, config)


def _get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        graph = build_smart_composition_graph(
            SmartCompositionGraphNodes(
                prepare=_graph_prepare,
                retrieve_materials=_graph_retrieve_materials,
                confirm_materials=_graph_confirm_materials,
                generate_composition=_graph_generate_composition,
                confirm_composition=_graph_confirm_composition,
                save_initial_draft=_graph_save_initial_draft,
                diagnose=_graph_diagnose,
                confirm_rewrite=_graph_confirm_rewrite,
                save_final_draft=_graph_save_final_draft,
            )
        )
        _compiled_graph = graph.compile(checkpointer=_checkpointer)
    return _compiled_graph


def _apply_graph_completion(
    run: SmartCompositionRunDetail,
    result: dict,
) -> SmartCompositionRunDetail:
    interrupts = result.get("__interrupt__") or []
    if interrupts:
        interrupt_value = getattr(interrupts[0], "value", {})
        return _apply_interrupt(run, interrupt_value if isinstance(interrupt_value, dict) else {})
    run.status = "finished"
    run.metadata.pop("pending_interrupt", None)
    return run


def _apply_interrupt(run: SmartCompositionRunDetail, payload: dict) -> SmartCompositionRunDetail:
    interrupt_type = str(payload.get("type") or "")
    run.status = "waiting_for_user"
    run.metadata["pending_interrupt"] = payload
    if interrupt_type == "confirm_materials":
        _set_step(
            run,
            "composition_generation",
            "waiting_for_user",
            message="Waiting for material confirmation.",
            metadata=payload,
        )
    elif interrupt_type == "confirm_composition":
        _set_step(
            run,
            "composition_selection",
            "waiting_for_user",
            message="Waiting for composition candidate confirmation.",
            metadata=payload,
        )
    elif interrupt_type == "confirm_rewrite":
        _set_step(
            run,
            "rewrite_selection",
            "waiting_for_user",
            message="Waiting for rewrite confirmation.",
            metadata=payload,
        )
    return run


def _run_from_graph_result(result: dict) -> SmartCompositionRunDetail:
    run_data = result.get("run")
    if not isinstance(run_data, dict):
        raise SmartCompositionError("Graph did not return a smart composition run.")
    return SmartCompositionRunDetail.model_validate(run_data)


def _graph_prepare(state: SmartCompositionGraphState) -> SmartCompositionGraphState:
    run = _state_run(state)
    run.status = "running"
    run.metadata.pop("pending_interrupt", None)
    _set_step(run, "brief_prefill", "completed", message="Brief options accepted.")
    _set_step(run, "knowledge_retrieval", "running", message="Retrieving reference materials.")
    return _state_update(run)


def _graph_retrieve_materials(state: SmartCompositionGraphState) -> SmartCompositionGraphState:
    run = _state_run(state)
    materials = compositions.retrieve_reference_fragments(_composition_brief(run.brief))
    run.result.materials = materials
    run.material_ids = [item.id for item in materials]
    _set_step(
        run,
        "knowledge_retrieval",
        "completed",
        message=f"Retrieved {len(materials)} reference fragments.",
        metadata={"material_ids": run.material_ids},
    )
    return _state_update(run)


def _graph_confirm_materials(state: SmartCompositionGraphState) -> SmartCompositionGraphState:
    run = _state_run(state)
    if run.mode == "guided":
        payload = interrupt(
            {
                "type": "confirm_materials",
                "materials": [item.model_dump(mode="json") for item in run.result.materials],
                "material_ids": run.material_ids,
            }
        )
        selected_ids = _coerce_str_list(payload.get("material_ids") if isinstance(payload, dict) else [])
        _validate_known_ids(selected_ids, run.material_ids, "Unknown material id")
        if selected_ids:
            by_id = {item.id: item for item in run.result.materials}
            run.result.materials = [by_id[item_id] for item_id in selected_ids]
            run.material_ids = selected_ids
    _set_step(run, "composition_generation", "running", message="Generating candidates.")
    return _state_update(run)


def _graph_generate_composition(state: SmartCompositionGraphState) -> SmartCompositionGraphState:
    run = _state_run(state)
    composition = compositions.generate_auto_composition_from_references(
        AutoCompositionRequest(brief=_composition_brief(run.brief)),
        run.result.materials,
    )
    run.result.composition = composition
    run.result.materials = composition.reference_fragments
    run.material_ids = [item.id for item in composition.reference_fragments]
    _set_step(
        run,
        "composition_generation",
        "completed",
        model=composition.model,
        message="Generated composition candidates.",
    )
    return _state_update(run)


def _graph_confirm_composition(state: SmartCompositionGraphState) -> SmartCompositionGraphState:
    run = _state_run(state)
    composition = _require_composition(run)
    _set_step(run, "composition_selection", "running", message="Selecting composition candidate.")
    if run.mode == "guided":
        payload = interrupt(
            {
                "type": "confirm_composition",
                "candidates": [item.model_dump(mode="json") for item in composition.candidates],
            }
        )
        candidate_id = payload.get("candidate_id") if isinstance(payload, dict) else None
        candidate = _find_candidate(composition.candidates, candidate_id)
        selection = SmartCompositionSelection(
            selected_id=candidate.candidate_id,
            method="user",
            reason="Selected by user confirmation.",
        )
    else:
        candidate, selection = _select_candidate(composition.candidates)
    run.result.selected_candidate = candidate
    run.result.composition_selection = selection
    run.selected_candidate_id = candidate.candidate_id
    _set_step(
        run,
        "composition_selection",
        "completed",
        model=selection.judge_model,
        reason=selection.reason,
        metadata=selection.model_dump(mode="json"),
    )
    return _state_update(run)


def _graph_save_initial_draft(state: SmartCompositionGraphState) -> SmartCompositionGraphState:
    run = _state_run(state)
    if run.draft_id and run.initial_version_id:
        return _state_update(run)
    if run.result.selected_candidate is None:
        raise SmartCompositionError("Selected composition candidate is missing.")
    _set_step(run, "initial_draft_save", "running", message="Saving initial draft.")
    draft = _create_draft_from_candidate(run, run.result.selected_candidate)
    initial_version = drafts.create_draft_version(
        draft.id,
        DraftVersionCreate(
            label="智能组稿初稿",
            metadata={
                "source": "smart_composition_agent",
                "workflow_run_id": run.id,
                "version_kind": "initial_draft",
                "candidate_id": run.result.selected_candidate.candidate_id,
            },
        ),
    )
    run.draft_id = draft.id
    run.initial_version_id = initial_version.id
    run.result.draft = draft
    run.result.initial_version = initial_version
    _set_step(run, "initial_draft_save", "completed", message="Initial draft saved.")
    return _state_update(run)


def _graph_diagnose(state: SmartCompositionGraphState) -> SmartCompositionGraphState:
    run = _state_run(state)
    if run.result.diagnosis is not None:
        return _state_update(run)
    if not run.draft_id:
        raise SmartCompositionError("Draft is missing before diagnosis.")
    _set_step(run, "diagnosis", "running", message="Diagnosing initial draft.")
    diagnosis = diagnostics.diagnose_copy(
        CopyDiagnosisRequest(
            draft_id=run.draft_id,
            platform=run.brief.platform,
            audience=run.brief.audience,
            purpose=run.brief.purpose,
            style=run.brief.style,
            constraints=[run.brief.constraints] if run.brief.constraints else [],
            metadata={"source": "smart_composition_agent", "workflow_run_id": run.id},
        )
    )
    run.result.diagnosis = diagnosis
    _set_step(run, "diagnosis", "completed", model=diagnosis.model, message="Diagnosis finished.")
    return _state_update(run)


def _graph_confirm_rewrite(state: SmartCompositionGraphState) -> SmartCompositionGraphState:
    run = _state_run(state)
    if run.result.diagnosis is None:
        raise SmartCompositionError("Diagnosis is missing before rewrite selection.")
    _set_step(run, "rewrite_selection", "running", message="Selecting best rewrite.")
    rewrites = run.result.diagnosis.rewrite_candidates
    if run.mode == "guided":
        payload = interrupt(
            {
                "type": "confirm_rewrite",
                "rewrite_candidates": [item.model_dump(mode="json") for item in rewrites],
            }
        )
        rewrite_id = payload.get("rewrite_candidate_id") if isinstance(payload, dict) else None
        rewrite = _find_rewrite(rewrites, rewrite_id)
        selection = SmartCompositionSelection(
            selected_id=rewrite.candidate_id,
            method="user",
            reason="Selected by user confirmation.",
        )
    else:
        rewrite, selection = _select_rewrite(rewrites)
    run.result.selected_rewrite = rewrite
    run.result.rewrite_selection = selection
    run.selected_rewrite_id = rewrite.candidate_id
    _set_step(
        run,
        "rewrite_selection",
        "completed",
        model=selection.judge_model,
        reason=selection.reason,
        metadata=selection.model_dump(mode="json"),
    )
    return _state_update(run)


def _graph_save_final_draft(state: SmartCompositionGraphState) -> SmartCompositionGraphState:
    run = _state_run(state)
    if run.final_version_id:
        return _state_update(run)
    if not run.draft_id or run.result.selected_rewrite is None or run.result.diagnosis is None:
        raise SmartCompositionError("Final draft inputs are missing.")
    _set_step(run, "final_draft_save", "running", message="Saving final draft.")
    final_draft = drafts.replace_draft_text(
        run.draft_id,
        run.result.selected_rewrite.text,
        role="diagnostic_rewrite",
        position="full_copy",
        metadata={
            "source": "smart_composition_agent",
            "workflow_run_id": run.id,
            "rewrite_candidate_id": run.result.selected_rewrite.candidate_id,
            "rewrite_mode": run.result.selected_rewrite.mode,
            "diagnostic_summary": run.result.diagnosis.summary,
        },
    )
    final_version = drafts.create_draft_version(
        run.draft_id,
        DraftVersionCreate(
            label="智能组稿终稿",
            metadata={
                "source": "smart_composition_agent",
                "workflow_run_id": run.id,
                "version_kind": "final_draft",
                "rewrite_candidate_id": run.result.selected_rewrite.candidate_id,
            },
        ),
    )
    run.final_version_id = final_version.id
    run.result.draft = final_draft
    run.result.final_version = final_version
    _set_step(run, "final_draft_save", "completed", message="Final draft saved.")
    return _state_update(run)


def _finish_auto_run(run: SmartCompositionRunDetail) -> None:
    if run.result.composition is None:
        raise SmartCompositionError("Composition result is missing.")
    _set_step(run, "composition_selection", "running", message="Selecting best candidate.")
    selected_candidate, composition_selection = _select_candidate(run.result.composition.candidates)
    run.result.selected_candidate = selected_candidate
    run.result.composition_selection = composition_selection
    run.selected_candidate_id = selected_candidate.candidate_id
    _set_step(
        run,
        "composition_selection",
        "completed",
        model=composition_selection.judge_model,
        reason=composition_selection.reason,
        metadata=composition_selection.model_dump(mode="json"),
    )

    _set_step(run, "initial_draft_save", "running", message="Saving initial draft.")
    draft = _create_draft_from_candidate(run, selected_candidate)
    initial_version = drafts.create_draft_version(
        draft.id,
        DraftVersionCreate(
            label="智能组稿初稿",
            metadata={
                "source": "smart_composition_agent",
                "workflow_run_id": run.id,
                "version_kind": "initial_draft",
                "candidate_id": selected_candidate.candidate_id,
            },
        ),
    )
    run.draft_id = draft.id
    run.initial_version_id = initial_version.id
    run.result.draft = draft
    run.result.initial_version = initial_version
    _set_step(run, "initial_draft_save", "completed", message="Initial draft saved.")

    _set_step(run, "diagnosis", "running", message="Diagnosing initial draft.")
    diagnosis = diagnostics.diagnose_copy(
        CopyDiagnosisRequest(
            draft_id=draft.id,
            platform=run.brief.platform,
            audience=run.brief.audience,
            purpose=run.brief.purpose,
            style=run.brief.style,
            constraints=[run.brief.constraints] if run.brief.constraints else [],
            metadata={"source": "smart_composition_agent", "workflow_run_id": run.id},
        )
    )
    run.result.diagnosis = diagnosis
    _set_step(run, "diagnosis", "completed", model=diagnosis.model, message="Diagnosis finished.")

    _set_step(run, "rewrite_selection", "running", message="Selecting best rewrite.")
    selected_rewrite, rewrite_selection = _select_rewrite(diagnosis.rewrite_candidates)
    run.result.selected_rewrite = selected_rewrite
    run.result.rewrite_selection = rewrite_selection
    run.selected_rewrite_id = selected_rewrite.candidate_id
    _set_step(
        run,
        "rewrite_selection",
        "completed",
        model=rewrite_selection.judge_model,
        reason=rewrite_selection.reason,
        metadata=rewrite_selection.model_dump(mode="json"),
    )

    _set_step(run, "final_draft_save", "running", message="Saving final draft.")
    final_draft = drafts.replace_draft_text(
        draft.id,
        selected_rewrite.text,
        role="diagnostic_rewrite",
        position="full_copy",
        metadata={
            "source": "smart_composition_agent",
            "workflow_run_id": run.id,
            "rewrite_candidate_id": selected_rewrite.candidate_id,
            "rewrite_mode": selected_rewrite.mode,
            "diagnostic_summary": diagnosis.summary,
        },
    )
    final_version = drafts.create_draft_version(
        draft.id,
        DraftVersionCreate(
            label="智能组稿终稿",
            metadata={
                "source": "smart_composition_agent",
                "workflow_run_id": run.id,
                "version_kind": "final_draft",
                "rewrite_candidate_id": selected_rewrite.candidate_id,
            },
        ),
    )
    run.final_version_id = final_version.id
    run.result.draft = final_draft
    run.result.final_version = final_version
    _set_step(run, "final_draft_save", "completed", message="Final draft saved.")


def _create_draft_from_candidate(
    run: SmartCompositionRunDetail,
    candidate: CompositionCandidate,
):
    draft = drafts.create_draft(
        DraftCreate(
            title=candidate.title,
            goal=run.brief.product,
            audience=run.brief.audience,
            platform=run.brief.platform,
            purpose=run.brief.purpose,
            metadata={
                "source": "smart_composition_agent",
                "workflow_run_id": run.id,
                "candidate_id": candidate.candidate_id,
                "brief": run.brief.model_dump(mode="json"),
            },
        )
    )
    for index, item in enumerate(candidate.items):
        primary_fragment_id = item.reference_fragment_ids[0] if item.reference_fragment_ids else None
        draft = drafts.add_draft_item(
            draft.id,
            DraftItemCreate(
                source_fragment_id=primary_fragment_id,
                edited_text=item.text,
                role=item.role,
                position=item.position,
                order_index=index,
                metadata={
                    "source": "smart_composition_agent",
                    "quote_mode": item.quote_mode,
                    "reference_fragment_ids": item.reference_fragment_ids,
                    "workflow_run_id": run.id,
                    "candidate_id": candidate.candidate_id,
                    "reason": item.reason,
                },
            ),
        )
    return draft


def _select_candidate(candidates: list[CompositionCandidate]) -> tuple[CompositionCandidate, SmartCompositionSelection]:
    scored = sorted(
        ((_candidate_score(candidate), candidate) for candidate in candidates),
        key=lambda item: item[0],
        reverse=True,
    )
    selected, selection = _judge_selection(
        "candidate",
        [candidate for _, candidate in scored[:3]],
        [candidate.candidate_id for _, candidate in scored[:3]],
    )
    if selected is not None:
        candidate = next(item for _, item in scored if item.candidate_id == selected)
        selection.score_signals = {"rule_score": _candidate_score(candidate)}
        return candidate, selection
    candidate = scored[0][1]
    return candidate, SmartCompositionSelection(
        selected_id=candidate.candidate_id,
        method="rule_fallback",
        score_signals={"rule_score": scored[0][0]},
        reason="Selected highest rule-scored candidate.",
        fallback_reason=selection.fallback_reason if selection else "llm_judge_unavailable",
    )


def _select_rewrite(candidates: list[RewriteCandidate]) -> tuple[RewriteCandidate, SmartCompositionSelection]:
    if not candidates:
        raise SmartCompositionError("Diagnosis did not return rewrite candidates.")
    scored = sorted(
        ((_rewrite_score(candidate), candidate) for candidate in candidates),
        key=lambda item: item[0],
        reverse=True,
    )
    selected, selection = _judge_selection(
        "rewrite",
        [candidate for _, candidate in scored[:3]],
        [candidate.candidate_id for _, candidate in scored[:3]],
    )
    if selected is not None:
        candidate = next(item for _, item in scored if item.candidate_id == selected)
        selection.score_signals = {"rule_score": _rewrite_score(candidate)}
        return candidate, selection
    candidate = scored[0][1]
    return candidate, SmartCompositionSelection(
        selected_id=candidate.candidate_id,
        method="rule_fallback",
        score_signals={"rule_score": scored[0][0]},
        reason="Selected highest rule-scored rewrite.",
        fallback_reason=selection.fallback_reason if selection else "llm_judge_unavailable",
    )


def _judge_selection(kind: str, candidates: list, allowed_ids: list[str]):
    llm = get_llm_client()
    model = getattr(llm, "model", settings.openai_model)
    try:
        raw = llm.complete(_build_judge_prompt(kind, candidates))
        parsed = _JudgeResponse.model_validate(json.loads(_strip_json_fence(raw)))
    except Exception as exc:
        return None, SmartCompositionSelection(
            selected_id=allowed_ids[0],
            method="rule_fallback",
            judge_model=model,
            fallback_reason=f"llm_judge_failed: {exc}",
        )
    if parsed.selected_id not in allowed_ids:
        return None, SmartCompositionSelection(
            selected_id=allowed_ids[0],
            method="rule_fallback",
            judge_model=model,
            fallback_reason="llm_judge_selected_unknown_id",
        )
    return parsed.selected_id, SmartCompositionSelection(
        selected_id=parsed.selected_id,
        method="llm_judge",
        judge_model=model,
        reason=parsed.reason,
    )


def _candidate_score(candidate: CompositionCandidate) -> float:
    score = 0.0
    score += 20 if len(candidate.items) == 5 else 0
    score += min(len(candidate.reference_fragment_ids), 5) * 3
    score += sum(1 for item in candidate.items if item.quote_mode in {"direct", "adapted"}) * 2
    score += min(sum(len(item.text) for item in candidate.items) / 100, 10)
    return score


def _rewrite_score(candidate: RewriteCandidate) -> float:
    score = 10.0
    if candidate.mode == "compliance_safe":
        score += 5
    if candidate.mode == "conversion":
        score += 3
    score += min(len(candidate.text) / 100, 10)
    return score


def _new_run(payload: SmartCompositionRunCreate) -> SmartCompositionRunDetail:
    now = datetime.now(timezone.utc)
    return SmartCompositionRunDetail(
        id=str(uuid4()),
        mode=payload.mode,
        status="running",
        brief=payload.brief,
        timeline=[
            SmartCompositionStep(step_id=step_id, label=label, order=index + 1, percent=percent)
            for index, (step_id, label, percent) in enumerate(STEP_DEFINITIONS)
        ],
        collection_ids=payload.brief.collection_ids,
        metadata=payload.metadata,
        created_at=now,
        updated_at=now,
    )


def _set_step(
    run: SmartCompositionRunDetail,
    step_id: SmartCompositionStepId,
    status: str,
    model: str | None = None,
    message: str | None = None,
    reason: str | None = None,
    metadata: dict | None = None,
) -> None:
    for index, step in enumerate(run.timeline):
        if step.step_id == step_id:
            run.timeline[index] = step.model_copy(
                update={
                    "status": status,
                    "model": model if model is not None else step.model,
                    "message": message,
                    "reason": reason,
                    "metadata": metadata or step.metadata,
                }
            )
            run.updated_at = datetime.now(timezone.utc)
            return


def _mark_running_step_failed(run: SmartCompositionRunDetail, message: str) -> None:
    for step in run.timeline:
        if step.status == "running":
            _set_step(run, step.step_id, "failed", message=message)
            return


def _save_run(run: SmartCompositionRunDetail) -> SmartCompositionRunDetail:
    run.updated_at = datetime.now(timezone.utc)
    db_item = _db_save_run(run)
    if db_item is not None:
        return db_item
    _store.runs[run.id] = run
    return run


def _db_save_run(run: SmartCompositionRunDetail) -> SmartCompositionRunDetail | None:
    if _db_available is False:
        return None
    try:
        with SessionLocal() as session:
            row = session.get(SmartCompositionRunModel, run.id)
            data = _run_model_data(run)
            if row is None:
                row = SmartCompositionRunModel(id=run.id, **data)
                session.add(row)
            else:
                for key, value in data.items():
                    setattr(row, key, value)
            session.commit()
            session.refresh(row)
            _mark_db_available(True)
            return _run_from_model(row)
    except SQLAlchemyError:
        _mark_db_available(False)
        return None


def _db_get_run(run_id: str) -> SmartCompositionRunDetail | None:
    if _db_available is False:
        return None
    try:
        with SessionLocal() as session:
            row = session.get(SmartCompositionRunModel, run_id)
            _mark_db_available(True)
            return _run_from_model(row) if row is not None else None
    except SQLAlchemyError:
        _mark_db_available(False)
        return None


def _db_list_runs(page: int, page_size: int) -> SmartCompositionRunListResponse | None:
    if _db_available is False:
        return None
    try:
        with SessionLocal() as session:
            stmt = (
                select(SmartCompositionRunModel)
                .order_by(SmartCompositionRunModel.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            rows = session.scalars(stmt).all()
            total = session.scalar(select(func.count()).select_from(SmartCompositionRunModel)) or 0
            _mark_db_available(True)
            return SmartCompositionRunListResponse(
                items=[_summary(_run_from_model(row)) for row in rows],
                page=page,
                page_size=page_size,
                total=total,
            )
    except SQLAlchemyError:
        _mark_db_available(False)
        return None


def _run_model_data(run: SmartCompositionRunDetail) -> dict:
    return {
        "mode": run.mode,
        "status": run.status,
        "brief_json": run.brief.model_dump(mode="json"),
        "timeline_json": [item.model_dump(mode="json") for item in run.timeline],
        "collection_ids_json": run.collection_ids,
        "material_ids_json": run.material_ids,
        "selected_candidate_id": run.selected_candidate_id,
        "selected_rewrite_id": run.selected_rewrite_id,
        "draft_id": run.draft_id,
        "initial_version_id": run.initial_version_id,
        "final_version_id": run.final_version_id,
        "result_json": run.result.model_dump(mode="json"),
        "metadata_json": run.metadata,
        "error": run.error,
    }


def _run_from_model(row: SmartCompositionRunModel) -> SmartCompositionRunDetail:
    return SmartCompositionRunDetail(
        id=str(row.id),
        mode=row.mode,
        status=row.status,
        brief=SmartCompositionBrief.model_validate(row.brief_json or {}),
        timeline=[SmartCompositionStep.model_validate(item) for item in row.timeline_json or []],
        collection_ids=row.collection_ids_json or [],
        material_ids=row.material_ids_json or [],
        selected_candidate_id=row.selected_candidate_id,
        selected_rewrite_id=row.selected_rewrite_id,
        draft_id=str(row.draft_id) if row.draft_id else None,
        initial_version_id=str(row.initial_version_id) if row.initial_version_id else None,
        final_version_id=str(row.final_version_id) if row.final_version_id else None,
        result=row.result_json or {},
        metadata=row.metadata_json or {},
        error=row.error,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _summary(run: SmartCompositionRunDetail) -> SmartCompositionRunSummary:
    return SmartCompositionRunSummary(**run.model_dump(exclude={"timeline", "result", "metadata", "collection_ids", "material_ids"}))


def _state_run(state: SmartCompositionGraphState) -> SmartCompositionRunDetail:
    run_data = state.get("run")
    if not isinstance(run_data, dict):
        raise SmartCompositionError("Graph state is missing run data.")
    return SmartCompositionRunDetail.model_validate(run_data)


def _state_update(run: SmartCompositionRunDetail) -> SmartCompositionGraphState:
    return {"run": run.model_dump(mode="json")}


def _require_composition(run: SmartCompositionRunDetail):
    if run.result.composition is None:
        raise SmartCompositionError("Composition result is missing.")
    return run.result.composition


def _find_candidate(candidates: list[CompositionCandidate], candidate_id: str | None):
    for candidate in candidates:
        if candidate.candidate_id == candidate_id:
            return candidate
    raise SmartCompositionInvalidSelectionError()


def _find_rewrite(candidates: list[RewriteCandidate], candidate_id: str | None):
    for candidate in candidates:
        if candidate.candidate_id == candidate_id:
            return candidate
    raise SmartCompositionInvalidSelectionError()


def _coerce_str_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _validate_known_ids(selected_ids: list[str], known_ids: list[str], message: str) -> None:
    unknown = set(selected_ids) - set(known_ids)
    if unknown:
        raise SmartCompositionInvalidSelectionError(message)


def _composition_brief(brief: SmartCompositionBrief) -> AutoCompositionBrief:
    return AutoCompositionBrief(**brief.model_dump(exclude={"collection_ids", "extra_notes"}))


def _build_prefill_prompt(text: str) -> str:
    return (
        "Extract a structured composition brief from the user's text.\n"
        "Return one valid JSON object only. Do not return Markdown or explanations.\n"
        "Use Simplified Chinese for natural-language values when appropriate. Keep platform/purpose/style short.\n"
        'Return shape: {"product":"","audience":"","platform":"","purpose":"","style":"","key_selling_points":[],"constraints":null,"target_length":null,"extra_notes":null,"confidence":0.8,"notes":[]}\n'
        f"User text:\n{text}"
    )


def _build_judge_prompt(kind: str, candidates: list) -> str:
    return (
        f"You are selecting the best {kind} for a copywriting workflow.\n"
        "Return one valid JSON object only. Do not return Markdown or explanations.\n"
        'Return shape: {"selected_id":"","reason":""}\n'
        f"Candidates JSON:\n{json.dumps([item.model_dump(mode='json') for item in candidates], ensure_ascii=False)}"
    )


def _strip_json_fence(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return text


def _mark_db_available(value: bool) -> None:
    global _db_available
    _db_available = value
