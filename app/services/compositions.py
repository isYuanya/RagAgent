import json
from dataclasses import dataclass, field
from uuid import uuid4

from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.llm import get_llm_client
from app.db.session import SessionLocal
from app.models.composition import AcceptedComposition as AcceptedCompositionModel
from app.schemas.composition import (
    AcceptCompositionRequest,
    AcceptCompositionResponse,
    AcceptedCompositionItem,
    AutoCompositionBrief,
    AutoCompositionRequest,
    AutoCompositionResult,
    CompositionCandidate,
    CompositionItemCandidate,
)
from app.schemas.draft import DraftCreate, DraftItemCreate
from app.schemas.recommendation import ReferenceFragmentSummary
from app.services import drafts, knowledge
from app.workers.queue import get_queue
from app.workers.tasks import get_task


COMPOSITION_ROLES = ("hook", "pain_point", "solution", "proof", "cta")
POSITION_BY_ROLE = {
    "hook": "opening",
    "pain_point": "body",
    "solution": "body",
    "proof": "body",
    "cta": "ending",
}


class CompositionError(Exception):
    pass


class CompositionTaskNotFoundError(Exception):
    pass


class CompositionCandidateNotFoundError(Exception):
    pass


@dataclass
class _Store:
    accepted: dict[str, AcceptedCompositionItem] = field(default_factory=dict)


class _LLMCompositionItem(BaseModel):
    role: str
    position: str | None = None
    text: str = Field(min_length=1)
    quote_mode: str = "original"
    reference_fragment_ids: list[str] = Field(default_factory=list)
    source_copy_id: str | None = None
    reason: str = ""

    @field_validator("reference_fragment_ids", mode="before")
    @classmethod
    def _coerce_reference_ids(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [str(item) for item in value if item]
        return []


class _LLMCompositionCandidate(BaseModel):
    title: str = "AI 自动组稿"
    strategy: str = ""
    items: list[_LLMCompositionItem] = Field(default_factory=list)


class _LLMCompositionResponse(BaseModel):
    candidates: list[_LLMCompositionCandidate] = Field(default_factory=list)


_store = _Store()
_db_available: bool | None = False if settings.app_env == "test" else None


def reset_composition_store() -> None:
    global _db_available, _store
    _store = _Store()
    _db_available = False if settings.app_env == "test" else None


def generate_auto_composition(payload: AutoCompositionRequest) -> AutoCompositionResult:
    reference_fragments = retrieve_reference_fragments(payload.brief)
    return generate_auto_composition_from_references(payload, reference_fragments)


def generate_auto_composition_from_references(
    payload: AutoCompositionRequest,
    reference_fragments: list[ReferenceFragmentSummary],
) -> AutoCompositionResult:
    fallback_reason = None if reference_fragments else "no_matching_fragments"
    llm = get_llm_client()
    raw = llm.complete(_build_prompt(payload.brief, reference_fragments, fallback_reason))
    model = getattr(llm, "model", settings.openai_model)

    try:
        parsed = _LLMCompositionResponse.model_validate(json.loads(_strip_json_fence(raw)))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise CompositionError(f"LLM returned invalid composition JSON: {exc}") from exc

    candidates = _normalize_candidates(parsed, payload.brief, reference_fragments)
    return AutoCompositionResult(
        brief=payload.brief,
        model=model,
        fallback_reason=fallback_reason,
        candidates=candidates,
        reference_fragments=reference_fragments,
    )


def accept_composition(payload: AcceptCompositionRequest) -> AcceptCompositionResponse:
    result = _get_composition_result(payload.task_id)
    candidate = next(
        (item for item in result.candidates if item.candidate_id == payload.candidate_id),
        None,
    )
    if candidate is None:
        raise CompositionCandidateNotFoundError()

    draft = drafts.create_draft(
        DraftCreate(
            title=candidate.title,
            goal=result.brief.product,
            audience=result.brief.audience,
            platform=result.brief.platform,
            purpose=result.brief.purpose,
            metadata={
                "source": "auto_composition",
                "task_id": payload.task_id,
                "candidate_id": payload.candidate_id,
                "brief": result.brief.model_dump(mode="json"),
                **payload.metadata,
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
                    "source": "auto_composition",
                    "quote_mode": item.quote_mode,
                    "reference_fragment_ids": item.reference_fragment_ids,
                    "generation_task_id": payload.task_id,
                    "generation_candidate_id": payload.candidate_id,
                    "generation_reason": item.reason,
                },
            ),
        )

    accepted = _create_accepted_composition(payload, result, candidate, draft.id)
    return AcceptCompositionResponse(accepted=accepted, draft=draft)


def retrieve_reference_fragments(brief: AutoCompositionBrief) -> list[ReferenceFragmentSummary]:
    fragments = []
    seen: set[str] = set()
    for query in _reference_queries(brief):
        response = knowledge.list_fragments(
            page=1,
            page_size=10,
            status="approved",
            platform=brief.platform,
            purpose=brief.purpose,
            audience=brief.audience,
            q=query,
        )
        for item in response.items:
            if item.id in seen:
                continue
            seen.add(item.id)
            fragments.append(_fragment_summary(item))
        if len(fragments) >= 10:
            break
    return fragments[:10]


def _reference_queries(brief: AutoCompositionBrief) -> list[str]:
    values = [brief.product, *brief.key_selling_points]
    queries: list[str] = []
    for value in values:
        text = value.strip()
        if text and text not in queries:
            queries.append(text)
    return queries


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
    brief: AutoCompositionBrief,
    reference_fragments: list[ReferenceFragmentSummary],
    fallback_reason: str | None,
) -> str:
    context = {
        "brief": brief.model_dump(mode="json"),
        "required_roles": list(COMPOSITION_ROLES),
        "position_by_role": POSITION_BY_ROLE,
        "fallback_reason": fallback_reason,
        "reference_fragments": [item.model_dump() for item in reference_fragments],
    }
    return (
        "You are an AI copywriting composition assistant. Generate exactly 3 complete candidate drafts.\n"
        "Return one valid JSON object only. Do not return Markdown, code fences, or explanations.\n"
        "All natural-language output must be Simplified Chinese. Keep enum fields in English.\n"
        "Each candidate must contain exactly 5 items with roles: hook, pain_point, solution, proof, cta.\n"
        "You may directly quote a reference fragment when it is suitable, but mark quote_mode as direct. "
        "Use adapted for rewritten source material and original for new text.\n"
        "If there are no reference fragments, all items must use quote_mode original and empty reference_fragment_ids.\n"
        "Return this JSON shape: "
        '{"candidates":[{"title":"","strategy":"","items":[{"role":"hook","position":"opening","text":"","quote_mode":"original","reference_fragment_ids":[],"source_copy_id":null,"reason":""}]}]}\n'
        f"Context JSON:\n{json.dumps(context, ensure_ascii=False)}"
    )


