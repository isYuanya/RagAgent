import json
from uuid import uuid4

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.core.config import settings
from app.core.llm import get_llm_client
from app.schemas.common import RiskWarning
from app.schemas.diagnostic import (
    AcceptDiagnosticRewriteRequest,
    AcceptDiagnosticRewriteResponse,
    AcceptedDiagnosticRewrite,
    CopyDiagnosisRequest,
    CopyDiagnosisResult,
    DiagnosticSource,
    DimensionFinding,
    RewriteCandidate,
    SentenceIssue,
)
from app.schemas.draft import DraftVersionCreate
from app.services import drafts
from app.services.compliance import inspect_risks
from app.workers.queue import get_queue
from app.workers.tasks import get_task


DIMENSIONS = (
    "opening_attractiveness",
    "audience_clarity",
    "pain_specificity",
    "context_coherence",
    "emotional_resonance",
    "spoken_naturalness",
    "conversion_action",
    "originality_risk",
    "compliance_risk",
)


class DiagnosticError(Exception):
    pass


class DiagnosticTaskNotFoundError(Exception):
    pass


class DiagnosticCandidateNotFoundError(Exception):
    pass


class _LLMDimension(BaseModel):
    dimension: str
    level: str = "fair"
    reason: str = ""
    suggestion: str = ""


class _LLMSentenceIssue(BaseModel):
    text: str
    dimension: str
    level: str = "fair"
    reason: str = ""
    suggestion: str = ""
    replacement: str = ""


class _LLMRewriteCandidate(BaseModel):
    candidate_id: str | None = None
    mode: str = "conservative"
    title: str = "改写版本"
    text: str = Field(min_length=1)
    reason: str = ""


class _LLMDiagnosisResponse(BaseModel):
    summary: str = ""
    overall_level: str = "fair"
    dimensions: list[_LLMDimension] = Field(default_factory=list)
    sentence_issues: list[_LLMSentenceIssue] = Field(default_factory=list)
    rewrite_candidates: list[_LLMRewriteCandidate] = Field(default_factory=list)
    risk_warnings: list[RiskWarning] = Field(default_factory=list)

    @field_validator("risk_warnings", mode="before")
    @classmethod
    def _coerce_risk_warnings(cls, value):
        if value is None:
            return []
        if isinstance(value, dict):
            return [value]
        if isinstance(value, str):
            return [{"level": "medium", "message": value}]
        if isinstance(value, list):
            return value
        return []


def diagnose_copy(payload: CopyDiagnosisRequest) -> CopyDiagnosisResult:
    source = _resolve_source(payload)
    rule_warnings = inspect_risks(source.text)
    llm = get_llm_client()
    raw = llm.complete(_build_prompt(payload, source, rule_warnings))
    model = getattr(llm, "model", settings.openai_model)

    try:
        parsed = _LLMDiagnosisResponse.model_validate(json.loads(_strip_json_fence(raw)))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise DiagnosticError(f"LLM returned invalid diagnosis JSON: {exc}") from exc

    return CopyDiagnosisResult(
        source=source,
        summary=parsed.summary or "AI 已完成文案诊断。",
        overall_level=_level(parsed.overall_level),
        dimensions=_normalize_dimensions(parsed.dimensions),
        sentence_issues=[
            SentenceIssue(
                text=item.text,
                dimension=item.dimension,
                level=_level(item.level),
                reason=item.reason,
                suggestion=item.suggestion,
                replacement=item.replacement,
            )
            for item in parsed.sentence_issues
            if item.text and item.replacement
        ],
        rewrite_candidates=_normalize_rewrites(parsed.rewrite_candidates, source.text),
        risk_warnings=[*rule_warnings, *parsed.risk_warnings],
        model=model,
    )


def accept_diagnostic_rewrite(
    payload: AcceptDiagnosticRewriteRequest,
) -> AcceptDiagnosticRewriteResponse:
    result = _get_diagnosis_result(payload.task_id)
    if result.source.draft_id != payload.draft_id:
        raise DiagnosticCandidateNotFoundError()
    candidate = next(
        (item for item in result.rewrite_candidates if item.candidate_id == payload.candidate_id),
        None,
    )
    if candidate is None:
        raise DiagnosticCandidateNotFoundError()

    draft = drafts.replace_draft_text(
        payload.draft_id,
        candidate.text,
        role="diagnostic_rewrite",
        position="full_copy",
        metadata={
            "source": "diagnostic_rewrite",
            "task_id": payload.task_id,
            "candidate_id": payload.candidate_id,
            "rewrite_mode": candidate.mode,
            "diagnostic_summary": result.summary,
            **payload.metadata,
        },
    )
    version = drafts.create_draft_version(
        payload.draft_id,
        DraftVersionCreate(
            label=payload.label,
            metadata={
                "source": "diagnostic_rewrite",
                "task_id": payload.task_id,
                "candidate_id": payload.candidate_id,
                "rewrite_mode": candidate.mode,
                **payload.metadata,
            },
        ),
    )
    accepted = AcceptedDiagnosticRewrite(
        draft_id=payload.draft_id,
        task_id=payload.task_id,
        candidate_id=payload.candidate_id,
        rewrite_text=candidate.text,
        model=result.model,
        metadata=payload.metadata,
    )
    return AcceptDiagnosticRewriteResponse(accepted=accepted, draft=draft, version=version)


