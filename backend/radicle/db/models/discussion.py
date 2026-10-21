import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from radicle.platform.db.models.base import Base, _enum, utcnow
from radicle.platform.db.models.users import User


class LinkType(enum.StrEnum):
    blocks = "blocks"
    relates_to = "relates_to"
    duplicates = "duplicates"
    clones = "clones"


# (label seen from the source, label seen from the target)
LINK_LABELS = {
    LinkType.blocks: ("blocks", "is blocked by"),
    LinkType.relates_to: ("relates to", "relates to"),
    LinkType.duplicates: ("duplicates", "is duplicated by"),
    LinkType.clones: ("clones", "is cloned by"),
}

link_type_enum = _enum(LinkType, "link_type")


class TicketLink(Base):
    __tablename__ = "ticket_links"
    __table_args__ = (
        UniqueConstraint("source_id", "target_id", "type", name="uq_ticket_links"),
        CheckConstraint("source_id <> target_id", name="ck_ticket_links_not_self"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), index=True
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[LinkType] = mapped_column(link_type_enum)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), index=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    body_md: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    author: Mapped[User] = relationship(lazy="joined")


class CommentReaction(Base):
    __tablename__ = "comment_reactions"

    comment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    emoji: Mapped[str] = mapped_column(Text, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )

    user: Mapped[User] = relationship(lazy="joined")
