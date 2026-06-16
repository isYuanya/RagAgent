import json
import re

from pydantic import BaseModel, Field, ValidationError

from app.core.llm import get_llm_client
from app.schemas.common import ContentType
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
    structure_type: str | None = None
    content_type: str | None = None
    metrics: dict[str, int | str | None] = Field(default_factory=dict)


def _build_copy_analysis_prompt(payload: CopyAnalysisRequest) -> str:
    context = {
        "industry": payload.industry,
        "audience": payload.audience,
        "platform": payload.platform,
        "purpose": payload.purpose,
        "style": payload.style,
        "structure_type": payload.structure_type,
        "content_type": payload.content_type,
    }
    return (
        "你是短视频、口播、图文种草文案的结构化拆解专家。\n"
        "任务：分析输入文案的表达策略，抽象出可复用的结构和写法。\n"
        "输出规则：\n"
        "1. 只返回一个合法 JSON 对象，不要返回 Markdown、代码块、解释文字或额外前后缀。\n"
        "2. 所有字段都必须出现；无法判断时用空字符串、空数组或 confidence 降低体现，不要省略字段。\n"
        "3. 不要编造文案中没有依据的产品功效、平台数据、作者信息或用户画像。\n"
        "4. 数组字段必须返回字符串数组，不要返回逗号分隔字符串。\n"
        "5. confidence 使用 0 到 1 的数字，表示本次拆解的可靠程度。\n"
        "JSON 字段定义：\n"
        "- topic: 文案主题，一句话概括。\n"
        "- target_user: 目标用户，优先结合文案和上下文判断。\n"
        "- core_pain: 被击中的核心痛点或欲望。\n"
        "- emotion_buttons: 触发用户情绪的关键词数组。\n"
        "- hook: 开头钩子或最能抓人的表达。\n"
        "- structure: 内容推进顺序数组，例如 痛点共鸣 -> 原因解释 -> 行动建议。\n"
        "- expression_skills: 表达技巧数组，例如 反问、对比、具体场景、口语化。\n"
        "- reusable_template: 可复用句式或框架，保留变量占位符 ___。\n"
        "- suitable_scenarios: 适用场景数组，例如 小红书种草、私域转化、短视频口播。\n"
        "- risk_warnings: 风险对象数组；每项必须包含 level: low | medium | high, message, suggestion。\n"
        "- confidence: 0 到 1 的数字。\n"
        "返回 JSON 示例：\n"
        '{"topic":"","target_user":"","core_pain":"","emotion_buttons":[],"hook":"","structure":[],"expression_skills":[],"reusable_template":"","suitable_scenarios":[],"risk_warnings":[],"confidence":0.8}\n'
        f"上下文：{json.dumps(context, ensure_ascii=False)}\n"
        f"待拆解文案：\n{payload.source_text.strip()}"
    )


def _build_text_import_prompt(text: str) -> str:
    return (
        "你是文案资产导入助手，负责从用户粘贴的混合文本中抽取原文案和来源元数据。\n"
        "输出规则：\n"
        "1. 只返回一个合法 JSON 对象，不要返回 Markdown、代码块、解释文字或额外前后缀。\n"
        "2. 只抽取输入中明确出现的信息；不要猜测作者、平台、粉丝数、行业、人群、目的或表现数据。\n"
        "3. 无法确定的字段返回 null；metrics 无法确定时返回空对象 {}。\n"
        "4. source_text 只保留真正的文案正文，不要包含作者、平台、链接、粉丝数、点赞评论等说明文字。\n"
        "5. author_follower_count、likes、comments、favorites、shares 尽量转成数字；5.2万 转为 52000，52k 转为 52000。\n"
        "6. content_type 只能使用：种草、情绪、知识、反转、故事、干货、争议；无法判断返回 null。\n"
        "字段定义：\n"
        "- source_text: 原文案正文。\n"
        "- source_url: 文案来源链接。\n"
        "- author_name: 作者、账号、博主、达人或发布者名称。\n"
        "- author_url: 作者主页链接。\n"
        "- author_follower_count: 作者粉丝数，非负整数。\n"
        "- platform: 发布平台或渠道，例如 小红书、抖音、视频号、公众号。\n"
        "- industry: 行业或赛道。\n"
        "- audience: 目标人群。\n"
        "- purpose: 内容目的，例如 种草、引流、成交、涨粉。\n"
        "- style: 表达风格。\n"
        "- structure_type: 内容结构类型。\n"
        "- content_type: 内容类型枚举。\n"
        "- metrics: 表现数据对象，只允许 likes, comments, favorites, shares。\n"
        "返回 JSON 示例：\n"
        '{"source_text":"","source_url":null,"author_name":null,"author_url":null,"author_follower_count":null,"platform":null,"industry":null,"audience":null,"purpose":null,"style":null,"structure_type":null,"content_type":null,"metrics":{}}\n'
        f"用户粘贴内容：\n{text.strip()}"
    )


