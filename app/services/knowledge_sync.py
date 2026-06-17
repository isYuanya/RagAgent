from app.schemas.copy import CopyAnalysisResponse, CopyAssetSummary
from app.schemas.knowledge import (
    SourceReference,
    TemplateCreate,
)
from app.services import knowledge


def sync_asset_analysis_to_knowledge(asset: CopyAssetSummary) -> None:
    analysis = asset.reviewed_analysis or asset.auto_analysis
    if analysis is None:
        return

    source = SourceReference(
        source_type="raw_copy",
        source_id=asset.id,
        source_display=_source_display(asset),
    )
    _sync_template(asset, analysis, source)


def _sync_template(
    asset: CopyAssetSummary, analysis: CopyAnalysisResponse, source: SourceReference
) -> None:
    template = analysis.reusable_template.strip()
    if not template or _exists("templates", asset.id, "template", template):
        return
    knowledge.create_template(
        TemplateCreate(
            title=analysis.topic or "Reusable copy template",
            content=template,
            structure=analysis.structure,
            suitable_scenarios=analysis.suitable_scenarios,
            source=source,
            metadata=_metadata(asset, "template", template),
        )
    )


def _exists(library: str, source_copy_id: str, kind: str, content_key: str) -> bool:
    list_func = {
        "templates": knowledge.list_templates,
    }[library]
    response = list_func(page=1, page_size=100)
    return any(
        item.metadata.get("derived_from_asset_id") == source_copy_id
        and item.metadata.get("derived_kind") == kind
        and item.metadata.get("derived_content_key") == content_key
        for item in response.items
    )


def _metadata(asset: CopyAssetSummary, kind: str, content_key: str) -> dict:
    return {
        "derived_from": "copy_analysis",
        "derived_from_asset_id": asset.id,
        "derived_kind": kind,
        "derived_content_key": content_key,
        "source_text": asset.source_text,
        "platform": asset.platform,
        "author_name": asset.author_name,
    }


def _source_display(asset: CopyAssetSummary) -> str:
    text = " ".join(asset.source_text.split())
    if len(text) <= 80:
        return text
    return f"{text[:77]}..."

