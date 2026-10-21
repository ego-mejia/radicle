"""Public links (Folio 5.1): a page or a whole space, read-only and without an account.

- Only the space's admins create, list and revoke them.
- What a link shows is decided when it is opened, not when it was made: published pages
  and the folders above them, never archived or deleted ones, and never a page under a
  view restriction (nor anything below it). A page link to a page restricted later stops
  working; a space link just leaves that branch out.
- Nothing about people leaves: no comments, no owner, no mentions or assignees in the text.
"""

import copy
import secrets
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import (
    FolioNode,
    FolioPageRestriction,
    FolioSpace,
    FolioVersion,
    NodeKind,
    RestrictionMode,
)
from radicle.folio.db.public_links import FolioPublicLink, PublicTarget
from radicle.folio.services import access
from radicle.platform.db.models import User, utcnow
from radicle.platform.errors import NotFound, ValidationFailed

ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
READABLE = (NodeKind.page, NodeKind.blog_post)
# Metadata a stranger may see; the owner and anything else stays inside.
PUBLIC_METADATA = ("description", "doc_type", "labels", "language", "audiences")


def new_token() -> str:
    """32 random bytes in base62 (43 characters)."""
    n = int.from_bytes(secrets.token_bytes(32), "big")
    out = []
    while n:
        n, r = divmod(n, 62)
        out.append(ALPHABET[r])
    return "".join(reversed(out)).rjust(43, "0")


def _invalid(field: str, message: str) -> ValidationFailed:
    return ValidationFailed(message, errors=[{"field": field, "message": "invalid"}])


def _closed() -> Select[Any]:
    """Nodes under a view restriction, archived or deleted, with all their descendants."""
    restricted = select(FolioPageRestriction.node_id).where(
        FolioPageRestriction.mode == RestrictionMode.view
    )
    roots = select(FolioNode.id).where(
        or_(
            FolioNode.id.in_(restricted),
            FolioNode.deleted_at.is_not(None),
            FolioNode.archived_at.is_not(None),
        )
    )
    closed = roots.cte("folio_public_closed", recursive=True)
    closed = closed.union_all(select(FolioNode.id).where(FolioNode.parent_id == closed.c.id))
    return select(closed.c.id)


async def _open_nodes(db: AsyncSession, space_id: uuid.UUID) -> list[FolioNode]:
    """Published pages and folders of the space that a stranger may see, in tree order."""
    rows = await db.scalars(
        select(FolioNode)
        .where(
            FolioNode.space_id == space_id,
            ~FolioNode.id.in_(_closed()),
            or_(
                FolioNode.kind == NodeKind.folder,
                FolioNode.kind.in_(READABLE) & FolioNode.published_version_id.is_not(None),
            ),
        )
        .order_by(FolioNode.rank, FolioNode.id)
    )
    nodes = list(rows)
    # Folders show only when something readable is under them.
    by_parent: dict[uuid.UUID | None, list[FolioNode]] = {}
    for n in nodes:
        by_parent.setdefault(n.parent_id, []).append(n)

    def has_pages(node: FolioNode) -> bool:
        return node.kind in READABLE or any(has_pages(c) for c in by_parent.get(node.id, []))

    return [n for n in nodes if has_pages(n)]


async def _space_of(db: AsyncSession, link: FolioPublicLink) -> FolioSpace | None:
    if link.target_type == PublicTarget.space:
        space = await db.get(FolioSpace, link.target_id)
    else:
        node = await db.get(FolioNode, link.target_id)
        space = await db.get(FolioSpace, node.space_id) if node else None
    return space if space and space.deleted_at is None else None


async def _target(db: AsyncSession, user: User, target: FolioNode | FolioSpace) -> FolioSpace:
    """The space whose admins decide, after checking the target can be shared."""
    if isinstance(target, FolioSpace):
        await access.require_admin(db, user, target)
        return target
    space = await db.get_one(FolioSpace, target.space_id)
    await access.require_admin(db, user, space)
    if target.kind not in READABLE:
        raise _invalid("target", "Only pages and blog posts get a public link; share the space.")
    if target.published_version_id is None:
        raise _invalid("target", "Publish the page first: a public link shows the published one.")
    if target.id not in {n.id for n in await _open_nodes(db, space.id)}:
        raise _invalid(
            "target",
            "This page is restricted, archived or under one. Lift that before sharing it.",
        )
    return space


