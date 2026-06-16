import json

from pydantic import BaseModel, Field, ValidationError

from app.core.config import settings
from app.core.llm import get_llm_client
from app.schemas.copy import CopyAssetSummary
from app.schemas.knowledge import (
    FragmentCreate,
    FragmentExtractionBatchResponse,
    FragmentExtractionResult,
    FragmentItem,
)
from app.services import knowledge
from app.services.copy_assets import get_copy_asset, list_copy_assets


DEFAULT_BACKFILL_LIMIT = 50


class _GeneratedFragment(BaseModel):
    fragment_text: str = Field(min_length=1)
    fragment_role: str = Field(min_length=1)
    position: str = Field(min_length=1)
    reason: str | None = None
    source_quality: str = "unknown"
    risk_level: str = "low"
    confidence: float = Field(ge=0, le=1)


class _FragmentExtractionResponse(BaseModel):
    fragments: list[_GeneratedFragment] = Field(default_factory=list)


def extract_fragments_for_asset_id(source_copy_id: str) -> FragmentExtractionResult:
    asset = get_copy_asset(source_copy_id)
    if asset is None:
        return FragmentExtractionResult(
            source_copy_id=source_copy_id,
            status="failed",
            message="Copy asset not found.",
        )
    return _extract_fragments_result(asset)


def extract_fragments_for_approved_assets(limit: int = DEFAULT_BACKFILL_LIMIT) -> FragmentExtractionBatchResponse:
    assets = list_copy_assets(page=1, page_size=limit, status="approved").items
    results = [_extract_fragments_result(asset) for asset in assets]
    return FragmentExtractionBatchResponse(
        items=results,
        processed_count=len(results),
        created_count=sum(result.fragment_count for result in results if result.status == "created"),
        failed_count=sum(1 for result in results if result.status == "failed"),
    )


def _extract_fragments_result(asset: CopyAssetSummary) -> FragmentExtractionResult:
    if asset.status != "approved":
        return FragmentExtractionResult(
            source_copy_id=asset.id,
            status="skipped",
            message="Only approved copy assets can be extracted.",
        )
    try:
        existing = _existing_fragments(asset.id)
        if existing:
            return FragmentExtractionResult(
                source_copy_id=asset.id,
                status="skipped",
                fragment_count=len(existing),
                message="Fragments already exist for this copy asset.",
            )
        created = extract_fragments_for_asset(asset)
        return FragmentExtractionResult(
            source_copy_id=asset.id,
            status="created",
            fragment_count=len(created),
        )
    except RuntimeError as exc:
        return FragmentExtractionResult(
            source_copy_id=asset.id,
            status="failed",
            message=str(exc),
        )


def extract_fragments_for_asset(asset: CopyAssetSummary) -> list[FragmentItem]:
    if asset.status != "approved":
        return []

    existing = _existing_fragments(asset.id)
    if existing:
        return existing

    raw = get_llm_client().complete(_build_fragment_extraction_prompt(asset))
    try:
        parsed = json.loads(_strip_json_fence(raw))
        response = _FragmentExtractionResponse.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise RuntimeError(f"LLM returned invalid fragment extraction JSON: {exc}") from exc

    created: list[FragmentItem] = []
    generated = response.fragments
    for index, fragment in enumerate(generated):
        previous_text = generated[index - 1].fragment_text if index > 0 else None
        next_text = generated[index + 1].fragment_text if index < len(generated) - 1 else None
        created.append(
            knowledge.create_fragment(
                FragmentCreate(
                    source_copy_id=asset.id,
                    analysis_id=asset.id if asset.auto_analysis is not None else None,
                    sequence_order=index,
                    previous_fragment=previous_text,
                    next_fragment=next_text,
                    before_context=previous_text,
                    after_context=next_text,
                    fragment_text=fragment.fragment_text,
                    fragment_role=fragment.fragment_role,
                    position=fragment.position,
                    industry=asset.industry,
                    platform=asset.platform,
                    purpose=asset.purpose,
                    audience=asset.audience,
                    source_quality=_coerce_quality(fragment.source_quality),
                    risk_level=_coerce_risk_level(fragment.risk_level),
                    status=_fragment_status(fragment.confidence),
                    confidence=fragment.confidence,
                    metadata={"generation_reason": fragment.reason} if fragment.reason else {},
                )
            )
        )
    return created


def _existing_fragments(source_copy_id: str) -> list[FragmentItem]:
    existing = knowledge.list_fragments(
        page=1,
        page_size=100,
        source_copy_id=source_copy_id,
    )
    return [item for item in existing.items if isinstance(item, FragmentItem)]


def _build_fragment_extraction_prompt(asset: CopyAssetSummary) -> str:
    analysis = asset.reviewed_analysis or asset.auto_analysis
    analysis_payload = analysis.model_dump(mode="json") if analysis is not None else None
    context = {
        "platform": asset.platform,
        "industry": asset.industry,
        "audience": asset.audience,
        "purpose": asset.purpose,
        "style": asset.style,
        "analysis": analysis_payload,
    }
    return (
        "你是短视频、口播、图文文案的功能段拆解专家。\n"
        "任务：把已审核文案拆成功能段级素材片段，不要机械按句子切分。\n"
        "输出规则：\n"
        "1. 只返回一个合法 JSON 对象，不要返回 Markdown、代码块或解释文字。\n"
        "2. 返回字段为 fragments，类型为数组。\n"
        "3. 每个 fragment 代表一个文案功能单元，可以包含 1-3 句。\n"
        "4. fragment_role 建议使用 hook, pain_point, explanation, transition, proof, solution, cta。\n"
        "5. position 使用 opening, middle, ending。\n"
        "6. source_quality 使用 unknown, low, medium, high。\n"
        "7. risk_level 使用 low, medium, high。\n"
        "8. confidence 使用 0 到 1 的数字；低于阈值的片段会进入人工校正。\n"
        "返回 JSON 示例：\n"
        '{"fragments":[{"fragment_text":"","fragment_role":"hook","position":"opening","reason":"","source_quality":"high","risk_level":"low","confidence":0.9}]}\n'
        f"上下文：{json.dumps(context, ensure_ascii=False)}\n"
        f"待拆解文案：\n{asset.source_text.strip()}"
    )


def _fragment_status(confidence: float) -> str:
    if confidence >= settings.fragment_auto_approve_min_confidence:
        return "approved"
    return "pending_review"


def _coerce_quality(value: str) -> str:
    return value if value in {"unknown", "low", "medium", "high"} else "unknown"


def _coerce_risk_level(value: str) -> str:
    return value if value in {"low", "medium", "high"} else "low"


def _strip_json_fence(raw: str) -> str:
    text = raw.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()
