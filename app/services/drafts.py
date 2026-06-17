from dataclasses import dataclass, field
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.draft import Draft as DraftModel
from app.models.draft import DraftItem as DraftItemModel
from app.models.draft import DraftVersion as DraftVersionModel
from app.schemas.draft import (
    DraftCreate,
    DraftDetail,
    DraftItem,
    DraftItemCreate,
    DraftItemReorderRequest,
    DraftItemSnapshot,
    DraftItemUpdate,
    DraftListResponse,
    DraftSummary,
    DraftUpdate,
    DraftVersionCreate,
    DraftVersionDetail,
    DraftVersionSummary,
)
from app.services import knowledge


class DraftNotFoundError(Exception):
    pass


class DraftItemNotFoundError(Exception):
    pass


class SourceFragmentNotFoundError(Exception):
    pass


@dataclass
class _Store:
    drafts: dict[str, DraftDetail] = field(default_factory=dict)
    versions: dict[str, list[DraftVersionDetail]] = field(default_factory=dict)


_store = _Store()
_db_available: bool | None = False if settings.app_env == "test" else None


def reset_draft_store() -> None:
    global _db_available, _store
    _store = _Store()
    _db_available = False if settings.app_env == "test" else None


def list_drafts(
    page: int = 1,
    page_size: int = 20,
    status: str | None = "draft",
) -> DraftListResponse:
    db_response = _db_list_drafts(page, page_size, status)
    if db_response is not None:
        return db_response
    items = [
        _to_summary(draft)
        for draft in _store.drafts.values()
        if status is None or draft.status == status
    ]
    return DraftListResponse(
        items=_page(items, page, page_size),
        page=page,
        page_size=page_size,
        total=len(items),
    )


def create_draft(payload: DraftCreate) -> DraftDetail:
    db_item = _db_create_draft(payload)
    if db_item is not None:
        return db_item
    draft = DraftDetail(
        id=str(uuid4()),
        title=payload.title,
        goal=payload.goal,
        audience=payload.audience,
        platform=payload.platform,
        purpose=payload.purpose,
        status="draft",
        current_text="",
        item_count=0,
        metadata=payload.metadata,
        items=[],
    )
    _store.drafts[draft.id] = draft
    _store.versions[draft.id] = []
    return draft


def get_draft(draft_id: str) -> DraftDetail | None:
    db_item = _db_get_draft(draft_id)
    if db_item is not None:
        return db_item
    draft = _store.drafts.get(draft_id)
    return _refresh_detail(draft) if draft is not None else None


def update_draft(draft_id: str, payload: DraftUpdate) -> DraftDetail | None:
    db_item = _db_update_draft(draft_id, payload)
    if db_item is not None:
        return db_item
    draft = get_draft(draft_id)
    if draft is None:
        return None
    updated = draft.model_copy(update=_without_none(payload.model_dump()))
    _store.drafts[draft_id] = _refresh_detail(updated)
    return _store.drafts[draft_id]


def archive_draft(draft_id: str) -> bool:
    payload = DraftUpdate(status="archived")
    return update_draft(draft_id, payload) is not None


def replace_draft_text(
    draft_id: str,
    text: str,
    role: str | None = None,
    position: str | None = None,
    metadata: dict | None = None,
) -> DraftDetail:
    db_item = _db_replace_draft_text(draft_id, text, role, position, metadata or {})
    if db_item is not None:
        return db_item
    draft = get_draft(draft_id)
    if draft is None:
        raise DraftNotFoundError()
    draft.items = [
        DraftItem(
            id=str(uuid4()),
            draft_id=draft_id,
            order_index=0,
            edited_text=text,
            role=role,
            position=position,
            metadata=metadata or {},
        )
    ]
    _store.drafts[draft_id] = _refresh_detail(draft)
    return _store.drafts[draft_id]


def add_draft_item(draft_id: str, payload: DraftItemCreate) -> DraftDetail:
    db_item = _db_add_draft_item(draft_id, payload)
    if db_item is not None:
        return db_item
    draft = get_draft(draft_id)
    if draft is None:
        raise DraftNotFoundError()
    fragment = _get_fragment_or_none(payload.source_fragment_id)
    if payload.source_fragment_id is not None and fragment is None:
        raise SourceFragmentNotFoundError()
    item = DraftItem(
        id=str(uuid4()),
        draft_id=draft_id,
        source_fragment_id=payload.source_fragment_id,
        source_copy_id=fragment.source_copy_id if fragment else None,
        order_index=payload.order_index if payload.order_index is not None else _next_order(draft.items),
        original_fragment_text=fragment.fragment_text if fragment else None,
        edited_text=payload.edited_text or (fragment.fragment_text if fragment else ""),
        role=payload.role if payload.role is not None else (fragment.fragment_role if fragment else None),
        position=payload.position if payload.position is not None else (fragment.position if fragment else None),
        metadata=payload.metadata,
    )
    draft.items.append(item)
    _store.drafts[draft_id] = _refresh_detail(draft)
    return _store.drafts[draft_id]


