"""keyword rankings

Revision ID: 20260720_0008
Revises: 20260618_0007
Create Date: 2026-07-20 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260720_0008"
down_revision: str | None = "20260618_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "keyword_industries",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_keyword_industries_status", "keyword_industries", ["status"])

    op.create_table(
        "keyword_groups",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("industry_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("keyword", sa.String(length=200), nullable=False),
        sa.Column("video_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["industry_id"], ["keyword_industries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("industry_id", "keyword", name="uq_keyword_groups_industry_keyword"),
    )
    op.create_index("ix_keyword_groups_industry_id", "keyword_groups", ["industry_id"])

    op.create_table(
        "keyword_videos",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("keyword_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("author_name", sa.String(length=200), nullable=True),
        sa.Column("author_url", sa.String(length=500), nullable=True),
        sa.Column("author_follower_count", sa.Integer(), nullable=True),
        sa.Column("platform", sa.String(length=100), nullable=True),
        sa.Column("industry", sa.String(length=100), nullable=True),
        sa.Column("audience", sa.String(length=200), nullable=True),
        sa.Column("purpose", sa.String(length=100), nullable=True),
        sa.Column("style", sa.String(length=100), nullable=True),
        sa.Column("likes", sa.Integer(), nullable=False),
        sa.Column("comments", sa.Integer(), nullable=False),
        sa.Column("favorites", sa.Integer(), nullable=False),
        sa.Column("shares", sa.Integer(), nullable=False),
        sa.Column("hot_score", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["keyword_id"], ["keyword_groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("keyword_id", "source_url", name="uq_keyword_videos_keyword_source_url"),
    )
    op.create_index("ix_keyword_videos_keyword_hot_score", "keyword_videos", ["keyword_id", "hot_score"])
    op.create_index("ix_keyword_videos_keyword_id", "keyword_videos", ["keyword_id"])


def downgrade() -> None:
    op.drop_index("ix_keyword_videos_keyword_id", table_name="keyword_videos")
    op.drop_index("ix_keyword_videos_keyword_hot_score", table_name="keyword_videos")
    op.drop_table("keyword_videos")
    op.drop_index("ix_keyword_groups_industry_id", table_name="keyword_groups")
    op.drop_table("keyword_groups")
    op.drop_index("ix_keyword_industries_status", table_name="keyword_industries")
    op.drop_table("keyword_industries")
