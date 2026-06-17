from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AcceptedRecommendation(Base):
    __tablename__ = "accepted_recommendations"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    draft_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    task_id: Mapped[str] = mapped_column(String(100))
    candidate_id: Mapped[str] = mapped_column(String(100))
    inserted_draft_item_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    candidate_text: Mapped[str] = mapped_column(Text)
    function: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tone: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reference_fragment_ids_json: Mapped[list] = mapped_column(JSONB, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
