"""Folio's tables, all prefixed `folio_` (Folio control document)."""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, CITEXT, JSONB, UUID
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
    published_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("folio_versions.id", name="fk_folio_nodes_published_version", use_alter=True)
    )
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


class FolioDraft(Base):
    """The live draft of a page or blog post: one per node, saved as you type."""

    __tablename__ = "folio_drafts"

    node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("folio_nodes.id", ondelete="CASCADE"), primary_key=True
    )
    content_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    # May be incomplete; publishing validates it.
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}"
    )
    # The published version this draft started from (set by publishing, Folio 1.3).
    base_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )


class FolioAsset(Base):
    """An image, file or video uploaded to a page, kept in the shared storage."""

    __tablename__ = "folio_assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("folio_nodes.id", ondelete="SET NULL"), index=True
    )
    uploader_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    filename: Mapped[str] = mapped_column(Text)
    mime_type: Mapped[str] = mapped_column(Text)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    storage_key: Mapped[str] = mapped_column(Text)
    width: Mapped[int | None] = mapped_column(BigInteger)
    height: Mapped[int | None] = mapped_column(BigInteger)
    variants: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )


class _CatalogEntry:
    """Shape shared by the editable catalogs: document types, audiences and languages."""

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    position: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FolioDocType(_CatalogEntry, Base):
    __tablename__ = "folio_doc_types"


class FolioAudience(_CatalogEntry, Base):
    __tablename__ = "folio_audiences"


class FolioLanguage(_CatalogEntry, Base):
    __tablename__ = "folio_languages"


class FolioVersion(Base):
    """A published version. Insert only: a database trigger rejects changes, and restoring
    an old version creates a new one."""

    __tablename__ = "folio_versions"
    __table_args__ = (UniqueConstraint("node_id", "number", name="uq_folio_versions_number"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("folio_nodes.id"), index=True)
    number: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(Text)
    content_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    content_md: Mapped[str] = mapped_column(Text)
    content_text: Mapped[str] = mapped_column(Text)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB)
    change_note: Mapped[str | None] = mapped_column(Text)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    restored_from: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("folio_versions.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )


class FolioNodeLabel(Base):
    """Labels of the published version, for filters, RQL and the RAG metadata."""

    __tablename__ = "folio_node_labels"

    node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("folio_nodes.id", ondelete="CASCADE"), primary_key=True
    )
    label: Mapped[str] = mapped_column(Text, primary_key=True, index=True)


class SpacePermission(enum.StrEnum):
    view = "view"
    create = "create"
    comment = "comment"
    delete_own = "delete_own"
    delete_any = "delete_any"
    admin = "admin"
    export = "export"


class FolioSpaceGrant(Base):
    """What a user, a group or everyone may do in a space. `admin` includes everything."""

    __tablename__ = "folio_space_grants"
    __table_args__ = (
        Index(
            "ux_folio_space_grants_grantee",
            "space_id",
            "grantee_type",
            text("coalesce(grantee_id, '00000000-0000-0000-0000-000000000000'::uuid)"),
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    space_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("folio_spaces.id", ondelete="CASCADE"), index=True
    )
    grantee_type: Mapped[GranteeType] = mapped_column(_enum(GranteeType, "folio_grantee_type"))
    grantee_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    permissions: Mapped[list[str]] = mapped_column(ARRAY(Text))


class RestrictionMode(enum.StrEnum):
    view = "view"
    edit = "edit"


class FolioPageRestriction(Base):
    """Who may see (inherited by every descendant) or edit (this node only) a page. Without
    restrictions of a mode, the space's permissions decide."""

    __tablename__ = "folio_page_restrictions"
    __table_args__ = (
        Index(
            "ux_folio_page_restrictions",
            "node_id",
            "mode",
            "grantee_type",
            "grantee_id",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("folio_nodes.id", ondelete="CASCADE"), index=True
    )
    mode: Mapped[RestrictionMode] = mapped_column(_enum(RestrictionMode, "folio_restriction_mode"))
    # user or group; never everyone (that would be no restriction at all)
    grantee_type: Mapped[GranteeType] = mapped_column(_enum(GranteeType, "folio_grantee_type"))
    grantee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))


class SubmissionStatus(enum.StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    superseded = "superseded"


class FolioSubmission(Base):
    """An agent's proposed version, waiting for a Folio or space admin to approve it."""

    __tablename__ = "folio_submissions"
    __table_args__ = (Index("ix_folio_submissions_status", "status", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("folio_nodes.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(Text)
    content_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB)
    change_note: Mapped[str | None] = mapped_column(Text)
    submitted_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    status: Mapped[SubmissionStatus] = mapped_column(
        _enum(SubmissionStatus, "folio_submission_status"), default=SubmissionStatus.pending
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    review_comment: Mapped[str | None] = mapped_column(Text)
    version_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("folio_versions.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