def _normalize_candidates(
    parsed: _LLMCompositionResponse,
    brief: AutoCompositionBrief,
    reference_fragments: list[ReferenceFragmentSummary],
) -> list[CompositionCandidate]:
    by_id = {item.id: item for item in reference_fragments}
    candidates: list[CompositionCandidate] = []
    for index, raw_candidate in enumerate(parsed.candidates[:3]):
        items = _normalize_candidate_items(raw_candidate.items, by_id)
        candidates.append(
            CompositionCandidate(
                candidate_id=str(uuid4()),
                title=raw_candidate.title or f"{brief.product} 自动组稿 {index + 1}",
                strategy=raw_candidate.strategy,
                items=items,
                reference_fragment_ids=_unique_ids(
                    fragment_id
                    for item in items
                    for fragment_id in item.reference_fragment_ids
                ),
            )
        )
    while len(candidates) < 3:
        candidates.append(_fallback_candidate(brief, len(candidates)))
    return candidates[:3]


def _normalize_candidate_items(
    raw_items: list[_LLMCompositionItem],
    references_by_id: dict[str, ReferenceFragmentSummary],
) -> list[CompositionItemCandidate]:
    by_role = {item.role: item for item in raw_items}
    items: list[CompositionItemCandidate] = []
    for role in COMPOSITION_ROLES:
        raw = by_role.get(role)
        if raw is None:
            items.append(
                CompositionItemCandidate(
                    role=role,  # type: ignore[arg-type]
                    position=POSITION_BY_ROLE[role],
                    text=f"{role} 待补充",
                    quote_mode="original",
                    reference_fragment_ids=[],
                    reason="LLM 未返回该结构段，系统补齐占位。",
                )
            )
            continue
        reference_ids = [item for item in raw.reference_fragment_ids if item in references_by_id]
        quote_mode = raw.quote_mode if raw.quote_mode in {"direct", "adapted", "original"} else "original"
        if not reference_ids:
            quote_mode = "original"
        source_copy_id = raw.source_copy_id
        if source_copy_id is None and reference_ids:
            source_copy_id = references_by_id[reference_ids[0]].source_copy_id
        items.append(
            CompositionItemCandidate(
                role=role,  # type: ignore[arg-type]
                position=raw.position or POSITION_BY_ROLE[role],
                text=raw.text.strip(),
                quote_mode=quote_mode,  # type: ignore[arg-type]
                reference_fragment_ids=reference_ids,
                source_copy_id=source_copy_id,
                reason=raw.reason,
            )
        )
    return items


