"""Who may do what in a project. Every check goes through `authorize`.

The three roles stay (admin, member, viewer); each project can change what member and
viewer may do. Admins may do everything. A user's role is the highest of their direct
membership and the roles of their groups; instance admins are admins everywhere.
"""

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import ColumnElement, and_, exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.db.models import (
    GroupMember,
    Project,
    ProjectGroupRole,
    ProjectMember,
    ProjectRole,
    ProjectRolePermission,
    SecurityLevel,
    SecurityLevelGrant,
    Ticket,
    TicketCollaborator,
    User,
)
from radicle.platform.errors import Conflict, Forbidden, NotFound

ROLE_RANK = {ProjectRole.viewer: 0, ProjectRole.member: 1, ProjectRole.admin: 2}

# permission -> (member by default, viewer by default)
CATALOG: dict[str, tuple[bool, bool]] = {
    "ticket.create": (True, False),
    "ticket.edit": (True, False),
    "ticket.transition": (True, False),
    "ticket.delete": (False, False),
    "ticket.move": (False, False),
    "ticket.bulk_edit": (True, False),
    "ticket.set_security": (False, False),
    "comment.create": (True, False),
    "comment.delete_any": (False, False),
    "attachment.upload": (True, False),
    "attachment.delete_any": (False, False),
    "worklog.create": (True, False),
    "worklog.edit_any": (False, False),
    "vote": (True, True),
    "link.manage": (True, False),
    "sprint.manage": (False, False),
    "board.manage": (False, False),
    "inbox.triage": (True, False),
    "project.settings": (False, False),
    "members.manage": (False, False),
}
PERMISSIONS = tuple(CATALOG)
EDITABLE_ROLES = (ProjectRole.member, ProjectRole.viewer)


def default_allowed(role: ProjectRole, permission: str) -> bool:
    if role is ProjectRole.admin:
        return True
    member, viewer = CATALOG[permission]
    return member if role is ProjectRole.member else viewer


def highest(roles: Iterable[ProjectRole | None]) -> ProjectRole | None:
    known = [r for r in roles if r is not None]
    return max(known, key=lambda r: ROLE_RANK[r]) if known else None


async def effective_role(db: AsyncSession, user: User, project: Project) -> ProjectRole | None:
    """The highest of the direct role and the roles of the user's groups; None = no access."""
    if user.is_instance_admin:
        return ProjectRole.admin
    direct = await db.scalar(
        select(ProjectMember.role).where(
            ProjectMember.project_id == project.id, ProjectMember.user_id == user.id
        )
    )
    via_groups = await db.scalars(
        select(ProjectGroupRole.role)
        .join(GroupMember, GroupMember.group_id == ProjectGroupRole.group_id)
        .where(ProjectGroupRole.project_id == project.id, GroupMember.user_id == user.id)
    )
    return highest([direct, *via_groups])


async def matrix(db: AsyncSession, project_id: uuid.UUID) -> dict[tuple[ProjectRole, str], bool]:
    """Overrides of this project: (role, permission) -> allowed."""
    rows = await db.execute(
        select(
            ProjectRolePermission.role,
            ProjectRolePermission.permission,
            ProjectRolePermission.allowed,
        ).where(ProjectRolePermission.project_id == project_id)
    )
    return {(role, perm): allowed for role, perm, allowed in rows}


async def permissions_for(
    db: AsyncSession, project: Project, role: ProjectRole | None
) -> frozenset[str]:
    if role is None:
        return frozenset()
    if role is ProjectRole.admin:
        return frozenset(PERMISSIONS)
    overrides = await matrix(db, project.id)
    return frozenset(p for p in PERMISSIONS if overrides.get((role, p), default_allowed(role, p)))


DESCRIPTIONS = {
    "ticket.create": "create tickets",
    "ticket.edit": "edit tickets",
    "ticket.transition": "move tickets between statuses",
    "ticket.delete": "delete tickets",
    "ticket.move": "move tickets to another project",
    "ticket.bulk_edit": "edit many tickets at once",
    "ticket.set_security": "change a ticket's security level",
    "comment.create": "comment",
    "comment.delete_any": "delete other people's comments",
    "attachment.upload": "attach files",
    "attachment.delete_any": "delete other people's files",
    "worklog.create": "log time",
    "worklog.edit_any": "edit other people's time",
    "vote": "vote",
    "link.manage": "link tickets",
    "sprint.manage": "manage sprints",
    "board.manage": "manage boards",
    "inbox.triage": "triage the inbox",
    "project.settings": "change project settings",
    "members.manage": "manage members",
}

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
    permissions: frozenset[str] = frozenset()

    def at_least(self, role: ProjectRole) -> bool:
        return ROLE_RANK[self.role] >= ROLE_RANK[role]

    def can(self, permission: str) -> bool:
        return permission in self.permissions

    def require(self, permission: str) -> None:
        if not self.can(permission):
            raise denied(self.project, self.role, permission)


