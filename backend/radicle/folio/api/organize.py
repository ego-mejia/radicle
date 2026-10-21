"""Organizing nodes over REST (Folio 2.6): archive and restore, the Archived section."""

import uuid

from fastapi import APIRouter

from radicle.folio.api.spaces import NodeOut, NodeRef, _node, _ref
from radicle.folio.services import archive, nodes, spaces
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Page, UtcDatetime
from radicle.platform.db.models import User

router = APIRouter(tags=["folio"])


class ArchivedOut(NodeRef):
    archived_at: UtcDatetime
    archived_by: str | None


async def _reader(db: Db, principal: CurrentPrincipal) -> None:
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()


@router.post("/nodes/{node_id}/archive", response_model=NodeOut)
async def archive_node(node_id: uuid.UUID, principal: CurrentPrincipal, db: Db) -> NodeOut:
    """Take the node and everything under it out of the tree, search and the RAG index.
    Needs the delete permission, like deleting."""
    await _reader(db, principal)
    node = await nodes.get_node(db, principal.user, node_id)
    return await _node(db, await archive.archive(db, principal.user, node))


@router.post("/nodes/{node_id}/unarchive", response_model=NodeOut)
async def unarchive_node(node_id: uuid.UUID, principal: CurrentPrincipal, db: Db) -> NodeOut:
    """Bring back what that archive took out, and index it again."""
    await _reader(db, principal)
    node = await nodes.get_node(db, principal.user, node_id)
    return await _node(db, await archive.unarchive(db, principal.user, node))


@router.get("/spaces/{key}/archived", response_model=Page[ArchivedOut])
async def list_archived(key: str, principal: CurrentPrincipal, db: Db) -> Page[ArchivedOut]:
    """The space's Archived section: what was archived, newest first."""
    await _reader(db, principal)
    space = await spaces.get_space(db, principal.user, key)
    rows = await archive.archived(db, principal.user, space)
    handles = {}
    for n in rows:
        if n.archived_by and n.archived_by not in handles:
            user = await db.get(User, n.archived_by)
            handles[n.archived_by] = user.handle if user else None
    return Page(
        items=[
            ArchivedOut(
                **_ref(n).model_dump(),
                archived_at=n.archived_at,
                archived_by=handles.get(n.archived_by) if n.archived_by else None,
            )
            for n in rows
            if n.archived_at is not None
        ]
    )
