"""Groups in projects: a group joins a project with a role."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.db.models import Group, Project, ProjectGroupRole, ProjectRole
from radicle.platform.errors import ValidationFailed
from radicle.services.access import ProjectAccess


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
