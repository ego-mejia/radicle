"""Folio chunks: the section's headings count in full-text search

Revision ID: 0039
Revises: 0038
Create Date: 2026-10-20

Folio 1.6. The heading path goes into the chunk's metadata as `section` and into the
search vector with the title's weight, so a search lands on the section it names.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0039"
down_revision: str | None = "0038"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _weighted(field: str, weight: str) -> str:
    return " || ".join(
        f"setweight(to_tsvector('{config}'::regconfig, coalesce({field}, '')), '{weight}')"
        for config in ("english", "spanish")
    )


BEFORE = " || ".join(
    [
        _weighted("metadata->>'title'", "A"),
        _weighted("metadata->>'description'", "B"),
        _weighted("text", "C"),
    ]
)
AFTER = " || ".join(
    [
        _weighted("metadata->>'title'", "A"),
        _weighted("metadata->>'section'", "A"),
        _weighted("metadata->>'description'", "B"),
        _weighted("text", "C"),
    ]
)


def _search_vector(expression: str) -> None:
    op.drop_index("ix_folio_chunks_search", table_name="folio_chunks")
    op.drop_column("folio_chunks", "search_vector")
    op.add_column(
        "folio_chunks",
        sa.Column("search_vector", postgresql.TSVECTOR(), sa.Computed(expression, persisted=True)),
    )
    op.create_index(
        "ix_folio_chunks_search", "folio_chunks", ["search_vector"], postgresql_using="gin"
    )


def upgrade() -> None:
    op.execute(
        "UPDATE folio_chunks SET metadata = metadata || "
        "jsonb_build_object('section', array_to_string(heading_path, ' > '))"
    )
    _search_vector(AFTER)


def downgrade() -> None:
    _search_vector(BEFORE)
    op.execute("UPDATE folio_chunks SET metadata = metadata - 'section'")
