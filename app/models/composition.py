from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AcceptedComposition(Base):
    __tablename__ = "accepted_compositions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    task_id: Mapped[str] = mapped_column(String(100))
    candidate_id: Mapped[str] = mapped_column(String(100))
    draft_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    brief_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    candidate_title: Mapped[str] = mapped_column(String(300))
    model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reference_fragment_ids_json: Mapped[list] = mapped_column(JSONB, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
