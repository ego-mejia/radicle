import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from radicle.db.models.projects import ProjectRole, project_role_enum
from radicle.platform.db.models.base import Base, utcnow


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


class SecurityLevel(Base):
    """Restricts who sees a ticket: its grants, the project's admins and, optionally, the
    ticket's participants."""

    __tablename__ = "security_levels"
    __table_args__ = (
        Index("uq_security_levels_project_name", "project_id", func.lower("name"), unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    include_participants: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )


class SecurityLevelGrant(Base):
    """A group or a user who may see the level's tickets (exactly one of the two)."""

    __tablename__ = "security_level_grants"
    __table_args__ = (
        CheckConstraint(
            "(group_id IS NULL) <> (user_id IS NULL)", name="ck_security_level_grants_one"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    level_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("security_levels.id", ondelete="CASCADE"), index=True
    )
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