async def create_link(
    db: AsyncSession, user: User, target: FolioNode | FolioSpace, *, noindex: bool = True
) -> FolioPublicLink:
    await _target(db, user, target)
    link = FolioPublicLink(
        target_type=PublicTarget.space if isinstance(target, FolioSpace) else PublicTarget.node,
        target_id=target.id,
        token=new_token(),
        noindex=noindex,
        created_by=user.id,
    )
    db.add(link)
    await db.flush()
    return link


async def revoke(db: AsyncSession, user: User, link_id: uuid.UUID) -> FolioPublicLink:
    link = await db.get(FolioPublicLink, link_id)
    space = await _space_of(db, link) if link else None
    if link is None or space is None or link.revoked_at is not None:
        raise NotFound("No live public link with that id.")
    await access.require_admin(db, user, space)
    link.revoked_at = utcnow()
    return link


@dataclass(frozen=True)
class PublicPage:
    node: FolioNode
    version: FolioVersion
    children: list[FolioNode]


@dataclass(frozen=True)
class PublicView:
    link: FolioPublicLink
    space: FolioSpace
    nodes: list[FolioNode]  # what the link opens: the page alone, or the open tree
    page: PublicPage | None


async def resolve(
    db: AsyncSession, token: str
) -> tuple[FolioPublicLink, FolioSpace, list[FolioNode]]:
    """The link, its space and what it may show; a revoked or broken link is not found."""
    link = await db.scalar(select(FolioPublicLink).where(FolioPublicLink.token == token))
    space = await _space_of(db, link) if link and link.revoked_at is None else None
    if link is None or space is None:
        raise NotFound("This public link doesn't exist or was revoked.")
    open_nodes = await _open_nodes(db, space.id)
    if link.target_type == PublicTarget.node:
        open_nodes = [n for n in open_nodes if n.id == link.target_id]
        if not open_nodes:
            raise NotFound("This public link doesn't exist or was revoked.")
    return link, space, open_nodes


async def view(db: AsyncSession, token: str, node_id: uuid.UUID | None = None) -> PublicView:
    """Open a link: the page it points at, or a page of its space (none: the space's index).
    Counts one view."""
    link, space, open_nodes = await resolve(db, token)
    if link.target_type == PublicTarget.node:
        node_id = link.target_id
    page = None
    if node_id is not None:
        node = next((n for n in open_nodes if n.id == node_id and n.kind in READABLE), None)
        if node is None or node.published_version_id is None:
            raise NotFound("That page isn't part of this public link.")
        version = await db.get_one(FolioVersion, node.published_version_id)
        children = [n for n in open_nodes if n.parent_id == node.id and n.kind in READABLE]
        if link.target_type == PublicTarget.node:
            children = []
        page = PublicPage(node, version, children)
    await db.execute(
        update(FolioPublicLink)
        .where(FolioPublicLink.id == link.id)
        .values(view_count=FolioPublicLink.view_count + 1)
    )
    return PublicView(link, space, open_nodes, page)


def public_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    return {k: metadata[k] for k in PUBLIC_METADATA if k in metadata}


def scrub(doc: dict[str, Any]) -> dict[str, Any]:
    """The document without people in it: mentions become an ellipsis, assignees go."""
    out = copy.deepcopy(doc)

    def walk(node: dict[str, Any]) -> None:
        children = node.get("content") or []
        for i, child in enumerate(children):
            if child.get("type") == "mention":
                children[i] = {"type": "text", "text": "@…"}
                continue
            if child.get("type") == "actionItem":
                attrs = child.setdefault("attrs", {})
                attrs["assignee"] = None
            walk(child)

    walk(out)
    return out