def analyze_copy(payload: CopyAnalysisRequest) -> CopyAnalysisResponse:
    prompt = _build_copy_analysis_prompt(payload)
    raw = get_llm_client().complete(prompt)

    try:
        parsed = json.loads(_strip_json_fence(raw))
        parsed = _normalize_analysis_payload(parsed)
        return CopyAnalysisResponse.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise RuntimeError(f"LLM returned invalid copy analysis JSON: {exc}") from exc


def extract_text_import_payload(text: str) -> CopyAnalysisRequest:
    prompt = _build_text_import_prompt(text)
    try:
        raw = get_llm_client().complete(prompt)
        parsed = json.loads(_strip_json_fence(raw))
        metadata = _TextImportMetadata.model_validate(parsed)
    except Exception:
        return CopyAnalysisRequest(source_text=text.strip())

    fallback = _extract_text_import_fallback(text)
    source_text = _blank_to_none(metadata.source_text) or fallback.get("source_text") or text.strip()
    return CopyAnalysisRequest(
        source_text=source_text,
        source_url=_blank_to_none(metadata.source_url) or fallback.get("source_url"),
        author_name=_blank_to_none(metadata.author_name) or fallback.get("author_name"),
        author_url=_blank_to_none(metadata.author_url) or fallback.get("author_url"),
        author_follower_count=_coerce_non_negative_int(metadata.author_follower_count)
        or fallback.get("author_follower_count"),
        platform=_blank_to_none(metadata.platform) or fallback.get("platform"),
        industry=_blank_to_none(metadata.industry) or fallback.get("industry"),
        audience=_blank_to_none(metadata.audience) or fallback.get("audience"),
        purpose=_blank_to_none(metadata.purpose) or fallback.get("purpose"),
        style=_blank_to_none(metadata.style) or fallback.get("style"),
        structure_type=_blank_to_none(metadata.structure_type) or fallback.get("structure_type"),
        content_type=_coerce_content_type(metadata.content_type or fallback.get("content_type")),
        metrics=_normalize_metrics(metadata.metrics) or fallback.get("metrics") or {},
    )


def _extract_text_import_fallback(text: str) -> dict:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    metadata: dict = {}
    body_lines: list[str] = []

    for line in lines:
        key, value = _split_metadata_line(line)
        if key is None or value is None:
            body_lines.append(line)
            continue

        normalized_key = _normalize_metadata_key(key)
        if normalized_key is None:
            body_lines.append(line)
            continue

        if normalized_key == "author_follower_count":
            parsed = _coerce_non_negative_int(value)
            if parsed is not None:
                metadata[normalized_key] = parsed
            continue

        if normalized_key == "metrics":
            metadata["metrics"] = _merge_metrics(metadata.get("metrics") or {}, value)
            continue

        metadata[normalized_key] = value.strip()

    if "source_url" not in metadata:
        url_match = re.search(r"https?://[^\s，。；;]+", text)
        if url_match:
            metadata["source_url"] = url_match.group(0)

    if "author_name" not in metadata:
        author_match = re.search(r"(?:作者|账号|博主|达人|发布者)\s*[：:]\s*([^\n，,；;]+)", text)
        if author_match:
            metadata["author_name"] = author_match.group(1).strip()

    if "author_follower_count" not in metadata:
        follower_patterns = (
            r"(?:粉丝数|粉丝数量|粉丝)\s*[：:：]?\s*([0-9][0-9,.\s]*(?:万|w|W|k|K)?)",
            r"([0-9][0-9,.\s]*(?:万|w|W|k|K)?)\s*粉丝",
        )
        for pattern in follower_patterns:
            follower_match = re.search(pattern, text)
            if follower_match:
                parsed = _coerce_non_negative_int(follower_match.group(1))
                if parsed is not None:
                    metadata["author_follower_count"] = parsed
                    break

    if "platform" not in metadata:
        platform_match = re.search(
            r"(小红书|抖音|快手|视频号|微信视频号|公众号|微博|知乎|B站|哔哩哔哩|TikTok|Instagram|YouTube)",
            text,
            re.IGNORECASE,
        )
        if platform_match:
            metadata["platform"] = platform_match.group(1)

    source_text = _blank_to_none(metadata.get("source_text"))
    if source_text is None:
        source_text = "\n".join(body_lines).strip()
    if source_text:
        metadata["source_text"] = source_text
    return metadata


