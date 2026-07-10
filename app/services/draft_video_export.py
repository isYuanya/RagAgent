import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.llm import get_llm_client
from app.db.session import SessionLocal
from app.models.draft import DraftVideoExport as DraftVideoExportModel
from app.schemas.draft import (
    DraftVideoExportListResponse,
    DraftVideoExportPayload,
    DraftVideoExportRecord,
)
from app.services import drafts


class DraftVideoExportError(Exception):
    pass


@dataclass
class _Store:
    records: dict[str, DraftVideoExportRecord] = field(default_factory=dict)


_store = _Store()
_db_available: bool | None = False if settings.app_env == "test" else None


def reset_draft_video_export_store() -> None:
    global _db_available, _store
    _store = _Store()
    _db_available = False if settings.app_env == "test" else None


def generate_draft_video_export(draft_id: str) -> DraftVideoExportRecord:
    draft = drafts.get_draft(draft_id)
    if draft is None:
        raise drafts.DraftNotFoundError()
    text = draft.current_text.strip()
    if not text:
        raise drafts.DraftEmptyError("Draft has no text to export")

    llm = get_llm_client()
    raw = llm.complete(_build_video_export_prompt(draft_id, text))
    model = getattr(llm, "model", settings.openai_model)

    try:
        generated = json.loads(_strip_json_fence(raw))
        payload = _validate_generated_payload(generated)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise DraftVideoExportError(f"LLM returned invalid video export JSON: {exc}") from exc

    record = DraftVideoExportRecord(
        id=str(uuid4()),
        draft_id=draft_id,
        status="finished",
        result=payload,
        model=model,
        metadata={"source": "draft_video_export"},
        created_at=_now(),
        updated_at=_now(),
    )
    return _create_record(record)


def list_draft_video_exports(
    draft_id: str,
    page: int = 1,
    page_size: int = 20,
) -> DraftVideoExportListResponse:
    if drafts.get_draft(draft_id) is None:
        raise drafts.DraftNotFoundError()
    db_response = _db_list_records(draft_id, page, page_size)
    if db_response is not None:
        return db_response
    items = [
        item
        for item in _store.records.values()
        if item.draft_id == draft_id and item.status == "finished"
    ]
    items.sort(key=lambda item: item.created_at or "", reverse=True)
    return DraftVideoExportListResponse(
        items=_page(items, page, page_size),
        page=page,
        page_size=page_size,
        total=len(items),
    )


def _create_record(record: DraftVideoExportRecord) -> DraftVideoExportRecord:
    db_record = _db_create_record(record)
    if db_record is not None:
        return db_record
    _store.records[record.id] = record
    return record


