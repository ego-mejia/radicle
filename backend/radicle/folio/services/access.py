"""Who may see and do what in Folio (Folio 1.4).

- The global role (reader, creator, admin) is the ceiling: readers never create or delete,
  and Folio admins (instance admins included) may do everything, everywhere but in
  other people's personal spaces.
- Each space grants permissions to users, groups or everyone; `admin` includes them all.
- Personal spaces are their owner's alone, even for Folio admins.
- A page's view restriction hides it, and everything under it, from whoever is not named
  in it. An edit restriction applies to that page only.
- Pages never published are seen by their author, the space's admins and, when a person
  wrote them, people who can write in the space; an agent's new page waits for approval.

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
from radicle.platform.db.models import GroupMember, User, UserKind
from radicle.platform.errors import Forbidden

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
        live_spaces = select(FolioSpace.id).where(
            FolioSpace.deleted_at.is_(None), _not_private(user)
        )
        return and_(
            FolioNode.space_id.in_(live_spaces),
            ~FolioNode.id.in_(_deleted_nodes()),
        )
    live = select(FolioSpace.id).where(FolioSpace.deleted_at.is_(None))
    readable = FolioNode.space_id.in_(
        _spaces_with(user, "view").where(FolioSpaceGrant.space_id.in_(live))
    )
    # Unpublished pages: their author, the space's admins, and (when a person wrote them)
    # anyone who can write in the space. An agent's new page waits for approval unseen.
    people = select(User.id).where(User.kind == UserKind.human)
    writers = []
    if role != FolioRole.reader:
        writers = [
            and_(
                FolioNode.space_id.in_(_spaces_with(user, "create")),
                FolioNode.created_by.in_(people),
            )
        ]
    ready = or_(
        FolioNode.published_version_id.is_not(None),
        FolioNode.kind == NodeKind.folder,
        FolioNode.kind == NodeKind.live_doc,  # never published: readable as they are written
        FolioNode.kind == NodeKind.database,  # likewise: its rows are its content
        FolioNode.created_by == user.id,
        FolioNode.space_id.in_(_spaces_with(user, "admin")),
        *writers,
    )
    return and_(readable, ready, ~FolioNode.id.in_(_hidden_nodes(user)))


def _not_private(user: User) -> ColumnElement[bool]:
    """Personal spaces are their owner's alone, even for Folio admins."""
    return or_(FolioSpace.owner_id.is_(None), FolioSpace.owner_id == user.id)


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
    if space.owner_id is not None and space.owner_id != user.id:
        return frozenset()  # someone else's personal space
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
    query = select(FolioSpace.id).where(FolioSpace.deleted_at.is_(None), _not_private(user))
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


async def require_create(db: AsyncSession, user: User, space: FolioSpace) -> None:
    if "create" not in await space_permissions(db, user, space):
        raise Forbidden(
            f"You can't write in {space.name}: it takes the Folio creator role and the create "
            "permission in the space. A space admin can give it in the space's permissions.",
            code="space_permission_denied",
        )


async def require_edit(db: AsyncSession, user: User, node: FolioNode) -> None:
    if not await may_edit(db, user, node):
        raise Forbidden(
            f"You can't edit '{node.title}'. Ask a space admin for the create permission, or "
            "to be added to the page's edit restriction.",
            code="page_permission_denied",
        )


async def require_delete(db: AsyncSession, user: User, node: FolioNode) -> None:
    if not await may_delete(db, user, node):
        raise Forbidden(
            f"You can't delete '{node.title}': it takes delete_any, or delete_own for your own "
            "pages, in the space.",
            code="page_permission_denied",
        )


async def require_admin(db: AsyncSession, user: User, space: FolioSpace) -> None:
    if "admin" not in await space_permissions(db, user, space):
        raise Forbidden(f"Only the admins of {space.name} can change it.", code="space_admin_only")
