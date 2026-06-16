from app.schemas.copy import CopyAnalysisResponse, CopyAssetSummary
from app.schemas.knowledge import (
    BlockCreate,
    CaseCreate,
    SourceReference,
    TagCreate,
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
    _sync_tags(asset, analysis, source)
    _sync_blocks(asset, analysis, source)
    _sync_case(asset, analysis, source)


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


def _sync_tags(
    asset: CopyAssetSummary, analysis: CopyAnalysisResponse, source: SourceReference
) -> None:
    candidates: list[tuple[str | None, str, str | None]] = [
        (asset.industry, "industry", "Source industry"),
        (asset.purpose, "purpose", "Source content purpose"),
        (asset.audience or analysis.target_user, "audience", "Target audience"),
        (analysis.hook, "hook_type", "Opening hook"),
    ]
    candidates.extend((item, "emotion", "Emotion button") for item in analysis.emotion_buttons)
    candidates.extend((item, "custom", "Expression skill") for item in analysis.expression_skills)

    for name, category, description in candidates:
        tag_name = (name or "").strip()
        if not tag_name or _exists("tags", asset.id, f"tag:{category}", tag_name):
            continue
        knowledge.create_tag(
            TagCreate(
                name=tag_name,
                category=category,  # type: ignore[arg-type]
                description=description,
                source=source,
                metadata=_metadata(asset, f"tag:{category}", tag_name),
            )
        )


def _sync_blocks(
    asset: CopyAssetSummary, analysis: CopyAnalysisResponse, source: SourceReference
) -> None:
    for warning in analysis.risk_warnings:
        content = warning.message.strip()
        if not content or _exists("blocks", asset.id, "risk_warning", content):
            continue
        severity = warning.level if warning.level in {"low", "medium", "high"} else "medium"
        knowledge.create_block(
            BlockCreate(
                content=content,
                block_type="violation",
                reason=warning.suggestion,
                severity=severity,  # type: ignore[arg-type]
                source=source,
                metadata=_metadata(asset, "risk_warning", content),
            )
        )


def _sync_case(
    asset: CopyAssetSummary, analysis: CopyAnalysisResponse, source: SourceReference
) -> None:
    if not any(value > 0 for value in asset.metrics.values()):
        return
    content_key = analysis.topic or asset.source_text
    if _exists("cases", asset.id, "case", content_key):
        return
    knowledge.create_case(
        CaseCreate(
            title=analysis.topic or "Imported copy case",
            reason=analysis.core_pain or analysis.hook,
            performance_summary=_performance_summary(asset.metrics),
            source=source,
            metadata=_metadata(asset, "case", content_key),
        )
    )


def _exists(library: str, source_copy_id: str, kind: str, content_key: str) -> bool:
    list_func = {
        "templates": knowledge.list_templates,
        "tags": knowledge.list_tags,
        "blocks": knowledge.list_blocks,
        "cases": knowledge.list_cases,
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


def _performance_summary(metrics: dict[str, int]) -> str:
    if not metrics:
        return "No performance metrics provided."
    return ", ".join(f"{key}: {value}" for key, value in sorted(metrics.items()))
