"""phase3 drafts

Revision ID: 20260617_0003
Revises: 20260616_0002
Create Date: 2026-06-17 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260617_0003"
down_revision: str | None = "20260616_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "drafts",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("goal", sa.Text(), nullable=True),
        sa.Column("audience", sa.String(length=200), nullable=True),
        sa.Column("platform", sa.String(length=100), nullable=True),
        sa.Column("purpose", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "draft_items",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("draft_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("source_fragment_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("source_copy_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("original_fragment_text", sa.Text(), nullable=True),
        sa.Column("edited_text", sa.Text(), nullable=False),
        sa.Column("role", sa.String(length=100), nullable=True),
        sa.Column("position", sa.String(length=100), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["draft_id"], ["drafts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "draft_versions",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("draft_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=True),
        sa.Column("current_text", sa.Text(), nullable=False),
        sa.Column("items_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["draft_id"], ["drafts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_drafts_status", "drafts", ["status"])
    op.create_index("ix_draft_items_draft_id", "draft_items", ["draft_id"])
    op.create_index("ix_draft_versions_draft_id", "draft_versions", ["draft_id"])


def downgrade() -> None:
    op.drop_index("ix_draft_versions_draft_id", table_name="draft_versions")
    op.drop_index("ix_draft_items_draft_id", table_name="draft_items")
    op.drop_index("ix_drafts_status", table_name="drafts")
    op.drop_table("draft_versions")
    op.drop_table("draft_items")
    op.drop_table("drafts")