def _split_metadata_line(line: str) -> tuple[str | None, str | None]:
    match = re.match(r"^\s*([^：:\-—]+?)\s*[：:\-—]\s*(.+?)\s*$", line)
    if not match:
        return None, None
    return match.group(1).strip(), match.group(2).strip()


def _normalize_metadata_key(key: str) -> str | None:
    normalized = key.strip().lower().replace(" ", "").replace("_", "")
    key_map = {
        "正文": "source_text",
        "内容": "source_text",
        "文案": "source_text",
        "原文": "source_text",
        "链接": "source_url",
        "来源链接": "source_url",
        "原文链接": "source_url",
        "url": "source_url",
        "sourceurl": "source_url",
        "作者": "author_name",
        "账号": "author_name",
        "博主": "author_name",
        "达人": "author_name",
        "发布者": "author_name",
        "author": "author_name",
        "作者主页": "author_url",
        "主页": "author_url",
        "authorurl": "author_url",
        "粉丝": "author_follower_count",
        "粉丝数": "author_follower_count",
        "粉丝数量": "author_follower_count",
        "followers": "author_follower_count",
        "平台": "platform",
        "渠道": "platform",
        "来源平台": "platform",
        "platform": "platform",
        "行业": "industry",
        "赛道": "industry",
        "industry": "industry",
        "人群": "audience",
        "目标人群": "audience",
        "受众": "audience",
        "audience": "audience",
        "目的": "purpose",
        "目标": "purpose",
        "purpose": "purpose",
        "风格": "style",
        "style": "style",
        "结构类型": "structure_type",
        "内容类型": "content_type",
        "类型": "content_type",
        "指标": "metrics",
        "数据": "metrics",
    }
    return key_map.get(normalized)


def _merge_metrics(metrics: dict[str, int], raw: str) -> dict[str, int]:
    merged = dict(metrics)
    patterns = {
        "likes": r"(?:点赞|赞|likes?)\s*[：:：]?\s*([0-9][0-9,.\s]*(?:万|w|W|k|K)?)",
        "comments": r"(?:评论|comments?)\s*[：:：]?\s*([0-9][0-9,.\s]*(?:万|w|W|k|K)?)",
        "favorites": r"(?:收藏|favorites?)\s*[：:：]?\s*([0-9][0-9,.\s]*(?:万|w|W|k|K)?)",
        "shares": r"(?:分享|转发|shares?)\s*[：:：]?\s*([0-9][0-9,.\s]*(?:万|w|W|k|K)?)",
    }
    for field, pattern in patterns.items():
        match = re.search(pattern, raw, re.IGNORECASE)
        if match:
            parsed = _coerce_non_negative_int(match.group(1))
            if parsed is not None:
                merged[field] = parsed
    return merged


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
    normalized = raw.replace(",", "").replace("，", "").replace(" ", "")
    suffix = normalized[-1:].lower()
    if suffix in {"万", "w", "k"}:
        multiplier = 10000 if suffix in {"万", "w"} else 1000
        try:
            parsed = float(normalized[:-1])
        except ValueError:
            return None
        result = round(parsed * multiplier)
        return result if result >= 0 else None
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


def _coerce_content_type(value: str | None) -> ContentType | None:
    normalized = _blank_to_none(value)
    if normalized is None:
        return None
    try:
        return ContentType(normalized)
    except ValueError:
        return None
