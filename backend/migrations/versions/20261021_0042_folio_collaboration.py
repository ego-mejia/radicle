"""Folio collaboration: comments, reactions, watches, favorites, action items, views,
Yjs state and live-doc snapshots

Revision ID: 0042
Revises: 0041
Create Date: 2026-10-21

Folio phase 2 (2.2 to 2.5, 2.7).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0042"
down_revision: str | None = "0041"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

comment_kind = postgresql.ENUM("footer", "inline", name="folio_comment_kind", create_type=False)
target_type = postgresql.ENUM(
    "node", "space", "comment", name="folio_target_type", create_type=False
)
watch_source = postgresql.ENUM("auto", "manual", name="folio_watch_source", create_type=False)
ENUMS = (comment_kind, target_type, watch_source)


def _node() -> sa.Column[object]:
    return sa.Column(
        "node_id",
        sa.Uuid(),
        sa.ForeignKey("folio_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )


def _user(name: str = "user_id", nullable: bool = False) -> sa.Column[object]:
    return sa.Column(
        name,
        sa.Uuid(),
        sa.ForeignKey("users.id", ondelete="SET NULL" if nullable else "CASCADE"),
        nullable=nullable,
    )


def _now(name: str) -> sa.Column[object]:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    for enum in ENUMS:
        enum.create(op.get_bind())
    op.create_table(
        "folio_comments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _node(),
        sa.Column("thread_id", sa.Uuid(), nullable=False),
        sa.Column(
            "parent_id",
            sa.Uuid(),
            sa.ForeignKey("folio_comments.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("kind", comment_kind, nullable=False),
        _user("author_id", nullable=True),
        sa.Column("body_json", postgresql.JSONB(), nullable=False),
        sa.Column("anchor", postgresql.JSONB(), nullable=True),
        sa.Column("orphaned", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        _user("resolved_by", nullable=True),
        _now("created_at"),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_folio_comments_node", "folio_comments", ["node_id", "thread_id", "created_at"]
    )
    op.create_table(
        "folio_reactions",
        sa.Column("target_type", target_type, nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        _user(),
        sa.Column("emoji", sa.Text(), nullable=False),
        _now("created_at"),
        sa.PrimaryKeyConstraint("target_type", "target_id", "user_id", "emoji"),
    )
    op.create_table(
        "folio_watches",
        _user(),
        sa.Column("target_type", target_type, nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("source", watch_source, nullable=False),
        _now("created_at"),
        sa.PrimaryKeyConstraint("user_id", "target_type", "target_id"),
    )
    op.create_table(
        "folio_favorites",
        _user(),
        sa.Column("target_type", target_type, nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        _now("created_at"),
        sa.PrimaryKeyConstraint("user_id", "target_type", "target_id"),
    )
    op.create_table(
        "folio_action_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _node(),
        sa.Column("item_key", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        _user("assignee_id", nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("done", sa.Boolean(), server_default="false", nullable=False),
        _now("updated_at"),
        sa.UniqueConstraint("node_id", "item_key"),
    )
    op.create_index(
        "ix_folio_action_items_assignee",
        "folio_action_items",
        ["assignee_id", "done", "due_date"],
    )
    op.create_table(
        "folio_views",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        _node(),
        _user(),
        _now("viewed_at"),
    )
    op.create_index("ix_folio_views_user", "folio_views", ["user_id", "viewed_at"])
    op.create_index("ix_folio_views_node", "folio_views", ["node_id", "viewed_at"])
    op.create_table(
        "folio_view_counts_daily",
        _node(),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("views", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("unique_viewers", sa.BigInteger(), server_default="0", nullable=False),
        sa.PrimaryKeyConstraint("node_id", "date"),
    )
    op.create_table(
        "folio_ydocs",
        sa.Column(
            "node_id",
            sa.Uuid(),
            sa.ForeignKey("folio_nodes.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("state", sa.LargeBinary(), nullable=False),
        _now("updated_at"),
    )
    op.create_table(
        "folio_yupdates",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        _node(),
        sa.Column("update", sa.LargeBinary(), nullable=False),
        _now("created_at"),
    )
    op.create_index("ix_folio_yupdates_node", "folio_yupdates", ["node_id", "id"])
    op.create_table(
        "folio_live_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _node(),
        sa.Column("content_json", postgresql.JSONB(), nullable=False),
        sa.Column("authors", postgresql.ARRAY(sa.Uuid()), nullable=False),
        _now("created_at"),
    )
    op.create_index(
        "ix_folio_live_snapshots_node", "folio_live_snapshots", ["node_id", "created_at"]
    )


def downgrade() -> None:
    for table in (
        "folio_live_snapshots",
        "folio_yupdates",
        "folio_ydocs",
        "folio_view_counts_daily",
        "folio_views",
        "folio_action_items",
        "folio_favorites",
        "folio_watches",
        "folio_reactions",
        "folio_comments",
    ):
        op.drop_table(table)
    for enum in reversed(ENUMS):
        enum.drop(op.get_bind())
