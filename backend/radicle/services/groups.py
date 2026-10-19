"""Groups of users (humans and agents) that join projects with a role."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.core.errors import Conflict, NotFound, ValidationFailed
from radicle.db.models import (
    Group,
    GroupMember,
    Project,
    ProjectGroupRole,
    ProjectRole,
    User,
)
from radicle.services import users as users_service
from radicle.services.access import ProjectAccess

NAME_MAX = 80


def _name(value: str) -> str:
    name = value.strip()
    if not 1 <= len(name) <= NAME_MAX or any(c.isspace() for c in name):
        raise ValidationFailed(
            f"Group names are 1 to {NAME_MAX} characters without spaces, e.g. equipo-legal.",
            errors=[{"field": "name", "message": "invalid"}],
        )
    return name


async def list_groups(db: AsyncSession) -> list[Group]:
    return list(await db.scalars(select(Group).order_by(func.lower(Group.name))))


async def get_group(db: AsyncSession, name: str) -> Group:
    group = await db.scalar(select(Group).where(Group.name == name))
    if group is None:
        raise NotFound(f"Group {name} not found.", code="group_not_found")
    return group


async def create_group(db: AsyncSession, name: str, description: str = "") -> Group:
    name = _name(name)
    if await db.scalar(select(Group.id).where(Group.name == name)):
        raise Conflict(f"A group named {name} already exists.", code="group_exists")
    group = Group(name=name, description=description.strip())
    db.add(group)
    await db.flush()
    return group


async def update_group(
    db: AsyncSession, group: Group, *, name: str | None, description: str | None
) -> Group:
    if name is not None and name != group.name:
        name = _name(name)
        if await db.scalar(select(Group.id).where(Group.name == name, Group.id != group.id)):
            raise Conflict(f"A group named {name} already exists.", code="group_exists")
        group.name = name
    if description is not None:
        group.description = description.strip()
    await db.flush()
    return group


async def members(db: AsyncSession, group: Group) -> list[User]:
    rows = await db.scalars(
        select(User)
        .join(GroupMember, GroupMember.user_id == User.id)
        .where(GroupMember.group_id == group.id)
        .order_by(User.handle)
    )
    return list(rows)


async def member_counts(db: AsyncSession) -> dict[uuid.UUID, int]:
    rows = await db.execute(
        select(GroupMember.group_id, func.count()).group_by(GroupMember.group_id)
    )
    return {g: int(n) for g, n in rows}


async def add_member(db: AsyncSession, group: Group, handle: str) -> User:
    user = await users_service.get_by_handle(db, handle)
    if not user.is_active:
        raise ValidationFailed(
            f"@{user.handle} is deactivated and cannot join groups.", code="user_inactive"
        )
    if await db.get(GroupMember, (group.id, user.id)) is None:
        db.add(GroupMember(group_id=group.id, user_id=user.id))
        await db.flush()
    return user


async def remove_member(db: AsyncSession, group: Group, handle: str) -> User:
    user = await users_service.get_by_handle(db, handle)
    row = await db.get(GroupMember, (group.id, user.id))
    if row is None:
        raise ValidationFailed(f"@{user.handle} is not in {group.name}.", code="not_in_group")
    await db.delete(row)
    await db.flush()
    return user


# --- groups in projects --------------------------------------------------------------------


async def project_groups(db: AsyncSession, project: Project) -> list[tuple[Group, ProjectRole]]:
    rows = await db.execute(
        select(Group, ProjectGroupRole.role)
        .join(ProjectGroupRole, ProjectGroupRole.group_id == Group.id)
        .where(ProjectGroupRole.project_id == project.id)
        .order_by(func.lower(Group.name))
    )
    return [(g, r) for g, r in rows]


async def set_group_role(
    db: AsyncSession, access: ProjectAccess, group: Group, role: ProjectRole
) -> ProjectRole | None:
    """Returns the previous role (None if the group was not in the project)."""
    row = await db.get(ProjectGroupRole, (access.project.id, group.id))
    previous = row.role if row else None
    if row is None:
        db.add(ProjectGroupRole(project_id=access.project.id, group_id=group.id, role=role))
    else:
        row.role = role
    await db.flush()
    return previous


async def remove_group_role(db: AsyncSession, access: ProjectAccess, group: Group) -> ProjectRole:
    row = await db.get(ProjectGroupRole, (access.project.id, group.id))
    if row is None:
        raise ValidationFailed(
            f"Group {group.name} is not in {access.project.key}.", code="group_not_in_project"
        )
    role = row.role
    await db.delete(row)
    await db.flush()
    return role


async def delete_group(db: AsyncSession, group: Group) -> None:
    await db.delete(group)
    await db.flush()
