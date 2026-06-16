"""add phase 2 fragment fields

Revision ID: 20260616_0002
Revises: 20260615_0001
Create Date: 2026-06-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260616_0002"
down_revision: str | None = "20260615_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("knowledge_fragments", sa.Column("platform", sa.String(length=100)))
    op.add_column("knowledge_fragments", sa.Column("purpose", sa.String(length=100)))
    op.add_column("knowledge_fragments", sa.Column("audience", sa.String(length=200)))
    op.add_column(
        "knowledge_fragments",
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending_review"),
    )
    op.add_column(
        "knowledge_fragments",
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("knowledge_fragments", "confidence")
    op.drop_column("knowledge_fragments", "status")
    op.drop_column("knowledge_fragments", "audience")
    op.drop_column("knowledge_fragments", "purpose")
    op.drop_column("knowledge_fragments", "platform")
