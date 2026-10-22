"""Folio external refs are per space

Revision ID: 0064
Revises: 0063
Create Date: 2026-10-22

Importing the same export into another space made new pages there instead of updating
the first space's (5.3): an external id now maps to one node per space.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0064"
down_revision: str | None = "0063"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("folio_external_refs", sa.Column("space_id", sa.Uuid(), nullable=True))
    op.execute(
        "UPDATE folio_external_refs r SET space_id = n.space_id "
        "FROM folio_nodes n WHERE n.id = r.node_id"
    )
    op.alter_column("folio_external_refs", "space_id", nullable=False)
    op.create_foreign_key(
        "fk_folio_external_refs_space_id",
        "folio_external_refs",
        "folio_spaces",
        ["space_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint("folio_external_refs_pkey", "folio_external_refs", type_="primary")
    op.create_primary_key(
        "folio_external_refs_pkey", "folio_external_refs", ["source", "external_id", "space_id"]
    )


def downgrade() -> None:
    # Keep the oldest node per external id, as before.
    op.execute(
        "DELETE FROM folio_external_refs r USING folio_external_refs o "
        "WHERE r.source = o.source AND r.external_id = o.external_id "
        "AND (r.created_at, r.node_id) > (o.created_at, o.node_id)"
    )
    op.drop_constraint("folio_external_refs_pkey", "folio_external_refs", type_="primary")
    op.create_primary_key(
        "folio_external_refs_pkey", "folio_external_refs", ["source", "external_id"]
    )
    op.drop_constraint("fk_folio_external_refs_space_id", "folio_external_refs", type_="foreignkey")
    op.drop_column("folio_external_refs", "space_id")
