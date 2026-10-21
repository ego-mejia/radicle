"""Copying and moving between spaces (Folio 2.6).

A copy is a new node whose draft holds the original's published content and metadata
(or its draft, if it was never published); nothing is published. With children, the
subtree you can see comes along in the same order. Moving to another space keeps the
node's id (and so its URL), history and restrictions.
"""

import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioDraft, FolioNode, FolioSpace, NodeKind
from radicle.folio.services import access, drafts, nodes, publishing, rag
from radicle.platform.db.models import User, utcnow
from radicle.platform.errors import ValidationFailed


async def _content(db: AsyncSession, node: FolioNode) -> tuple[dict[str, Any], dict[str, Any]]:
    version = await publishing.current_version(db, node)
    if version is not None:
        meta = {k: v for k, v in version.metadata_.items() if k != "title"}
        return version.content_json, meta
    draft = await drafts.get_draft(db, node)
    return draft.content_json, dict(draft.metadata)


async def copy_node(
    db: AsyncSession,
    user: User,
    node: FolioNode,
    *,
    space: FolioSpace,
    parent_id: uuid.UUID | None = None,
    include_children: bool = False,
) -> FolioNode:
    """Copy into `space` (under `parent_id`); needs create there."""
    if node.kind == NodeKind.blog_post and include_children:
        raise ValidationFailed(
            "Blog posts have no children to copy.",
            errors=[{"field": "include_children", "message": "not for blog posts"}],
        )
    copy = await nodes.create_node(
        db, user, space, kind=node.kind, title=node.title, parent_id=parent_id
    )
    copy.icon, copy.cover_asset_id = node.icon, node.cover_asset_id
    if node.kind != NodeKind.folder:
        content, metadata = await _content(db, node)
        db.add(FolioDraft(node_id=copy.id, content_json=content, metadata_=metadata))
    nodes.record(db, copy, user, "copied", source=str(node.id))
    await db.flush()
    if include_children:
        children = await db.scalars(
            select(FolioNode)
            .where(
                FolioNode.parent_id == node.id,
                FolioNode.archived_at.is_(None),
                await access.node_filter(db, user),
            )
            .order_by(FolioNode.rank, FolioNode.id)
        )
        for child in list(children):
            await copy_node(db, user, child, space=space, parent_id=copy.id, include_children=True)
    return copy


async def move_to_space(
    db: AsyncSession,
    user: User,
    node: FolioNode,
    space: FolioSpace,
    *,
    parent_id: uuid.UUID | None = None,
) -> FolioNode:
    """Move the node and its subtree to another space: create there, delete here."""
    await access.require_delete(db, user, node)
    await access.require_create(db, user, space)
    if node.kind == NodeKind.blog_post and parent_id is not None:
        raise ValidationFailed(
            "Blog posts live outside the tree: leave parent empty.",
            errors=[{"field": "parent", "message": "not for blog posts"}],
        )
    origin = node.space_id
    parent = await nodes._parent(db, user, space, parent_id)
    ids = await rag.subtree(db, node)
    await db.execute(update(FolioNode).where(FolioNode.id.in_(ids)).values(space_id=space.id))
    node.parent_id = parent.id if parent else None
    node.rank = await nodes._last_rank(db, space, node.parent_id)
    node.updated_at = utcnow()
    nodes.record(db, node, user, "moved_space", old_space=str(origin), new_space=str(space.id))
    await db.flush()
    await db.refresh(node)
    await rag.schedule(db, ids)
    return node
