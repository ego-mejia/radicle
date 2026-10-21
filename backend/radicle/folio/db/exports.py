"""Folio exports (phase 5.2): a page or a space written to PDF, Word, HTML or Markdown by
the worker, kept in storage for its author to download."""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from radicle.platform.db.models.base import Base, _enum, utcnow


class ExportFormat(enum.StrEnum):
    pdf = "pdf"
    docx = "docx"
    html = "html"
    markdown = "markdown"


class ExportScope(enum.StrEnum):
    node = "node"
    space = "space"


class ExportStatus(enum.StrEnum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"


class FolioExport(Base):
    __tablename__ = "folio_exports"
    __table_args__ = (Index("ix_folio_exports_created_by", "created_by", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    format: Mapped[ExportFormat] = mapped_column(_enum(ExportFormat, "folio_export_format"))
    scope: Mapped[ExportScope] = mapped_column(_enum(ExportScope, "folio_export_scope"))
    space_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("folio_spaces.id", ondelete="CASCADE"))
    node_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("folio_nodes.id", ondelete="CASCADE")
    )
    options: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    status: Mapped[ExportStatus] = mapped_column(
        _enum(ExportStatus, "folio_export_status"), default=ExportStatus.queued
    )
    # Pages written, size and, when it failed, why.
    stats: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    file_key: Mapped[str | None] = mapped_column(Text)  # the result in storage
    filename: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
