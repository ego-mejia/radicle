"""Folio glossary terms

Revision ID: 0053
Revises: 0052
Create Date: 2026-10-21

Folio phase 4 (4.6). The AI suggests terms from Verified docs and a Folio admin approves them.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0053"
down_revision: str | None = "0052"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

status = postgresql.ENUM(
    "suggested", "approved", "rejected", name="folio_term_status", create_type=False
)


def upgrade() -> None:
    status.create(op.get_bind())
    op.create_table(
        "folio_glossary_terms",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("term", postgresql.CITEXT(), nullable=False),
        sa.Column("aliases", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False),
        sa.Column("definition", sa.Text(), nullable=False),
        sa.Column(
            "source_node_id",
            sa.Uuid(),
            sa.ForeignKey("folio_nodes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", status, nullable=False),
        sa.Column(
            "updated_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ux_folio_glossary_terms_term", "folio_glossary_terms", ["term"], unique=True)


def downgrade() -> None:
    op.drop_index("ux_folio_glossary_terms_term", table_name="folio_glossary_terms")
    op.drop_table("folio_glossary_terms")
    status.drop(op.get_bind())
