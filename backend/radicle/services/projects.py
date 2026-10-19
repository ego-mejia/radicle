"""Projects and their members."""

import re
import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.core.errors import Conflict, Forbidden, ValidationFailed
from radicle.db.models import Project, ProjectMember, ProjectRole, TemplateMode, User, utcnow
from radicle.services import users as users_service
from radicle.services.access import ProjectAccess

KEY_RE = re.compile(r"^[A-Z][A-Z0-9]{1,9}$")
NAME_MAX = 100
DESCRIPTION_MAX = 50_000

_UNSET = object()


def normalize_key(key: str) -> str:
    value = key.strip().upper()
    if not KEY_RE.fullmatch(value):
        raise ValidationFailed(
            f"Invalid project key '{key}'. Use 2 to 10 characters: an uppercase letter "
            "followed by uppercase letters or digits, like PA or WEB2.",
            errors=[{"field": "key", "message": "invalid format"}],
        )
    return value


def normalize_name(name: str, *, field: str = "name", limit: int = NAME_MAX) -> str:
    value = " ".join(name.split())
    if not value or len(value) > limit:
        raise ValidationFailed(
            f"{field.replace('_', ' ').capitalize()} must be 1 to {limit} characters.",
            errors=[{"field": field, "message": "invalid length"}],
        )
    return value


def check_description(text: str) -> str:
    if len(text) > DESCRIPTION_MAX:
        raise ValidationFailed(
            f"Description must be at most {DESCRIPTION_MAX} characters.",
            errors=[{"field": "description_md", "message": "too long"}],
        )
    return text


@dataclass(frozen=True)
class ProjectSummary:
    project: Project
    role: ProjectRole


async def create_project(
    db: AsyncSession,
    creator: User,
    *,
    key: str,
    name: str,
    description_md: str = "",
    template_id: uuid.UUID | None = None,
    template_mode: TemplateMode = TemplateMode.linked,
) -> Project:
    """Create a project with the configuration of a template (Radicle default if none)."""
    from radicle.services import templates

    if not creator.is_instance_admin:
        raise Forbidden("Only instance admins can create projects.")
    key = normalize_key(key)
    if await db.scalar(select(Project.id).where(Project.key == key)):
        raise Conflict(
            f"Project key {key} is already taken.",
            code="duplicate_key",
            errors=[{"field": "key", "message": "already taken"}],
        )
    project = Project(
        key=key,
        name=normalize_name(name),
        description_md=check_description(description_md),
        created_by=creator.id,
    )
    db.add(project)
    await db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=creator.id, role=ProjectRole.admin))
    await templates.instantiate(db, project, creator, template_id=template_id, mode=template_mode)
    from radicle.services import boards

    await boards.create_default_board(db, project, creator)
    from radicle.services import dashboards

    await dashboards.create_project_summary(db, project)
    return project


async def list_projects(
    db: AsyncSession, user: User, *, include_archived: bool = False
) -> list[ProjectSummary]:
    """Projects where the user is a member. Instance admins see every project as admin."""
    if user.is_instance_admin:
        rows = [
            ProjectSummary(p, ProjectRole.admin)
            for p in await db.scalars(select(Project).order_by(Project.key))
        ]
    else:
        from radicle.core.permissions import effective_role
        from radicle.services.search import visible_project_ids

        found = await db.scalars(
            select(Project).where(Project.id.in_(visible_project_ids(user))).order_by(Project.key)
        )
        rows = []
        for p in found:
            role = await effective_role(db, user, p)
            if role is not None:
                rows.append(ProjectSummary(p, role))
    if not include_archived:
        rows = [r for r in rows if r.project.archived_at is None]
    return rows


async def update_project(
    access: ProjectAccess, *, name: str | None = None, description_md: str | None = None
) -> Project:
    project = access.project
    if name is not None:
        project.name = normalize_name(name)
    if description_md is not None:
        project.description_md = check_description(description_md)
    project.updated_at = utcnow()
    return project


