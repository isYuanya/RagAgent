from dataclasses import dataclass, field
from typing import Any, TypeVar
from uuid import uuid4

from sqlalchemy import delete, insert, select
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.models.knowledge import (
    KnowledgeAnalysis,
    KnowledgeBlock,
    KnowledgeCase,
    KnowledgeCollection as KnowledgeCollectionModel,
    KnowledgeFragment,
    KnowledgeTag,
    KnowledgeTemplate,
    copy_source_collections,
)
from app.schemas.copy import CopyAnalysisRequest, CopyAnalysisResponse
from app.schemas.knowledge import (
    AnalysisCreate,
    AnalysisListResponse,
    AnalysisSummary,
    AnalysisUpdate,
    BlockCreate,
    BlockItem,
    BlockUpdate,
    CaseCreate,
    CaseItem,
    CaseUpdate,
    FragmentCreate,
    FragmentItem,
    FragmentUpdate,
    KnowledgeCollection,
    KnowledgeCollectionCreate,
    KnowledgeCollectionListResponse,
    KnowledgeCollectionUpdate,
    KnowledgeItemListResponse,
    RawCopyCreate,
    RawCopyListResponse,
    RawCopySummary,
    RawCopyUpdate,
    TagCreate,
    TagItem,
    TagUpdate,
    TemplateCreate,
    TemplateItem,
    TemplateUpdate,
)
from app.services.copy_assets import create_copy_asset, get_copy_asset, list_copy_assets


T = TypeVar("T")


@dataclass
class _Store:
    collections: dict[str, KnowledgeCollection] = field(default_factory=dict)
    raw_collection_ids: dict[str, list[str]] = field(default_factory=dict)
    raw_deleted: set[str] = field(default_factory=set)
    analyses: dict[str, AnalysisSummary] = field(default_factory=dict)
    deleted_analyses: set[str] = field(default_factory=set)
    templates: dict[str, TemplateItem] = field(default_factory=dict)
    deleted_templates: set[str] = field(default_factory=set)
    tags: dict[str, TagItem] = field(default_factory=dict)
    deleted_tags: set[str] = field(default_factory=set)
    cases: dict[str, CaseItem] = field(default_factory=dict)
    deleted_cases: set[str] = field(default_factory=set)
    blocks: dict[str, BlockItem] = field(default_factory=dict)
    deleted_blocks: set[str] = field(default_factory=set)
    fragments: dict[str, FragmentItem] = field(default_factory=dict)
    deleted_fragments: set[str] = field(default_factory=set)


_store = _Store()
_db_available: bool | None = None


def reset_knowledge_store() -> None:
    global _store
    _store = _Store()


def list_collections(page: int = 1, page_size: int = 20) -> KnowledgeCollectionListResponse:
    db_response = _db_list_collections(page, page_size)
    if db_response is not None:
        return db_response
    items = list(_store.collections.values())
    return KnowledgeCollectionListResponse(
        items=_page(items, page, page_size),
        page=page,
        page_size=page_size,
        total=len(items),
    )


def create_collection(payload: KnowledgeCollectionCreate) -> KnowledgeCollection:
    db_item = _db_create_collection(payload)
    if db_item is not None:
        return db_item
    item = KnowledgeCollection(id=str(uuid4()), **payload.model_dump())
    _store.collections[item.id] = item
    return item


def get_collection(collection_id: str) -> KnowledgeCollection | None:
    db_item = _db_get_collection(collection_id)
    if db_item is not None:
        return db_item
    return _store.collections.get(collection_id)


def update_collection(
    collection_id: str, payload: KnowledgeCollectionUpdate
) -> KnowledgeCollection | None:
    db_item = _db_update_collection(collection_id, payload)
    if db_item is not None:
        return db_item
    item = get_collection(collection_id)
    if item is None:
        return None
    updated = item.model_copy(update=_without_none(payload.model_dump()))
    _store.collections[collection_id] = updated
    return updated


def delete_collection(collection_id: str) -> bool:
    db_result = _db_delete_collection(collection_id)
    if db_result is not None:
        return db_result
    if collection_id not in _store.collections:
        return False
    del _store.collections[collection_id]
    for ids in _store.raw_collection_ids.values():
        if collection_id in ids:
            ids.remove(collection_id)
    return True


