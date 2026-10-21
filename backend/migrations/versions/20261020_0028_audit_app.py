"""Audit entries say which app they belong to

Revision ID: 0028
Revises: 0027
Create Date: 2026-10-20

Folio 0.3: platform, docket or folio. Existing entries stay docket (the log is append-only).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0028"
down_revision: str | None = "0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

audit_app = postgresql.ENUM("platform", "docket", "folio", name="audit_app", create_type=False)


def upgrade() -> None:
    audit_app.create(op.get_bind())
    op.add_column("audit_log", sa.Column("app", audit_app, nullable=False, server_default="docket"))


def downgrade() -> None:
    op.drop_column("audit_log", "app")
    audit_app.drop(op.get_bind())
