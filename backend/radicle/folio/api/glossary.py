"""The glossary over REST (Folio 4.6): approved terms for readers, the rest for admins."""

import uuid
from typing import Literal

from fastapi import APIRouter, Query
from pydantic import Field

from radicle.folio.db.glossary import FolioGlossaryTerm, TermStatus
from radicle.folio.services import glossary
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Input, Output, UtcDatetime

router = APIRouter(tags=["folio"])

Status = Literal["suggested", "approved", "rejected"]


class GlossarySource(Output):
    id: uuid.UUID
    title: str
    slug: str


class GlossaryTermOut(Output):
    id: uuid.UUID
    term: str
    aliases: list[str]
    definition: str
    status: Status
    source: GlossarySource | None = Field(description="The doc it comes from, if you can see it")
    updated_at: UtcDatetime


class GlossaryTermsOut(Output):
    items: list[GlossaryTermOut]


class GlossaryTermIn(Input):
    term: str
    definition: str
    aliases: list[str] = Field(default_factory=list)
    source: uuid.UUID | None = Field(default=None, description="The id of the source page")


class GlossaryTermPatch(Input):
    term: str | None = None
    definition: str | None = None
    aliases: list[str] | None = None
    source: uuid.UUID | None = Field(default=None, description="null removes it")
    status: Status | None = Field(default=None, description="approved shows it to readers")


def _out(t: glossary.Term) -> GlossaryTermOut:
    row, source = t.row, t.source
    return GlossaryTermOut(
        id=row.id,
        term=row.term,
        aliases=list(row.aliases),
        definition=row.definition,
        status=row.status.value,
        source=GlossarySource(id=source.id, title=source.title, slug=source.slug)
        if source
        else None,
        updated_at=row.updated_at,
    )


async def _one(db: Db, principal: CurrentPrincipal, row: FolioGlossaryTerm) -> GlossaryTermOut:
    return _out((await glossary.with_sources(db, principal.user, [row]))[0])


async def _reader(db: Db, principal: CurrentPrincipal) -> None:
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()


@router.get("/glossary", response_model=GlossaryTermsOut)
async def list_glossary(
    principal: CurrentPrincipal,
    db: Db,
    status: Status | None = Query(default=None, description="Not approved: Folio admins only"),
) -> GlossaryTermsOut:
    """Approved terms, A to Z, for tooltips when reading."""
    await _reader(db, principal)
    terms = await glossary.list_terms(db, principal.user, TermStatus(status) if status else None)
    return GlossaryTermsOut(items=[_out(t) for t in terms])


@router.post("/glossary", response_model=GlossaryTermOut, status_code=201)
async def create_glossary_term(
    body: GlossaryTermIn, principal: CurrentPrincipal, db: Db
) -> GlossaryTermOut:
    """A term written by a Folio admin, approved right away."""
    await _reader(db, principal)
    data = glossary.TermData(
        term=body.term, definition=body.definition, aliases=body.aliases, source_node_id=body.source
    )
    row = await glossary.create_term(db, principal.user, data)
    return await _one(db, principal, row)


@router.patch("/glossary/{term_id}", response_model=GlossaryTermOut)
async def patch_glossary_term(
    term_id: uuid.UUID, body: GlossaryTermPatch, principal: CurrentPrincipal, db: Db
) -> GlossaryTermOut:
    """Edit, approve or reject a term. Folio admins only."""
    await _reader(db, principal)
    data = glossary.TermData(
        term=body.term,
        definition=body.definition,
        aliases=body.aliases,
        source_node_id=body.source,
        clear_source="source" in body.model_fields_set and body.source is None,
        status=TermStatus(body.status) if body.status else None,
    )
    row = await glossary.update_term(db, principal.user, term_id, data)
    return await _one(db, principal, row)
