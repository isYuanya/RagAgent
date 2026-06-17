import json
from dataclasses import dataclass, field
from uuid import uuid4

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.llm import get_llm_client
from app.db.session import SessionLocal
from app.models.recommendation import AcceptedRecommendation as AcceptedRecommendationModel
from app.schemas.draft import DraftItemCreate
from app.schemas.recommendation import (
    AcceptRecommendationRequest,
    AcceptRecommendationResponse,
    AcceptedRecommendationItem,
    NextSentenceRecommendationRequest,
    NextSentenceRecommendationResult,
    RecommendationCandidate,
    ReferenceFragmentSummary,
)
from app.services import drafts, knowledge
from app.workers.queue import get_queue
from app.workers.tasks import get_task


class RecommendationError(Exception):
    pass


class RecommendationTaskNotFoundError(Exception):
    pass


class RecommendationCandidateNotFoundError(Exception):
    pass


@dataclass
class _Store:
    accepted: dict[str, AcceptedRecommendationItem] = field(default_factory=dict)


class _LLMCandidate(BaseModel):
    text: str = Field(min_length=1)
    function: str = Field(default="transition")
    reason: str = Field(default="")
    tone: str = Field(default="")
    suggested_order_index: int = Field(default=0, ge=0)
    risk_warnings: list[dict] = Field(default_factory=list)
    reference_fragment_ids: list[str] = Field(default_factory=list)


class _LLMRecommendationResponse(BaseModel):
    next_function: str = Field(default="transition")
    candidates: list[_LLMCandidate] = Field(default_factory=list)


_store = _Store()
_db_available: bool | None = False if settings.app_env == "test" else None


def reset_recommendation_store() -> None:
    global _db_available, _store
    _store = _Store()
    _db_available = False if settings.app_env == "test" else None


def generate_next_sentence(
    payload: NextSentenceRecommendationRequest,
) -> NextSentenceRecommendationResult:
    draft = drafts.get_draft(payload.draft_id)
    if draft is None:
        raise drafts.DraftNotFoundError()

    reference_fragments = _retrieve_reference_fragments(payload, draft)
    llm = get_llm_client()
    raw = llm.complete(_build_prompt(payload, draft, reference_fragments))
    model = getattr(llm, "model", settings.openai_model)

    try:
        parsed = _LLMRecommendationResponse.model_validate(json.loads(_strip_json_fence(raw)))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise RecommendationError(f"LLM returned invalid recommendation JSON: {exc}") from exc

    candidates = _normalize_candidates(parsed, payload, draft, reference_fragments)
    return NextSentenceRecommendationResult(
        draft_id=draft.id,
        current_text=draft.current_text,
        next_function=parsed.next_function or (candidates[0].function if candidates else "transition"),
        model=model,
        candidates=candidates,
        reference_fragments=reference_fragments,
    )


def accept_recommendation(payload: AcceptRecommendationRequest) -> AcceptRecommendationResponse:
    result = _get_recommendation_result(payload.task_id)
    if result.draft_id != payload.draft_id:
        raise RecommendationCandidateNotFoundError()

    candidate = next(
        (item for item in result.candidates if item.candidate_id == payload.candidate_id),
        None,
    )
    if candidate is None:
        raise RecommendationCandidateNotFoundError()

    draft = drafts.add_draft_item(
        payload.draft_id,
        DraftItemCreate(
            edited_text=candidate.text,
            role=candidate.function,
            position="ai_recommendation",
            order_index=payload.order_index
            if payload.order_index is not None
            else candidate.suggested_order_index,
            metadata={
                "source": "recommendation",
                "task_id": payload.task_id,
                "candidate_id": payload.candidate_id,
            },
        ),
    )
    inserted_item = next(
        (
            item
            for item in draft.items
            if item.metadata.get("task_id") == payload.task_id
            and item.metadata.get("candidate_id") == payload.candidate_id
        ),
        draft.items[-1],
    )
    accepted = _create_accepted_recommendation(
        payload=payload,
        candidate=candidate,
        inserted_draft_item_id=inserted_item.id,
        model=result.model,
    )
    return AcceptRecommendationResponse(accepted=accepted, draft=draft)


def _get_recommendation_result(task_id: str) -> NextSentenceRecommendationResult:
    task = get_task(task_id)
    if task is None:
        task = _get_rq_task(task_id)
    if task is None or task.result is None:
        raise RecommendationTaskNotFoundError()
    return NextSentenceRecommendationResult.model_validate(task.result)


def _get_rq_task(task_id: str):
    for queue_name in ("recommendation", "copy_import"):
        try:
            from rq.job import Job

            job = Job.fetch(task_id, connection=get_queue(queue_name).connection)
        except Exception:
            continue
        task_data = job.meta.get("task")
        if isinstance(task_data, dict):
            from app.schemas.task import TaskResponse

            return TaskResponse.model_validate(task_data)
    return None


def _create_accepted_recommendation(
    payload: AcceptRecommendationRequest,
    candidate: RecommendationCandidate,
    inserted_draft_item_id: str,
    model: str | None,
) -> AcceptedRecommendationItem:
    db_item = _db_create_accepted_recommendation(
        payload=payload,
        candidate=candidate,
        inserted_draft_item_id=inserted_draft_item_id,
        model=model,
    )
    if db_item is not None:
        return db_item
    item = AcceptedRecommendationItem(
        id=str(uuid4()),
        draft_id=payload.draft_id,
        task_id=payload.task_id,
        candidate_id=payload.candidate_id,
        inserted_draft_item_id=inserted_draft_item_id,
        candidate_text=candidate.text,
        function=candidate.function,
        tone=candidate.tone,
        reason=candidate.reason,
        model=model,
        reference_fragment_ids=candidate.reference_fragment_ids,
        metadata=payload.metadata,
    )
    _store.accepted[item.id] = item
    return item


