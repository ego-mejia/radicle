"""Publishing over REST (Folio 1.3): /api/v1/folio/nodes/{id}/publish."""

import uuid
from typing import Any

from fastapi import APIRouter
from pydantic import Field

from radicle.folio.db.models import FolioVersion
from radicle.folio.services import nodes, publishing
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Input, Output, UtcDatetime
from radicle.platform.db.models import User

router = APIRouter(tags=["folio"])


class VersionOut(Output):
    number: int
    title: str
    change_note: str | None
    author: str
    approved_by: str | None = Field(description="The admin who approved an agent's version")
    restored_from: int | None = Field(description="The version it restored, if any")
    created_at: UtcDatetime
    metadata: dict[str, Any]


class PublishIn(Input):
    change_note: str | None = Field(default=None, description="What changed, for the history")
    confirm: bool = Field(
        default=False, description="Publish even if someone published after this draft started"
    )


async def version_out(db: Db, v: FolioVersion) -> VersionOut:
    author = await db.get(User, v.author_id)
    approver = await db.get(User, v.approved_by) if v.approved_by else None
    restored = await db.get(FolioVersion, v.restored_from) if v.restored_from else None
    return VersionOut(
        number=v.number,
        title=v.title,
        change_note=v.change_note,
        author=author.handle if author else "",
        approved_by=approver.handle if approver else None,
        restored_from=restored.number if restored else None,
        created_at=v.created_at,
        metadata=v.metadata_,
    )


@router.post("/nodes/{node_id}/publish", response_model=VersionOut, status_code=201)
async def publish(
    node_id: uuid.UUID, body: PublishIn, principal: CurrentPrincipal, db: Db
) -> VersionOut:
    """Publish the draft as the next version. 422 lists every missing metadata field; 409
    when someone published after this draft started (send `confirm` to go ahead)."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    node = await nodes.get_node(db, principal.user, node_id)
    version = await publishing.publish(
        db, principal.user, node, change_note=body.change_note, confirm=body.confirm
    )
    return await version_out(db, version)
