"""Folio spaces, the tree of nodes and its append-only history

Revision ID: 0031
Revises: 0030
Create Date: 2026-10-20

Folio 1.1. Team and personal spaces (one personal space per user); pages, folders and
blog posts ordered by fractional rank; soft delete everywhere.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0031"
down_revision: str | None = "0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

space_kind = postgresql.ENUM("team", "personal", name="folio_space_kind", create_type=False)
node_kind = postgresql.ENUM(
    "page", "folder", "blog_post", name="folio_node_kind", create_type=False
)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    ]


def upgrade() -> None:
    space_kind.create(op.get_bind())
    node_kind.create(op.get_bind())
    op.create_table(
        "folio_spaces",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("key", postgresql.CITEXT(), nullable=False, unique=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("kind", space_kind, nullable=False),
        sa.Column(
            "owner_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True
        ),
        sa.Column("icon", sa.Text(), nullable=True),
        sa.Column("cover_asset_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        *_timestamps(),
    )
    op.create_index(
        "ux_folio_spaces_personal_owner",
        "folio_spaces",
        ["owner_id"],
        unique=True,
        postgresql_where=sa.text("kind = 'personal'"),
    )
    op.create_table(
        "folio_nodes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "space_id",
            sa.Uuid(),
            sa.ForeignKey("folio_spaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_id",
            sa.Uuid(),
            sa.ForeignKey("folio_nodes.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("kind", node_kind, nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("icon", sa.Text(), nullable=True),
        sa.Column("cover_asset_id", sa.Uuid(), nullable=True),
        sa.Column("rank", sa.Text(collation="C"), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        *_timestamps(),
    )
    op.create_index("ix_folio_nodes_space_id", "folio_nodes", ["space_id"])
    op.create_index(
        "ix_folio_nodes_space_parent_rank", "folio_nodes", ["space_id", "parent_id", "rank"]
    )
    op.create_index("ix_folio_nodes_space_published", "folio_nodes", ["space_id", "published_at"])
    op.create_table(
        "folio_node_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("node_id", sa.Uuid(), sa.ForeignKey("folio_nodes.id"), nullable=False),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column(
            "data", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_folio_node_events_node_id_id", "folio_node_events", ["node_id", "id"])
    op.execute(
        """
        CREATE FUNCTION folio_node_events_append_only() RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'folio_node_events is append-only: % is not allowed', TG_OP
            USING ERRCODE = 'insufficient_privilege';
        END $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER folio_node_events_no_update_delete BEFORE UPDATE OR DELETE "
        "ON folio_node_events FOR EACH ROW EXECUTE FUNCTION folio_node_events_append_only()"
    )
    op.execute(
        "CREATE TRIGGER folio_node_events_no_truncate BEFORE TRUNCATE ON folio_node_events "
        "FOR EACH STATEMENT EXECUTE FUNCTION folio_node_events_append_only()"
    )


def downgrade() -> None:
    op.drop_table("folio_node_events")
    op.execute("DROP FUNCTION folio_node_events_append_only()")
    op.drop_table("folio_nodes")
    op.drop_table("folio_spaces")
    node_kind.drop(op.get_bind())
    space_kind.drop(op.get_bind())
