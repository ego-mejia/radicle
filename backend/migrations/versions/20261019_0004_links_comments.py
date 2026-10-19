"""ticket links, comments and reactions

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ts(name: str, nullable: bool = False) -> sa.Column:
    return sa.Column(
        name,
        sa.DateTime(timezone=True),
        nullable=nullable,
        server_default=None if nullable else sa.func.now(),
    )


def _ticket_fk(name: str) -> sa.Column:
    return sa.Column(
        name,
        sa.Uuid(),
        sa.ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


def upgrade() -> None:
    link_type = postgresql.ENUM("blocks", "relates_to", "duplicates", "clones", name="link_type")
    link_type.create(op.get_bind())

    op.create_table(
        "ticket_links",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _ticket_fk("source_id"),
        _ticket_fk("target_id"),
        sa.Column("type", postgresql.ENUM(name="link_type", create_type=False), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        _ts("created_at"),
        sa.UniqueConstraint("source_id", "target_id", "type", name="uq_ticket_links"),
        sa.CheckConstraint("source_id <> target_id", name="ck_ticket_links_not_self"),
    )

    op.create_table(
        "comments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _ticket_fk("ticket_id"),
        sa.Column("author_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body_md", sa.Text(), nullable=False),
        _ts("created_at"),
        _ts("edited_at", nullable=True),
        _ts("deleted_at", nullable=True),
        sa.CheckConstraint("char_length(body_md) <= 50000", name="ck_comments_body"),
    )

    op.create_table(
        "comment_reactions",
        sa.Column(
            "comment_id",
            sa.Uuid(),
            sa.ForeignKey("comments.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("emoji", sa.Text(), primary_key=True),
        _ts("created_at"),
    )

    op.create_foreign_key(
        "mentions_comment_id_fkey",
        "mentions",
        "comments",
        ["comment_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("mentions_comment_id_fkey", "mentions", type_="foreignkey")
    op.drop_table("comment_reactions")
    op.drop_table("comments")
    op.drop_table("ticket_links")
    postgresql.ENUM(name="link_type").drop(op.get_bind())
