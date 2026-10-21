"""Folio phase 5 public links (5.1): a read-only, revocable link to a page or a whole space
that opens without an account."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from radicle.platform.db.models.base import Base, _enum, utcnow


class PublicTarget(enum.StrEnum):
    node = "node"
    space = "space"


class FolioPublicLink(Base):
    __tablename__ = "folio_public_links"
    __table_args__ = (
        Index("ux_folio_public_links_token", "token", unique=True),
        Index("ix_folio_public_links_target", "target_type", "target_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_type: Mapped[PublicTarget] = mapped_column(_enum(PublicTarget, "folio_public_target"))
    # A node or a space id; no foreign key since it points at either.
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    token: Mapped[str] = mapped_column(Text)
    noindex: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    view_count: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
