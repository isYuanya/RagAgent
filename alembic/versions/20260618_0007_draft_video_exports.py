"""draft video exports

Revision ID: 20260618_0007
Revises: 20260617_0006
Create Date: 2026-06-18 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260618_0007"
down_revision: str | None = "20260617_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "draft_video_exports",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("draft_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("result_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["draft_id"], ["drafts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_draft_video_exports_draft_id", "draft_video_exports", ["draft_id"])
    op.create_index("ix_draft_video_exports_status", "draft_video_exports", ["status"])


def downgrade() -> None:
    op.drop_index("ix_draft_video_exports_status", table_name="draft_video_exports")
    op.drop_index("ix_draft_video_exports_draft_id", table_name="draft_video_exports")
    op.drop_table("draft_video_exports")