def denied(project: Project, role: ProjectRole, permission: str) -> Forbidden:
    return Forbidden(
        f"You cannot {DESCRIPTIONS[permission]} in {project.key}: the '{permission}' permission "
        f"is off for the {role.value} role. A project admin can change it in Settings, "
        "Permissions.",
        code="permission_denied",
        extra={"permission": permission},
    )


def project_not_found(key: str) -> NotFound:
    return NotFound(f"Project {key.upper()} not found.", code="project_not_found")


def check_access(
    project: Project,
    role: ProjectRole | None,
    user: User,
    *,
    need: ProjectRole = ProjectRole.viewer,
    write: bool = False,
    permissions: frozenset[str] = frozenset(),
    permission: str | None = None,
) -> ProjectAccess:
    """404 when the user cannot see the project, 403 when they see it but may not act,
    409 when it is archived and the action writes."""
    if role is None:
        raise project_not_found(project.key)
    if permission is not None:
        if permission not in permissions:
            raise denied(project, role, permission)
    elif ROLE_RANK[role] < ROLE_RANK[need]:
        raise Forbidden(
            f"Your role in {project.key} is {role.value}; this action needs {_NEEDS[need]}.",
            code="insufficient_role",
        )
    if write and project.archived_at is not None:
        raise Conflict(
            f"Project {project.key} is archived and read-only. Unarchive it to make changes.",
            code="project_archived",
        )
    return ProjectAccess(project=project, role=role, user=user, permissions=permissions)


async def authorize(
    db: AsyncSession,
    user: User,
    permission: str | None,
    project: Project,
    *,
    need: ProjectRole = ProjectRole.viewer,
    write: bool = False,
) -> ProjectAccess:
    """The single authorization check: role (direct or via groups), then the project's
    permission matrix. With `permission=None` it only checks that the user may see it."""
    role = await effective_role(db, user, project)
    perms = await permissions_for(db, project, role)
    return check_access(
        project, role, user, need=need, write=write, permissions=perms, permission=permission
    )


# --- ticket visibility ----------------------------------------------------------------------


def visible_project_ids(user: User) -> Any:
    """Projects the user belongs to, directly or through a group."""
    if user.is_instance_admin:
        return select(Project.id)
    direct = select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)
    via_groups = (
        select(ProjectGroupRole.project_id)
        .join(GroupMember, GroupMember.group_id == ProjectGroupRole.group_id)
        .where(GroupMember.user_id == user.id)
    )
    return direct.union(via_groups)


def admin_project_ids(user: User) -> Any:
    direct = select(ProjectMember.project_id).where(
        ProjectMember.user_id == user.id, ProjectMember.role == ProjectRole.admin
    )
    via_groups = (
        select(ProjectGroupRole.project_id)
        .join(GroupMember, GroupMember.group_id == ProjectGroupRole.group_id)
        .where(GroupMember.user_id == user.id, ProjectGroupRole.role == ProjectRole.admin)
    )
    return direct.union(via_groups)


def visible_tickets_clause(user: User) -> ColumnElement[bool]:
    """The one SQL rule for which tickets a user may see: projects they belong to and, for a
    ticket with a security level, being granted (directly or by group), being an admin of
    its project, or taking part in it when the level includes participants.

    Every ticket read goes through this: RQL, fetch by key, boards, reports, MCP..."""
    in_projects = Ticket.project_id.in_(visible_project_ids(user))
    if user.is_instance_admin:
        return in_projects
    groups = select(GroupMember.group_id).where(GroupMember.user_id == user.id)
    granted = select(SecurityLevelGrant.level_id).where(
        or_(SecurityLevelGrant.user_id == user.id, SecurityLevelGrant.group_id.in_(groups))
    )
    with_participants = select(SecurityLevel.id).where(SecurityLevel.include_participants.is_(True))
    participant = or_(
        Ticket.reporter_id == user.id,
        Ticket.assignee_id == user.id,
        exists().where(
            TicketCollaborator.ticket_id == Ticket.id, TicketCollaborator.user_id == user.id
        ),
    )
    return and_(
        in_projects,
        or_(
            Ticket.security_level_id.is_(None),
            Ticket.project_id.in_(admin_project_ids(user)),
            Ticket.security_level_id.in_(granted),
            and_(Ticket.security_level_id.in_(with_participants), participant),
        ),
    )


async def can_see(db: AsyncSession, user: User, ticket: Ticket) -> bool:
    """Whether the user may see this ticket of a project they already can see."""
    if ticket.security_level_id is None or user.is_instance_admin:
        return True
    return await can_see_ticket(db, user, ticket.id)


async def can_see_ticket(db: AsyncSession, user: User, ticket_id: uuid.UUID) -> bool:
    found = await db.scalar(
        select(Ticket.id).where(Ticket.id == ticket_id, visible_tickets_clause(user))
    )
    return found is not None
