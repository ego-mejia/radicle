"""Where collaborative documents live (Folio 2.2, ADR 0039): the compacted state in
folio_ydocs plus the updates that came after it in folio_yupdates.

A document that was never opened together is seeded once from its phase 1 draft (or its
published content), so every client starts from the same Yjs structure. The draft's
`content_json` is kept as the JSON read of the Y.Doc, for REST, MCP and publishing.
"""

import uuid
from typing import Any

import pycrdt
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.collab import FolioYDoc, FolioYUpdate
from radicle.folio.db.models import FolioDraft, FolioNode
from radicle.folio.services import publishing, schema, ydoc
from radicle.platform.db.models import utcnow


async def _seed_content(db: AsyncSession, node: FolioNode) -> dict[str, Any]:
    draft = await db.get(FolioDraft, node.id)
    if draft is not None:
        return draft.content_json
    version = await publishing.current_version(db, node)
    return version.content_json if version is not None else schema.empty()


async def load(db: AsyncSession, node: FolioNode) -> pycrdt.Doc[Any]:
    """The node's Y.Doc: the stored state with every later update applied."""
    row = await db.get(FolioYDoc, node.id)
    if row is None:
        seeded = ydoc.from_json(await _seed_content(db, node))
        await db.execute(
            insert(FolioYDoc)
            .values(node_id=node.id, state=seeded.get_update(), updated_at=utcnow())
            .on_conflict_do_nothing()
        )
        await db.flush()
        row = await db.get(FolioYDoc, node.id, populate_existing=True)
    doc: pycrdt.Doc[Any] = pycrdt.Doc()
    if row is not None:
        doc.apply_update(row.state)
    updates = await db.scalars(
        select(FolioYUpdate.update).where(FolioYUpdate.node_id == node.id).order_by(FolioYUpdate.id)
    )
    for update in updates:
        doc.apply_update(update)
    return doc


async def append_update(db: AsyncSession, node_id: uuid.UUID, update: bytes) -> None:
    db.add(FolioYUpdate(node_id=node_id, update=update))
    await db.flush()


async def compact(db: AsyncSession, node_id: uuid.UUID, doc: pycrdt.Doc[Any]) -> int:
    """Fold the pending updates into the stored state; returns how many were folded."""
    last = await db.scalar(select(func.max(FolioYUpdate.id)).where(FolioYUpdate.node_id == node_id))
    await db.execute(
        insert(FolioYDoc)
        .values(node_id=node_id, state=doc.get_update(), updated_at=utcnow())
        .on_conflict_do_update(
            index_elements=["node_id"], set_={"state": doc.get_update(), "updated_at": utcnow()}
        )
    )
    if last is None:
        return 0
    result = await db.execute(
        delete(FolioYUpdate).where(FolioYUpdate.node_id == node_id, FolioYUpdate.id <= last)
    )
    await db.flush()
    return int(getattr(result, "rowcount", 0) or 0)


async def save_json(db: AsyncSession, node: FolioNode, doc: pycrdt.Doc[Any]) -> bool:
    """Keep the draft's JSON in step with the Y.Doc; False if it read as invalid (the
    draft then keeps its last valid content)."""
    try:
        content = schema.validate(ydoc.to_json(doc))
    except schema.SchemaError:
        return False
    row = await db.get(FolioDraft, node.id)
    if row is None:
        row = FolioDraft(node_id=node.id, content_json=content, metadata_={})
        db.add(row)
    elif row.content_json == content:
        return True
    row.content_json = content
    row.updated_at = utcnow()
    await db.flush()
    # Here, not at the top: actions changes documents through the room, which uses this.
    from radicle.folio.services import actions

    await actions.sync(db, node, content, None)
    return True
