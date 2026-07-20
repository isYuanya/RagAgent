from collections.abc import Mapping
import csv
from io import StringIO

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError

from app.db.session import SessionLocal
from app.models.keyword_rankings import KeywordGroup, KeywordIndustry, KeywordVideo
from app.schemas.keyword_rankings import (
    KeywordGroupCreate,
    KeywordGroupItem,
    KeywordGroupListResponse,
    KeywordIndustryCreate,
    KeywordIndustryItem,
    KeywordIndustryListResponse,
    KeywordVideoImportRequest,
    KeywordVideoImportResponse,
    KeywordVideoImportRowError,
    KeywordVideoItem,
    KeywordVideoListResponse,
)


HOT_SCORE_WEIGHTS: dict[str, float] = {
    "likes": 0.4,
    "comments": 0.2,
    "favorites": 0.25,
    "shares": 0.15,
}

CSV_FIELDS = [
    "source_text",
    "source_url",
    "author_name",
    "author_url",
    "author_follower_count",
    "platform",
    "industry",
    "audience",
    "purpose",
    "style",
    "likes",
    "comments",
    "favorites",
    "shares",
]

INTEGER_FIELDS = ["author_follower_count", "likes", "comments", "favorites", "shares"]


def calculate_hot_score(
    *,
    likes: int,
    comments: int,
    favorites: int,
    shares: int,
    weights: Mapping[str, float] | None = None,
) -> float:
    active_weights = weights or HOT_SCORE_WEIGHTS
    return round(
        likes * active_weights["likes"]
        + comments * active_weights["comments"]
        + favorites * active_weights["favorites"]
        + shares * active_weights["shares"],
        4,
    )


def reset_keyword_ranking_store() -> None:
    db = SessionLocal()
    try:
        db.query(KeywordVideo).delete()
        db.query(KeywordGroup).delete()
        db.query(KeywordIndustry).delete()
        db.commit()
    finally:
        db.close()


