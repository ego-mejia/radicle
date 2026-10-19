import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column

from radicle.db.models.base import Base, utcnow
from radicle.db.models.projects import ProjectRole, project_role_enum


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(CITEXT, unique=True)
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )


class GroupMember(Base):
    """Humans and agents alike."""

    __tablename__ = "group_members"

    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )


class ProjectGroupRole(Base):
    """A group joins a project with a role; a user's role is the highest of all of theirs."""

    __tablename__ = "project_group_roles"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    role: Mapped[ProjectRole] = mapped_column(project_role_enum)


class ProjectRolePermission(Base):
    """An override of the catalog default for one role in one project."""

    __tablename__ = "project_role_permissions"
    __table_args__ = (Index("ix_project_role_permissions_project", "project_id"),)

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[ProjectRole] = mapped_column(project_role_enum, primary_key=True)
    permission: Mapped[str] = mapped_column(Text, primary_key=True)
    allowed: Mapped[bool] = mapped_column(Boolean)
