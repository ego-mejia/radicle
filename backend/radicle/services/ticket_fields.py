"""Validation of ticket fields and lookup of the things they reference by name."""

import re
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.db.models import (
    Area,
    Milestone,
    MilestoneStatus,
    Project,
    ProjectMember,
    ProjectRole,
    Ticket,
    TicketType,
    User,
)
from radicle.platform.errors import NotFound, ValidationFailed
from radicle.services.access import ROLE_RANK

TITLE_MAX = 255
DESCRIPTION_MAX = 200_000
TAG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,49}$")
TAGS_MAX = 20
KEY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9]{1,9})-(\d{1,9})$")
ESTIMATE_MAX = Decimal("9999")


def invalid(field: str, message: str, detail: str) -> ValidationFailed:
    return ValidationFailed(detail, errors=[{"field": field, "message": message}])


def parse_key(key: str) -> tuple[str, int]:
    match = KEY_RE.fullmatch(key.strip())
    if not match:
        raise NotFound(
            f"Ticket '{key}' not found. Ticket keys look like PA-12.", code="ticket_not_found"
        )
    return match.group(1).upper(), int(match.group(2))


def normalize_title(title: str) -> str:
    value = title.strip()
    if "\n" in value or "\r" in value:
        raise invalid("title", "no line breaks", "Title cannot contain line breaks.")
    if not 1 <= len(value) <= TITLE_MAX:
        raise invalid("title", "invalid length", f"Title must be 1 to {TITLE_MAX} characters.")
    return value


def check_description(text_md: str) -> str:
    if len(text_md) > DESCRIPTION_MAX:
        raise invalid(
            "description_md", "too long", f"Description must be at most {DESCRIPTION_MAX} chars."
        )
    return text_md


def normalize_tags(tags: list[str]) -> list[str]:
    result: list[str] = []
    for raw in tags:
        tag = raw.strip().lstrip("#").lower()
        if not TAG_RE.fullmatch(tag):
            raise invalid(
                "tags",
                "invalid tag",
                f"Invalid tag '{raw}'. Tags are 1 to 50 chars: lowercase letters, digits, "
                "'-' or '_', starting with a letter or digit.",
            )
        if tag not in result:
            result.append(tag)
    if len(result) > TAGS_MAX:
        raise invalid("tags", "too many", f"A ticket can have at most {TAGS_MAX} tags.")
    return result


def normalize_estimate(value: float | Decimal | str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        estimate = Decimal(str(value)).quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise invalid("estimate_hours", "not a number", "estimate_hours must be a number.") from exc
    if not Decimal(0) <= estimate <= ESTIMATE_MAX:
        raise invalid(
            "estimate_hours", "out of range", "estimate_hours must be between 0 and 9999."
        )
    return estimate


def require_area(ticket_type: TicketType, area: Area | None) -> None:
    if area is None and ticket_type is not TicketType.draft:
        raise invalid(
            "area",
            "required",
            f"Area is required for {ticket_type.value} tickets (only drafts may omit it).",
        )


async def resolve_area(db: AsyncSession, project: Project, name: str) -> Area:
    area = await db.scalar(
        select(Area).where(
            Area.project_id == project.id, func.lower(Area.name) == name.strip().lower()
        )
    )
    if area is None or area.archived_at is not None:
        names = await db.scalars(
            select(Area.name)
            .where(Area.project_id == project.id, Area.archived_at.is_(None))
            .order_by(Area.position)
        )
        options = ", ".join(names) or "none yet"
        state = "is archived" if area is not None else "does not exist"
        raise invalid(
            "area",
            "unknown",
            f"Area '{name}' {state} in {project.key}. Valid areas: {options}.",
        )
    return area


async def resolve_milestone(db: AsyncSession, project: Project, name: str) -> Milestone:
    milestone = await db.scalar(
        select(Milestone).where(
            Milestone.project_id == project.id,
            func.lower(Milestone.name) == name.strip().lower(),
        )
    )
    if milestone is None or milestone.status is not MilestoneStatus.open:
        names = await db.scalars(
            select(Milestone.name).where(
                Milestone.project_id == project.id, Milestone.status == MilestoneStatus.open
            )
        )
        options = ", ".join(names) or "none"
        state = "is closed" if milestone is not None else "does not exist"
        raise invalid(
            "milestone",
            "unknown",
            f"Milestone '{name}' {state} in {project.key}. Open milestones: {options}.",
        )
    return milestone


async def resolve_assignable(
    db: AsyncSession, project: Project, handle: str, *, field: str
) -> User:
    """Assignees and collaborators must be active members with role member or admin."""
    value = handle.strip().lstrip("@").lower()
    user = await db.scalar(select(User).where(User.handle == value))
    if user is None:
        raise invalid(field, "unknown user", f"User @{value} does not exist.")
    role = await db.scalar(
        select(ProjectMember.role).where(
            ProjectMember.project_id == project.id, ProjectMember.user_id == user.id
        )
    )
    if role is None and user.is_instance_admin:
        role = ProjectRole.admin
    if not user.is_active or role is None or ROLE_RANK[role] < ROLE_RANK[ProjectRole.member]:
        raise invalid(
            field,
            "not assignable",
            f"@{value} cannot be {field.rstrip('s')} in {project.key}: only active members "
            "with role member or admin can.",
        )
    return user


async def resolve_parent(
    db: AsyncSession, project: Project, key: str, *, child: Ticket | None = None
) -> Ticket:
    project_key, number = parse_key(key)
    parent = await db.scalar(
        select(Ticket).where(
            Ticket.project_id == project.id,
            Ticket.number == number,
            Ticket.deleted_at.is_(None),
        )
    )
    if parent is None or project_key != project.key.upper():
        raise invalid(
            "parent", "unknown", f"Parent {key.upper()} must be a ticket in {project.key}."
        )
    if child is not None and await _is_ancestor_or_self(db, child.id, parent.id):
        raise invalid(
            "parent",
            "cycle",
            f"{key.upper()} cannot be the parent: it is this ticket or one of its subtickets.",
        )
    return parent


async def _is_ancestor_or_self(db: AsyncSession, ancestor: uuid.UUID, node: uuid.UUID) -> bool:
    """True if `ancestor` is `node` or appears in node's parent chain."""
    found = await db.scalar(
        text(
            """
            WITH RECURSIVE chain(id, parent_id) AS (
              SELECT id, parent_id FROM tickets WHERE id = :node
              UNION
              SELECT t.id, t.parent_id FROM tickets t JOIN chain c ON t.id = c.parent_id
            )
            SELECT EXISTS (SELECT 1 FROM chain WHERE id = :ancestor)
            """
        ),
        {"node": node, "ancestor": ancestor},
    )
    return bool(found)


def iso(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def estimate_json(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None
