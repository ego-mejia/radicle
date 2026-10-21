"""Folio phase 3 tables. Templates (3.1): page templates (a document with variables and default
metadata) and space templates (a tree of pages, grants and a cover), global or per space."""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from radicle.platform.db.models.base import Base, _enum, utcnow


class TemplateKind(enum.StrEnum):
    page = "page"
    space = "space"


class TemplateScope(enum.StrEnum):
    global_ = "global"
    space = "space"


class FolioTemplate(Base):
    __tablename__ = "folio_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind: Mapped[TemplateKind] = mapped_column(_enum(TemplateKind, "folio_template_kind"))
    scope: Mapped[TemplateScope] = mapped_column(_enum(TemplateScope, "folio_template_scope"))
    space_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("folio_spaces.id", ondelete="CASCADE")
    )
    # The included templates (build-spec, how-to...) keep their key; ours have none.
    builtin_key: Mapped[str | None] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    icon: Mapped[str | None] = mapped_column(Text)
    doc_type_key: Mapped[str | None] = mapped_column(Text)
    # Page: a document whose text may use {{date}}, {{author}}, {{space}}, {{title}}.
    content_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    default_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default="{}"
    )
    # Space: [{title, kind, template?, children: [...]}], grants and cover.
    structure: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FolioLinkPreview(Base):
    """A pasted link's preview, cached 24 hours (Folio 3.7)."""

    __tablename__ = "folio_link_previews"

    url_hash: Mapped[str] = mapped_column(Text, primary_key=True)
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text, default="", server_default="")
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    site_name: Mapped[str] = mapped_column(Text, default="", server_default="")
    icon_url: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    provider: Mapped[str | None] = mapped_column(Text)
    embed_html_allowed: Mapped[bool] = mapped_column(default=False, server_default="false")
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