def update_draft_item(
    draft_id: str,
    item_id: str,
    payload: DraftItemUpdate,
) -> DraftDetail:
    db_item = _db_update_draft_item(draft_id, item_id, payload)
    if db_item is not None:
        return db_item
    draft = get_draft(draft_id)
    if draft is None:
        raise DraftNotFoundError()
    for index, item in enumerate(draft.items):
        if item.id == item_id:
            draft.items[index] = item.model_copy(update=_without_none(payload.model_dump()))
            _store.drafts[draft_id] = _refresh_detail(draft)
            return _store.drafts[draft_id]
    raise DraftItemNotFoundError()


def delete_draft_item(draft_id: str, item_id: str) -> None:
    db_result = _db_delete_draft_item(draft_id, item_id)
    if db_result is not None:
        if not db_result:
            raise DraftItemNotFoundError()
        return
    draft = get_draft(draft_id)
    if draft is None:
        raise DraftNotFoundError()
    before = len(draft.items)
    draft.items = [item for item in draft.items if item.id != item_id]
    if len(draft.items) == before:
        raise DraftItemNotFoundError()
    _store.drafts[draft_id] = _refresh_detail(draft)


def reorder_draft_items(draft_id: str, payload: DraftItemReorderRequest) -> DraftDetail:
    db_item = _db_reorder_draft_items(draft_id, payload)
    if db_item is not None:
        return db_item
    draft = get_draft(draft_id)
    if draft is None:
        raise DraftNotFoundError()
    updates = {item.item_id: item.order_index for item in payload.items}
    existing = {item.id for item in draft.items}
    if not set(updates).issubset(existing):
        raise DraftItemNotFoundError()
    draft.items = [
        item.model_copy(update={"order_index": updates.get(item.id, item.order_index)})
        for item in draft.items
    ]
    _store.drafts[draft_id] = _refresh_detail(draft)
    return _store.drafts[draft_id]


def create_draft_version(draft_id: str, payload: DraftVersionCreate) -> DraftVersionDetail:
    db_item = _db_create_draft_version(draft_id, payload)
    if db_item is not None:
        return db_item
    draft = get_draft(draft_id)
    if draft is None:
        raise DraftNotFoundError()
    versions = _store.versions.setdefault(draft_id, [])
    snapshot = _snapshot_items(draft.items)
    version = DraftVersionDetail(
        id=str(uuid4()),
        draft_id=draft_id,
        version_number=len(versions) + 1,
        label=payload.label,
        current_text=draft.current_text,
        item_count=len(snapshot),
        metadata=payload.metadata,
        items=snapshot,
    )
    versions.append(version)
    return version


def list_draft_versions(draft_id: str) -> list[DraftVersionSummary]:
    db_items = _db_list_draft_versions(draft_id)
    if db_items is not None:
        return db_items
    if draft_id not in _store.drafts:
        raise DraftNotFoundError()
    return [_version_summary(version) for version in _store.versions.get(draft_id, [])]


def get_draft_version(draft_id: str, version_id: str) -> DraftVersionDetail | None:
    db_item = _db_get_draft_version(draft_id, version_id)
    if db_item is not None:
        return db_item
    if draft_id not in _store.drafts:
        raise DraftNotFoundError()
    for version in _store.versions.get(draft_id, []):
        if version.id == version_id:
            return version
    return None


def _db_list_drafts(
    page: int,
    page_size: int,
    status: str | None,
) -> DraftListResponse | None:
    if _db_available is False:
        return None
    try:
        with SessionLocal() as session:
            stmt = select(DraftModel).options(selectinload(DraftModel.items))
            count_stmt = select(func.count()).select_from(DraftModel)
            if status is not None:
                stmt = stmt.where(DraftModel.status == status)
                count_stmt = count_stmt.where(DraftModel.status == status)
            stmt = stmt.order_by(DraftModel.updated_at.desc()).offset((page - 1) * page_size).limit(
                page_size
            )
            rows = session.scalars(stmt).all()
            total = session.scalar(count_stmt) or 0
            _mark_db_available(True)
            return DraftListResponse(
                items=[_summary_from_model(row) for row in rows],
                page=page,
                page_size=page_size,
                total=total,
            )
    except SQLAlchemyError:
        _mark_db_available(False)
        return None


