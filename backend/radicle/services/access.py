"""Project-level permissions shared by REST and MCP.

Non-members get 404 for everything in a project, never 403, so a project's existence
is not revealed. Instance admins act as project admins everywhere.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.core.errors import Conflict, Forbidden, NotFound
from radicle.db.models import Project, ProjectMember, ProjectRole, User

ROLE_RANK = {ProjectRole.viewer: 0, ProjectRole.member: 1, ProjectRole.admin: 2}

_NEEDS = {
    ProjectRole.viewer: "view it",
    ProjectRole.member: "the member or admin role",
    ProjectRole.admin: "the admin role",
}


@dataclass(frozen=True)
class ProjectAccess:
    project: Project
    role: ProjectRole
    user: User

    def at_least(self, role: ProjectRole) -> bool:
        return ROLE_RANK[self.role] >= ROLE_RANK[role]


def project_not_found(key: str) -> NotFound:
    return NotFound(f"Project {key.upper()} not found.", code="project_not_found")


async def role_in(db: AsyncSession, user: User, project: Project) -> ProjectRole | None:
    if user.is_instance_admin:
        return ProjectRole.admin
    role = await db.scalar(
        select(ProjectMember.role).where(
            ProjectMember.project_id == project.id, ProjectMember.user_id == user.id
        )
    )
    return role


async def project_access(
    db: AsyncSession,
    user: User,
    key: str,
    *,
    need: ProjectRole = ProjectRole.viewer,
    write: bool = False,
) -> ProjectAccess:
    """Load a project by key and check the user's role in it.

    `write=True` also rejects changes to archived projects, which are read-only.
    """
    project = await db.scalar(select(Project).where(Project.key == key))
    if project is None:
        raise project_not_found(key)
    return check_access(project, await role_in(db, user, project), user, need=need, write=write)


def check_access(
    project: Project,
    role: ProjectRole | None,
    user: User,
    *,
    need: ProjectRole = ProjectRole.viewer,
    write: bool = False,
) -> ProjectAccess:
    if role is None:
        raise project_not_found(project.key)
    if ROLE_RANK[role] < ROLE_RANK[need]:
        raise Forbidden(
            f"Your role in {project.key} is {role.value}; this action needs {_NEEDS[need]}.",
            code="insufficient_role",
        )
    if write and project.archived_at is not None:
        raise Conflict(
            f"Project {project.key} is archived and read-only. Unarchive it to make changes.",
            code="project_archived",
        )
    return ProjectAccess(project=project, role=role, user=user)
