"""Read and change a project's permission matrix (member and viewer; admins have all)."""

from dataclasses import dataclass

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.core.permissions import (
    CATALOG,
    DESCRIPTIONS,
    EDITABLE_ROLES,
    PERMISSIONS,
    default_allowed,
    matrix,
)
from radicle.db.models import Project, ProjectRole, ProjectRolePermission
from radicle.platform.errors import ValidationFailed


@dataclass(frozen=True)
class Row:
    permission: str
    description: str
    member: bool
    viewer: bool
    member_default: bool
    viewer_default: bool


async def read(db: AsyncSession, project: Project) -> list[Row]:
    overrides = await matrix(db, project.id)

    def value(role: ProjectRole, p: str) -> bool:
        return overrides.get((role, p), default_allowed(role, p))

    return [
        Row(
            p,
            DESCRIPTIONS[p],
            value(ProjectRole.member, p),
            value(ProjectRole.viewer, p),
            CATALOG[p][0],
            CATALOG[p][1],
        )
        for p in PERMISSIONS
    ]


async def change(
    db: AsyncSession, project: Project, values: dict[ProjectRole, dict[str, bool]]
) -> list[tuple[ProjectRole, str, bool, bool]]:
    """Set (role, permission) values; returns the ones that changed as (role, perm, old, new).
    Values equal to the catalog default are stored as no row."""
    unknown = sorted({p for perms in values.values() for p in perms} - set(PERMISSIONS))
    if unknown:
        raise ValidationFailed(
            f"Unknown permissions: {', '.join(unknown)}. Permissions: {', '.join(PERMISSIONS)}.",
            errors=[{"field": "permissions", "message": "unknown"}],
        )
    roles = set(values) - set(EDITABLE_ROLES)
    if roles:
        raise ValidationFailed(
            "Only member and viewer can be changed; admins can always do everything.",
            errors=[{"field": "role", "message": "not editable"}],
        )
    current = await matrix(db, project.id)
    changed = []
    for role, perms in values.items():
        for p, allowed in perms.items():
            old = current.get((role, p), default_allowed(role, p))
            if old == allowed:
                continue
            changed.append((role, p, old, allowed))
            await db.execute(
                delete(ProjectRolePermission).where(
                    ProjectRolePermission.project_id == project.id,
                    ProjectRolePermission.role == role,
                    ProjectRolePermission.permission == p,
                )
            )
            if allowed != default_allowed(role, p):
                db.add(
                    ProjectRolePermission(
                        project_id=project.id, role=role, permission=p, allowed=allowed
                    )
                )
    await db.flush()
    return changed


async def reset(db: AsyncSession, project: Project) -> None:
    await db.execute(
        delete(ProjectRolePermission).where(ProjectRolePermission.project_id == project.id)
    )
    await db.flush()
