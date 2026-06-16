from app.schemas.copy import CopyAssetSummary
from app.services.fragment_extraction import extract_fragments_for_asset_id
from app.services.knowledge_sync import sync_asset_analysis_to_knowledge


def sync_imported_asset_to_knowledge(asset: CopyAssetSummary) -> None:
    sync_asset_analysis_to_knowledge(asset)
    if asset.status == "approved":
        extract_fragments_for_asset_id(asset.id)
