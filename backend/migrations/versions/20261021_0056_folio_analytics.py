"""Folio page views and search logs

Revision ID: 0056
Revises: 0055
Create Date: 2026-10-21

Folio phase 5 (5.9). Daily page views per reader, searches with their result count and
click, and a space setting that shows who read a page.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0056"
down_revision: str | None = "0055"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "folio_page_views",
        sa.Column(
            "node_id",
            sa.Uuid(),
            sa.ForeignKey("folio_nodes.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("views", sa.BigInteger(), server_default="1", nullable=False),
    )
    op.create_index("ix_folio_page_views_day", "folio_page_views", ["day"])
    op.create_table(
        "folio_search_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.Column("results_count", sa.BigInteger(), nullable=False),
        sa.Column(
            "clicked_node_id",
            sa.Uuid(),
            sa.ForeignKey("folio_nodes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_folio_search_logs_created_at", "folio_search_logs", ["created_at"])
    op.add_column(
        "folio_spaces",
        sa.Column("show_readers", sa.Boolean(), server_default="false", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("folio_spaces", "show_readers")
    op.drop_index("ix_folio_search_logs_created_at", table_name="folio_search_logs")
    op.drop_table("folio_search_logs")
    op.drop_index("ix_folio_page_views_day", table_name="folio_page_views")
    op.drop_table("folio_page_views")
