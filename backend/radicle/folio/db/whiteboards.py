"""Folio whiteboards (phase 3.5): a node of kind `whiteboard` is an Excalidraw scene.

While people draw, the scene lives in the node's Y.Doc (folio_ydocs); this row is its
JSON read, for readers, embeds and search, and keeps the text of its elements."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from radicle.platform.db.models.base import Base, utcnow


class FolioWhiteboard(Base):
    __tablename__ = "folio_whiteboards"

    node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("folio_nodes.id", ondelete="CASCADE"), primary_key=True
    )
    # Excalidraw elements, deleted ones left out; see docs/folio/whiteboards.md.
    elements: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    text: Mapped[str] = mapped_column(Text, default="", server_default="")
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
