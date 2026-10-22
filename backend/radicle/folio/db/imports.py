"""Folio imports (phase 5.3): an uploaded export, its dry run and its run, and which
Folio node each imported page became, so importing again updates instead of duplicating."""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from radicle.platform.db.models.base import Base, _enum, utcnow


class ImportSource(enum.StrEnum):
    confluence = "confluence"
    notion = "notion"
    word = "word"
    markdown = "markdown"


class ImportStatus(enum.StrEnum):
    uploaded = "uploaded"  # waiting for its dry run
    checked = "checked"  # dry run done, ready to run
    running = "running"
    done = "done"
    failed = "failed"


class FolioImport(Base):
    __tablename__ = "folio_imports"
    __table_args__ = (Index("ix_folio_imports_created_at", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[ImportSource] = mapped_column(_enum(ImportSource, "folio_import_source"))
    target_space_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("folio_spaces.id", ondelete="CASCADE")
    )
    filename: Mapped[str] = mapped_column(Text)
    upload_key: Mapped[str] = mapped_column(Text)  # the uploaded file in storage
    options: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    status: Mapped[ImportStatus] = mapped_column(
        _enum(ImportStatus, "folio_import_status"), default=ImportStatus.uploaded
    )
    # The dry run's plan, then the run's outcome per page.
    report: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    stats: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FolioExternalRef(Base):
    """The node an imported page became in a space; unique per source, the source's own id
    and the space, so the same export imported into two spaces makes two pages."""

    __tablename__ = "folio_external_refs"

    source: Mapped[ImportSource] = mapped_column(
        _enum(ImportSource, "folio_import_source"), primary_key=True
    )
    external_id: Mapped[str] = mapped_column(Text, primary_key=True)
    space_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("folio_spaces.id", ondelete="CASCADE"), primary_key=True
    )
    node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("folio_nodes.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
