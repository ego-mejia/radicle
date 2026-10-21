"""Archiving (Folio 2.6): an archived node and everything under it leave the tree, search
and the RAG index, and wait in the space's Archived section until restored.

The subtree gets the same `archived_at`, so restoring brings back exactly what that
archive took out, not what was archived on its own before.
"""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioNode, FolioSpace
from radicle.folio.services import access, rag
from radicle.folio.services.nodes import record
from radicle.platform.db.models import User, utcnow
from radicle.platform.errors import Conflict


async def archive(db: AsyncSession, user: User, node: FolioNode) -> FolioNode:
    await access.require_delete(db, user, node)
    if node.archived_at is not None:
        raise Conflict(f"'{node.title}' is already archived.", code="already_archived")
    ids = await rag.subtree(db, node)
    when = utcnow()
    await db.execute(
        update(FolioNode)
        .where(FolioNode.id.in_(ids), FolioNode.archived_at.is_(None))
        .values(archived_at=when, archived_by=user.id)
    )
    record(db, node, user, "archived", nodes=len(ids))
    await db.flush()
    await db.refresh(node)
    await rag.schedule(db, ids)
    return node


async def unarchive(db: AsyncSession, user: User, node: FolioNode) -> FolioNode:
    await access.require_delete(db, user, node)
    if node.archived_at is None:
        raise Conflict(f"'{node.title}' is not archived.", code="not_archived")
    if node.parent_id is not None:
        parent = await db.get(FolioNode, node.parent_id)
        if parent is not None and parent.archived_at is not None:
            raise Conflict(
                f"'{node.title}' is inside the archived '{parent.title}'. Restore that one.",
                code="parent_archived",
            )
    ids = await rag.subtree(db, node)
    await db.execute(
        update(FolioNode)
        .where(FolioNode.id.in_(ids), FolioNode.archived_at == node.archived_at)
        .values(archived_at=None, archived_by=None)
    )
    record(db, node, user, "unarchived")
    await db.flush()
    await db.refresh(node)
    await rag.schedule(db, ids)
    return node


async def archived(db: AsyncSession, user: User, space: FolioSpace) -> list[FolioNode]:
    """The space's archived roots you can see: what someone archived, newest first."""
    parent = FolioNode.__table__.alias("parent")
    rows = await db.scalars(
        select(FolioNode)
        .outerjoin(parent, parent.c.id == FolioNode.parent_id)
        .where(
            FolioNode.space_id == space.id,
            FolioNode.archived_at.is_not(None),
            await access.node_filter(db, user),
            # A root of an archive: its parent was not archived with it.
            (parent.c.id.is_(None))
            | (parent.c.archived_at.is_(None))
            | (parent.c.archived_at != FolioNode.archived_at),
        )
        .order_by(FolioNode.archived_at.desc(), FolioNode.id)
    )
    return list(rows)
