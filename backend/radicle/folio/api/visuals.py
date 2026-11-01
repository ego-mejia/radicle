"""Visuals over REST (Folio 3.3 and 3.4, ADR 0046): check a visual, add a block to a
draft, and list, read, change or remove the visuals already in it."""

import uuid
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import Field

from radicle.folio.db.models import FolioNode
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


class VisualSummary(Output):
    index: int = Field(description="Position among the draft's visuals, from 0")
    title: str | None
    format: Literal["svg", "html"]
    description: str
    size: int = Field(description="Bytes of code")


class VisualListOut(Output):
    items: list[VisualSummary]


class VisualOut(Output):
    index: int
    format: Literal["svg", "html"]
    code: str
    title: str | None
    description: str


class VisualPatch(Input):
    format: Literal["svg", "html"] | None = None
    code: str | None = None
    title: str | None = None
    description: str | None = None


class VisualChangeOut(Output):
    visuals: list[VisualSummary] = Field(description="The draft's visuals after the change")
    content_md: str = Field(description="The whole draft after the change")


async def _editable_draft(
    db: Db, principal: CurrentPrincipal, node_id: uuid.UUID
) -> tuple[FolioNode, dict[str, Any]]:
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    node = await nodes.get_node(db, principal.user, node_id)
    await access.require_edit(db, principal.user, node)
    return node, (await drafts.get_draft(db, node)).content_json


async def _save(
    db: Db, principal: CurrentPrincipal, node: FolioNode, doc: dict[str, Any]
) -> VisualChangeOut:
    saved = await drafts.save_draft(db, principal.user, node, content_json=doc)
    items = [VisualSummary(**v) for v in visuals.summary(doc)]
    return VisualChangeOut(visuals=items, content_md=saved.content_md)


@router.get("/nodes/{node_id}/visuals", response_model=VisualListOut)
async def list_visuals(node_id: uuid.UUID, principal: CurrentPrincipal, db: Db) -> VisualListOut:
    """The draft's visuals in document order, without their code."""
    _, doc = await _editable_draft(db, principal, node_id)
    return VisualListOut(items=[VisualSummary(**v) for v in visuals.summary(doc)])


@router.get("/nodes/{node_id}/visuals/{index}", response_model=VisualOut)
async def get_visual(
    node_id: uuid.UUID, index: int, principal: CurrentPrincipal, db: Db
) -> VisualOut:
    """One visual of the draft with its code."""
    _, doc = await _editable_draft(db, principal, node_id)
    return VisualOut(**visuals.get_visual(doc, index))


@router.patch("/nodes/{node_id}/visuals/{index}", response_model=VisualChangeOut)
async def update_visual(
    node_id: uuid.UUID, index: int, body: VisualPatch, principal: CurrentPrincipal, db: Db
) -> VisualChangeOut:
    """Change some fields of one visual; it is checked again like a new one."""
    node, doc = await _editable_draft(db, principal, node_id)
    edited = visuals.update_visual(doc, index, body.model_dump(exclude_none=True))
    return await _save(db, principal, node, edited)


@router.delete("/nodes/{node_id}/visuals/{index}", response_model=VisualChangeOut)
async def remove_visual(
    node_id: uuid.UUID, index: int, principal: CurrentPrincipal, db: Db
) -> VisualChangeOut:
    """Take one visual out of the draft."""
    node, doc = await _editable_draft(db, principal, node_id)
    return await _save(db, principal, node, visuals.remove_visual(doc, index))
