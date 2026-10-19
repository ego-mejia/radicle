import enum
import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, CITEXT, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from radicle.db.models.base import Base, utcnow
from radicle.db.models.users import User


class ProjectRole(enum.StrEnum):
    admin = "admin"
    member = "member"
    viewer = "viewer"


class TicketType(enum.StrEnum):
    task = "task"
    bug = "bug"
    draft = "draft"


class StatusCategory(enum.StrEnum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


class Resolution(enum.StrEnum):
    done = "done"
    wont_do = "wont_do"
    duplicate = "duplicate"
    cannot_reproduce = "cannot_reproduce"


class TemplateMode(enum.StrEnum):
    linked = "linked"
    detached = "detached"


class BlockedPolicy(enum.StrEnum):
    warn = "warn"
    enforce = "enforce"


class RuleKind(enum.StrEnum):
    condition = "condition"
    validator = "validator"
    post_function = "post_function"


class MilestoneStatus(enum.StrEnum):
    open = "open"
    closed = "closed"


def _enum[E: enum.Enum](cls: type[E], name: str) -> Enum:
    return Enum(cls, name=name, values_callable=lambda e: [m.value for m in e])


project_role_enum = _enum(ProjectRole, "project_role")
ticket_type_enum = _enum(TicketType, "ticket_type")
status_category_enum = _enum(StatusCategory, "status_category")
resolution_enum = _enum(Resolution, "resolution")
milestone_status_enum = _enum(MilestoneStatus, "milestone_status")
template_mode_enum = _enum(TemplateMode, "template_mode")
blocked_policy_enum = _enum(BlockedPolicy, "blocked_policy")
rule_kind_enum = _enum(RuleKind, "rule_kind")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(CITEXT, unique=True)
    name: Mapped[str] = mapped_column(Text)
    description_md: Mapped[str] = mapped_column(Text, default="", server_default="")
    ticket_seq: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), onupdate=utcnow
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("templates.id", ondelete="SET NULL")
    )
    template_mode: Mapped[TemplateMode | None] = mapped_column(template_mode_enum)
    template_version: Mapped[int | None] = mapped_column(Integer)
    blocked_policy: Mapped[BlockedPolicy] = mapped_column(
        blocked_policy_enum, default=BlockedPolicy.warn, server_default="warn"
    )
    # Tags offered by autocompletion; templates add to it.
    suggested_tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}"
    )


class ProjectMember(Base):
    __tablename__ = "project_members"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    role: Mapped[ProjectRole] = mapped_column(project_role_enum)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )

    user: Mapped[User] = relationship(lazy="joined")


class Area(Base):
    __tablename__ = "areas"
    __table_args__ = (
        Index("uq_areas_project_name", "project_id", func.lower("name"), unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(Text)
    color: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, default=0)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )


class Milestone(Base):
    __tablename__ = "milestones"
    __table_args__ = (
        Index("uq_milestones_project_name", "project_id", func.lower("name"), unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(Text)
    description_md: Mapped[str] = mapped_column(Text, default="", server_default="")
    target_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[MilestoneStatus] = mapped_column(
        milestone_status_enum, default=MilestoneStatus.open, server_default="open"
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )


class Status(Base):
    __tablename__ = "statuses"
    __table_args__ = (
        Index(
            "uq_statuses_project_type_name",
            "project_id",
            "ticket_type",
            func.lower("name"),
            unique=True,
        ),
        Index(
            "uq_statuses_initial",
            "project_id",
            "ticket_type",
            unique=True,
            postgresql_where="is_initial",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    ticket_type: Mapped[TicketType] = mapped_column(ticket_type_enum)
    name: Mapped[str] = mapped_column(Text)
    category: Mapped[StatusCategory] = mapped_column(status_category_enum)
    position: Mapped[int] = mapped_column(Integer)
    is_initial: Mapped[bool] = mapped_column(Boolean, default=False)
    # Stable slug shared with the template, so a rename is still the same status.
    template_ref: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )


class Transition(Base):
    __tablename__ = "transitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    ticket_type: Mapped[TicketType] = mapped_column(ticket_type_enum)
    name: Mapped[str] = mapped_column(Text)
    # None means "from any status that is not in the done category".
    from_status_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("statuses.id", ondelete="CASCADE")
    )
    to_status_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("statuses.id", ondelete="CASCADE"))
    # None means every resolution; only relevant when the target is a done status.
    allowed_resolutions: Mapped[list[Resolution] | None] = mapped_column(ARRAY(resolution_enum))
    position: Mapped[int] = mapped_column(Integer)
    template_ref: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )


class TransitionRule(Base):
    """A condition, validator or post-function attached to one transition."""

    __tablename__ = "transition_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("transitions.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[RuleKind] = mapped_column(rule_kind_enum)
    rule_type: Mapped[str] = mapped_column(Text)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    position: Mapped[int] = mapped_column(Integer)
