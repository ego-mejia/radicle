"""pgvector and Folio's chunks: the search and RAG index of published pages

Revision ID: 0038
Revises: 0037
Create Date: 2026-10-20

Folio 1.6 (ADR 0037). Needs the pgvector extension, which the database image of docker
compose includes.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from radicle.folio.db.models import CHUNK_SEARCH_SQL

revision: str = "0038"
down_revision: str | None = "0037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    available = op.get_bind().scalar(
        sa.text("SELECT count(*) FROM pg_available_extensions WHERE name = 'vector'")
    )
    if not available:
        raise RuntimeError(
            "Folio's search needs the pgvector extension. Rebuild the database image "
            "(docker compose build db && docker compose up -d) and run the migrations again."
        )
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "folio_chunks",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "node_id",
            sa.Uuid(),
            sa.ForeignKey("folio_nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_id", sa.Uuid(), sa.ForeignKey("folio_versions.id"), nullable=False),
        sa.Column("position", sa.BigInteger(), nullable=False),
        sa.Column("heading_path", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("anchor", sa.Text(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.BigInteger(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False),
        sa.Column("embedding", Vector(), nullable=True),
        sa.Column("embedding_dims", sa.BigInteger(), nullable=True),
        sa.Column("embedded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed(CHUNK_SEARCH_SQL, persisted=True),
        ),
    )
    op.create_index(
        "ix_folio_chunks_search", "folio_chunks", ["search_vector"], postgresql_using="gin"
    )
    op.create_index("ix_folio_chunks_node_position", "folio_chunks", ["node_id", "position"])


def downgrade() -> None:
    op.drop_table("folio_chunks")
    op.execute("DROP EXTENSION IF EXISTS vector")
