"""Who may see and do what in Folio (Folio 1.4).

- The global role (reader, creator, admin) is the ceiling: readers never create or delete,
  and Folio admins (instance admins included) may do everything everywhere.
- Each space grants permissions to users, groups or everyone; `admin` includes them all.
- A page's view restriction hides it, and everything under it, from whoever is not named
  in it. An edit restriction applies to that page only.
- Pages never published are seen only by people who can write in their space.

`visible_nodes(user)` is the one SQL rule for which nodes someone may see: the tree, search,
RQL, the RAG index and the MCP all go through it, and `can_view` asks it for one node.
"""

import uuid
from collections.abc import Iterable
from typing import Any

from sqlalchemy import ColumnElement, Select, and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import (
    FolioNode,
    FolioPageRestriction,
    FolioRole,
    FolioSpace,
    FolioSpaceGrant,
    GranteeType,
    NodeKind,
    RestrictionMode,
    SpacePermission,
)
from radicle.folio.services import roles
from radicle.platform.db.models import GroupMember, User

ALL = frozenset(p.value for p in SpacePermission)
READER_CAP = frozenset({"view", "comment", "export", "admin"})
WRITE = frozenset({"create", "delete_own", "delete_any"})


def _my_groups(user: User) -> Select[Any]:
    return select(GroupMember.group_id).where(GroupMember.user_id == user.id)


def _grant_matches(user: User) -> ColumnElement[bool]:
    return or_(
        FolioSpaceGrant.grantee_type == GranteeType.everyone,
        and_(
            FolioSpaceGrant.grantee_type == GranteeType.user,
            FolioSpaceGrant.grantee_id == user.id,
        ),
        and_(
            FolioSpaceGrant.grantee_type == GranteeType.group,
            FolioSpaceGrant.grantee_id.in_(_my_groups(user)),
        ),
    )


def _spaces_with(user: User, *permissions: str) -> Select[Any]:
    wanted = or_(*(FolioSpaceGrant.permissions.contains([p]) for p in (*permissions, "admin")))
    return select(FolioSpaceGrant.space_id).where(_grant_matches(user), wanted)


def _hidden_nodes(user: User) -> Select[Any]:
    """Nodes under a view restriction that doesn't name the user, or under a deleted node,
    with all their descendants."""
    named = or_(
        and_(
            FolioPageRestriction.grantee_type == GranteeType.user,
            FolioPageRestriction.grantee_id == user.id,
        ),
        and_(
            FolioPageRestriction.grantee_type == GranteeType.group,
            FolioPageRestriction.grantee_id.in_(_my_groups(user)),
        ),
    )
    restricted = (
        select(FolioPageRestriction.node_id)
        .where(FolioPageRestriction.mode == RestrictionMode.view)
        .group_by(FolioPageRestriction.node_id)
        .having(~func.bool_or(named))
    )
    roots = select(FolioNode.id).where(
        or_(FolioNode.id.in_(restricted), FolioNode.deleted_at.is_not(None))
    )
    hidden = roots.cte("folio_hidden", recursive=True)
    hidden = hidden.union_all(select(FolioNode.id).where(FolioNode.parent_id == hidden.c.id))
    return select(hidden.c.id)


def visible_nodes(user: User, role: FolioRole | None) -> ColumnElement[bool]:
    """SQL filter for the nodes `user` may see, given their global role."""
    if role is None:
        return FolioNode.id.is_(None)  # matches nothing
    if role == FolioRole.admin:
        live_spaces = select(FolioSpace.id).where(FolioSpace.deleted_at.is_(None))
        return and_(
            FolioNode.space_id.in_(live_spaces),
            ~FolioNode.id.in_(_deleted_nodes()),
        )
    live = select(FolioSpace.id).where(FolioSpace.deleted_at.is_(None))
    readable = FolioNode.space_id.in_(
        _spaces_with(user, "view").where(FolioSpaceGrant.space_id.in_(live))
    )
    writable = _spaces_with(user, "create") if role != FolioRole.reader else None
    ready = or_(
        FolioNode.published_version_id.is_not(None),
        FolioNode.kind == NodeKind.folder,
        FolioNode.created_by == user.id,
        *([FolioNode.space_id.in_(writable)] if writable is not None else []),
    )
    return and_(readable, ready, ~FolioNode.id.in_(_hidden_nodes(user)))