def list_raw_copies(
    page: int = 1,
    page_size: int = 20,
    collection_id: str | None = None,
) -> RawCopyListResponse:
    assets = list_copy_assets(page=1, page_size=100, status=None).items
    items = [
        _to_raw_summary(asset.id)
        for asset in assets
        if asset.id not in _store.raw_deleted
        and (collection_id is None or collection_id in _store.raw_collection_ids.get(asset.id, []))
    ]
    return RawCopyListResponse(
        items=_page([item for item in items if item is not None], page, page_size),
        page=page,
        page_size=page_size,
        total=len(items),
    )


def create_raw_copy(payload: RawCopyCreate) -> RawCopySummary:
    asset = create_copy_asset(
        CopyAnalysisRequest(
            source_text=payload.source_text,
            source_url=payload.source_url,
            author_name=payload.author_name,
            author_url=payload.author_url,
            author_follower_count=payload.author_follower_count,
            platform=payload.platform,
            industry=payload.industry,
            audience=payload.audience,
            purpose=payload.purpose,
            style=payload.style,
            metrics=payload.metrics,
        ),
        None,
    )
    _store.raw_collection_ids[asset.id] = _valid_collection_ids(payload.collection_ids)
    _db_replace_raw_collections(asset.id, payload.collection_ids)
    return _to_raw_summary(asset.id) or RawCopySummary(**asset.model_dump())


def get_raw_copy(raw_copy_id: str) -> RawCopySummary | None:
    if raw_copy_id in _store.raw_deleted:
        return None
    return _to_raw_summary(raw_copy_id)


def update_raw_copy(raw_copy_id: str, payload: RawCopyUpdate) -> RawCopySummary | None:
    asset = get_copy_asset(raw_copy_id)
    if asset is None or raw_copy_id in _store.raw_deleted:
        return None
    if payload.collection_ids is not None:
        _store.raw_collection_ids[raw_copy_id] = _valid_collection_ids(payload.collection_ids)
        _db_replace_raw_collections(raw_copy_id, payload.collection_ids)
    # Existing copy asset persistence is append-only for source text. For MVP, support collection
    # updates and keep text metadata updates for the dedicated DB-backed implementation slice.
    return _to_raw_summary(raw_copy_id)


def delete_raw_copy(raw_copy_id: str) -> bool:
    if get_copy_asset(raw_copy_id) is None:
        return False
    _store.raw_deleted.add(raw_copy_id)
    return True


def list_analyses(page: int = 1, page_size: int = 20) -> AnalysisListResponse:
    db_manual = _db_list_knowledge_analyses()
    from_assets = []
    for asset in list_copy_assets(page=1, page_size=100).items:
        if asset.auto_analysis is None:
            continue
        from_assets.append(
            AnalysisSummary(
                id=asset.id,
                raw_copy_id=asset.id,
                auto_analysis=asset.auto_analysis,
                reviewed_analysis=asset.reviewed_analysis,
                status=asset.status,
            )
        )
    manual_items = db_manual if db_manual is not None else list(_store.analyses.values())
    items = [item for item in [*from_assets, *manual_items] if item.id not in _store.deleted_analyses]
    return AnalysisListResponse(
        items=_page(items, page, page_size),
        page=page,
        page_size=page_size,
        total=len(items),
    )


def create_analysis(payload: AnalysisCreate) -> AnalysisSummary:
    db_item = _db_create_knowledge_analysis(payload)
    if db_item is not None:
        return db_item
    item = AnalysisSummary(id=str(uuid4()), **payload.model_dump())
    _store.analyses[item.id] = item
    return item


def get_analysis(analysis_id: str) -> AnalysisSummary | None:
    if analysis_id in _store.deleted_analyses:
        return None
    db_item = _db_get_knowledge_analysis(analysis_id)
    if db_item is not None:
        return db_item
    if analysis_id in _store.analyses:
        return _store.analyses[analysis_id]
    asset = get_copy_asset(analysis_id)
    if asset is None or asset.auto_analysis is None:
        return None
    return AnalysisSummary(
        id=asset.id,
        raw_copy_id=asset.id,
        auto_analysis=asset.auto_analysis,
        reviewed_analysis=asset.reviewed_analysis,
        status=asset.status,
    )


