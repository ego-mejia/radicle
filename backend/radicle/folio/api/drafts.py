"""A page's live draft over REST (Folio 1.2): /api/v1/folio/nodes/{id}/draft."""

import uuid
from typing import Any

from fastapi import APIRouter
from pydantic import Field

from radicle.folio.services import drafts, nodes
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Input, Output, UtcDatetime

router = APIRouter(tags=["folio"])


class DraftOut(Output):
    content_json: dict[str, Any] = Field(description="TipTap document")
    content_md: str = Field(description="The same content as Markdown")
    metadata: dict[str, Any] = Field(description="May be incomplete until publishing")
    saved: bool = Field(description="False until someone writes")
    updated_at: UtcDatetime | None


class DraftIn(Input):
    content_json: dict[str, Any] | None = Field(default=None, description="TipTap document")
    content_md: str | None = Field(default=None, description="Markdown (docs/folio/markdown.md)")
    metadata: dict[str, Any] | None = None


def _out(d: drafts.Draft) -> DraftOut:
    return DraftOut(
        content_json=d.content_json,
        content_md=d.content_md,
        metadata=d.metadata,
        saved=d.exists,
        updated_at=d.draft.updated_at if d.draft else None,
    )


@router.get("/nodes/{node_id}/draft", response_model=DraftOut)
async def get_draft(node_id: uuid.UUID, principal: CurrentPrincipal, db: Db) -> DraftOut:
    (await authz.authorize(db, principal.user, "folio", "folio.create")).raise_if_denied()
    node = await nodes.get_node(db, principal.user, node_id)
    return _out(await drafts.get_draft(db, node))


@router.put("/nodes/{node_id}/draft", response_model=DraftOut)
async def put_draft(
    node_id: uuid.UUID, body: DraftIn, principal: CurrentPrincipal, db: Db
) -> DraftOut:
    """Save the draft: content as JSON or Markdown (one of them), and/or metadata."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    node = await nodes.get_node(db, principal.user, node_id)
    saved = await drafts.save_draft(
        db,
        principal.user,
        node,
        content_json=body.content_json,
        content_md=body.content_md,
        metadata=body.metadata,
    )
    return _out(saved)
