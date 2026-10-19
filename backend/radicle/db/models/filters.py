import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from radicle.db.models.base import Base, utcnow
from radicle.db.models.projects import _enum
from radicle.db.models.users import User


class FilterVisibility(enum.StrEnum):
    private = "private"
    project = "project"
    instance = "instance"


filter_visibility_enum = _enum(FilterVisibility, "filter_visibility")


class SavedFilter(Base):
    __tablename__ = "saved_filters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(Text)
    rql: Mapped[str] = mapped_column(Text)
    visibility: Mapped[FilterVisibility] = mapped_column(filter_visibility_enum)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )

    owner: Mapped[User] = relationship(lazy="joined")


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    prefs: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
