"""Folio space grants and page restrictions

Revision ID: 0036
Revises: 0035
Create Date: 2026-10-20

Folio 1.4. Existing team spaces get the defaults: everyone may view and their creator
administers them; personal spaces are only their owner's.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0036"
down_revision: str | None = "0035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

grantee_type = postgresql.ENUM(
    "user", "group", "everyone", name="folio_grantee_type", create_type=False
)
restriction_mode = postgresql.ENUM("view", "edit", name="folio_restriction_mode", create_type=False)


def upgrade() -> None:
    restriction_mode.create(op.get_bind())
    op.create_table(
        "folio_space_grants",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "space_id",
            sa.Uuid(),
            sa.ForeignKey("folio_spaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("grantee_type", grantee_type, nullable=False),
        sa.Column("grantee_id", sa.Uuid(), nullable=True),
        sa.Column("permissions", postgresql.ARRAY(sa.Text()), nullable=False),
    )
    op.create_index("ix_folio_space_grants_space_id", "folio_space_grants", ["space_id"])
    op.create_index(
        "ux_folio_space_grants_grantee",
        "folio_space_grants",
        [
            "space_id",
            "grantee_type",
            sa.text("coalesce(grantee_id, '00000000-0000-0000-0000-000000000000'::uuid)"),
        ],
        unique=True,
    )
    op.create_table(
        "folio_page_restrictions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "node_id",
            sa.Uuid(),
            sa.ForeignKey("folio_nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("mode", restriction_mode, nullable=False),
        sa.Column("grantee_type", grantee_type, nullable=False),
        sa.Column("grantee_id", sa.Uuid(), nullable=False),
    )
    op.create_index("ix_folio_page_restrictions_node_id", "folio_page_restrictions", ["node_id"])
    op.create_index(
        "ux_folio_page_restrictions",
        "folio_page_restrictions",
        ["node_id", "mode", "grantee_type", "grantee_id"],
        unique=True,
    )
    op.execute(
        """
        INSERT INTO folio_space_grants (id, space_id, grantee_type, grantee_id, permissions)
        SELECT gen_random_uuid(), id, 'everyone', NULL, ARRAY['view']
        FROM folio_spaces WHERE kind = 'team'
        """
    )
    op.execute(
        """
        INSERT INTO folio_space_grants (id, space_id, grantee_type, grantee_id, permissions)
        SELECT gen_random_uuid(), id, 'user', coalesce(owner_id, created_by), ARRAY['admin']
        FROM folio_spaces WHERE coalesce(owner_id, created_by) IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_table("folio_page_restrictions")
    op.drop_table("folio_space_grants")
    restriction_mode.drop(op.get_bind())