def update_analysis(analysis_id: str, payload: AnalysisUpdate) -> AnalysisSummary | None:
    db_item = _db_update_knowledge_analysis(analysis_id, payload)
    if db_item is not None:
        return db_item
    item = get_analysis(analysis_id)
    if item is None or analysis_id not in _store.analyses:
        return item
    updated = item.model_copy(update=_without_none(payload.model_dump()))
    _store.analyses[analysis_id] = updated
    return updated


def delete_analysis(analysis_id: str) -> bool:
    db_result = _db_delete_item(KnowledgeAnalysis, analysis_id)
    if db_result is not None:
        return db_result
    if get_analysis(analysis_id) is None:
        return False
    _store.deleted_analyses.add(analysis_id)
    return True


def _crud_list(
    items: dict[str, T], deleted: set[str], page: int, page_size: int
) -> KnowledgeItemListResponse:
    active = [item for item_id, item in items.items() if item_id not in deleted]
    return KnowledgeItemListResponse(
        items=_page(active, page, page_size),
        page=page,
        page_size=page_size,
        total=len(active),
    )


def _crud_create(payload, cls, items: dict[str, T]) -> T:
    item = cls(id=str(uuid4()), **payload.model_dump())
    items[item.id] = item
    return item


def _crud_get(item_id: str, items: dict[str, T], deleted: set[str]) -> T | None:
    if item_id in deleted:
        return None
    return items.get(item_id)


def _crud_update(item_id: str, payload, items: dict[str, T], deleted: set[str]) -> T | None:
    item = _crud_get(item_id, items, deleted)
    if item is None:
        return None
    updated = item.model_copy(update=_without_none(payload.model_dump()))
    items[item_id] = updated
    return updated


def _crud_delete(item_id: str, items: dict[str, T], deleted: set[str]) -> bool:
    if item_id not in items or item_id in deleted:
        return False
    deleted.add(item_id)
    return True


def list_templates(page: int = 1, page_size: int = 20) -> KnowledgeItemListResponse:
    db_response = _db_list_items(KnowledgeTemplate, _template_from_model, page, page_size)
    return db_response or _crud_list(_store.templates, _store.deleted_templates, page, page_size)


def create_template(payload: TemplateCreate) -> TemplateItem:
    db_item = _db_create_template(payload)
    if db_item is not None:
        return db_item
    return _crud_create(payload, TemplateItem, _store.templates)


def get_template(item_id: str) -> TemplateItem | None:
    db_item = _db_get_item(KnowledgeTemplate, _template_from_model, item_id)
    return db_item or _crud_get(item_id, _store.templates, _store.deleted_templates)


def update_template(item_id: str, payload: TemplateUpdate) -> TemplateItem | None:
    db_item = _db_update_template(item_id, payload)
    if db_item is not None:
        return db_item
    return _crud_update(item_id, payload, _store.templates, _store.deleted_templates)


def delete_template(item_id: str) -> bool:
    db_result = _db_delete_item(KnowledgeTemplate, item_id)
    if db_result is not None:
        return db_result
    return _crud_delete(item_id, _store.templates, _store.deleted_templates)


def list_tags(page: int = 1, page_size: int = 20) -> KnowledgeItemListResponse:
    db_response = _db_list_items(KnowledgeTag, _tag_from_model, page, page_size)
    return db_response or _crud_list(_store.tags, _store.deleted_tags, page, page_size)


def create_tag(payload: TagCreate) -> TagItem:
    db_item = _db_create_tag(payload)
    if db_item is not None:
        return db_item
    return _crud_create(payload, TagItem, _store.tags)


def get_tag(item_id: str) -> TagItem | None:
    db_item = _db_get_item(KnowledgeTag, _tag_from_model, item_id)
    return db_item or _crud_get(item_id, _store.tags, _store.deleted_tags)


def update_tag(item_id: str, payload: TagUpdate) -> TagItem | None:
    db_item = _db_update_tag(item_id, payload)
    if db_item is not None:
        return db_item
    return _crud_update(item_id, payload, _store.tags, _store.deleted_tags)


def delete_tag(item_id: str) -> bool:
    db_result = _db_delete_item(KnowledgeTag, item_id)
    if db_result is not None:
        return db_result
    return _crud_delete(item_id, _store.tags, _store.deleted_tags)


