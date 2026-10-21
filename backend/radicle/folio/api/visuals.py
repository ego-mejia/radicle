"""Visuals over REST (Folio 3.3 and 3.4): check a visual, and add a block to a draft."""

import uuid
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import Field

from radicle.folio.services import access, drafts, nodes, visuals
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Input, Output

router = APIRouter(tags=["folio"])


class VisualCheckIn(Input):
    format: Literal["svg", "html"]
    code: str
    title: str | None = None
    description: str | None = None


class VisualCheckOut(Output):
    valid: bool = Field(description="False when a problem would stop it")
    problems: list[str] = Field(description="What to fix before it goes in a page")
    warnings: list[str] = Field(description="What would make it better (tokens, description)")


class BlockIn(Input):
    block: dict[str, Any] = Field(description="One block of the document schema (TipTap JSON)")
    after_heading: str | None = Field(
        default=None, description="Add it at the end of this section; the end of the doc if not"
    )


class BlockOut(Output):
    content_md: str = Field(description="The whole draft after adding the block")


@router.post("/visuals/check", response_model=VisualCheckOut)
async def check_visual(body: VisualCheckIn, principal: CurrentPrincipal, db: Db) -> VisualCheckOut:
    """What the sandbox would block in a visual, and how to make it follow the theme."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    report = visuals.check(body.format, body.code, body.description, body.title)
    return VisualCheckOut(valid=report.valid, problems=report.problems, warnings=report.warnings)


@router.post("/nodes/{node_id}/blocks", response_model=BlockOut)
async def add_block(
    node_id: uuid.UUID, body: BlockIn, principal: CurrentPrincipal, db: Db
) -> BlockOut:
    """Add a block to the draft under a heading. Visuals are checked first."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    node = await nodes.get_node(db, principal.user, node_id)
    await access.require_edit(db, principal.user, node)
    current = await drafts.get_draft(db, node)
    doc = visuals.insert(current.content_json, body.block, body.after_heading)
    saved = await drafts.save_draft(db, principal.user, node, content_json=doc)
    return BlockOut(content_md=saved.content_md)
