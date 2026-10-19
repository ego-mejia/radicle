"""Security levels: per-project restrictions of who sees a ticket."""

import uuid
from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.core.errors import Conflict, NotFound, ValidationFailed
from radicle.db.models import (
    EventType,
    Group,
    Project,
    ProjectRole,
    SecurityLevel,
    SecurityLevelGrant,
    Ticket,
    User,
)
from radicle.services import history
from radicle.services.access import ProjectAccess, project_access

NAME_MAX = 80


def _not_found(level_id: object) -> NotFound:
    return NotFound(f"Security level {level_id} not found.", code="security_level_not_found")


def _name(value: str) -> str:
    name = " ".join(value.split())
    if not 1 <= len(name) <= NAME_MAX:
        raise ValidationFailed(
            f"Security level names are 1 to {NAME_MAX} characters.",
            errors=[{"field": "name", "message": "invalid length"}],
        )
    return name


async def list_levels(db: AsyncSession, project: Project) -> list[SecurityLevel]:
    rows = await db.scalars(
        select(SecurityLevel)
        .where(SecurityLevel.project_id == project.id)
        .order_by(func.lower(SecurityLevel.name))
    )
    return list(rows)


@dataclass(frozen=True)
class Grants:
    groups: list[str]
    users: list[str]


async def grants(db: AsyncSession, level: SecurityLevel) -> Grants:
    groups = await db.scalars(
        select(Group.name)
        .join(SecurityLevelGrant, SecurityLevelGrant.group_id == Group.id)
        .where(SecurityLevelGrant.level_id == level.id)
        .order_by(Group.name)
    )
    users = await db.scalars(
        select(User.handle)
        .join(SecurityLevelGrant, SecurityLevelGrant.user_id == User.id)
        .where(SecurityLevelGrant.level_id == level.id)
        .order_by(User.handle)
    )
    return Grants(list(groups), list(users))


async def ticket_counts(db: AsyncSession, levels: list[SecurityLevel]) -> dict[uuid.UUID, int]:
    if not levels:
        return {}
    rows = await db.execute(
        select(Ticket.security_level_id, func.count())
        .where(Ticket.security_level_id.in_([lv.id for lv in levels]))
        .group_by(Ticket.security_level_id)
    )
    return {lid: int(n) for lid, n in rows if lid is not None}


async def create_level(
    db: AsyncSession,
    access: ProjectAccess,
    *,
    name: str,
    description: str = "",
    include_participants: bool = True,
) -> SecurityLevel:
    name = _name(name)
    await _ensure_unique(db, access.project, name)
    level = SecurityLevel(
        project_id=access.project.id,
        name=name,
        description=description.strip(),
        include_participants=include_participants,
    )
    db.add(level)
    await db.flush()
    return level


async def _ensure_unique(
    db: AsyncSession, project: Project, name: str, skip: uuid.UUID | None = None
) -> None:
    query = select(SecurityLevel.id).where(
        SecurityLevel.project_id == project.id, func.lower(SecurityLevel.name) == name.lower()
    )
    if skip is not None:
        query = query.where(SecurityLevel.id != skip)
    if await db.scalar(query):
        raise Conflict(
            f"{project.key} already has a security level named {name}.", code="level_exists"
        )


async def load_level(
    db: AsyncSession, user: User, level_id: uuid.UUID, *, admin: bool = False
) -> tuple[ProjectAccess, SecurityLevel]:
    level = await db.get(SecurityLevel, level_id)
    if level is None:
        raise _not_found(level_id)
    project = await db.get(Project, level.project_id)
    if project is None:  # pragma: no cover - FK
        raise _not_found(level_id)
    try:
        access = await project_access(
            db,
            user,
            project.key,
            need=ProjectRole.admin if admin else ProjectRole.viewer,
            write=admin,
        )
    except NotFound:
        raise _not_found(level_id) from None
    return access, level


async def update_level(
    db: AsyncSession,
    level: SecurityLevel,
    project: Project,
    *,
    name: str | None,
    description: str | None,
    include_participants: bool | None,
) -> SecurityLevel:
    if name is not None:
        name = _name(name)
        await _ensure_unique(db, project, name, skip=level.id)
        level.name = name
    if description is not None:
        level.description = description.strip()
    if include_participants is not None:
        level.include_participants = include_participants
    await db.flush()
    return level


async def delete_level(db: AsyncSession, level: SecurityLevel) -> None:
    used = await db.scalar(select(func.count()).where(Ticket.security_level_id == level.id))
    if used:
        raise Conflict(
            f"{used} tickets use '{level.name}'. Remove the level from them first.",
            code="level_in_use",
        )
    await db.delete(level)
    await db.flush()


async def set_grants(
    db: AsyncSession, level: SecurityLevel, *, groups: list[str], users: list[str]
) -> Grants:
    group_rows = list(await db.scalars(select(Group).where(Group.name.in_(groups))))
    missing = sorted(set(g.lower() for g in groups) - {g.name.lower() for g in group_rows})
    if missing:
        raise ValidationFailed(
            f"Unknown groups: {', '.join(missing)}.",
            errors=[{"field": "groups", "message": "unknown"}],
        )
    handles = [u.lstrip("@").lower() for u in users]
    user_rows = list(await db.scalars(select(User).where(User.handle.in_(handles))))
    missing = sorted(set(handles) - {u.handle for u in user_rows})
    if missing:
        raise ValidationFailed(
            f"Unknown users: {', '.join('@' + h for h in missing)}.",
            errors=[{"field": "users", "message": "unknown"}],
        )
    await db.execute(delete(SecurityLevelGrant).where(SecurityLevelGrant.level_id == level.id))
    for g in group_rows:
        db.add(SecurityLevelGrant(level_id=level.id, group_id=g.id))
    for u in user_rows:
        db.add(SecurityLevelGrant(level_id=level.id, user_id=u.id))
    await db.flush()
    return await grants(db, level)


async def find_level(db: AsyncSession, project: Project, value: str) -> SecurityLevel:
    """By name (or id) within the project."""
    query = select(SecurityLevel).where(SecurityLevel.project_id == project.id)
    try:
        level = await db.scalar(query.where(SecurityLevel.id == uuid.UUID(value)))
    except ValueError:
        level = await db.scalar(query.where(func.lower(SecurityLevel.name) == value.lower()))
    if level is None:
        names = [lv.name for lv in await list_levels(db, project)]
        raise ValidationFailed(
            f"{project.key} has no security level '{value}'. Levels: "
            f"{', '.join(names) or 'none yet'}.",
            errors=[{"field": "security_level", "message": "unknown"}],
        )
    return level


async def set_ticket_level(
    db: AsyncSession, access: ProjectAccess, ticket: Ticket, value: str | None
) -> tuple[str | None, str | None] | None:
    """Put or take away a ticket's level (needs ticket.set_security). Returns (old, new)
    names when it changed."""
    access.require("ticket.set_security")
    level = await find_level(db, access.project, value) if value else None
    new_id = level.id if level else None
    if new_id == ticket.security_level_id:
        return None
    old = (
        await db.get(SecurityLevel, ticket.security_level_id) if ticket.security_level_id else None
    )
    ticket.security_level_id = new_id
    history.record(
        db,
        ticket,
        access.user,
        EventType.field_changed,
        field="security_level",
        old=old.name if old else None,
        new=level.name if level else None,
    )
    await db.flush()
    return (old.name if old else None, level.name if level else None)