def list_cases(page: int = 1, page_size: int = 20) -> KnowledgeItemListResponse:
    db_response = _db_list_items(KnowledgeCase, _case_from_model, page, page_size)
    return db_response or _crud_list(_store.cases, _store.deleted_cases, page, page_size)


def create_case(payload: CaseCreate) -> CaseItem:
    db_item = _db_create_case(payload)
    if db_item is not None:
        return db_item
    return _crud_create(payload, CaseItem, _store.cases)


def get_case(item_id: str) -> CaseItem | None:
    db_item = _db_get_item(KnowledgeCase, _case_from_model, item_id)
    return db_item or _crud_get(item_id, _store.cases, _store.deleted_cases)


def update_case(item_id: str, payload: CaseUpdate) -> CaseItem | None:
    db_item = _db_update_case(item_id, payload)
    if db_item is not None:
        return db_item
    return _crud_update(item_id, payload, _store.cases, _store.deleted_cases)


def delete_case(item_id: str) -> bool:
    db_result = _db_delete_item(KnowledgeCase, item_id)
    if db_result is not None:
        return db_result
    return _crud_delete(item_id, _store.cases, _store.deleted_cases)


def list_blocks(page: int = 1, page_size: int = 20) -> KnowledgeItemListResponse:
    db_response = _db_list_items(KnowledgeBlock, _block_from_model, page, page_size)
    return db_response or _crud_list(_store.blocks, _store.deleted_blocks, page, page_size)


def create_block(payload: BlockCreate) -> BlockItem:
    db_item = _db_create_block(payload)
    if db_item is not None:
        return db_item
    return _crud_create(payload, BlockItem, _store.blocks)


def get_block(item_id: str) -> BlockItem | None:
    db_item = _db_get_item(KnowledgeBlock, _block_from_model, item_id)
    return db_item or _crud_get(item_id, _store.blocks, _store.deleted_blocks)


def update_block(item_id: str, payload: BlockUpdate) -> BlockItem | None:
    db_item = _db_update_block(item_id, payload)
    if db_item is not None:
        return db_item
    return _crud_update(item_id, payload, _store.blocks, _store.deleted_blocks)


def delete_block(item_id: str) -> bool:
    db_result = _db_delete_item(KnowledgeBlock, item_id)
    if db_result is not None:
        return db_result
    return _crud_delete(item_id, _store.blocks, _store.deleted_blocks)


def list_fragments(
    page: int = 1,
    page_size: int = 20,
    source_copy_id: str | None = None,
    fragment_role: str | None = None,
    position: str | None = None,
    industry: str | None = None,
) -> KnowledgeItemListResponse:
    filters = {
        "source_copy_id": source_copy_id,
        "fragment_role": fragment_role,
        "position": position,
        "industry": industry,
    }
    db_response = _db_list_fragments(page, page_size, filters)
    if db_response is not None:
        return db_response
    active = [
        item
        for item_id, item in _store.fragments.items()
        if item_id not in _store.deleted_fragments and _fragment_matches(item, filters)
    ]
    return KnowledgeItemListResponse(
        items=_page(active, page, page_size),
        page=page,
        page_size=page_size,
        total=len(active),
    )


def create_fragment(payload: FragmentCreate) -> FragmentItem:
    db_item = _db_create_fragment(payload)
    if db_item is not None:
        return db_item
    return _crud_create(payload, FragmentItem, _store.fragments)


def get_fragment(item_id: str) -> FragmentItem | None:
    db_item = _db_get_item(KnowledgeFragment, _fragment_from_model, item_id)
    return db_item or _crud_get(item_id, _store.fragments, _store.deleted_fragments)


def update_fragment(item_id: str, payload: FragmentUpdate) -> FragmentItem | None:
    db_item = _db_update_fragment(item_id, payload)
    if db_item is not None:
        return db_item
    return _crud_update(item_id, payload, _store.fragments, _store.deleted_fragments)


def delete_fragment(item_id: str) -> bool:
    db_result = _db_delete_item(KnowledgeFragment, item_id)
    if db_result is not None:
        return db_result
    return _crud_delete(item_id, _store.fragments, _store.deleted_fragments)


