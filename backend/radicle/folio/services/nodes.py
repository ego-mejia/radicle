"""The tree of a space (Folio 1.1): pages and folders under each other, ordered by
fractional rank, and blog posts outside the tree. Deleting is soft and hides descendants."""

import re
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioNode, FolioNodeEvent, FolioSpace, NodeKind
from radicle.platform import authz
from radicle.platform.db.models import User, utcnow
from radicle.platform.errors import NotFound, ValidationFailed
from radicle.platform.services import rank

TITLE_MAX = 200
SLUG_MAX = 60


def slugify(title: str) -> str:
    """ASCII, lowercase, dash separated: "Conecta un agente" -> "conecta-un-agente"."""
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-")
    return slug[:SLUG_MAX].rstrip("-") or "page"


def _invalid(field_name: str, message: str) -> ValidationFailed:
    return ValidationFailed(message, errors=[{"field": field_name, "message": "invalid"}])


def _title(value: str) -> str:
    title = value.strip()
    if not 1 <= len(title) <= TITLE_MAX:
        raise _invalid("title", f"Titles are 1 to {TITLE_MAX} characters.")
    return title


def record(db: AsyncSession, node: FolioNode, actor: User, event: str, **data: Any) -> None:
    db.add(FolioNodeEvent(node_id=node.id, actor_id=actor.id, event_type=event, data=data))


async def _space_nodes(db: AsyncSession, space: FolioSpace) -> list[FolioNode]:
    rows = await db.scalars(select(FolioNode).where(FolioNode.space_id == space.id))
    return list(rows)


def _alive(nodes: list[FolioNode]) -> dict[uuid.UUID, FolioNode]:
    """Nodes not deleted and with no deleted ancestor."""
    by_id = {n.id: n for n in nodes}
    alive: dict[uuid.UUID, bool] = {}

    def ok(n: FolioNode) -> bool:
        if n.id in alive:
            return alive[n.id]
        result = n.deleted_at is None and (
            n.parent_id is None or (n.parent_id in by_id and ok(by_id[n.parent_id]))
        )
        alive[n.id] = result
        return result

    return {n.id: n for n in nodes if ok(n)}


async def get_node(db: AsyncSession, user: User, node_id: uuid.UUID) -> FolioNode:
    """A node you can see. Deleted nodes and those under a deleted ancestor are 404."""
    from radicle.folio.services import spaces  # avoid an import cycle at module load

    node = await db.get(FolioNode, node_id)
    if node is not None:
        space = await db.get(FolioSpace, node.space_id)
        if space is not None:
            try:
                await spaces.get_space(db, user, space.key)
            except NotFound:
                node = None
            else:
                if node.id not in _alive(await _space_nodes(db, space)):
                    node = None
    if node is None:
        raise NotFound(f"Page {node_id} not found.", code="node_not_found")
    return node


async def breadcrumbs(db: AsyncSession, node: FolioNode) -> list[FolioNode]:
    """Ancestors from the root down, not including the node."""
    chain: list[FolioNode] = []
    parent_id = node.parent_id
    while parent_id is not None:
        parent = await db.get(FolioNode, parent_id)
        if parent is None:
            break
        chain.append(parent)
        parent_id = parent.parent_id
    return list(reversed(chain))


async def _parent(
    db: AsyncSession, space: FolioSpace, parent_id: uuid.UUID | None
) -> FolioNode | None:
    if parent_id is None:
        return None
    parent = await db.get(FolioNode, parent_id)
    alive = _alive(await _space_nodes(db, space))
    if parent is None or parent.space_id != space.id or parent.id not in alive:
        raise _invalid("parent", f"Parent {parent_id} is not a page or folder in {space.key}.")
    if parent.kind == NodeKind.blog_post:
        raise _invalid("parent", "Blog posts cannot have children.")
    return parent


async def _last_rank(db: AsyncSession, space: FolioSpace, parent_id: uuid.UUID | None) -> str:
    last = await db.scalar(
        select(func.max(FolioNode.rank)).where(
            FolioNode.space_id == space.id,
            FolioNode.parent_id.is_(None)
            if parent_id is None
            else FolioNode.parent_id == parent_id,
        )
    )
    return rank.after(last)


async def create_node(
    db: AsyncSession,
    user: User,
    space: FolioSpace,
    *,
    kind: NodeKind,
    title: str,
    parent_id: uuid.UUID | None = None,
) -> FolioNode:
    """A page or folder (optionally under a parent) or a blog post (never in the tree)."""
    (await authz.authorize(db, user, "folio", "folio.create")).raise_if_denied()
    if kind == NodeKind.blog_post and parent_id is not None:
        raise _invalid("parent", "Blog posts live outside the tree: leave parent empty.")
    parent = await _parent(db, space, parent_id)
    title = _title(title)
    node = FolioNode(
        space_id=space.id,
        parent_id=parent.id if parent else None,
        kind=kind,
        title=title,
        slug=slugify(title),
        rank=await _last_rank(db, space, parent.id if parent else None),
        created_by=user.id,
    )
    db.add(node)
    await db.flush()
    record(db, node, user, "created", kind=kind.value, title=title)
    return node


