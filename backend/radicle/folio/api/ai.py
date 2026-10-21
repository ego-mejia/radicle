"""AI in the editor over REST (Folio 4.6): proposals to accept or discard, never changes."""

import uuid
from typing import Literal

from fastapi import APIRouter, Query
from pydantic import Field

from radicle.folio.services import editor_ai, spaces
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Input, Output

router = APIRouter(tags=["folio"])


class AiAvailabilityOut(Output):
    available: bool
    reason: Literal["no_provider", "off_for_folio", "off_in_space"] | None
    message: str | None = Field(description="Why it is off and who can turn it on")


class NodeAiIn(Input):
    node_id: uuid.UUID


class SummaryOut(Output):
    summary: str = Field(description="Markdown bullets; insert it as a block if you want")


class RewriteIn(NodeAiIn):
    text: str = Field(description="The selected passage, in Markdown")
    mode: editor_ai.Mode
    language: str | None = Field(default=None, description="Only for translate, e.g. English")


class RewriteOut(Output):
    text: str = Field(description="The proposed passage; nothing changes until you accept it")


class MetadataSuggestionOut(Output):
    description: str | None
    labels: list[str]
    doc_type: str | None = Field(description="A key of the document types")


async def _reader(db: Db, principal: CurrentPrincipal) -> None:
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()


@router.get("/ai/availability", response_model=AiAvailabilityOut)
async def ai_availability(
    principal: CurrentPrincipal, db: Db, space: str = Query(description="The space key")
) -> AiAvailabilityOut:
    """Whether the editor shows its AI in this space."""
    await _reader(db, principal)
    off = await editor_ai.unavailable(db, await spaces.get_space(db, principal.user, space))
    return AiAvailabilityOut(
        available=off is None, reason=off, message=editor_ai.REASONS[off] if off else None
    )


@router.post("/ai/summarize", response_model=SummaryOut)
async def ai_summarize(body: NodeAiIn, principal: CurrentPrincipal, db: Db) -> SummaryOut:
    """A summary of the page you can read: the draft if you may edit it."""
    await _reader(db, principal)
    return SummaryOut(summary=await editor_ai.summarize(db, principal.user, body.node_id))


@router.post("/ai/rewrite", response_model=RewriteOut)
async def ai_rewrite(body: RewriteIn, principal: CurrentPrincipal, db: Db) -> RewriteOut:
    """A clearer, shorter, more formal or translated version of a selection."""
    await _reader(db, principal)
    text = await editor_ai.rewrite(
        db, principal.user, body.node_id, body.text, body.mode, body.language
    )
    return RewriteOut(text=text)


@router.post("/ai/suggest-metadata", response_model=MetadataSuggestionOut)
async def ai_suggest_metadata(
    body: NodeAiIn, principal: CurrentPrincipal, db: Db
) -> MetadataSuggestionOut:
    """Description, labels and document type for the publish dialog. It never publishes."""
    await _reader(db, principal)
    s = await editor_ai.suggest_metadata(db, principal.user, body.node_id)
    return MetadataSuggestionOut(description=s.description, labels=s.labels, doc_type=s.doc_type)