def _to_raw_summary(raw_copy_id: str) -> RawCopySummary | None:
    asset = get_copy_asset(raw_copy_id)
    if asset is None:
        return None
    collection_ids = _db_get_raw_collection_ids(raw_copy_id)
    if collection_ids is None:
        collection_ids = _store.raw_collection_ids.get(raw_copy_id, [])
    collections = [
        collection
        for collection_id in collection_ids
        if (collection := get_collection(collection_id)) is not None
    ]
    return RawCopySummary(
        **asset.model_dump(),
        collection_ids=collection_ids,
        collections=collections,
    )


def _db_list_collections(page: int, page_size: int) -> KnowledgeCollectionListResponse | None:
    if _db_available is False:
        return None
    db = SessionLocal()
    try:
        rows = db.scalars(
            select(KnowledgeCollectionModel)
            .where(KnowledgeCollectionModel.is_deleted.is_(False))
            .order_by(KnowledgeCollectionModel.created_at.desc())
        ).all()
        items = [_collection_from_model(row) for row in rows]
        return KnowledgeCollectionListResponse(
            items=_page(items, page, page_size),
            page=page,
            page_size=page_size,
            total=len(items),
        )
    except SQLAlchemyError:
        _mark_db_available(False)
        return None
    finally:
        db.close()


