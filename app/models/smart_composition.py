from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SmartCompositionRun(Base):
    __tablename__ = "smart_composition_runs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    mode: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(40), index=True)
    brief_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    timeline_json: Mapped[list] = mapped_column(JSONB, default=list)
    collection_ids_json: Mapped[list] = mapped_column(JSONB, default=list)
    material_ids_json: Mapped[list] = mapped_column(JSONB, default=list)
    selected_candidate_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    selected_rewrite_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    draft_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    initial_version_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    final_version_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    result_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
