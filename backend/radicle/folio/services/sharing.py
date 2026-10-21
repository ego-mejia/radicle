"""Managing who may do what (Folio 1.4): a space's grants and a page's restrictions."""

import uuid
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import (
    FolioNode,
    FolioPageRestriction,
    FolioSpace,
    FolioSpaceGrant,
    GranteeType,
    RestrictionMode,
    SpacePermission,
)
from radicle.folio.services import access, nodes
from radicle.platform.db.models import Group, User
from radicle.platform.errors import ValidationFailed
from radicle.platform.services import groups, users

PERMISSIONS = tuple(p.value for p in SpacePermission)


@dataclass(frozen=True)
class Grantee:
    type: GranteeType
    name: str | None  # handle, group name, or None for everyone


def _invalid(field: str, message: str) -> ValidationFailed:
    return ValidationFailed(message, errors=[{"field": field, "message": "invalid"}])


async def _resolve(db: AsyncSession, grantee: Grantee, field: str) -> uuid.UUID | None:
    if grantee.type == GranteeType.everyone:
        return None
    if not grantee.name:
        raise _invalid(field, f"Name the {grantee.type.value}: a handle or a group name.")
    if grantee.type == GranteeType.user:
        return (await users.get_by_handle(db, grantee.name.lstrip("@"))).id
    return (await groups.get_group(db, grantee.name)).id


async def _names(db: AsyncSession, ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    handles = await db.execute(select(User.id, User.handle).where(User.id.in_(ids)))
    names = await db.execute(select(Group.id, Group.name).where(Group.id.in_(ids)))
    return {i: n for i, n in [*handles.all(), *names.all()]}


# --- space grants ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GrantRow:
    grantee: Grantee
    permissions: list[str]


async def space_grants(db: AsyncSession, space: FolioSpace) -> list[GrantRow]:
    rows = list(
        await db.scalars(select(FolioSpaceGrant).where(FolioSpaceGrant.space_id == space.id))
    )
    names = await _names(db, {r.grantee_id for r in rows if r.grantee_id})
    out = [
        GrantRow(
            Grantee(r.grantee_type, names.get(r.grantee_id) if r.grantee_id else None),
            sorted(r.permissions, key=PERMISSIONS.index),
        )
        for r in rows
        if r.grantee_id is None or r.grantee_id in names
    ]
    order = {GranteeType.everyone: 0, GranteeType.group: 1, GranteeType.user: 2}
    return sorted(out, key=lambda g: (order[g.grantee.type], (g.grantee.name or "").lower()))


async def set_space_grants(
    db: AsyncSession, user: User, space: FolioSpace, rows: list[GrantRow]
) -> list[GrantRow]:
    """Replace the space's grants. Someone must keep `admin`; personal spaces stay private."""
    await access.require_admin(db, user, space)
    if space.owner_id is not None:
        raise _invalid(
            "grants", "Personal spaces are only their owner's; their grants don't change."
        )
    seen: set[tuple[GranteeType, uuid.UUID | None]] = set()
    new: list[FolioSpaceGrant] = []
    for i, row in enumerate(rows):
        unknown = sorted(set(row.permissions) - set(PERMISSIONS))
        if unknown or not row.permissions:
            raise _invalid(
                f"grants[{i}].permissions",
                f"Use one or more of: {', '.join(PERMISSIONS)}.",
            )
        grantee_id = await _resolve(db, row.grantee, f"grants[{i}].grantee")
        if (row.grantee.type, grantee_id) in seen:
            raise _invalid(f"grants[{i}]", "Each user, group or everyone appears once.")
        seen.add((row.grantee.type, grantee_id))
        new.append(
            FolioSpaceGrant(
                space_id=space.id,
                grantee_type=row.grantee.type,
                grantee_id=grantee_id,
                permissions=sorted(set(row.permissions), key=PERMISSIONS.index),
            )
        )
    if not any("admin" in g.permissions and g.grantee_type != GranteeType.everyone for g in new):
        raise _invalid("grants", "Keep at least one user or group with admin in the space.")
    await db.execute(delete(FolioSpaceGrant).where(FolioSpaceGrant.space_id == space.id))
    db.add_all(new)
    await db.flush()
    return await space_grants(db, space)


# --- page restrictions ----------------------------------------------------------------------


async def restrictions(db: AsyncSession, node: FolioNode) -> dict[str, list[Grantee]]:
    rows = list(
        await db.scalars(
            select(FolioPageRestriction).where(FolioPageRestriction.node_id == node.id)
        )
    )
    names = await _names(db, {r.grantee_id for r in rows})
    out: dict[str, list[Grantee]] = {"view": [], "edit": []}
    for r in rows:
        if r.grantee_id in names:
            out[r.mode.value].append(Grantee(r.grantee_type, names[r.grantee_id]))
    for mode in out:
        out[mode].sort(key=lambda g: (g.type.value, (g.name or "").lower()))
    return out


async def set_restrictions(
    db: AsyncSession,
    user: User,
    node: FolioNode,
    *,
    view: list[Grantee],
    edit: list[Grantee],
) -> dict[str, list[Grantee]]:
    """Replace the page's restrictions. Empty lists lift them. You can't lock yourself out."""
    await access.require_edit(db, user, node)
    rows: list[FolioPageRestriction] = []
    for mode, grantees in ((RestrictionMode.view, view), (RestrictionMode.edit, edit)):
        for i, g in enumerate(grantees):
            if g.type == GranteeType.everyone:
                raise _invalid(
                    f"{mode.value}[{i}]", "Name users or groups; everyone means no restriction."
                )
            gid = await _resolve(db, g, f"{mode.value}[{i}]")
            if gid is None:  # pragma: no cover - users and groups always have an id
                continue
            rows.append(
                FolioPageRestriction(
                    node_id=node.id, mode=mode, grantee_type=g.type, grantee_id=gid
                )
            )
    await db.execute(delete(FolioPageRestriction).where(FolioPageRestriction.node_id == node.id))
    db.add_all(rows)
    await db.flush()
    if not await access.can_view(db, user, node.id) or not await access.may_edit(db, user, node):
        raise _invalid(
            "view", "Include yourself (or a group you're in), or you'd lose access to the page."
        )
    nodes.record(
        db,
        node,
        user,
        "restriction_changed",
        view=[g.name for g in view],
        edit=[g.name for g in edit],
    )
    return await restrictions(db, node)