def _resolve_source(payload: CopyDiagnosisRequest) -> DiagnosticSource:
    if payload.text:
        return DiagnosticSource(
            source_type="text",
            text=payload.text,
            platform=payload.platform,
            audience=payload.audience,
            purpose=payload.purpose,
            style=payload.style,
            industry=payload.industry,
        )

    draft = drafts.get_draft(payload.draft_id or "")
    if draft is None:
        raise drafts.DraftNotFoundError()
    return DiagnosticSource(
        source_type="draft",
        text=draft.current_text,
        draft_id=draft.id,
        platform=payload.platform or draft.platform,
        audience=payload.audience or draft.audience,
        purpose=payload.purpose or draft.purpose,
        style=payload.style,
        industry=payload.industry,
    )


def _build_prompt(
    payload: CopyDiagnosisRequest,
    source: DiagnosticSource,
    rule_warnings: list[RiskWarning],
) -> str:
    context = {
        "source": source.model_dump(mode="json"),
        "constraints": payload.constraints,
        "rewrite_modes": payload.rewrite_modes or ["conservative", "conversion", "compliance_safe"],
        "dimensions": DIMENSIONS,
        "rule_warnings": [item.model_dump(mode="json") for item in rule_warnings],
    }
    return (
        "You are a copy diagnosis and rewrite assistant.\n"
        "Return one valid JSON object only. Do not return Markdown, code fences, or explanations.\n"
        "All natural-language text fields must be Simplified Chinese. Keep enum fields in English.\n"
        "Do not use numeric scores. Use only these level labels: weak, fair, strong, risk, high_risk.\n"
        "Diagnose these dimensions: opening_attractiveness, audience_clarity, pain_specificity, "
        "context_coherence, emotional_resonance, spoken_naturalness, conversion_action, "
        "originality_risk, compliance_risk.\n"
        "Point out specific sentences when they need editing and provide replacement text.\n"
        "Return this JSON shape: "
        '{"summary":"","overall_level":"fair","dimensions":[{"dimension":"opening_attractiveness","level":"weak","reason":"","suggestion":""}],"sentence_issues":[{"text":"","dimension":"","level":"risk","reason":"","suggestion":"","replacement":""}],"rewrite_candidates":[{"candidate_id":"conservative","mode":"conservative","title":"","text":"","reason":""}],"risk_warnings":[{"level":"low","message":"","suggestion":""}]}\n'
        f"Context JSON:\n{json.dumps(context, ensure_ascii=False)}"
    )


def _normalize_dimensions(items: list[_LLMDimension]) -> list[DimensionFinding]:
    by_name = {item.dimension: item for item in items}
    findings: list[DimensionFinding] = []
    for dimension in DIMENSIONS:
        item = by_name.get(dimension)
        findings.append(
            DimensionFinding(
                dimension=dimension,
                level=_level(item.level if item else "fair"),
                reason=item.reason if item else "LLM 未返回该维度的详细判断。",
                suggestion=item.suggestion if item else "建议人工复核该维度。",
            )
        )
    return findings


def _normalize_rewrites(
    items: list[_LLMRewriteCandidate],
    original_text: str,
) -> list[RewriteCandidate]:
    candidates: list[RewriteCandidate] = []
    for item in items:
        mode = item.mode if item.mode in {"conservative", "conversion", "compliance_safe"} else "conservative"
        candidates.append(
            RewriteCandidate(
                candidate_id=item.candidate_id or str(uuid4()),
                mode=mode,  # type: ignore[arg-type]
                title=item.title,
                text=item.text.strip(),
                reason=item.reason,
            )
        )
    if candidates:
        return candidates
    return [
        RewriteCandidate(
            candidate_id="conservative",
            mode="conservative",
            title="保守改写版",
            text=original_text,
            reason="LLM 未返回改写版本，系统保留原文作为兜底候选。",
        )
    ]


def _get_diagnosis_result(task_id: str) -> CopyDiagnosisResult:
    task = get_task(task_id)
    if task is None or task.result is None:
        rq_task = _get_rq_task(task_id)
        if rq_task is not None and rq_task.result is not None:
            task = rq_task
    if task is None or task.result is None:
        raise DiagnosticTaskNotFoundError()
    return CopyDiagnosisResult.model_validate(task.result)


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


def _level(value: str) -> str:
    return value if value in {"weak", "fair", "strong", "risk", "high_risk"} else "fair"


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
