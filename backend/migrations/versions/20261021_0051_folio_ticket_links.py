"""Folio ticket links: docs linked to Docket tickets

Revision ID: 0051
Revises: 0050
Create Date: 2026-10-21

Folio phase 4.1. A doc (and optionally one of its sections) linked to a ticket because it
mentions it, created it from text, made it from a build spec deliverable, or by hand.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0051"
down_revision: str | None = "0050"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

kind = postgresql.ENUM(
    "mention",
    "created_from_text",
    "build_spec_item",
    "manual",
    name="folio_ticket_link_kind",
    create_type=False,
)


def upgrade() -> None:
    kind.create(op.get_bind())
    op.create_table(
        "folio_ticket_links",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "node_id",
            sa.Uuid(),
            sa.ForeignKey("folio_nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("anchor", sa.Text(), nullable=True),
        sa.Column(
            "ticket_id", sa.Uuid(), sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("kind", kind, nullable=False),
        sa.Column("item_key", sa.Text(), nullable=True),
        sa.Column(
            "created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("node_id", "ticket_id", "kind", name="uq_folio_ticket_links"),
    )
    op.create_index("ix_folio_ticket_links_node_id", "folio_ticket_links", ["node_id"])
    op.create_index("ix_folio_ticket_links_ticket_id", "folio_ticket_links", ["ticket_id"])
    op.create_index(
        "uq_folio_ticket_links_item",
        "folio_ticket_links",
        ["node_id", "item_key"],
        unique=True,
        postgresql_where=sa.text("item_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_folio_ticket_links_item", table_name="folio_ticket_links")
    op.drop_index("ix_folio_ticket_links_ticket_id", table_name="folio_ticket_links")
    op.drop_index("ix_folio_ticket_links_node_id", table_name="folio_ticket_links")
    op.drop_table("folio_ticket_links")
    kind.drop(op.get_bind())
