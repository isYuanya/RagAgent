"""phase4 recommendations

Revision ID: 20260617_0004
Revises: 20260617_0003
Create Date: 2026-06-17 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260617_0004"
down_revision: str | None = "20260617_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "accepted_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("draft_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("task_id", sa.String(length=100), nullable=False),
        sa.Column("candidate_id", sa.String(length=100), nullable=False),
        sa.Column("inserted_draft_item_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("candidate_text", sa.Text(), nullable=False),
        sa.Column("function", sa.String(length=100), nullable=True),
        sa.Column("tone", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("model", sa.String(length=200), nullable=True),
        sa.Column("reference_fragment_ids_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_accepted_recommendations_draft_id",
        "accepted_recommendations",
        ["draft_id"],
    )
    op.create_index(
        "ix_accepted_recommendations_task_id",
        "accepted_recommendations",
        ["task_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_accepted_recommendations_task_id", table_name="accepted_recommendations")
    op.drop_index("ix_accepted_recommendations_draft_id", table_name="accepted_recommendations")
    op.drop_table("accepted_recommendations")