def set_archived(access: ProjectAccess, archived: bool) -> Project:
    project = access.project
    if archived and project.archived_at is not None:
        raise Conflict(f"Project {project.key} is already archived.", code="already_archived")
    if not archived and project.archived_at is None:
        raise Conflict(f"Project {project.key} is not archived.", code="not_archived")
    project.archived_at = utcnow() if archived else None
    return project


# --- members -----------------------------------------------------------------------------


async def list_members(db: AsyncSession, project: Project) -> list[ProjectMember]:
    result = await db.scalars(
        select(ProjectMember)
        .join(User, User.id == ProjectMember.user_id)
        .where(ProjectMember.project_id == project.id)
        .order_by(User.handle)
    )
    return list(result)


@dataclass(frozen=True)
class MemberRow:
    user: User
    role: ProjectRole | None
    effective_role: ProjectRole
    groups: list[str]


async def member_rows(db: AsyncSession, project: Project) -> list[MemberRow]:
    """Everyone in the project, directly or through groups, with their effective role."""
    from radicle.core.permissions import highest
    from radicle.db.models import Group, GroupMember, ProjectGroupRole

    direct = {m.user_id: m for m in await list_members(db, project)}
    via = await db.execute(
        select(GroupMember.user_id, Group.name, ProjectGroupRole.role)
        .join(Group, Group.id == GroupMember.group_id)
        .join(ProjectGroupRole, ProjectGroupRole.group_id == Group.id)
        .where(ProjectGroupRole.project_id == project.id)
    )
    group_roles: dict[uuid.UUID, list[tuple[str, ProjectRole]]] = {}
    for user_id, name, role in via:
        group_roles.setdefault(user_id, []).append((name, role))
    ids = set(direct) | set(group_roles)
    users = {u.id: u for u in await db.scalars(select(User).where(User.id.in_(ids)))}
    rows = []
    for user_id in ids:
        d = direct.get(user_id)
        gr = group_roles.get(user_id, [])
        best = highest([d.role if d else None, *(r for _, r in gr)])
        assert best is not None  # noqa: S101 - every id has a direct or group role
        rows.append(
            MemberRow(users[user_id], d.role if d else None, best, sorted(n for n, _ in gr))
        )
    return sorted(rows, key=lambda r: r.user.handle)


async def direct_role(db: AsyncSession, project: Project, handle: str) -> ProjectRole | None:
    user = await users_service.get_by_handle(db, handle)
    member = await db.get(ProjectMember, (project.id, user.id))
    return member.role if member else None


async def set_member(
    db: AsyncSession, access: ProjectAccess, handle: str, role: ProjectRole
) -> ProjectMember:
    project = access.project
    user = await users_service.get_by_handle(db, handle)
    if not user.is_active:
        raise ValidationFailed(
            f"@{user.handle} is deactivated and cannot join projects.", code="user_inactive"
        )
    member = await db.get(ProjectMember, (project.id, user.id))
    if member is None:
        member = ProjectMember(project_id=project.id, user_id=user.id, role=role)
        db.add(member)
    else:
        if member.role is ProjectRole.admin and role is not ProjectRole.admin:
            await _ensure_other_admin(db, project, user)
        member.role = role
    await db.flush()
    await db.refresh(member)
    return member


async def remove_member(db: AsyncSession, access: ProjectAccess, handle: str) -> None:
    project = access.project
    user = await users_service.get_by_handle(db, handle)
    member = await db.get(ProjectMember, (project.id, user.id))
    if member is None:
        raise ValidationFailed(
            f"@{user.handle} is not a member of {project.key}.", code="not_a_member"
        )
    if member.role is ProjectRole.admin:
        await _ensure_other_admin(db, project, user)
    await db.delete(member)
    await db.flush()


async def _ensure_other_admin(db: AsyncSession, project: Project, leaving: User) -> None:
    others = await db.scalar(
        select(func.count())
        .select_from(ProjectMember)
        .where(
            ProjectMember.project_id == project.id,
            ProjectMember.role == ProjectRole.admin,
            ProjectMember.user_id != leaving.id,
        )
    )
    if not others:
        raise Conflict(
            f"{project.key} would be left without an admin. Make someone else admin first.",
            code="last_project_admin",
        )
