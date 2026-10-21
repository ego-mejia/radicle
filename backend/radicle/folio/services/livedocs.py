"""Live docs (Folio 2.5): minutes and dailies that are always editable and never
published. The Y.Doc is the content; there is no metadata and no RAG indexing. Their
history is a snapshot every 10 minutes with changes, with who wrote in it.
"""

import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.collab import FolioLiveSnapshot
from radicle.folio.db.models import FolioNode, NodeKind
from radicle.folio.services import access, collab, nodes, schema, ydoc
from radicle.folio.services.parse_markdown import from_markdown
from radicle.platform.db.models import User, utcnow
from radicle.platform.errors import NotFound, ValidationFailed

SNAPSHOT_EVERY = timedelta(minutes=10)


def require_live(node: FolioNode) -> None:
    if node.kind != NodeKind.live_doc:
        raise ValidationFailed(
            f"'{node.title}' is not a live doc. Live docs are created with kind live_doc.",
            errors=[{"field": "node", "message": "not a live doc"}],
        )


async def snapshot(
    db: AsyncSession, node_id: uuid.UUID, content: dict[str, Any], authors: set[uuid.UUID]
) -> FolioLiveSnapshot:
    row = FolioLiveSnapshot(
        node_id=node_id,
        content_json=schema.validate(content),
        authors=sorted(authors, key=str),
        created_at=utcnow(),
    )
    db.add(row)
    await db.flush()
    return row


async def last_snapshot(db: AsyncSession, node_id: uuid.UUID) -> FolioLiveSnapshot | None:
    found: FolioLiveSnapshot | None = await db.scalar(
        select(FolioLiveSnapshot)
        .where(FolioLiveSnapshot.node_id == node_id)
        .order_by(FolioLiveSnapshot.created_at.desc(), FolioLiveSnapshot.id)
        .limit(1)
    )
    return found


async def snapshot_if_due(db: AsyncSession, node: FolioNode, authors: set[uuid.UUID]) -> None:
    """After a change made without a room: a snapshot when the last is 10 minutes old."""
    last = await last_snapshot(db, node.id)
    if last is not None and utcnow() - last.created_at < SNAPSHOT_EVERY:
        return
    doc = await collab.current(db, node)
    await snapshot(db, node.id, ydoc.to_json(doc), authors)


async def snapshots(db: AsyncSession, node: FolioNode) -> list[FolioLiveSnapshot]:
    require_live(node)
    rows = await db.scalars(
        select(FolioLiveSnapshot)
        .where(FolioLiveSnapshot.node_id == node.id)
        .order_by(FolioLiveSnapshot.created_at.desc(), FolioLiveSnapshot.id)
    )
    return list(rows)


async def get_snapshot(
    db: AsyncSession, node: FolioNode, snapshot_id: uuid.UUID
) -> FolioLiveSnapshot:
    require_live(node)
    row = await db.get(FolioLiveSnapshot, snapshot_id)
    if row is None or row.node_id != node.id:
        raise NotFound(f"Snapshot {snapshot_id} not found.", code="snapshot_not_found")
    return row


async def restore(
    db: AsyncSession, user: User, node: FolioNode, snapshot_id: uuid.UUID
) -> FolioLiveSnapshot:
    """Bring the doc back to a snapshot; that becomes a new snapshot, nothing is lost."""
    await access.require_edit(db, user, node)
    old = await get_snapshot(db, node, snapshot_id)
    content = old.content_json
    await collab.apply_change(db, node, user, lambda doc: ydoc.write(ydoc.fragment(doc), content))
    nodes.record(db, node, user, "snapshot_restored", snapshot=str(old.id))
    return await snapshot(db, node.id, content, {user.id})


async def append(db: AsyncSession, user: User, node: FolioNode, content_md: str) -> None:
    """Add Markdown at the end without touching what others are writing."""
    await access.require_edit(db, user, node)
    require_live(node)
    blocks = from_markdown(content_md)["content"]
    if not blocks:
        raise ValidationFailed(
            "Nothing to append: send some Markdown.",
            errors=[{"field": "content_md", "message": "empty"}],
        )
    await collab.apply_change(db, node, user, lambda doc: ydoc.append(ydoc.fragment(doc), blocks))
    if collab.rooms.get(node.id) is None:
        await snapshot_if_due(db, node, {user.id})
