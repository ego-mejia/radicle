"""Folio's editable catalogs: document types, audiences and languages

Revision ID: 0034
Revises: 0033
Create Date: 2026-10-20

Folio 1.3. Seeded with the document types of the Folio control document, one audience
(everyone) and two languages (es, en); Folio admins edit them.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0034"
down_revision: str | None = "0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("folio_doc_types", "folio_audiences", "folio_languages")
SEED = {
    "folio_doc_types": [
        ("guide", "Guide"),
        ("reference", "Reference"),
        ("how-to", "How-to"),
        ("announcement", "Announcement"),
        ("build-spec", "Build spec"),
        ("minutes", "Meeting minutes"),
        ("decision-log", "Decision log"),
        ("retrospective", "Retrospective"),
        ("requirements", "Requirements"),
    ],
    "folio_audiences": [("everyone", "Everyone")],
    "folio_languages": [("es", "Español"), ("en", "English")],
}


def upgrade() -> None:
    for table in TABLES:
        created = op.create_table(
            table,
            sa.Column("key", sa.Text(), primary_key=True),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("position", sa.BigInteger(), nullable=False, server_default="0"),
            sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.bulk_insert(
            created,
            [{"key": k, "name": n, "position": i} for i, (k, n) in enumerate(SEED[table])],
        )


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_table(table)
