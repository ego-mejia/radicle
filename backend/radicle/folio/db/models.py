"""Folio's tables, all prefixed `folio_` (Folio control document)."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, func, text
from sqlalchemy.dialects.postgresql import UUID
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