def _db_create_collection(payload: KnowledgeCollectionCreate) -> KnowledgeCollection | None:
    if _db_available is False:
        return None
    db = SessionLocal()
    try:
        row = KnowledgeCollectionModel(
            name=payload.name,
            description=payload.description,
            metadata_json=payload.metadata,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        _mark_db_available(True)
        return _collection_from_model(row)
    except SQLAlchemyError:
        db.rollback()
        _mark_db_available(False)
        return None
    finally:
        db.close()


def _db_get_collection(collection_id: str) -> KnowledgeCollection | None:
    if _db_available is False:
        return None
    db = SessionLocal()
    try:
        row = db.get(KnowledgeCollectionModel, collection_id)
        if row is None or row.is_deleted:
            return None
        _mark_db_available(True)
        return _collection_from_model(row)
    except SQLAlchemyError:
        _mark_db_available(False)
        return None
    finally:
        db.close()


def _db_update_collection(
    collection_id: str, payload: KnowledgeCollectionUpdate
) -> KnowledgeCollection | None:
    if _db_available is False:
        return None
    db = SessionLocal()
    try:
        row = db.get(KnowledgeCollectionModel, collection_id)
        if row is None or row.is_deleted:
            return None
        data = _without_none(payload.model_dump())
        if "metadata" in data:
            row.metadata_json = data.pop("metadata")
        for key, value in data.items():
            setattr(row, key, value)
        db.commit()
        db.refresh(row)
        _mark_db_available(True)
        return _collection_from_model(row)
    except SQLAlchemyError:
        db.rollback()
        _mark_db_available(False)
        return None
    finally:
        db.close()


def _db_delete_collection(collection_id: str) -> bool | None:
    if _db_available is False:
        return None
    db = SessionLocal()
    try:
        row = db.get(KnowledgeCollectionModel, collection_id)
        if row is None or row.is_deleted:
            return False
        row.is_deleted = True
        db.execute(
            delete(copy_source_collections).where(
                copy_source_collections.c.collection_id == collection_id
            )
        )
        db.commit()
        _mark_db_available(True)
        return True
    except SQLAlchemyError:
        db.rollback()
        _mark_db_available(False)
        return None
    finally:
        db.close()


def _db_get_raw_collection_ids(raw_copy_id: str) -> list[str] | None:
    if _db_available is False:
        return None
    db = SessionLocal()
    try:
        rows = db.execute(
            select(copy_source_collections.c.collection_id).where(
                copy_source_collections.c.copy_source_id == raw_copy_id
            )
        ).all()
        _mark_db_available(True)
        return [row[0] for row in rows]
    except SQLAlchemyError:
        _mark_db_available(False)
        return None
    finally:
        db.close()


def _db_replace_raw_collections(raw_copy_id: str, collection_ids: list[str]) -> None:
    if _db_available is False:
        return
    valid_ids = [collection_id for collection_id in collection_ids if _db_get_collection(collection_id)]
    db = SessionLocal()
    try:
        db.execute(
            delete(copy_source_collections).where(
                copy_source_collections.c.copy_source_id == raw_copy_id
            )
        )
        if valid_ids:
            db.execute(
                insert(copy_source_collections),
                [
                    {"copy_source_id": raw_copy_id, "collection_id": collection_id}
                    for collection_id in valid_ids
                ],
            )
        db.commit()
        _mark_db_available(True)
    except SQLAlchemyError:
        db.rollback()
        _mark_db_available(False)
    finally:
        db.close()


def _collection_from_model(row: KnowledgeCollectionModel) -> KnowledgeCollection:
    return KnowledgeCollection(
        id=str(row.id),
        name=row.name,
        description=row.description,
        metadata=row.metadata_json or {},
    )


def _db_list_items(model_cls, converter, page: int, page_size: int) -> KnowledgeItemListResponse | None:
    if _db_available is False:
        return None
    db = SessionLocal()
    try:
        rows = db.scalars(
            select(model_cls).where(model_cls.is_deleted.is_(False)).order_by(model_cls.created_at.desc())
        ).all()
        items = [converter(row) for row in rows]
        _mark_db_available(True)
        return KnowledgeItemListResponse(
            items=_page(items, page, page_size),
            page=page,
            page_size=page_size,
            total=len(items),
        )
    except SQLAlchemyError:
        _mark_db_available(False)
        return None
    finally:
        db.close()


def _db_get_item(model_cls, converter, item_id: str):
    if _db_available is False:
        return None
    db = SessionLocal()
    try:
        row = db.get(model_cls, item_id)
        if row is None or row.is_deleted:
            return None
        _mark_db_available(True)
        return converter(row)
    except SQLAlchemyError:
        _mark_db_available(False)
        return None
    finally:
        db.close()


def _db_delete_item(model_cls, item_id: str) -> bool | None:
    if _db_available is False:
        return None
    db = SessionLocal()
    try:
        row = db.get(model_cls, item_id)
        if row is None or row.is_deleted:
            return False
        row.is_deleted = True
        db.commit()
        _mark_db_available(True)
        return True
    except SQLAlchemyError:
        db.rollback()
        _mark_db_available(False)
        return None
    finally:
        db.close()


def _db_list_knowledge_analyses() -> list[AnalysisSummary] | None:
    if _db_available is False:
        return None
    db = SessionLocal()
    try:
        rows = db.scalars(
            select(KnowledgeAnalysis)
            .where(KnowledgeAnalysis.is_deleted.is_(False))
            .order_by(KnowledgeAnalysis.created_at.desc())
        ).all()
        _mark_db_available(True)
        return [_analysis_from_model(row) for row in rows]
    except SQLAlchemyError:
        _mark_db_available(False)
        return None
    finally:
        db.close()


def _db_create_knowledge_analysis(payload: AnalysisCreate) -> AnalysisSummary | None:
    row = KnowledgeAnalysis(
        raw_copy_id=payload.raw_copy_id,
        auto_analysis_json=payload.auto_analysis.model_dump(mode="json")
        if payload.auto_analysis
        else None,
        reviewed_analysis_json=payload.reviewed_analysis.model_dump(mode="json")
        if payload.reviewed_analysis
        else None,
        status=payload.status,
    )
    return _db_add_item(row, _analysis_from_model)


def _db_get_knowledge_analysis(analysis_id: str) -> AnalysisSummary | None:
    return _db_get_item(KnowledgeAnalysis, _analysis_from_model, analysis_id)


def _db_update_knowledge_analysis(
    analysis_id: str, payload: AnalysisUpdate
) -> AnalysisSummary | None:
    if _db_available is False:
        return None
    db = SessionLocal()
    try:
        row = db.get(KnowledgeAnalysis, analysis_id)
        if row is None or row.is_deleted:
            return None
        data = _without_none(payload.model_dump())
        if "auto_analysis" in data:
            row.auto_analysis_json = (
                payload.auto_analysis.model_dump(mode="json") if payload.auto_analysis else None
            )
        if "reviewed_analysis" in data:
            row.reviewed_analysis_json = (
                payload.reviewed_analysis.model_dump(mode="json")
                if payload.reviewed_analysis
                else None
            )
        if "status" in data:
            row.status = payload.status
        db.commit()
        db.refresh(row)
        _mark_db_available(True)
        return _analysis_from_model(row)
    except SQLAlchemyError:
        db.rollback()
        _mark_db_available(False)
        return None
    finally:
        db.close()


def _db_create_template(payload: TemplateCreate) -> TemplateItem | None:
    row = KnowledgeTemplate(
        title=payload.title,
        content=payload.content,
        structure_json=payload.structure,
        suitable_scenarios_json=payload.suitable_scenarios,
        metadata_json=payload.metadata,
    )
    _apply_source(row, payload.source)
    return _db_add_item(row, _template_from_model)


def _db_update_template(item_id: str, payload: TemplateUpdate) -> TemplateItem | None:
    return _db_update_item(
        KnowledgeTemplate,
        _template_from_model,
        item_id,
        payload,
        {
            "structure": "structure_json",
            "suitable_scenarios": "suitable_scenarios_json",
            "metadata": "metadata_json",
        },
    )


def _db_create_tag(payload: TagCreate) -> TagItem | None:
    row = KnowledgeTag(
        name=payload.name,
        category=payload.category,
        description=payload.description,
        metadata_json=payload.metadata,
    )
    _apply_source(row, payload.source)
    return _db_add_item(row, _tag_from_model)


def _db_update_tag(item_id: str, payload: TagUpdate) -> TagItem | None:
    return _db_update_item(
        KnowledgeTag, _tag_from_model, item_id, payload, {"metadata": "metadata_json"}
    )


def _db_create_case(payload: CaseCreate) -> CaseItem | None:
    row = KnowledgeCase(
        title=payload.title,
        reason=payload.reason,
        performance_summary=payload.performance_summary,
        metadata_json=payload.metadata,
    )
    _apply_source(row, payload.source)
    return _db_add_item(row, _case_from_model)


def _db_update_case(item_id: str, payload: CaseUpdate) -> CaseItem | None:
    return _db_update_item(
        KnowledgeCase, _case_from_model, item_id, payload, {"metadata": "metadata_json"}
    )


def _db_create_block(payload: BlockCreate) -> BlockItem | None:
    row = KnowledgeBlock(
        content=payload.content,
        block_type=payload.block_type,
        reason=payload.reason,
        severity=payload.severity,
        metadata_json=payload.metadata,
    )
    _apply_source(row, payload.source)
    return _db_add_item(row, _block_from_model)


def _db_update_block(item_id: str, payload: BlockUpdate) -> BlockItem | None:
    return _db_update_item(
        KnowledgeBlock, _block_from_model, item_id, payload, {"metadata": "metadata_json"}
    )


def _db_list_fragments(
    page: int, page_size: int, filters: dict[str, str | None]
) -> KnowledgeItemListResponse | None:
    if _db_available is False:
        return None
    db = SessionLocal()
    try:
        statement = select(KnowledgeFragment).where(KnowledgeFragment.is_deleted.is_(False))
        for key, value in filters.items():
            if value is not None:
                statement = statement.where(getattr(KnowledgeFragment, key) == value)
        rows = db.scalars(
            statement.order_by(KnowledgeFragment.source_copy_id, KnowledgeFragment.sequence_order)
        ).all()
        items = [_fragment_from_model(row) for row in rows]
        _mark_db_available(True)
        return KnowledgeItemListResponse(
            items=_page(items, page, page_size),
            page=page,
            page_size=page_size,
            total=len(items),
        )
    except SQLAlchemyError:
        _mark_db_available(False)
        return None
    finally:
        db.close()


def _db_create_fragment(payload: FragmentCreate) -> FragmentItem | None:
    row = KnowledgeFragment(
        source_copy_id=payload.source_copy_id,
        analysis_id=payload.analysis_id,
        sequence_order=payload.sequence_order,
        previous_fragment=payload.previous_fragment,
        next_fragment=payload.next_fragment,
        before_context=payload.before_context,
        after_context=payload.after_context,
        fragment_text=payload.fragment_text,
        fragment_role=payload.fragment_role,
        position=payload.position,
        industry=payload.industry,
        source_quality=payload.source_quality,
        risk_level=payload.risk_level,
        metadata_json=payload.metadata,
    )
    return _db_add_item(row, _fragment_from_model)


def _db_update_fragment(item_id: str, payload: FragmentUpdate) -> FragmentItem | None:
    return _db_update_item(
        KnowledgeFragment,
        _fragment_from_model,
        item_id,
        payload,
        {"metadata": "metadata_json"},
    )


def _db_add_item(row, converter):
    if _db_available is False:
        return None
    db = SessionLocal()
    try:
        db.add(row)
        db.commit()
        db.refresh(row)
        _mark_db_available(True)
        return converter(row)
    except SQLAlchemyError:
        db.rollback()
        _mark_db_available(False)
        return None
    finally:
        db.close()


def _db_update_item(model_cls, converter, item_id: str, payload, field_map: dict[str, str]):
    if _db_available is False:
        return None
    db = SessionLocal()
    try:
        row = db.get(model_cls, item_id)
        if row is None or row.is_deleted:
            return None
        data = _without_none(payload.model_dump())
        source = data.pop("source", None)
        if source is not None:
            _apply_source(row, payload.source)
        for key, value in data.items():
            setattr(row, field_map.get(key, key), value)
        db.commit()
        db.refresh(row)
        _mark_db_available(True)
        return converter(row)
    except SQLAlchemyError:
        db.rollback()
        _mark_db_available(False)
        return None
    finally:
        db.close()


def _apply_source(row, source) -> None:
    if source is None:
        row.source_type = None
        row.source_id = None
        return
    row.source_type = source.source_type
    row.source_id = source.source_id


def _source_from_model(row):
    if not row.source_type or not row.source_id:
        return None
    return {"source_type": row.source_type, "source_id": str(row.source_id)}


def _template_from_model(row: KnowledgeTemplate) -> TemplateItem:
    return TemplateItem(
        id=str(row.id),
        title=row.title,
        content=row.content,
        structure=row.structure_json or [],
        suitable_scenarios=row.suitable_scenarios_json or [],
        source=_source_from_model(row),
        metadata=row.metadata_json or {},
    )


def _tag_from_model(row: KnowledgeTag) -> TagItem:
    return TagItem(
        id=str(row.id),
        name=row.name,
        category=row.category,
        description=row.description,
        source=_source_from_model(row),
        metadata=row.metadata_json or {},
    )


def _case_from_model(row: KnowledgeCase) -> CaseItem:
    return CaseItem(
        id=str(row.id),
        title=row.title,
        reason=row.reason,
        performance_summary=row.performance_summary,
        source=_source_from_model(row),
        metadata=row.metadata_json or {},
    )


def _block_from_model(row: KnowledgeBlock) -> BlockItem:
    return BlockItem(
        id=str(row.id),
        content=row.content,
        block_type=row.block_type,
        reason=row.reason,
        severity=row.severity,
        source=_source_from_model(row),
        metadata=row.metadata_json or {},
    )


def _fragment_from_model(row: KnowledgeFragment) -> FragmentItem:
    return FragmentItem(
        id=str(row.id),
        source_copy_id=str(row.source_copy_id),
        analysis_id=str(row.analysis_id) if row.analysis_id else None,
        sequence_order=row.sequence_order,
        previous_fragment=row.previous_fragment,
        next_fragment=row.next_fragment,
        before_context=row.before_context,
        after_context=row.after_context,
        fragment_text=row.fragment_text,
        fragment_role=row.fragment_role,
        position=row.position,
        industry=row.industry,
        source_quality=row.source_quality,
        risk_level=row.risk_level,
        metadata=row.metadata_json or {},
    )


def _analysis_from_model(row: KnowledgeAnalysis) -> AnalysisSummary:
    return AnalysisSummary(
        id=str(row.id),
        raw_copy_id=str(row.raw_copy_id),
        auto_analysis=CopyAnalysisResponse.model_validate(row.auto_analysis_json)
        if row.auto_analysis_json
        else None,
        reviewed_analysis=CopyAnalysisResponse.model_validate(row.reviewed_analysis_json)
        if row.reviewed_analysis_json
        else None,
        status=row.status,
    )


def _mark_db_available(value: bool) -> None:
    global _db_available
    _db_available = value


def _valid_collection_ids(collection_ids: list[str]) -> list[str]:
    return [collection_id for collection_id in collection_ids if collection_id in _store.collections]


def _fragment_matches(item: FragmentItem, filters: dict[str, str | None]) -> bool:
    return all(value is None or getattr(item, key) == value for key, value in filters.items())


def _without_none(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value is not None}


def _page(items: list[T], page: int, page_size: int) -> list[T]:
    start = (page - 1) * page_size
    return items[start : start + page_size]