def _db_create_accepted_recommendation(
    payload: AcceptRecommendationRequest,
    candidate: RecommendationCandidate,
    inserted_draft_item_id: str,
    model: str | None,
) -> AcceptedRecommendationItem | None:
    if _db_available is False:
        return None
    try:
        with SessionLocal() as session:
            row = AcceptedRecommendationModel(
                draft_id=payload.draft_id,
                task_id=payload.task_id,
                candidate_id=payload.candidate_id,
                inserted_draft_item_id=inserted_draft_item_id,
                candidate_text=candidate.text,
                function=candidate.function,
                tone=candidate.tone,
                reason=candidate.reason,
                model=model,
                reference_fragment_ids_json=candidate.reference_fragment_ids,
                metadata_json=payload.metadata,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            _mark_db_available(True)
            return _accepted_from_model(row)
    except SQLAlchemyError:
        _mark_db_available(False)
        return None


def _retrieve_reference_fragments(
    payload: NextSentenceRecommendationRequest,
    draft,
) -> list[ReferenceFragmentSummary]:
    query = payload.q or draft.current_text[-160:]
    response = knowledge.list_fragments(
        page=1,
        page_size=5,
        status="approved",
        platform=draft.platform,
        purpose=draft.purpose,
        audience=draft.audience,
        q=query or None,
    )
    items = list(response.items)
    if not items:
        response = knowledge.list_fragments(page=1, page_size=5, status="approved", q=query or None)
        items = list(response.items)
    if not items:
        response = knowledge.list_fragments(page=1, page_size=5, status="approved")
        items = list(response.items)
    return [_fragment_summary(item) for item in items]


def _fragment_summary(fragment) -> ReferenceFragmentSummary:
    source_display = None
    raw = knowledge.get_raw_copy(fragment.source_copy_id)
    if raw is not None:
        source_display = raw.source_text[:120]
    return ReferenceFragmentSummary(
        id=fragment.id,
        text=fragment.fragment_text,
        role=fragment.fragment_role,
        position=fragment.position,
        source_copy_id=fragment.source_copy_id,
        source_display=source_display,
    )


def _build_prompt(
    payload: NextSentenceRecommendationRequest,
    draft,
    reference_fragments: list[ReferenceFragmentSummary],
) -> str:
    context = {
        "draft": draft.model_dump(),
        "candidate_count": payload.candidate_count,
        "reference_fragments": [item.model_dump() for item in reference_fragments],
    }
    return (
        "You are a short-form copywriting assistant. Recommend the next sentence or micro-paragraph "
        "for the current draft.\n"
        "Return one valid JSON object only. Do not return Markdown, code fences, or explanations.\n"
        "The candidate text must be original and must not copy reference fragments verbatim.\n"
        "Each candidate may contain 1-2 sentences and must be short enough to insert as one draft item.\n"
        "Infer the next_function, such as transition, pain_point, proof, solution, or cta.\n"
        "Return this JSON shape: "
        '{"next_function":"proof","candidates":[{"text":"","function":"","reason":"","tone":"","suggested_order_index":0,"risk_warnings":[],"reference_fragment_ids":[]}]}\n'
        f"Context JSON:\n{json.dumps(context, ensure_ascii=False)}"
    )


def _normalize_candidates(
    parsed: _LLMRecommendationResponse,
    payload: NextSentenceRecommendationRequest,
    draft,
    reference_fragments: list[ReferenceFragmentSummary],
) -> list[RecommendationCandidate]:
    reference_ids = [item.id for item in reference_fragments]
    by_id = {item.id: item for item in reference_fragments}
    candidates: list[RecommendationCandidate] = []
    for item in parsed.candidates[: payload.candidate_count]:
        candidate_id = str(uuid4())
        item_reference_ids = item.reference_fragment_ids or reference_ids
        candidates.append(
            RecommendationCandidate(
                candidate_id=candidate_id,
                text=item.text.strip(),
                function=item.function or parsed.next_function or "transition",
                reason=item.reason,
                tone=item.tone,
                suggested_order_index=item.suggested_order_index
                if item.suggested_order_index is not None
                else len(draft.items),
                risk_warnings=item.risk_warnings,
                reference_fragment_ids=item_reference_ids,
                reference_fragments=[by_id[fragment_id] for fragment_id in item_reference_ids if fragment_id in by_id],
            )
        )
    return candidates


def _accepted_from_model(row: AcceptedRecommendationModel) -> AcceptedRecommendationItem:
    return AcceptedRecommendationItem(
        id=str(row.id),
        draft_id=str(row.draft_id),
        task_id=row.task_id,
        candidate_id=row.candidate_id,
        inserted_draft_item_id=str(row.inserted_draft_item_id),
        candidate_text=row.candidate_text,
        function=row.function,
        tone=row.tone,
        reason=row.reason,
        model=row.model,
        reference_fragment_ids=row.reference_fragment_ids_json or [],
        metadata=row.metadata_json or {},
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
