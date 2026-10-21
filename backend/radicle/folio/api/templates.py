"""Templates over REST (Folio 3.1): list, manage, and create pages and spaces from them."""

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Query, Response
from pydantic import Field

from radicle.folio.api.spaces import NodeOut, SpaceOut, _node, _space
from radicle.folio.db.models import FolioSpace, NodeKind
from radicle.folio.db.templates import FolioTemplate, TemplateKind
from radicle.folio.services import templates
from radicle.folio.services.spaces import get_space
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Input, Output, Page, UtcDatetime

router = APIRouter(tags=["folio"])


class FolioTemplateOut(Output):
    id: uuid.UUID
    kind: Literal["page", "space"]
    scope: Literal["global", "space"]
    space: str | None
    builtin: bool = Field(description="Ships with Folio; admins may still edit it")
    name: str
    description: str
    icon: str | None
    doc_type_key: str | None
    content_json: dict[str, Any] | None
    default_metadata: dict[str, Any]
    structure: dict[str, Any] | None
    updated_at: UtcDatetime


class FolioTemplateIn(Input):
    kind: Literal["page", "space"] = "page"
    space: str | None = Field(default=None, description="A space key for a space's own template")
    name: str
    description: str = ""
    icon: str | None = None
    doc_type_key: str | None = None
    content_json: dict[str, Any] | None = None
    content_md: str | None = Field(
        default=None, description="Markdown with {{date}}, {{author}}, {{space}}, {{title}}"
    )
    default_metadata: dict[str, Any] | None = None
    structure: dict[str, Any] | None = Field(
        default=None,
        description='Space templates: {"pages": [{"title", "kind", "template", "children"}], '
        '"grants": [...]}',
    )


class FolioTemplatePatch(Input):
    name: str
    description: str = ""
    icon: str | None = None
    doc_type_key: str | None = None
    content_json: dict[str, Any] | None = None
    content_md: str | None = None
    default_metadata: dict[str, Any] | None = None
    structure: dict[str, Any] | None = None


class NodeFromTemplateIn(Input):
    template: uuid.UUID
    space: str
    title: str
    parent: uuid.UUID | None = None
    kind: Literal["page", "blog_post"] = "page"


class SpaceFromTemplateIn(Input):
    template: uuid.UUID
    key: str = Field(description="2 to 40 lowercase letters, digits and dashes")
    name: str


async def _reader(db: Db, principal: CurrentPrincipal) -> None:
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()


async def _out(db: Db, t: FolioTemplate) -> FolioTemplateOut:
    space = await db.get(FolioSpace, t.space_id) if t.space_id else None
    return FolioTemplateOut(
        id=t.id,
        kind=t.kind.value,
        scope=t.scope.value,
        space=space.key if space else None,
        builtin=t.builtin_key is not None,
        name=t.name,
        description=t.description,
        icon=t.icon,
        doc_type_key=t.doc_type_key,
        content_json=t.content_json,
        default_metadata=t.default_metadata,
        structure=t.structure,
        updated_at=t.updated_at,
    )


def _data(kind: TemplateKind, body: FolioTemplateIn | FolioTemplatePatch) -> templates.TemplateData:
    return templates.TemplateData(
        kind=kind,
        name=body.name,
        description=body.description,
        icon=body.icon,
        doc_type_key=body.doc_type_key,
        content_json=body.content_json,
        content_md=body.content_md,
        default_metadata=body.default_metadata,
        structure=body.structure,
    )


@router.get("/templates", response_model=Page[FolioTemplateOut])
async def list_templates(
    principal: CurrentPrincipal,
    db: Db,
    kind: Literal["page", "space"] | None = None,
    space: str | None = Query(default=None, description="Only this space's (plus global)"),
) -> Page[FolioTemplateOut]:
    """Templates you can use: Folio's own, the global ones and your spaces'."""
    await _reader(db, principal)
    in_space = await get_space(db, principal.user, space) if space else None
    rows = await templates.list_templates(
        db, principal.user, kind=TemplateKind(kind) if kind else None, space=in_space
    )
    return Page(items=[await _out(db, t) for t in rows])


@router.post("/templates", response_model=FolioTemplateOut, status_code=201)
async def create_template(
    body: FolioTemplateIn, principal: CurrentPrincipal, db: Db
) -> FolioTemplateOut:
    """Global templates take a Folio admin; a space's, that space's admin."""
    await _reader(db, principal)
    space = await get_space(db, principal.user, body.space) if body.space else None
    created = await templates.create_template(
        db, principal.user, _data(TemplateKind(body.kind), body), space=space
    )
    return await _out(db, created)


@router.get("/templates/{template_id}", response_model=FolioTemplateOut)
async def get_template(
    template_id: uuid.UUID, principal: CurrentPrincipal, db: Db
) -> FolioTemplateOut:
    await _reader(db, principal)
    return await _out(db, await templates.get_template(db, principal.user, template_id))


@router.patch("/templates/{template_id}", response_model=FolioTemplateOut)
async def update_template(
    template_id: uuid.UUID, body: FolioTemplatePatch, principal: CurrentPrincipal, db: Db
) -> FolioTemplateOut:
    await _reader(db, principal)
    found = await templates.get_template(db, principal.user, template_id)
    updated = await templates.update_template(db, principal.user, found, _data(found.kind, body))
    return await _out(db, updated)


@router.delete("/templates/{template_id}", status_code=204)
async def archive_template(template_id: uuid.UUID, principal: CurrentPrincipal, db: Db) -> Response:
    """Archive it: pages made from it keep their content."""
    await _reader(db, principal)
    found = await templates.get_template(db, principal.user, template_id)
    await templates.archive_template(db, principal.user, found)
    return Response(status_code=204)


@router.post("/nodes/from-template", response_model=NodeOut, status_code=201)
async def node_from_template(
    body: NodeFromTemplateIn, principal: CurrentPrincipal, db: Db
) -> NodeOut:
    """A page or post whose draft starts with the template's document and metadata."""
    await _reader(db, principal)
    template = await templates.get_template(db, principal.user, body.template)
    space = await get_space(db, principal.user, body.space)
    node = await templates.create_page(
        db,
        principal.user,
        template,
        space,
        title=body.title,
        parent_id=body.parent,
        kind=NodeKind(body.kind),
    )
    return await _node(db, principal.user, node)


@router.post("/spaces/from-template", response_model=SpaceOut, status_code=201)
async def space_from_template(
    body: SpaceFromTemplateIn, principal: CurrentPrincipal, db: Db
) -> SpaceOut:
    """A space with the template's folders, pages and grants."""
    await _reader(db, principal)
    template = await templates.get_template(db, principal.user, body.template)
    space = await templates.create_space(db, principal.user, template, key=body.key, name=body.name)
    return await _space(db, principal.user, space)