def _fallback_candidate(brief: AutoCompositionBrief, index: int) -> CompositionCandidate:
    selling_points = "、".join(brief.key_selling_points)
    texts = {
        "hook": f"如果你正在为{brief.product}找一个更适合{brief.audience}的表达方式，先看这个思路。",
        "pain_point": f"很多内容的问题不是卖点不够，而是没有把{brief.audience}真正关心的场景说清楚。",
        "solution": f"这版文案会围绕{selling_points}展开，用{brief.style}的方式把价值讲具体。",
        "proof": f"结合{brief.platform}的阅读习惯，把卖点放进可感知的使用场景里，降低理解成本。",
        "cta": "如果你也想解决这个问题，可以先从最关键的一个卖点开始尝试。",
    }
    return CompositionCandidate(
        candidate_id=str(uuid4()),
        title=f"{brief.product} 自动组稿 {index + 1}",
        strategy="无匹配素材时基于 brief 生成的兜底候选。",
        items=[
            CompositionItemCandidate(
                role=role,  # type: ignore[arg-type]
                position=POSITION_BY_ROLE[role],
                text=texts[role],
                quote_mode="original",
                reference_fragment_ids=[],
                reason="Fallback generated from structured brief.",
            )
            for role in COMPOSITION_ROLES
        ],
        reference_fragment_ids=[],
    )


def _get_composition_result(task_id: str) -> AutoCompositionResult:
    task = get_task(task_id)
    if task is None or task.result is None:
        rq_task = _get_rq_task(task_id)
        if rq_task is not None and rq_task.result is not None:
            task = rq_task
    if task is None or task.result is None:
        raise CompositionTaskNotFoundError()
    return AutoCompositionResult.model_validate(task.result)


def _get_rq_task(task_id: str):
    try:
        from rq.job import Job

        job = Job.fetch(task_id, connection=get_queue("recommendation").connection)
    except Exception:
        return None
    task_data = job.meta.get("task")
    if isinstance(task_data, dict):
        from app.schemas.task import TaskResponse

        return TaskResponse.model_validate(task_data)
    return None


def _create_accepted_composition(
    payload: AcceptCompositionRequest,
    result: AutoCompositionResult,
    candidate: CompositionCandidate,
    draft_id: str,
) -> AcceptedCompositionItem:
    db_item = _db_create_accepted_composition(payload, result, candidate, draft_id)
    if db_item is not None:
        return db_item
    item = AcceptedCompositionItem(
        id=str(uuid4()),
        task_id=payload.task_id,
        candidate_id=payload.candidate_id,
        draft_id=draft_id,
        brief=result.brief,
        candidate_title=candidate.title,
        model=result.model,
        reference_fragment_ids=candidate.reference_fragment_ids,
        metadata=payload.metadata,
    )
    _store.accepted[item.id] = item
    return item


def _db_create_accepted_composition(
    payload: AcceptCompositionRequest,
    result: AutoCompositionResult,
    candidate: CompositionCandidate,
    draft_id: str,
) -> AcceptedCompositionItem | None:
    if _db_available is False:
        return None
    try:
        with SessionLocal() as session:
            row = AcceptedCompositionModel(
                task_id=payload.task_id,
                candidate_id=payload.candidate_id,
                draft_id=draft_id,
                brief_json=result.brief.model_dump(mode="json"),
                candidate_title=candidate.title,
                model=result.model,
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


def _accepted_from_model(row: AcceptedCompositionModel) -> AcceptedCompositionItem:
    return AcceptedCompositionItem(
        id=str(row.id),
        task_id=row.task_id,
        candidate_id=row.candidate_id,
        draft_id=str(row.draft_id),
        brief=AutoCompositionBrief.model_validate(row.brief_json),
        candidate_title=row.candidate_title,
        model=row.model,
        reference_fragment_ids=row.reference_fragment_ids_json or [],
        metadata=row.metadata_json or {},
    )


def _unique_ids(values) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


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
