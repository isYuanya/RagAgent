from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Draft(Base):
    __tablename__ = "drafts"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    title: Mapped[str] = mapped_column(String(300))
    goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    audience: Mapped[str | None] = mapped_column(String(200), nullable=True)
    platform: Mapped[str | None] = mapped_column(String(100), nullable=True)
    purpose: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list["DraftItem"]] = relationship(
        back_populates="draft",
        cascade="all, delete-orphan",
        order_by="DraftItem.order_index",
    )
    versions: Mapped[list["DraftVersion"]] = relationship(
        back_populates="draft",
        cascade="all, delete-orphan",
        order_by="DraftVersion.version_number",
    )


class DraftItem(Base):
    __tablename__ = "draft_items"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    draft_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("drafts.id", ondelete="CASCADE")
    )
    source_fragment_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    source_copy_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    original_fragment_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    edited_text: Mapped[str] = mapped_column(Text)
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    position: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    draft: Mapped[Draft] = relationship(back_populates="items")


class DraftVersion(Base):
    __tablename__ = "draft_versions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    draft_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("drafts.id", ondelete="CASCADE")
    )
    version_number: Mapped[int] = mapped_column(Integer)
    label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    current_text: Mapped[str] = mapped_column(Text, default="")
    items_json: Mapped[list] = mapped_column(JSONB, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    draft: Mapped[Draft] = relationship(back_populates="versions")


class DraftVideoExport(Base):
    __tablename__ = "draft_video_exports"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    draft_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("drafts.id", ondelete="CASCADE")
    )
    status: Mapped[str] = mapped_column(String(40), default="finished")
    result_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
