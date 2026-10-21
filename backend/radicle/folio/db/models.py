"""Folio's tables, all prefixed `folio_` (Folio control document)."""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Text, func, text
from sqlalchemy.dialects.postgresql import CITEXT, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from radicle.platform.db.models.base import Base, _enum, utcnow


class GranteeType(enum.StrEnum):
    user = "user"
    group = "group"
    everyone = "everyone"


class FolioRole(enum.StrEnum):
    reader = "reader"
    creator = "creator"
    admin = "admin"


ROLE_RANK = {FolioRole.reader: 0, FolioRole.creator: 1, FolioRole.admin: 2}


class FolioGlobalGrant(Base):
    """A global Folio role for a user, a group or everyone. One grant per grantee."""

    __tablename__ = "folio_global_grants"
    __table_args__ = (
        Index(
            "ux_folio_global_grants_grantee",
            "grantee_type",
            text("coalesce(grantee_id, '00000000-0000-0000-0000-000000000000'::uuid)"),
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    grantee_type: Mapped[GranteeType] = mapped_column(_enum(GranteeType, "folio_grantee_type"))
    # A user's or group's id; null for everyone.
    grantee_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    role: Mapped[FolioRole] = mapped_column(_enum(FolioRole, "folio_role"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )


class SpaceKind(enum.StrEnum):
    team = "team"
    personal = "personal"


class NodeKind(enum.StrEnum):
    page = "page"
    folder = "folder"
    blog_post = "blog_post"


class FolioSpace(Base):
    """A team's or a person's space. Its key goes in the URL."""

    __tablename__ = "folio_spaces"
    __table_args__ = (
        # One personal space per user.
        Index(
            "ux_folio_spaces_personal_owner",
            "owner_id",
            unique=True,
            postgresql_where=text("kind = 'personal'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(CITEXT, unique=True)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    kind: Mapped[SpaceKind] = mapped_column(_enum(SpaceKind, "folio_space_kind"))
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    icon: Mapped[str | None] = mapped_column(Text)
    cover_asset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FolioNode(Base):
    """Everything in a space: pages and folders form a tree; blog posts sit outside it."""

    __tablename__ = "folio_nodes"
    __table_args__ = (
        Index("ix_folio_nodes_space_parent_rank", "space_id", "parent_id", "rank"),
        Index("ix_folio_nodes_space_published", "space_id", "published_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    space_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("folio_spaces.id", ondelete="CASCADE"), index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("folio_nodes.id", ondelete="CASCADE")
    )
    kind: Mapped[NodeKind] = mapped_column(_enum(NodeKind, "folio_node_kind"))
    title: Mapped[str] = mapped_column(Text)
    # Derived from the title and not unique: URLs use <id>-<slug>.
    slug: Mapped[str] = mapped_column(Text)
    icon: Mapped[str | None] = mapped_column(Text)
    cover_asset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    # Byte order, as fractional ranks expect, whatever the database locale.
    rank: Mapped[str] = mapped_column(Text(collation="C"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FolioNodeEvent(Base):
    """A node's history. Append only: a database trigger rejects changes."""

    __tablename__ = "folio_node_events"
    __table_args__ = (Index("ix_folio_node_events_node_id_id", "node_id", "id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # No cascades: the trigger would reject them, and nodes are only ever soft deleted.
    node_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("folio_nodes.id"))
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    event_type: Mapped[str] = mapped_column(Text)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
