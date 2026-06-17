"""smart composition runs

Revision ID: 20260617_0006
Revises: 20260617_0005
Create Date: 2026-06-17 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260617_0006"
down_revision: str | None = "20260617_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "smart_composition_runs",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("mode", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("brief_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("timeline_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("collection_ids_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("material_ids_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("selected_candidate_id", sa.String(length=100), nullable=True),
        sa.Column("selected_rewrite_id", sa.String(length=100), nullable=True),
        sa.Column("draft_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("initial_version_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("final_version_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("result_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_smart_composition_runs_status", "smart_composition_runs", ["status"])
    op.create_index("ix_smart_composition_runs_draft_id", "smart_composition_runs", ["draft_id"])


def downgrade() -> None:
    op.drop_index("ix_smart_composition_runs_draft_id", table_name="smart_composition_runs")
    op.drop_index("ix_smart_composition_runs_status", table_name="smart_composition_runs")
    op.drop_table("smart_composition_runs")
