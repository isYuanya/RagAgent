"""phase5 compositions

Revision ID: 20260617_0005
Revises: 20260617_0004
Create Date: 2026-06-17 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260617_0005"
down_revision: str | None = "20260617_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "accepted_compositions",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("task_id", sa.String(length=100), nullable=False),
        sa.Column("candidate_id", sa.String(length=100), nullable=False),
        sa.Column("draft_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("brief_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("candidate_title", sa.String(length=300), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=True),
        sa.Column("reference_fragment_ids_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_accepted_compositions_draft_id", "accepted_compositions", ["draft_id"])
    op.create_index("ix_accepted_compositions_task_id", "accepted_compositions", ["task_id"])


def downgrade() -> None:
    op.drop_index("ix_accepted_compositions_task_id", table_name="accepted_compositions")
    op.drop_index("ix_accepted_compositions_draft_id", table_name="accepted_compositions")
    op.drop_table("accepted_compositions")