def list_industries(page: int = 1, page_size: int = 20) -> KeywordIndustryListResponse:
    db = SessionLocal()
    try:
        statement = select(KeywordIndustry).where(KeywordIndustry.is_deleted.is_(False))
        total = _count(db, statement)
        rows = db.scalars(
            statement.order_by(KeywordIndustry.updated_at.desc(), KeywordIndustry.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return KeywordIndustryListResponse(
            items=[_industry_item(db, row) for row in rows],
            page=page,
            page_size=page_size,
            total=total,
        )
    finally:
        db.close()


def create_industry(payload: KeywordIndustryCreate) -> KeywordIndustryItem:
    db = SessionLocal()
    try:
        row = KeywordIndustry(
            name=payload.name.strip(),
            description=payload.description,
            status=payload.status,
        )
        db.add(row)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("行业名称已存在。") from exc
        db.refresh(row)
        return _industry_item(db, row)
    finally:
        db.close()


def get_industry(industry_id: str) -> KeywordIndustryItem | None:
    db = SessionLocal()
    try:
        row = _get_active_industry(db, industry_id)
        if row is None:
            return None
        return _industry_item(db, row)
    finally:
        db.close()


def delete_industry(industry_id: str) -> bool:
    db = SessionLocal()
    try:
        row = _get_active_industry(db, industry_id)
        if row is None:
            return False
        keyword_ids = db.scalars(
            select(KeywordGroup.id).where(KeywordGroup.industry_id == industry_id)
        ).all()
        if keyword_ids:
            db.query(KeywordVideo).filter(KeywordVideo.keyword_id.in_(keyword_ids)).delete(
                synchronize_session=False
            )
        db.query(KeywordGroup).filter(KeywordGroup.industry_id == industry_id).delete(
            synchronize_session=False
        )
        db.delete(row)
        db.commit()
        return True
    finally:
        db.close()


def list_keywords(
    industry_id: str,
    page: int = 1,
    page_size: int = 20,
) -> KeywordGroupListResponse | None:
    db = SessionLocal()
    try:
        if _get_active_industry(db, industry_id) is None:
            return None
        statement = select(KeywordGroup).where(KeywordGroup.industry_id == industry_id)
        total = _count(db, statement)
        rows = db.scalars(
            statement.order_by(KeywordGroup.updated_at.desc(), KeywordGroup.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return KeywordGroupListResponse(
            items=[_keyword_item(db, row) for row in rows],
            page=page,
            page_size=page_size,
            total=total,
        )
    finally:
        db.close()


def create_keyword(payload: KeywordGroupCreate) -> KeywordGroupItem | None:
    db = SessionLocal()
    try:
        if _get_active_industry(db, payload.industry_id) is None:
            return None
        row = _get_keyword_by_value(db, payload.industry_id, payload.keyword.strip())
        if row is None:
            row = KeywordGroup(industry_id=payload.industry_id, keyword=payload.keyword.strip())
            db.add(row)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                row = _get_keyword_by_value(db, payload.industry_id, payload.keyword.strip())
                if row is None:
                    raise
            else:
                db.refresh(row)
        return _keyword_item(db, row)
    finally:
        db.close()


def delete_keyword(keyword_id: str) -> bool:
    db = SessionLocal()
    try:
        row = db.get(KeywordGroup, keyword_id)
        if row is None:
            return False
        db.query(KeywordVideo).filter(KeywordVideo.keyword_id == keyword_id).delete(
            synchronize_session=False
        )
        db.delete(row)
        db.commit()
        return True
    finally:
        db.close()


def list_videos(keyword_id: str, page: int = 1, page_size: int = 50) -> KeywordVideoListResponse | None:
    db = SessionLocal()
    try:
        if db.get(KeywordGroup, keyword_id) is None:
            return None
        statement = select(KeywordVideo).where(KeywordVideo.keyword_id == keyword_id)
        total = _count(db, statement)
        rows = db.scalars(
            statement.order_by(KeywordVideo.hot_score.desc(), KeywordVideo.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        start_rank = (page - 1) * page_size + 1
        return KeywordVideoListResponse(
            items=[_video_item(row, start_rank + index) for index, row in enumerate(rows)],
            page=page,
            page_size=page_size,
            total=total,
        )
    finally:
        db.close()


def import_keyword_videos(payload: KeywordVideoImportRequest) -> KeywordVideoImportResponse | None:
    db = SessionLocal()
    try:
        if _get_active_industry(db, payload.industry_id) is None:
            return None
        keyword = payload.keyword.strip()
        group = _get_keyword_by_value(db, payload.industry_id, keyword)
        if group is None:
            group = KeywordGroup(industry_id=payload.industry_id, keyword=keyword)
            db.add(group)
            db.flush()

        fieldnames, rows = _read_csv(payload.csv_text)
        errors: list[KeywordVideoImportRowError] = []
        if fieldnames is None or "source_text" not in fieldnames:
            return KeywordVideoImportResponse(
                industry_id=payload.industry_id,
                keyword_id=str(group.id),
                keyword=keyword,
                created_count=0,
                updated_count=0,
                failed_count=1,
                video_count=_keyword_video_count(db, str(group.id)),
                errors=[
                    KeywordVideoImportRowError(row_number=1, message="CSV 必须包含 source_text 表头。")
                ],
            )

        created_count = 0
        updated_count = 0
        for index, row in enumerate(rows, start=2):
            parsed = _parse_video_row(row, index)
            if isinstance(parsed, KeywordVideoImportRowError):
                errors.append(parsed)
                continue
            existing = (
                _get_video_by_source_url(db, str(group.id), parsed["source_url"])
                if parsed["source_url"]
                else None
            )
            if existing is None:
                db.add(KeywordVideo(keyword_id=str(group.id), **parsed))
                created_count += 1
            else:
                for key, value in parsed.items():
                    setattr(existing, key, value)
                updated_count += 1

        db.flush()
        group.video_count = _keyword_video_count(db, str(group.id))
        db.commit()
        db.refresh(group)
        return KeywordVideoImportResponse(
            industry_id=payload.industry_id,
            keyword_id=str(group.id),
            keyword=keyword,
            created_count=created_count,
            updated_count=updated_count,
            failed_count=len(errors),
            video_count=group.video_count,
            errors=errors,
        )
    finally:
        db.close()


def _read_csv(csv_text: str) -> tuple[list[str] | None, list[dict[str, str | None]]]:
    reader = csv.DictReader(StringIO(csv_text))
    if reader.fieldnames is not None:
        reader.fieldnames = [_normalize_header(field) for field in reader.fieldnames]
    return reader.fieldnames, list(reader)


def _parse_video_row(
    row: dict[str, str | None], row_number: int
) -> dict | KeywordVideoImportRowError:
    source_text = (row.get("source_text") or "").strip()
    if not source_text:
        return KeywordVideoImportRowError(row_number=row_number, message="source_text 不能为空。")
    values: dict[str, object] = {
        "source_text": source_text,
        "source_url": _blank_to_none(row.get("source_url")),
        "author_name": _blank_to_none(row.get("author_name")),
        "author_url": _blank_to_none(row.get("author_url")),
        "platform": _blank_to_none(row.get("platform")),
        "industry": _blank_to_none(row.get("industry")),
        "audience": _blank_to_none(row.get("audience")),
        "purpose": _blank_to_none(row.get("purpose")),
        "style": _blank_to_none(row.get("style")),
    }
    for field in INTEGER_FIELDS:
        parsed = _optional_non_negative_int(row.get(field), field)
        if isinstance(parsed, str):
            return KeywordVideoImportRowError(row_number=row_number, message=parsed)
        values[field] = parsed if parsed is not None else 0
    values["hot_score"] = calculate_hot_score(
        likes=int(values["likes"]),
        comments=int(values["comments"]),
        favorites=int(values["favorites"]),
        shares=int(values["shares"]),
    )
    if row.get("author_follower_count") in (None, ""):
        values["author_follower_count"] = None
    return values


def _optional_non_negative_int(raw: str | None, field: str) -> int | str | None:
    value = (raw or "").strip()
    if not value:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return f"{field} 必须是非负整数。"
    if parsed < 0:
        return f"{field} 必须是非负整数。"
    return parsed


def _blank_to_none(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


def _normalize_header(value: str | None) -> str:
    return (value or "").strip().lstrip("\ufeff")


def _count(db, statement: Select) -> int:
    return int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)


def _get_active_industry(db, industry_id: str) -> KeywordIndustry | None:
    return db.scalar(
        select(KeywordIndustry).where(
            KeywordIndustry.id == industry_id,
            KeywordIndustry.is_deleted.is_(False),
        )
    )


def _get_keyword_by_value(db, industry_id: str, keyword: str) -> KeywordGroup | None:
    return db.scalar(
        select(KeywordGroup).where(
            KeywordGroup.industry_id == industry_id,
            KeywordGroup.keyword == keyword,
        )
    )


def _get_video_by_source_url(db, keyword_id: str, source_url: str | None) -> KeywordVideo | None:
    if source_url is None:
        return None
    return db.scalar(
        select(KeywordVideo).where(
            KeywordVideo.keyword_id == keyword_id,
            KeywordVideo.source_url == source_url,
        )
    )


def _keyword_video_count(db, keyword_id: str) -> int:
    return int(
        db.scalar(select(func.count()).select_from(KeywordVideo).where(KeywordVideo.keyword_id == keyword_id))
        or 0
    )


def _industry_item(db, row: KeywordIndustry) -> KeywordIndustryItem:
    keyword_count = int(
        db.scalar(select(func.count()).select_from(KeywordGroup).where(KeywordGroup.industry_id == row.id))
        or 0
    )
    video_count = int(
        db.scalar(
            select(func.count())
            .select_from(KeywordVideo)
            .join(KeywordGroup, KeywordGroup.id == KeywordVideo.keyword_id)
            .where(KeywordGroup.industry_id == row.id)
        )
        or 0
    )
    last_updated_at = db.scalar(
        select(func.max(KeywordVideo.updated_at))
        .select_from(KeywordVideo)
        .join(KeywordGroup, KeywordGroup.id == KeywordVideo.keyword_id)
        .where(KeywordGroup.industry_id == row.id)
    )
    return KeywordIndustryItem(
        id=str(row.id),
        name=row.name,
        description=row.description,
        status=row.status,
        keyword_count=keyword_count,
        video_count=video_count,
        last_updated_at=last_updated_at or row.updated_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _keyword_item(db, row: KeywordGroup) -> KeywordGroupItem:
    last_updated_at = db.scalar(
        select(func.max(KeywordVideo.updated_at)).where(KeywordVideo.keyword_id == row.id)
    )
    return KeywordGroupItem(
        id=str(row.id),
        industry_id=str(row.industry_id),
        keyword=row.keyword,
        video_count=_keyword_video_count(db, str(row.id)),
        last_updated_at=last_updated_at or row.updated_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _video_item(row: KeywordVideo, rank: int) -> KeywordVideoItem:
    return KeywordVideoItem(
        id=str(row.id),
        keyword_id=str(row.keyword_id),
        rank=rank,
        source_text=row.source_text,
        source_url=row.source_url,
        author_name=row.author_name,
        author_url=row.author_url,
        author_follower_count=row.author_follower_count,
        platform=row.platform,
        industry=row.industry,
        audience=row.audience,
        purpose=row.purpose,
        style=row.style,
        likes=row.likes,
        comments=row.comments,
        favorites=row.favorites,
        shares=row.shares,
        hot_score=row.hot_score,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
