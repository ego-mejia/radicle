"""Live docs over REST (Folio 2.5): their snapshots, restoring one, and appending."""

import uuid

from fastapi import APIRouter
from pydantic import Field
from sqlalchemy import select

from radicle.folio.db.collab import FolioLiveSnapshot
from radicle.folio.services import collab, convert, livedocs, nodes, ydoc
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Input, Output, Page, UtcDatetime
from radicle.platform.db.models import User

router = APIRouter(tags=["folio"])


class SnapshotOut(Output):
    id: uuid.UUID
    created_at: UtcDatetime
    authors: list[str] = Field(description="Handles of who wrote since the previous one")


class SnapshotContentOut(SnapshotOut):
    content_json: dict[str, object]
    content_md: str


class AppendIn(Input):
    content_md: str = Field(description="Markdown to add at the end")


class LiveOut(Output):
    content_md: str = Field(description="The whole doc after appending")


async def _reader(db: Db, principal: CurrentPrincipal) -> None:
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()


async def _out(db: Db, row: FolioLiveSnapshot) -> SnapshotOut:
    handles = {}
    if row.authors:
        found = await db.execute(select(User.id, User.handle).where(User.id.in_(row.authors)))
        handles = {user_id: handle for user_id, handle in found.all()}
    return SnapshotOut(
        id=row.id,
        created_at=row.created_at,
        authors=[handles[a] for a in row.authors if a in handles],
    )


@router.get("/nodes/{node_id}/snapshots", response_model=Page[SnapshotOut])
async def list_snapshots(
    node_id: uuid.UUID, principal: CurrentPrincipal, db: Db
) -> Page[SnapshotOut]:
    """A live doc's history, newest first."""
    await _reader(db, principal)
    node = await nodes.get_node(db, principal.user, node_id)
    rows = await livedocs.snapshots(db, node)
    return Page(items=[await _out(db, r) for r in rows])


@router.get("/nodes/{node_id}/snapshots/{snapshot_id}", response_model=SnapshotContentOut)
async def get_snapshot(
    node_id: uuid.UUID, snapshot_id: uuid.UUID, principal: CurrentPrincipal, db: Db
) -> SnapshotContentOut:
    await _reader(db, principal)
    node = await nodes.get_node(db, principal.user, node_id)
    row = await livedocs.get_snapshot(db, node, snapshot_id)
    base = await _out(db, row)
    return SnapshotContentOut(
        **base.model_dump(),
        content_json=row.content_json,
        content_md=convert.to_markdown(row.content_json),
    )


@router.post(
    "/nodes/{node_id}/snapshots/{snapshot_id}/restore",
    response_model=SnapshotOut,
    status_code=201,
)
async def restore_snapshot(
    node_id: uuid.UUID, snapshot_id: uuid.UUID, principal: CurrentPrincipal, db: Db
) -> SnapshotOut:
    """Bring the doc back to a snapshot, live for whoever is editing; it becomes a new one."""
    await _reader(db, principal)
    node = await nodes.get_node(db, principal.user, node_id)
    return await _out(db, await livedocs.restore(db, principal.user, node, snapshot_id))


@router.post("/nodes/{node_id}/append", response_model=LiveOut)
async def append(
    node_id: uuid.UUID, body: AppendIn, principal: CurrentPrincipal, db: Db
) -> LiveOut:
    """Add Markdown at the end of a live doc without touching what others are writing."""
    await _reader(db, principal)
    node = await nodes.get_node(db, principal.user, node_id)
    await livedocs.append(db, principal.user, node, body.content_md)
    doc = await collab.current(db, node)
    return LiveOut(content_md=convert.to_markdown(ydoc.to_json(doc)))
