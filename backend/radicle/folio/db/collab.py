"""Folio's collaboration tables (phase 2): comments, reactions, watches, action items,
favorites, reading history, live-doc snapshots and the Yjs state of drafts."""

import enum
import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    PrimaryKeyConstraint,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from radicle.platform.db.models.base import Base, _enum, utcnow


class CommentKind(enum.StrEnum):
    footer = "footer"
    inline = "inline"


class TargetType(enum.StrEnum):
    node = "node"
    space = "space"
    comment = "comment"


class WatchSource(enum.StrEnum):
    auto = "auto"  # the author follows their page
    manual = "manual"


def _node_fk() -> Mapped[uuid.UUID]:
    return mapped_column(ForeignKey("folio_nodes.id", ondelete="CASCADE"))


def _user_fk(nullable: bool = False) -> Any:
    return mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL" if nullable else "CASCADE"),
        nullable=nullable,
    )


def _now() -> Any:
    return mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now())


class FolioComment(Base):
    """A comment at the foot of a page or anchored to its text (Folio 2.3). A thread is its
    first comment; replies point at it."""

    __tablename__ = "folio_comments"
    __table_args__ = (Index("ix_folio_comments_node", "node_id", "thread_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id: Mapped[uuid.UUID] = _node_fk()
    thread_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("folio_comments.id", ondelete="CASCADE")
    )
    kind: Mapped[CommentKind] = mapped_column(_enum(CommentKind, "folio_comment_kind"))
    author_id: Mapped[uuid.UUID | None] = _user_fk(nullable=True)
    body_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    # Yjs relative positions and the quoted text of an inline comment.
    anchor: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    orphaned: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[uuid.UUID | None] = _user_fk(nullable=True)
    created_at: Mapped[datetime] = _now()
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FolioReaction(Base):
    __tablename__ = "folio_reactions"
    __table_args__ = (PrimaryKeyConstraint("target_type", "target_id", "user_id", "emoji"),)

    target_type: Mapped[TargetType] = mapped_column(_enum(TargetType, "folio_target_type"))
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    user_id: Mapped[uuid.UUID] = _user_fk()
    emoji: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = _now()


class FolioWatch(Base):
    __tablename__ = "folio_watches"
    __table_args__ = (PrimaryKeyConstraint("user_id", "target_type", "target_id"),)

    user_id: Mapped[uuid.UUID] = _user_fk()
    target_type: Mapped[TargetType] = mapped_column(_enum(TargetType, "folio_target_type"))
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    source: Mapped[WatchSource] = mapped_column(_enum(WatchSource, "folio_watch_source"))
    created_at: Mapped[datetime] = _now()


class FolioFavorite(Base):
    __tablename__ = "folio_favorites"
    __table_args__ = (PrimaryKeyConstraint("user_id", "target_type", "target_id"),)

    user_id: Mapped[uuid.UUID] = _user_fk()
    target_type: Mapped[TargetType] = mapped_column(_enum(TargetType, "folio_target_type"))
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = _now()


class FolioActionItem(Base):
    """An action item block, indexed from the document it lives in (Folio 2.4)."""

    __tablename__ = "folio_action_items"
    __table_args__ = (
        UniqueConstraint("node_id", "item_key"),
        Index("ix_folio_action_items_assignee", "assignee_id", "done", "due_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id: Mapped[uuid.UUID] = _node_fk()
    item_key: Mapped[str] = mapped_column(Text)  # the block's stable id in the document
    text: Mapped[str] = mapped_column(Text)
    assignee_id: Mapped[uuid.UUID | None] = _user_fk(nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date)
    done: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    updated_at: Mapped[datetime] = _now()


class FolioView(Base):
    """A read, for recents and the most read."""

    __tablename__ = "folio_views"
    __table_args__ = (
        Index("ix_folio_views_user", "user_id", "viewed_at"),
        Index("ix_folio_views_node", "node_id", "viewed_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    node_id: Mapped[uuid.UUID] = _node_fk()
    user_id: Mapped[uuid.UUID] = _user_fk()
    viewed_at: Mapped[datetime] = _now()


class FolioViewCountDaily(Base):
    __tablename__ = "folio_view_counts_daily"
    __table_args__ = (PrimaryKeyConstraint("node_id", "date"),)

    node_id: Mapped[uuid.UUID] = _node_fk()
    date: Mapped[date] = mapped_column(Date)
    views: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    unique_viewers: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")


class FolioYDoc(Base):
    """The collaborative state of a draft or live doc (Folio 2.2), compacted."""

    __tablename__ = "folio_ydocs"

    node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("folio_nodes.id", ondelete="CASCADE"), primary_key=True
    )
    state: Mapped[bytes] = mapped_column(LargeBinary)
    updated_at: Mapped[datetime] = _now()


class FolioYUpdate(Base):
    """Incremental Yjs updates waiting to be compacted into folio_ydocs."""

    __tablename__ = "folio_yupdates"
    __table_args__ = (Index("ix_folio_yupdates_node", "node_id", "id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    node_id: Mapped[uuid.UUID] = _node_fk()
    update: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = _now()


class FolioLiveSnapshot(Base):
    """A live doc's history: its content every 10 minutes it changed (Folio 2.5)."""

    __tablename__ = "folio_live_snapshots"
    __table_args__ = (Index("ix_folio_live_snapshots_node", "node_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id: Mapped[uuid.UUID] = _node_fk()
    content_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    authors: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)))
    created_at: Mapped[datetime] = _now()
