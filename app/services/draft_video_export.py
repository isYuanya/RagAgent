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
    raw = llm.complete(_build_prompt(draft_id, text))
    model = getattr(llm, "model", settings.openai_model)

    try:
        payload = DraftVideoExportPayload.model_validate(json.loads(_strip_json_fence(raw)))
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
            return _record_from_model(row)
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
            total = session.scalar(count_stmt) or 0
            _mark_db_available(True)
            return DraftVideoExportListResponse(
                items=[_record_from_model(row) for row in rows],
                page=page,
                page_size=page_size,
                total=total,
            )
    except SQLAlchemyError:
        _mark_db_available(False)
        return None


def _record_from_model(row: DraftVideoExportModel) -> DraftVideoExportRecord:
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
