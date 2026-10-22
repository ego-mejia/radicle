"""Folio's catalogs and the publishing schema over REST (Folio 1.3)."""

from typing import Literal

from fastapi import APIRouter, Query
from pydantic import Field

from radicle.folio.services import catalogs
from radicle.folio.services.catalogs import Catalog, Entry
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Input, Output, Page

router = APIRouter(tags=["folio"])


class EntryOut(Output):
    key: str
    name: str
    description: str
    position: int
    archived: bool


class EntryIn(Input):
    key: str = Field(description="Lowercase letters, digits and dashes, e.g. how-to")
    name: str
    description: str = ""


class EntryPatch(Input):
    name: str | None = None
    description: str | None = None
    position: int | None = None
    archived: bool | None = Field(default=None, description="Archived entries can't be chosen")


class FieldRule(Output):
    name: str
    required: bool
    rule: str


class MetadataSchemaOut(Output):
    fields: list[FieldRule]
    doc_types: list[EntryOut]
    audiences: list[EntryOut]
    languages: list[EntryOut]


def _out(e: Entry) -> EntryOut:
    return EntryOut(
        key=e.key,
        name=e.name,
        description=e.description,
        position=e.position,
        archived=e.archived_at is not None,
    )


FIELDS = [
    FieldRule(name="title", required=True, rule="1 to 200 characters"),
    FieldRule(name="description", required=True, rule="40 to 400 characters, 1 to 3 sentences"),
    FieldRule(name="doc_type", required=True, rule="A key of doc_types"),
    FieldRule(name="labels", required=True, rule="1 to 15, lowercase letters, digits, - and _"),
    FieldRule(name="owner", required=True, rule="Handle of an active person who can see the space"),
    FieldRule(name="audiences", required=True, rule="One or more keys of audiences"),
    FieldRule(name="language", required=True, rule="A key of languages"),
    FieldRule(name="docket_project", required=False, rule="A Docket project key, e.g. PA"),
    FieldRule(
        name="docket_milestones", required=False, rule="Up to 20 milestone names of that project"
    ),
    FieldRule(name="docket_areas", required=False, rule="Up to 20 area names of that project"),
    FieldRule(
        name="decision_status",
        required=False,
        rule="For a decision log: accepted, proposed or replaced",
    ),
    FieldRule(name="decision_topic", required=False, rule="For a decision log: up to 40 chars"),
    FieldRule(
        name="decision_replaces", required=False, rule="Id of the decision this one replaces"
    ),
]


@router.get("/metadata-schema", response_model=MetadataSchemaOut)
async def metadata_schema(principal: CurrentPrincipal, db: Db) -> MetadataSchemaOut:
    """What publishing needs: the fields with their rules and the catalogs' active entries."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    return MetadataSchemaOut(
        fields=FIELDS,
        doc_types=[_out(e) for e in await catalogs.entries(db, "doc-types")],
        audiences=[_out(e) for e in await catalogs.entries(db, "audiences")],
        languages=[_out(e) for e in await catalogs.entries(db, "languages")],
    )


CatalogPath = Literal["doc-types", "audiences", "languages"]


@router.get("/admin/{catalog}", response_model=Page[EntryOut])
async def list_entries(
    catalog: CatalogPath,
    principal: CurrentPrincipal,
    db: Db,
    include_archived: bool = Query(default=True),
) -> Page[EntryOut]:
    (await authz.authorize(db, principal.user, "folio", "folio.admin")).raise_if_denied()
    rows = await catalogs.entries(db, catalog, include_archived=include_archived)
    return Page(items=[_out(e) for e in rows])


@router.post("/admin/{catalog}", response_model=EntryOut, status_code=201)
async def create_entry(
    catalog: CatalogPath, body: EntryIn, principal: CurrentPrincipal, db: Db
) -> EntryOut:
    entry = await catalogs.create(
        db, principal.user, catalog, key=body.key, name=body.name, description=body.description
    )
    return _out(entry)


@router.patch("/admin/{catalog}/{key}", response_model=EntryOut)
async def update_entry(
    catalog: CatalogPath, key: str, body: EntryPatch, principal: CurrentPrincipal, db: Db
) -> EntryOut:
    changes = catalogs.EntryChanges(
        name=body.name,
        description=body.description,
        position=body.position,
        archived=body.archived,
    )
    return _out(await catalogs.update(db, principal.user, catalog, key, changes))


__all__ = ["Catalog", "router"]