@dataclass
class TreeNode:
    node: FolioNode
    children: list["TreeNode"] = field(default_factory=list)


async def tree(db: AsyncSession, space: FolioSpace) -> list[TreeNode]:
    """Pages and folders of the space as a forest, siblings by rank. No blog posts."""
    alive = _alive(await _space_nodes(db, space))
    items = {i: TreeNode(n) for i, n in alive.items() if n.kind != NodeKind.blog_post}
    roots: list[TreeNode] = []
    for item in items.values():
        parent = items.get(item.node.parent_id) if item.node.parent_id else None
        (parent.children if parent else roots).append(item)

    def order(level: list[TreeNode]) -> list[TreeNode]:
        level.sort(key=lambda t: (t.node.rank, str(t.node.id)))
        for t in level:
            order(t.children)
        return level

    return order(roots)


async def posts(
    db: AsyncSession, space: FolioSpace, *, before: datetime | None = None, limit: int = 20
) -> list[FolioNode]:
    """Blog posts, newest first (by publication date, or creation until published)."""
    when = func.coalesce(FolioNode.published_at, FolioNode.created_at)
    query = select(FolioNode).where(
        FolioNode.space_id == space.id,
        FolioNode.kind == NodeKind.blog_post,
        FolioNode.deleted_at.is_(None),
    )
    if before is not None:
        query = query.where(when < before)
    rows = await db.scalars(query.order_by(when.desc(), FolioNode.id).limit(limit))
    return list(rows)


@dataclass(frozen=True)
class NodeChanges:
    title: str | None = None
    icon: str | None = None
    clear_icon: bool = False
    cover_asset_id: uuid.UUID | None = None
    clear_cover: bool = False


async def update_node(db: AsyncSession, user: User, node: FolioNode, ch: NodeChanges) -> FolioNode:
    (await authz.authorize(db, user, "folio", "folio.create")).raise_if_denied()
    if ch.title is not None:
        old = node.title
        node.title = _title(ch.title)
        node.slug = slugify(node.title)
        if node.title != old:
            record(db, node, user, "renamed", old=old, new=node.title)
    if ch.clear_icon:
        node.icon = None
    elif ch.icon is not None:
        node.icon = ch.icon.strip() or None
    if ch.clear_cover:
        node.cover_asset_id = None
    elif ch.cover_asset_id is not None:
        node.cover_asset_id = ch.cover_asset_id
    node.updated_at = utcnow()
    await db.flush()
    return node


async def move_node(
    db: AsyncSession,
    user: User,
    node: FolioNode,
    *,
    parent_id: uuid.UUID | None,
    before_id: uuid.UUID | None = None,
    after_id: uuid.UUID | None = None,
) -> FolioNode:
    """Move within the space: under `parent_id` (None for the root), placed after
    `after_id` and/or before `before_id` among its new siblings (else at the end)."""
    (await authz.authorize(db, user, "folio", "folio.create")).raise_if_denied()
    if node.kind == NodeKind.blog_post:
        raise _invalid("parent", "Blog posts live outside the tree and cannot be moved in it.")
    space = await db.get(FolioSpace, node.space_id)
    if space is None:  # pragma: no cover - a node always has its space
        raise NotFound(f"Page {node.id} not found.", code="node_not_found")
    parent = await _parent(db, space, parent_id)
    ancestor = parent
    while ancestor is not None:
        if ancestor.id == node.id:
            raise _invalid("parent", "A page cannot move under itself or one of its children.")
        ancestor = await db.get(FolioNode, ancestor.parent_id) if ancestor.parent_id else None

    async def sibling(sibling_id: uuid.UUID | None, name: str) -> str | None:
        if sibling_id is None:
            return None
        other = await db.get(FolioNode, sibling_id)
        new_parent = parent.id if parent else None
        if other is None or other.space_id != space.id or other.parent_id != new_parent:
            raise _invalid(name, f"{name.capitalize()} {sibling_id} is not a sibling there.")
        return other.rank

    low, high = await sibling(after_id, "after"), await sibling(before_id, "before")
    if low is None and high is None:
        new_rank = await _last_rank(db, space, parent.id if parent else None)
    else:
        try:
            new_rank = rank.between(low, high)
        except ValueError:
            raise _invalid("before", "'after' must come before 'before'.") from None
    old_parent = node.parent_id
    node.parent_id = parent.id if parent else None
    node.rank = new_rank
    node.updated_at = utcnow()
    record(
        db,
        node,
        user,
        "moved",
        old_parent=str(old_parent) if old_parent else None,
        new_parent=str(node.parent_id) if node.parent_id else None,
    )
    await db.flush()
    return node


async def delete_node(db: AsyncSession, user: User, node: FolioNode) -> None:
    """Soft delete; its children disappear with it."""
    (await authz.authorize(db, user, "folio", "folio.create")).raise_if_denied()
    node.deleted_at = utcnow()
    record(db, node, user, "deleted")
    await db.flush()