def _db_create_draft(payload: DraftCreate) -> DraftDetail | None:
    if _db_available is False:
        return None
    try:
        with SessionLocal() as session:
            row = DraftModel(
                title=payload.title,
                goal=payload.goal,
                audience=payload.audience,
                platform=payload.platform,
                purpose=payload.purpose,
                status="draft",
                metadata_json=payload.metadata,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            _mark_db_available(True)
            return _detail_from_model(row)
    except SQLAlchemyError:
        _mark_db_available(False)
        return None


def _db_get_draft(draft_id: str) -> DraftDetail | None:
    if _db_available is False:
        return None
    try:
        with SessionLocal() as session:
            row = session.scalar(
                select(DraftModel)
                .options(selectinload(DraftModel.items))
                .where(DraftModel.id == draft_id)
            )
            _mark_db_available(True)
            return _detail_from_model(row) if row is not None else None
    except SQLAlchemyError:
        _mark_db_available(False)
        return None


def _db_update_draft(draft_id: str, payload: DraftUpdate) -> DraftDetail | None:
    if _db_available is False:
        return None
    try:
        with SessionLocal() as session:
            row = session.scalar(
                select(DraftModel)
                .options(selectinload(DraftModel.items))
                .where(DraftModel.id == draft_id)
            )
            if row is None:
                _mark_db_available(True)
                return None
            updates = _without_none(payload.model_dump())
            metadata = updates.pop("metadata", None)
            for field_name, value in updates.items():
                setattr(row, field_name, value)
            if metadata is not None:
                row.metadata_json = metadata
            session.commit()
            session.refresh(row)
            _mark_db_available(True)
            return _detail_from_model(row)
    except SQLAlchemyError:
        _mark_db_available(False)
        return None


def _db_add_draft_item(draft_id: str, payload: DraftItemCreate) -> DraftDetail | None:
    if _db_available is False:
        return None
    try:
        with SessionLocal() as session:
            draft = session.scalar(
                select(DraftModel)
                .options(selectinload(DraftModel.items))
                .where(DraftModel.id == draft_id)
            )
            if draft is None:
                raise DraftNotFoundError()
            fragment = _get_fragment_or_none(payload.source_fragment_id)
            if payload.source_fragment_id is not None and fragment is None:
                raise SourceFragmentNotFoundError()
            row = DraftItemModel(
                draft_id=draft_id,
                source_fragment_id=payload.source_fragment_id,
                source_copy_id=fragment.source_copy_id if fragment else None,
                order_index=payload.order_index
                if payload.order_index is not None
                else _next_order([_item_from_model(item) for item in draft.items]),
                original_fragment_text=fragment.fragment_text if fragment else None,
                edited_text=payload.edited_text or (fragment.fragment_text if fragment else ""),
                role=payload.role if payload.role is not None else (fragment.fragment_role if fragment else None),
                position=payload.position
                if payload.position is not None
                else (fragment.position if fragment else None),
                metadata_json=payload.metadata,
            )
            session.add(row)
            session.commit()
            refreshed = session.scalar(
                select(DraftModel)
                .options(selectinload(DraftModel.items))
                .where(DraftModel.id == draft_id)
            )
            _mark_db_available(True)
            return _detail_from_model(refreshed)
    except (DraftNotFoundError, SourceFragmentNotFoundError):
        raise
    except SQLAlchemyError:
        _mark_db_available(False)
        return None


def _db_replace_draft_text(
    draft_id: str,
    text: str,
    role: str | None,
    position: str | None,
    metadata: dict,
) -> DraftDetail | None:
    if _db_available is False:
        return None
    try:
        with SessionLocal() as session:
            draft = session.scalar(
                select(DraftModel)
                .options(selectinload(DraftModel.items))
                .where(DraftModel.id == draft_id)
            )
            if draft is None:
                raise DraftNotFoundError()
            for item in list(draft.items):
                session.delete(item)
            session.flush()
            session.add(
                DraftItemModel(
                    draft_id=draft_id,
                    order_index=0,
                    edited_text=text,
                    role=role,
                    position=position,
                    metadata_json=metadata,
                )
            )
            session.commit()
            refreshed = session.scalar(
                select(DraftModel)
                .options(selectinload(DraftModel.items))
                .where(DraftModel.id == draft_id)
            )
            _mark_db_available(True)
            return _detail_from_model(refreshed)
    except DraftNotFoundError:
        raise
    except SQLAlchemyError:
        _mark_db_available(False)
        return None


def _db_update_draft_item(
    draft_id: str,
    item_id: str,
    payload: DraftItemUpdate,
) -> DraftDetail | None:
    if _db_available is False:
        return None
    try:
        with SessionLocal() as session:
            row = session.scalar(
                select(DraftItemModel).where(
                    DraftItemModel.id == item_id,
                    DraftItemModel.draft_id == draft_id,
                )
            )
            if row is None:
                raise DraftItemNotFoundError()
            updates = _without_none(payload.model_dump())
            metadata = updates.pop("metadata", None)
            for field_name, value in updates.items():
                setattr(row, field_name, value)
            if metadata is not None:
                row.metadata_json = metadata
            session.commit()
            draft = session.scalar(
                select(DraftModel)
                .options(selectinload(DraftModel.items))
                .where(DraftModel.id == draft_id)
            )
            _mark_db_available(True)
            return _detail_from_model(draft)
    except DraftItemNotFoundError:
        raise
    except SQLAlchemyError:
        _mark_db_available(False)
        return None


def _db_delete_draft_item(draft_id: str, item_id: str) -> bool | None:
    if _db_available is False:
        return None
    try:
        with SessionLocal() as session:
            row = session.scalar(
                select(DraftItemModel).where(
                    DraftItemModel.id == item_id,
                    DraftItemModel.draft_id == draft_id,
                )
            )
            if row is None:
                _mark_db_available(True)
                return False
            session.delete(row)
            session.commit()
            _mark_db_available(True)
            return True
    except SQLAlchemyError:
        _mark_db_available(False)
        return None


def _db_reorder_draft_items(
    draft_id: str,
    payload: DraftItemReorderRequest,
) -> DraftDetail | None:
    if _db_available is False:
        return None
    try:
        with SessionLocal() as session:
            rows = session.scalars(
                select(DraftItemModel).where(DraftItemModel.draft_id == draft_id)
            ).all()
            if not rows and session.get(DraftModel, draft_id) is None:
                raise DraftNotFoundError()
            by_id = {str(row.id): row for row in rows}
            for item in payload.items:
                if item.item_id not in by_id:
                    raise DraftItemNotFoundError()
                by_id[item.item_id].order_index = item.order_index
            session.commit()
            draft = session.scalar(
                select(DraftModel)
                .options(selectinload(DraftModel.items))
                .where(DraftModel.id == draft_id)
            )
            _mark_db_available(True)
            return _detail_from_model(draft)
    except (DraftNotFoundError, DraftItemNotFoundError):
        raise
    except SQLAlchemyError:
        _mark_db_available(False)
        return None


def _db_create_draft_version(
    draft_id: str,
    payload: DraftVersionCreate,
) -> DraftVersionDetail | None:
    if _db_available is False:
        return None
    try:
        with SessionLocal() as session:
            draft = session.scalar(
                select(DraftModel)
                .options(selectinload(DraftModel.items))
                .where(DraftModel.id == draft_id)
            )
            if draft is None:
                raise DraftNotFoundError()
            current_text = _assemble_text([_item_from_model(item) for item in draft.items])
            items = [item.model_dump() for item in _snapshot_items([_item_from_model(item) for item in draft.items])]
            version_number = (
                session.scalar(
                    select(func.max(DraftVersionModel.version_number)).where(
                        DraftVersionModel.draft_id == draft_id
                    )
                )
                or 0
            ) + 1
            row = DraftVersionModel(
                draft_id=draft_id,
                version_number=version_number,
                label=payload.label,
                current_text=current_text,
                items_json=items,
                metadata_json=payload.metadata,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            _mark_db_available(True)
            return _version_detail_from_model(row)
    except DraftNotFoundError:
        raise
    except SQLAlchemyError:
        _mark_db_available(False)
        return None


def _db_list_draft_versions(draft_id: str) -> list[DraftVersionSummary] | None:
    if _db_available is False:
        return None
    try:
        with SessionLocal() as session:
            if session.get(DraftModel, draft_id) is None:
                raise DraftNotFoundError()
            rows = session.scalars(
                select(DraftVersionModel)
                .where(DraftVersionModel.draft_id == draft_id)
                .order_by(DraftVersionModel.version_number.desc())
            ).all()
            _mark_db_available(True)
            return [_version_summary_from_model(row) for row in rows]
    except DraftNotFoundError:
        raise
    except SQLAlchemyError:
        _mark_db_available(False)
        return None


def _db_get_draft_version(draft_id: str, version_id: str) -> DraftVersionDetail | None:
    if _db_available is False:
        return None
    try:
        with SessionLocal() as session:
            if session.get(DraftModel, draft_id) is None:
                raise DraftNotFoundError()
            row = session.scalar(
                select(DraftVersionModel).where(
                    DraftVersionModel.id == version_id,
                    DraftVersionModel.draft_id == draft_id,
                )
            )
            _mark_db_available(True)
            return _version_detail_from_model(row) if row is not None else None
    except DraftNotFoundError:
        raise
    except SQLAlchemyError:
        _mark_db_available(False)
        return None


def _get_fragment_or_none(fragment_id: str | None):
    if fragment_id is None:
        return None
    return knowledge.get_fragment(fragment_id)


def _detail_from_model(row: DraftModel | None) -> DraftDetail | None:
    if row is None:
        return None
    items = [_item_from_model(item) for item in sorted(row.items, key=lambda item: item.order_index)]
    return DraftDetail(
        id=str(row.id),
        title=row.title,
        goal=row.goal,
        audience=row.audience,
        platform=row.platform,
        purpose=row.purpose,
        status=row.status,
        current_text=_assemble_text(items),
        item_count=len(items),
        metadata=row.metadata_json or {},
        items=items,
    )


def _summary_from_model(row: DraftModel) -> DraftSummary:
    items = [_item_from_model(item) for item in sorted(row.items, key=lambda item: item.order_index)]
    return DraftSummary(
        id=str(row.id),
        title=row.title,
        goal=row.goal,
        audience=row.audience,
        platform=row.platform,
        purpose=row.purpose,
        status=row.status,
        current_text=_assemble_text(items),
        item_count=len(items),
        metadata=row.metadata_json or {},
    )


def _item_from_model(row: DraftItemModel) -> DraftItem:
    return DraftItem(
        id=str(row.id),
        draft_id=str(row.draft_id),
        source_fragment_id=str(row.source_fragment_id) if row.source_fragment_id else None,
        source_copy_id=str(row.source_copy_id) if row.source_copy_id else None,
        order_index=row.order_index,
        original_fragment_text=row.original_fragment_text,
        edited_text=row.edited_text,
        role=row.role,
        position=row.position,
        metadata=row.metadata_json or {},
    )


def _version_summary_from_model(row: DraftVersionModel) -> DraftVersionSummary:
    return DraftVersionSummary(
        id=str(row.id),
        draft_id=str(row.draft_id),
        version_number=row.version_number,
        label=row.label,
        current_text=row.current_text,
        item_count=len(row.items_json or []),
        metadata=row.metadata_json or {},
    )


def _version_detail_from_model(row: DraftVersionModel) -> DraftVersionDetail:
    items = [DraftItemSnapshot.model_validate(item) for item in row.items_json or []]
    return DraftVersionDetail(
        id=str(row.id),
        draft_id=str(row.draft_id),
        version_number=row.version_number,
        label=row.label,
        current_text=row.current_text,
        item_count=len(items),
        metadata=row.metadata_json or {},
        items=items,
    )


def _refresh_detail(draft: DraftDetail) -> DraftDetail:
    items = sorted(draft.items, key=lambda item: item.order_index)
    return draft.model_copy(
        update={
            "items": items,
            "current_text": _assemble_text(items),
            "item_count": len(items),
        }
    )


def _to_summary(draft: DraftDetail) -> DraftSummary:
    refreshed = _refresh_detail(draft)
    return DraftSummary(**refreshed.model_dump(exclude={"items"}))


def _version_summary(version: DraftVersionDetail) -> DraftVersionSummary:
    return DraftVersionSummary(**version.model_dump(exclude={"items"}))


def _snapshot_items(items: list[DraftItem]) -> list[DraftItemSnapshot]:
    return [
        DraftItemSnapshot(**item.model_dump(exclude={"draft_id"}))
        for item in sorted(items, key=lambda item: item.order_index)
    ]


def _assemble_text(items: list[DraftItem]) -> str:
    return "\n\n".join(
        item.edited_text.strip()
        for item in sorted(items, key=lambda item: item.order_index)
        if item.edited_text.strip()
    )


def _next_order(items: list[DraftItem]) -> int:
    if not items:
        return 0
    return max(item.order_index for item in items) + 1


def _page(items: list, page: int, page_size: int) -> list:
    start = (page - 1) * page_size
    return items[start : start + page_size]


def _without_none(data: dict) -> dict:
    return {key: value for key, value in data.items() if value is not None}


def _mark_db_available(value: bool) -> None:
    global _db_available
    _db_available = value