def _deleted_nodes() -> Select[Any]:
    roots = select(FolioNode.id).where(FolioNode.deleted_at.is_not(None))
    gone = roots.cte("folio_deleted", recursive=True)
    gone = gone.union_all(select(FolioNode.id).where(FolioNode.parent_id == gone.c.id))
    return select(gone.c.id)


async def node_filter(db: AsyncSession, user: User) -> ColumnElement[bool]:
    return visible_nodes(user, await roles.effective_role(db, user))


async def can_view(db: AsyncSession, user: User, node_id: uuid.UUID) -> bool:
    found = await db.scalar(
        select(FolioNode.id).where(FolioNode.id == node_id, await node_filter(db, user))
    )
    return found is not None


async def visible_ids(db: AsyncSession, user: User, space: FolioSpace) -> set[uuid.UUID]:
    rows = await db.scalars(
        select(FolioNode.id).where(FolioNode.space_id == space.id, await node_filter(db, user))
    )
    return set(rows)


async def space_permissions(db: AsyncSession, user: User, space: FolioSpace) -> frozenset[str]:
    """What the user may do in the space, capped by their global role."""
    role = await roles.effective_role(db, user)
    if role is None or space.deleted_at is not None:
        return frozenset()
    if role == FolioRole.admin:
        return ALL
    rows = await db.scalars(
        select(FolioSpaceGrant.permissions).where(
            FolioSpaceGrant.space_id == space.id, _grant_matches(user)
        )
    )
    granted: set[str] = set()
    for permissions in rows:
        granted.update(permissions)
    perms = ALL if "admin" in granted else frozenset(granted)
    return perms & READER_CAP if role == FolioRole.reader else perms


async def visible_space_ids(db: AsyncSession, user: User) -> set[uuid.UUID]:
    role = await roles.effective_role(db, user)
    if role is None:
        return set()
    query = select(FolioSpace.id).where(FolioSpace.deleted_at.is_(None))
    if role != FolioRole.admin:
        query = query.where(FolioSpace.id.in_(_spaces_with(user, "view")))
    return set(await db.scalars(query))


async def may_edit(db: AsyncSession, user: User, node: FolioNode) -> bool:
    """Create rights in the space, and named in the page's edit restriction if it has one."""
    space = await db.get(FolioSpace, node.space_id)
    if space is None:
        return False
    perms = await space_permissions(db, user, space)
    if "create" not in perms:
        return False
    if "admin" in perms:
        return True
    restricted = await db.scalar(
        select(
            exists().where(
                FolioPageRestriction.node_id == node.id,
                FolioPageRestriction.mode == RestrictionMode.edit,
            )
        )
    )
    if not restricted:
        return True
    named = await db.scalar(
        select(
            exists().where(
                FolioPageRestriction.node_id == node.id,
                FolioPageRestriction.mode == RestrictionMode.edit,
                or_(
                    and_(
                        FolioPageRestriction.grantee_type == GranteeType.user,
                        FolioPageRestriction.grantee_id == user.id,
                    ),
                    and_(
                        FolioPageRestriction.grantee_type == GranteeType.group,
                        FolioPageRestriction.grantee_id.in_(_my_groups(user)),
                    ),
                ),
            )
        )
    )
    return bool(named)


async def may_delete(db: AsyncSession, user: User, node: FolioNode) -> bool:
    space = await db.get(FolioSpace, node.space_id)
    if space is None:
        return False
    perms = await space_permissions(db, user, space)
    return "delete_any" in perms or ("delete_own" in perms and node.created_by == user.id)


def default_grants(space: FolioSpace, creator: User) -> Iterable[FolioSpaceGrant]:
    """Team spaces: everyone views, the creator administers. Personal: only the owner."""
    if space.owner_id is None:
        yield FolioSpaceGrant(
            space_id=space.id,
            grantee_type=GranteeType.everyone,
            grantee_id=None,
            permissions=["view"],
        )
    yield FolioSpaceGrant(
        space_id=space.id,
        grantee_type=GranteeType.user,
        grantee_id=creator.id,
        permissions=["admin"],
    )
