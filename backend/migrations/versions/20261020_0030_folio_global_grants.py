"""Folio's global roles: reader, creator or admin for a user, a group or everyone

Revision ID: 0030
Revises: 0029
Create Date: 2026-10-20

Folio 0.5. Seeded with everyone = reader.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0030"
down_revision: str | None = "0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

grantee_type = postgresql.ENUM(
    "user", "group", "everyone", name="folio_grantee_type", create_type=False
)
folio_role = postgresql.ENUM("reader", "creator", "admin", name="folio_role", create_type=False)


def upgrade() -> None:
    grantee_type.create(op.get_bind())
    folio_role.create(op.get_bind())
    op.create_table(
        "folio_global_grants",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("grantee_type", grantee_type, nullable=False),
        sa.Column("grantee_id", sa.Uuid(), nullable=True),
        sa.Column("role", folio_role, nullable=False),
        sa.Column(
            "created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ux_folio_global_grants_grantee",
        "folio_global_grants",
        [
            "grantee_type",
            sa.text("coalesce(grantee_id, '00000000-0000-0000-0000-000000000000'::uuid)"),
        ],
        unique=True,
    )
    op.execute(
        "INSERT INTO folio_global_grants (id, grantee_type, grantee_id, role) "
        "VALUES (gen_random_uuid(), 'everyone', NULL, 'reader')"
    )


def downgrade() -> None:
    op.drop_table("folio_global_grants")
    folio_role.drop(op.get_bind())
    grantee_type.drop(op.get_bind())
