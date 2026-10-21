"""Global Folio roles (Folio 0.5): reader, creator or admin, given to a user, a group or
everyone. A user's role is the highest that applies; instance admins are always admins."""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import ROLE_RANK, FolioGlobalGrant, FolioRole, GranteeType
from radicle.platform.db.models import Group, User
from radicle.platform.errors import NotFound, ValidationFailed
from radicle.platform.services import groups, users


async def effective_role(db: AsyncSession, user: User) -> FolioRole | None:
    """None when no grant reaches the user: then Folio is hidden for them."""
    if user.is_instance_admin:
        return FolioRole.admin
    group_ids = await groups.group_ids(db, user)
    rows = await db.scalars(
        select(FolioGlobalGrant.role).where(
            (FolioGlobalGrant.grantee_type == GranteeType.everyone)
            | (
                (FolioGlobalGrant.grantee_type == GranteeType.user)
                & (FolioGlobalGrant.grantee_id == user.id)
            )
            | (
                (FolioGlobalGrant.grantee_type == GranteeType.group)
                & FolioGlobalGrant.grantee_id.in_(group_ids)
            )
        )
    )
    roles = list(rows)
    return max(roles, key=ROLE_RANK.__getitem__) if roles else None


@dataclass(frozen=True)
class Grant:
    id: uuid.UUID
    grantee_type: GranteeType
    grantee: str | None  # handle, group name, or None for everyone
    role: FolioRole


async def list_grants(db: AsyncSession) -> list[Grant]:
    """Everyone first, then groups and users by name. Grants whose user or group was
    deleted are left out."""
    rows = list(await db.scalars(select(FolioGlobalGrant)))
    user_ids = [g.grantee_id for g in rows if g.grantee_type == GranteeType.user]
    group_ids = [g.grantee_id for g in rows if g.grantee_type == GranteeType.group]
    found = await db.execute(select(User.id, User.handle).where(User.id.in_(user_ids)))
    handles: dict[uuid.UUID | None, str] = {i: h for i, h in found.all()}
    found = await db.execute(select(Group.id, Group.name).where(Group.id.in_(group_ids)))
    names: dict[uuid.UUID | None, str] = {i: n for i, n in found.all()}
    out = []
    for g in rows:
        if g.grantee_type == GranteeType.everyone:
            out.append(Grant(g.id, g.grantee_type, None, g.role))
            continue
        name = (handles if g.grantee_type == GranteeType.user else names).get(g.grantee_id)
        if name is not None:
            out.append(Grant(g.id, g.grantee_type, name, g.role))
    order = {GranteeType.everyone: 0, GranteeType.group: 1, GranteeType.user: 2}
    return sorted(out, key=lambda g: (order[g.grantee_type], (g.grantee or "").lower()))


async def _grantee_id(
    db: AsyncSession, grantee_type: GranteeType, grantee: str | None
) -> uuid.UUID | None:
    if grantee_type == GranteeType.everyone:
        if grantee:
            raise ValidationFailed(
                "A grant for everyone has no grantee; leave it empty.",
                errors=[{"field": "grantee", "message": "must be empty"}],
            )
        return None
    if not grantee:
        raise ValidationFailed(
            f"Say which {grantee_type.value} gets the role: a handle or a group name.",
            errors=[{"field": "grantee", "message": "required"}],
        )
    if grantee_type == GranteeType.user:
        return (await users.get_by_handle(db, grantee)).id
    return (await groups.get_group(db, grantee)).id


async def set_grant(
    db: AsyncSession, actor: User, grantee_type: GranteeType, grantee: str | None, role: FolioRole
) -> tuple[Grant, FolioRole | None]:
    """Give the grantee this role, replacing their previous one. Returns the grant and the
    role it had before (None if it is new)."""
    grantee_id = await _grantee_id(db, grantee_type, grantee)
    row = await db.scalar(
        select(FolioGlobalGrant).where(
            FolioGlobalGrant.grantee_type == grantee_type,
            FolioGlobalGrant.grantee_id.is_(None)
            if grantee_id is None
            else FolioGlobalGrant.grantee_id == grantee_id,
        )
    )
    previous = row.role if row else None
    if row is None:
        row = FolioGlobalGrant(
            grantee_type=grantee_type, grantee_id=grantee_id, role=role, created_by=actor.id
        )
        db.add(row)
    else:
        row.role = role
    await db.flush()
    name = None if grantee_type == GranteeType.everyone else (grantee or "").lstrip("@")
    return Grant(row.id, grantee_type, name, role), previous


async def remove_grant(db: AsyncSession, grant_id: uuid.UUID) -> FolioGlobalGrant:
    row = await db.get(FolioGlobalGrant, grant_id)
    if row is None:
        raise NotFound(
            f"Grant {grant_id} not found. GET /api/v1/folio/admin/grants lists them.",
            code="grant_not_found",
        )
    await db.delete(row)
    await db.flush()
    return row
