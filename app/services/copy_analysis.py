import json
import re

from pydantic import BaseModel, Field, ValidationError

from app.core.llm import get_llm_client
from app.schemas.copy import CopyAnalysisRequest, CopyAnalysisResponse


class _TextImportMetadata(BaseModel):
    source_text: str | None = None
    source_url: str | None = None
    author_name: str | None = None
    author_url: str | None = None
    author_follower_count: int | str | None = None
    platform: str | None = None
    industry: str | None = None
    audience: str | None = None
    purpose: str | None = None
    style: str | None = None
    metrics: dict[str, int | str | None] = Field(default_factory=dict)


def analyze_copy(payload: CopyAnalysisRequest) -> CopyAnalysisResponse:
    prompt = (
        "你是短视频/口播文案拆解专家。请只返回 JSON，不要返回 Markdown。\n"
        "JSON 字段必须包含：topic、target_user、core_pain、emotion_buttons、hook、"
        "structure、expression_skills、reusable_template、suitable_scenarios、"
        "risk_warnings、confidence。\n"
        "emotion_buttons、structure、expression_skills、suitable_scenarios 必须是字符串数组。\n"
        "risk_warnings 必须是对象数组，每项包含 level、message、suggestion。\n"
        f"文案：{payload.source_text.strip()}\n"
        f"上下文：industry={payload.industry}, audience={payload.audience}, "
        f"platform={payload.platform}, purpose={payload.purpose}, style={payload.style}"
    )
    raw = get_llm_client().complete(prompt)

    try:
        parsed = json.loads(_strip_json_fence(raw))
        parsed = _normalize_analysis_payload(parsed)
        return CopyAnalysisResponse.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise RuntimeError(f"LLM returned invalid copy analysis JSON: {exc}") from exc


def extract_text_import_payload(text: str) -> CopyAnalysisRequest:
    prompt = (
        "你是文案导入助手。请只返回 JSON，不要返回 Markdown。\n"
        "从用户粘贴内容中提取正文和来源元数据。无法确定的字段返回 null 或空对象。\n"
        "JSON 字段包括：source_text, source_url, author_name, author_url, "
        "author_follower_count, platform, industry, audience, purpose, style, metrics。\n"
        "metrics 可以包含 likes, comments, favorites, shares，数值字段尽量转成数字。\n"
        "source_text 只保留真正的文案正文，不要包含作者、平台、粉丝数等说明文字。\n"
        f"用户粘贴内容：{text.strip()}"
    )
    try:
        raw = get_llm_client().complete(prompt)
        parsed = json.loads(_strip_json_fence(raw))
        metadata = _TextImportMetadata.model_validate(parsed)
    except Exception:
        return CopyAnalysisRequest(source_text=text.strip())

    source_text = _blank_to_none(metadata.source_text) or text.strip()
    return CopyAnalysisRequest(
        source_text=source_text,
        source_url=_blank_to_none(metadata.source_url),
        author_name=_blank_to_none(metadata.author_name),
        author_url=_blank_to_none(metadata.author_url),
        author_follower_count=_coerce_non_negative_int(metadata.author_follower_count),
        platform=_blank_to_none(metadata.platform),
        industry=_blank_to_none(metadata.industry),
        audience=_blank_to_none(metadata.audience),
        purpose=_blank_to_none(metadata.purpose),
        style=_blank_to_none(metadata.style),
        metrics=_normalize_metrics(metadata.metrics),
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


def _normalize_analysis_payload(payload: object) -> object:
    if not isinstance(payload, dict):
        return payload

    normalized = dict(payload)
    for field in (
        "emotion_buttons",
        "structure",
        "expression_skills",
        "suitable_scenarios",
    ):
        normalized[field] = _coerce_string_list(normalized.get(field))
    return normalized


def _coerce_string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    if isinstance(value, str):
        return [
            item.strip(" -•\t")
            for item in re.split(r"\s*(?:->|→|、|，|,|/|；|;|\n)\s*", value)
            if item.strip(" -•\t")
        ]
    return [str(value).strip()]


def _normalize_metrics(metrics: dict[str, int | str | None]) -> dict[str, int]:
    normalized: dict[str, int] = {}
    for field in ("likes", "comments", "favorites", "shares"):
        value = _coerce_non_negative_int(metrics.get(field))
        if value is not None:
            normalized[field] = value
    return normalized


def _coerce_non_negative_int(value: int | str | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    raw = value.strip()
    if not raw:
        return None
    multiplier = 1
    if raw.endswith("万"):
        multiplier = 10000
        raw = raw[:-1]
    elif raw.lower().endswith("k"):
        multiplier = 1000
        raw = raw[:-1]
    raw = raw.replace(",", "").replace("，", "")
    try:
        parsed = float(raw)
    except ValueError:
        return None
    result = round(parsed * multiplier)
    return result if result >= 0 else None


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
