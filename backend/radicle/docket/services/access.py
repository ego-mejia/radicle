"""Project-level access shared by REST and MCP; the rules live in `core.permissions`.

Non-members get 404 for everything in a project, never 403, so a project's existence
is not revealed. Instance admins act as project admins everywhere.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.docket.core.permissions import (
    ROLE_RANK,
    ProjectAccess,
    authorize,
    check_access,
    effective_role,
    project_not_found,
)
from radicle.docket.db.models import Project, ProjectRole, User

__all__ = [
    "ROLE_RANK",
    "ProjectAccess",
    "access_for",
    "check_access",
    "project_access",
    "project_not_found",
    "role_in",
]


async def role_in(db: AsyncSession, user: User, project: Project) -> ProjectRole | None:
    """Effective role: direct membership or groups, the highest one."""
    return await effective_role(db, user, project)


async def access_for(
    db: AsyncSession,
    user: User,
    project: Project,
    *,
    need: ProjectRole = ProjectRole.viewer,
    write: bool = False,
    permission: str | None = None,
) -> ProjectAccess:
    return await authorize(db, user, permission, project, need=need, write=write)


async def project_access(
    db: AsyncSession,
    user: User,
    key: str,
    *,
    need: ProjectRole = ProjectRole.viewer,
    write: bool = False,
    permission: str | None = None,
) -> ProjectAccess:
    """Load a project by key and check the user may see it (and do `permission`).

    `write=True` also rejects changes to archived projects, which are read-only.
    """
    project = await db.scalar(select(Project).where(Project.key == key))
    if project is None:
        raise project_not_found(key)
    return await access_for(db, user, project, need=need, write=write, permission=permission)
