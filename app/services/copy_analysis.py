import json
import re

from pydantic import ValidationError

from app.core.llm import get_llm_client
from app.schemas.copy import CopyAnalysisRequest, CopyAnalysisResponse


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
