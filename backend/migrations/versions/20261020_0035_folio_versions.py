"""Folio versions (insert only), the published version of each node, and labels

Revision ID: 0035
Revises: 0034
Create Date: 2026-10-20

Folio 1.3.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0035"
down_revision: str | None = "0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "folio_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("node_id", sa.Uuid(), sa.ForeignKey("folio_nodes.id"), nullable=False),
        sa.Column("number", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content_json", postgresql.JSONB(), nullable=False),
        sa.Column("content_md", sa.Text(), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False),
        sa.Column("change_note", sa.Text(), nullable=True),
        sa.Column("author_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("approved_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("restored_from", sa.Uuid(), sa.ForeignKey("folio_versions.id"), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("node_id", "number", name="uq_folio_versions_number"),
    )
    op.create_index("ix_folio_versions_node_id", "folio_versions", ["node_id"])
    op.execute(
        """
        CREATE FUNCTION folio_versions_immutable() RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'folio_versions is insert-only: % is not allowed', TG_OP
            USING ERRCODE = 'insufficient_privilege';
        END $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER folio_versions_no_update_delete BEFORE UPDATE OR DELETE "
        "ON folio_versions FOR EACH ROW EXECUTE FUNCTION folio_versions_immutable()"
    )
    op.execute(
        "CREATE TRIGGER folio_versions_no_truncate BEFORE TRUNCATE ON folio_versions "
        "FOR EACH STATEMENT EXECUTE FUNCTION folio_versions_immutable()"
    )
    op.add_column("folio_nodes", sa.Column("published_version_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_folio_nodes_published_version",
        "folio_nodes",
        "folio_versions",
        ["published_version_id"],
        ["id"],
    )
    op.create_table(
        "folio_node_labels",
        sa.Column(
            "node_id",
            sa.Uuid(),
            sa.ForeignKey("folio_nodes.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("label", sa.Text(), primary_key=True),
    )
    op.create_index("ix_folio_node_labels_label", "folio_node_labels", ["label"])


def downgrade() -> None:
    op.drop_table("folio_node_labels")
    op.drop_constraint("fk_folio_nodes_published_version", "folio_nodes", type_="foreignkey")
    op.drop_column("folio_nodes", "published_version_id")
    op.drop_table("folio_versions")
    op.execute("DROP FUNCTION folio_versions_immutable()")
