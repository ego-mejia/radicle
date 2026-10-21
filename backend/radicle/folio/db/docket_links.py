"""Folio phase 4 tables: links between docs and Docket tickets (4.1 to 4.3). Folio stores
only the ticket's id; everything else about the ticket comes from `radicle.docket.public`
with the reader's access."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from radicle.platform.db.models.base import Base, _enum, utcnow


class TicketLinkKind(enum.StrEnum):
    mention = "mention"  # the published doc names the key
    created_from_text = "created_from_text"  # made from a selection or an action item
    build_spec_item = "build_spec_item"  # one per deliverable of a build spec (4.3)
    manual = "manual"


class FolioTicketLink(Base):
    __tablename__ = "folio_ticket_links"
    __table_args__ = (
        UniqueConstraint("node_id", "ticket_id", "kind", name="uq_folio_ticket_links"),
        Index(
            "uq_folio_ticket_links_item",
            "node_id",
            "item_key",
            unique=True,
            postgresql_where=text("item_key IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("folio_nodes.id", ondelete="CASCADE"), index=True
    )
    # The section's heading anchor (`#conecta-un-agente`), as the reader computes it.
    anchor: Mapped[str | None] = mapped_column(Text)
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[TicketLinkKind] = mapped_column(_enum(TicketLinkKind, "folio_ticket_link_kind"))
    item_key: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
