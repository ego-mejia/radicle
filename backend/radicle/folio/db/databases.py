"""Folio databases (phase 3.6): a node of kind `database` holds typed columns and saved
views; its rows live apart, each with its values by column key."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from radicle.platform.db.models.base import Base, utcnow


class FolioDatabase(Base):
    __tablename__ = "folio_databases"

    node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("folio_nodes.id", ondelete="CASCADE"), primary_key=True
    )
    # [{key, name, type, options}]; see docs/folio/databases.md.
    columns: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    # [{id, name, kind, group_by, filters, sort, visible_columns}]
    views: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)


class FolioDbRow(Base):
    __tablename__ = "folio_db_rows"
    __table_args__ = (Index("ix_folio_db_rows_node_rank", "node_id", "rank"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("folio_nodes.id", ondelete="CASCADE"))
    values: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    # Byte order, as fractional ranks expect, whatever the database locale.
    rank: Mapped[str] = mapped_column(Text(collation="C"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
