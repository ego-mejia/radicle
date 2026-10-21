"""Whiteboards over REST (Folio 3.5): the scene as it is now, for readers and embeds.
Drawing goes through the real-time room (/collab/{node_id})."""

import uuid
from typing import Any

from fastapi import APIRouter

from radicle.folio.db.models import FolioSpace
from radicle.folio.services import access, collab, nodes, whiteboards
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Output, UtcDatetime

router = APIRouter(tags=["folio"])


class WhiteboardOut(Output):
    node_id: uuid.UUID
    title: str
    space: str
    can_edit: bool
    elements: list[dict[str, Any]]
    updated_at: UtcDatetime


@router.get("/whiteboards/{node_id}", response_model=WhiteboardOut)
async def get_whiteboard(node_id: uuid.UUID, principal: CurrentPrincipal, db: Db) -> WhiteboardOut:
    """The scene's elements as they are now, and whether you may draw on it."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    node = await nodes.get_node(db, principal.user, node_id)
    row = await whiteboards.get(db, node)
    room = collab.rooms.get(node.id)  # someone is drawing: what is on their screens
    space = await db.get(FolioSpace, node.space_id)
    return WhiteboardOut(
        node_id=node.id,
        title=node.title,
        space=space.key if space else "",
        can_edit=await access.may_edit(db, principal.user, node),
        elements=whiteboards.read(room.doc) if room is not None else row.elements,
        updated_at=row.updated_at,
    )