def _db_create_record(record: DraftVideoExportRecord) -> DraftVideoExportRecord | None:
    if _db_available is False:
        return None
    try:
        with SessionLocal() as session:
            row = DraftVideoExportModel(
                id=record.id,
                draft_id=record.draft_id,
                status=record.status,
                result_json=record.result.model_dump(mode="json"),
                model=record.model,
                error=record.error,
                metadata_json=record.metadata,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            _mark_db_available(True)
            return _record_from_model(row) or record
    except SQLAlchemyError:
        _mark_db_available(False)
        return None


def _db_list_records(
    draft_id: str,
    page: int,
    page_size: int,
) -> DraftVideoExportListResponse | None:
    if _db_available is False:
        return None
    try:
        with SessionLocal() as session:
            stmt = (
                select(DraftVideoExportModel)
                .where(
                    DraftVideoExportModel.draft_id == draft_id,
                    DraftVideoExportModel.status == "finished",
                )
                .order_by(DraftVideoExportModel.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            count_stmt = select(func.count()).select_from(DraftVideoExportModel).where(
                DraftVideoExportModel.draft_id == draft_id,
                DraftVideoExportModel.status == "finished",
            )
            rows = session.scalars(stmt).all()
            items = [
                record
                for row in rows
                if (record := _record_from_model(row)) is not None
            ]
            total = session.scalar(count_stmt) or 0
            total = max(0, total - (len(rows) - len(items)))
            _mark_db_available(True)
            return DraftVideoExportListResponse(
                items=items,
                page=page,
                page_size=page_size,
                total=total,
            )
    except SQLAlchemyError:
        _mark_db_available(False)
        return None


def _record_from_model(row: DraftVideoExportModel) -> DraftVideoExportRecord | None:
    try:
        return DraftVideoExportRecord(
            id=str(row.id),
            draft_id=str(row.draft_id),
            status=row.status,
            result=DraftVideoExportPayload.model_validate(row.result_json or {}),
            model=row.model,
            error=row.error,
            metadata=row.metadata_json or {},
            created_at=_datetime_to_str(row.created_at),
            updated_at=_datetime_to_str(row.updated_at),
        )
    except ValidationError:
        return None


def _build_video_export_prompt(draft_id: str, text: str) -> str:
    context = {"draft_id": draft_id, "current_text": text}
    return (
        "You are a short-video copy formatting assistant.\n"
        "Return one valid JSON object only. Do not return Markdown, code fences, or explanations.\n"
        "All natural-language fields must be Simplified Chinese.\n"
        "The JSON object must contain exactly these fields:\n"
        '{"title":"2-16字视频发布标题","title_break":"顶部标题字幕，可最多一处换行",'
        '"description":"10-100字发布描述","script":"完整口播正文",'
        '"tts_script":"默认与script完全一致；必要时用[pinyin]替换一个多音字","hashtags":["最多5个话题文本，不带#"]}\n'
        "Rules:\n"
        "- title must be 2-16 Chinese characters, like a publishing title, not a long sentence.\n"
        "- title should avoid colon, question mark, exclamation mark, and complex punctuation.\n"
        "- title, title_break, and description must avoid these high-risk marketing terms: "
        "白户, 黑户, 包过, 包下, 秒批, 必下, 强开, 无视征信, 洗白征信, 包装资料, 流水, 百分百, 100%.\n"
        "- If source text contains high-risk terms, rewrite them into neutral wording: "
        "白户 -> 征信空白 or 信用记录少; 黑户 -> 严重逾期记录; 秒批/必下 -> 审批更快 or 匹配度更高.\n"
        "- description is required, 10-100 Chinese characters, and must summarize the core video idea. "
        "Do not copy the full spoken script.\n"
        "- title_break is for prominent top-of-video title subtitles, not the publishing title.\n"
        "- title_break must express the same meaning as title. It may be visually clearer, but must not add promises, quota guarantees, or change the core meaning.\n"
        "- title_break may contain at most two lines, using one newline character \\n. Short titles may have no newline.\n"
        "- title_break must split by meaning naturally, such as object/problem/result/action. Do not split one word, number-unit, or proper noun.\n"
        "- Each title_break line should preferably be 6-12 Chinese characters.\n"
        "- script must be a complete directly speakable script with its own hook and natural ending. The backend will not append hook or ending.\n"
        "- script must not depend on separate hook or ending fields, and must not repeat the same opening or ending sentence.\n"
        "- script ending must not contain interactive instructions such as 评论, 留言, 私信, 加好友, 打关键词, or 说出自己情况.\n"
        "- script must not contain pronunciation or pinyin annotations, including bracketed forms like [háng], [huán], [xíng].\n"
        "- script is normal subtitle and spoken-copy text for viewers.\n"
        "- tts_script must equal script exactly by default. Only when a polyphonic character needs a pronunciation hint, replace that single Chinese character with its bracketed pinyin token.\n"
        "- Correct example: script=你的选择越还越多，先别急着定。; tts_script=你的选择越[huán]越多，先别急着定。\n"
        "- Incorrect example: tts_script=你的选择越还[huán]越多，先别急着定。 Do not keep the Chinese character before its pinyin token.\n"
        "- script itself should use natural spoken language and avoid formal phrasing that TTS may segment poorly.\n"
        "- hashtags must contain at most 5 plain topic strings. Do not prefix hashtags with #.\n"
        f"Context JSON:\n{json.dumps(context, ensure_ascii=False)}"
    )


def _build_prompt(draft_id: str, text: str) -> str:
    context = {"draft_id": draft_id, "current_text": text}
    return (
        "You are a short-video copy formatting assistant.\n"
        "Return one valid JSON object only. Do not return Markdown, code fences, or explanations.\n"
        "All natural-language fields must be Simplified Chinese.\n"
        "The JSON object must contain exactly these fields:\n"
        '{"title":"2-16字视频标题","title_break":"适合顶部标题字幕的自然换行版本",'
        '"description":"10-100字发布描述","script":"字幕正文，不含拼音标注，按自然段换行",'
        '"tts_script":"配音正文，可少量使用多音字拼音标注","hashtags":["最多5个话题标签"]}\n'
        "Rules:\n"
        "- title must be 2-16 Chinese characters.\n"
        "- title_break should insert natural line breaks for top title subtitles.\n"
        "- description must be 10-100 Chinese characters.\n"
        "- script must not contain pinyin annotations and should keep natural paragraph breaks.\n"
        "- tts_script can include a small number of pinyin annotations only when needed for polyphonic words.\n"
        "- hashtags must contain at most 5 items.\n"
        f"Context JSON:\n{json.dumps(context, ensure_ascii=False)}"
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


def _validate_generated_payload(payload: object) -> DraftVideoExportPayload:
    try:
        return DraftVideoExportPayload.model_validate(payload)
    except ValidationError as original_error:
        normalized = _normalize_legacy_tts_pinyin_format(payload)
        if normalized == payload:
            raise original_error
        try:
            return DraftVideoExportPayload.model_validate(normalized)
        except ValidationError:
            raise original_error from None


def _normalize_legacy_tts_pinyin_format(payload: object) -> object:
    """Convert a legacy `汉字[pinyin]` TTS annotation only after strict validation fails."""
    if not isinstance(payload, dict):
        return payload
    tts_script = payload.get("tts_script")
    script = payload.get("script")
    if not isinstance(tts_script, str) or not isinstance(script, str):
        return payload

    normalized = dict(payload)
    normalized["tts_script"] = _replace_legacy_pinyin_annotations(tts_script, script)
    return normalized


def _replace_legacy_pinyin_annotations(tts_script: str, script: str) -> str:
    source = "".join(script.split())
    result: list[str] = []
    source_index = 0
    index = 0

    while index < len(tts_script):
        char = tts_script[index]
        if char.isspace():
            result.append(char)
            index += 1
            continue
        if char == "[":
            closing = tts_script.find("]", index + 1)
            if closing != -1:
                result.append(tts_script[index : closing + 1])
                source_index += 1
                index = closing + 1
                continue
        if source_index < len(source) and char == source[source_index]:
            next_index = index + 1
            if next_index < len(tts_script) and tts_script[next_index] == "[":
                closing = tts_script.find("]", next_index + 1)
                if closing != -1:
                    result.append(tts_script[next_index : closing + 1])
                    source_index += 1
                    index = closing + 1
                    continue
        result.append(char)
        source_index += 1
        index += 1

    return "".join(result)


def _page(items: list, page: int, page_size: int) -> list:
    start = (page - 1) * page_size
    return items[start : start + page_size]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _datetime_to_str(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _mark_db_available(value: bool) -> None:
    global _db_available
    _db_available = value
