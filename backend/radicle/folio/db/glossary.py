"""Folio phase 4 glossary (4.6): terms with their definition. The AI suggests them from
Verified docs; a Folio admin approves them; readers see approved ones as tooltips."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column

from radicle.platform.db.models.base import Base, _enum, utcnow


class TermStatus(enum.StrEnum):
    suggested = "suggested"
    approved = "approved"
    rejected = "rejected"


class FolioGlossaryTerm(Base):
    __tablename__ = "folio_glossary_terms"
    __table_args__ = (Index("ux_folio_glossary_terms_term", "term", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    term: Mapped[str] = mapped_column(CITEXT)
    aliases: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, server_default="{}")
    definition: Mapped[str] = mapped_column(Text)
    source_node_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("folio_nodes.id", ondelete="SET NULL")
    )
    status: Mapped[TermStatus] = mapped_column(
        _enum(TermStatus, "folio_term_status"), default=TermStatus.suggested
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
