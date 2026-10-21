"""Public links over REST (Folio 5.1): space admins manage them under /public-links, and
anyone with the token reads under /pub/{token}, without an account."""

import uuid
from typing import Any, Literal
from urllib.parse import quote

from fastapi import APIRouter, Query, Response
from fastapi.responses import RedirectResponse
from pydantic import Field

from radicle.folio.db.models import FolioNode, FolioSpace
from radicle.folio.db.public_links import FolioPublicLink, PublicTarget
from radicle.folio.services import assets, audit_log, nodes, public_links, spaces
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Input, Output, UtcDatetime
from radicle.platform.config import get_settings
from radicle.platform.errors import ValidationFailed
from radicle.platform.storage import get_storage

router = APIRouter(tags=["folio"])


class PublicLinkOut(Output):
    id: uuid.UUID
    url: str = Field(description="Opens without an account")
    target_type: Literal["node", "space"]
    target_id: uuid.UUID
    noindex: bool = Field(description="Asks search engines not to index it")
    view_count: int
    created_at: UtcDatetime


class PublicLinksOut(Output):
    items: list[PublicLinkOut]


class PublicLinkIn(Input):
    node: uuid.UUID | None = Field(default=None, description="A published page or post")
    space: str | None = Field(default=None, description="Space key, for the whole space")
    noindex: bool = True


class PublicSpaceOut(Output):
    name: str
    description: str
    icon: str | None
    cover_asset_id: uuid.UUID | None


class PublicNodeOut(Output):
    id: uuid.UUID
    kind: str
    title: str
    slug: str
    icon: str | None
    parent_id: uuid.UUID | None


class PublicPageOut(PublicNodeOut):
    cover_asset_id: uuid.UUID | None
    published_at: UtcDatetime | None
    version: int
    metadata: dict[str, Any] = Field(description="Only what a stranger may see")
    content_json: dict[str, Any] = Field(description="Without mentions or assignees")
    children: list[PublicNodeOut]


class PublicViewOut(Output):
    target_type: Literal["node", "space"]
    space: PublicSpaceOut
    nodes: list[PublicNodeOut] = Field(description="The space's open tree, flat, in order")
    page: PublicPageOut | None


def _link_out(link: FolioPublicLink) -> PublicLinkOut:
    return PublicLinkOut(
        id=link.id,
        url=f"{get_settings().base_url.rstrip('/')}/pub/{link.token}",
        target_type=link.target_type.value,
        target_id=link.target_id,
        noindex=link.noindex,
        view_count=link.view_count,
        created_at=link.created_at,
    )


def _node_out(n: FolioNode) -> PublicNodeOut:
    return PublicNodeOut(
        id=n.id, kind=n.kind.value, title=n.title, slug=n.slug, icon=n.icon, parent_id=n.parent_id
    )


def _headers(response: Response, noindex: bool) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    if noindex:
        response.headers["X-Robots-Tag"] = "noindex, nofollow"


def _view_out(v: public_links.PublicView) -> PublicViewOut:
    page = None
    if v.page is not None:
        n, version = v.page.node, v.page.version
        page = PublicPageOut(
            **_node_out(n).model_dump(),
            cover_asset_id=n.cover_asset_id,
            published_at=n.published_at,
            version=version.number,
            metadata=public_links.public_metadata(version.metadata_),
            content_json=public_links.scrub(version.content_json),
            children=[_node_out(c) for c in v.page.children],
        )
    return PublicViewOut(
        target_type=v.link.target_type.value,
        space=PublicSpaceOut(
            name=v.space.name,
            description=v.space.description,
            icon=v.space.icon,
            cover_asset_id=v.space.cover_asset_id,
        ),
        nodes=[_node_out(n) for n in v.nodes],
        page=page,
    )


async def _target(
    db: Db, principal: CurrentPrincipal, node: uuid.UUID | None, space: str | None
) -> FolioNode | FolioSpace:
    if node is not None and space is None:
        return await nodes.get_node(db, principal.user, node)
    if space is not None and node is None:
        return await spaces.get_space(db, principal.user, space)
    raise ValidationFailed(
        "Send either node (a page id) or space (a space key).",
        errors=[{"field": "node", "message": "one of node or space"}],
    )


@router.get("/public-links", response_model=PublicLinksOut)
async def list_public_links(
    principal: CurrentPrincipal,
    db: Db,
    node: uuid.UUID | None = Query(default=None, description="A page's links"),
    space: str | None = Query(default=None, description="A space's links, its pages' too"),
) -> PublicLinksOut:
    """Live public links. Space admins only."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    target = await _target(db, principal, node, space)
    rows = await public_links.list_links(db, principal.user, target)
    return PublicLinksOut(items=[_link_out(r) for r in rows])


@router.post("/public-links", response_model=PublicLinkOut, status_code=201)
async def create_public_link(
    body: PublicLinkIn, principal: CurrentPrincipal, db: Db
) -> PublicLinkOut:
    """A read-only link to a published page or a whole space. Space admins only."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    target = await _target(db, principal, body.node, body.space)
    link = await public_links.create_link(db, principal.user, target, noindex=body.noindex)
    audit_log.record(
        db,
        principal.user,
        "public_link_create",
        target_type="folio_space" if link.target_type == PublicTarget.space else "folio_node",
        target_id=link.target_id,
        after={"link": str(link.id), "noindex": link.noindex},
    )
    return _link_out(link)


@router.delete("/public-links/{link_id}", status_code=204)
async def revoke_public_link(link_id: uuid.UUID, principal: CurrentPrincipal, db: Db) -> Response:
    """From now on the link answers 404."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    link = await public_links.revoke(db, principal.user, link_id)
    audit_log.record(
        db,
        principal.user,
        "public_link_revoke",
        target_type="folio_space" if link.target_type == PublicTarget.space else "folio_node",
        target_id=link.target_id,
        before={"link": str(link.id), "views": link.view_count},
    )
    return Response(status_code=204)


@router.get("/pub/{token}", response_model=PublicViewOut)
async def read_public(token: str, response: Response, db: Db) -> PublicViewOut:
    """Without an account: the shared page, or the shared space's index."""
    view = await public_links.view(db, token)
    _headers(response, view.link.noindex)
    return _view_out(view)


@router.get("/pub/{token}/pages/{node_id}", response_model=PublicViewOut)
async def read_public_page(
    token: str, node_id: uuid.UUID, response: Response, db: Db
) -> PublicViewOut:
    """Without an account: one page of a shared space."""
    view = await public_links.view(db, token, node_id)
    _headers(response, view.link.noindex)
    return _view_out(view)


@router.get("/pub/{token}/assets/{asset_id}", response_class=Response)
async def read_public_asset(token: str, asset_id: uuid.UUID, db: Db) -> Response:
    """An image or file of a shared page."""
    link, asset = await public_links.asset(db, token, asset_id)
    inline = asset.mime_type in assets.INLINE_TYPES
    url = await get_storage().download_url(asset.storage_key, asset.filename, inline=inline)
    if url is not None:
        return RedirectResponse(url, status_code=302)
    data = await get_storage().get(asset.storage_key)
    disposition = "inline" if inline else "attachment"
    response = Response(
        content=data,
        media_type=asset.mime_type,
        headers={
            "Content-Disposition": f"{disposition}; filename*=UTF-8''{quote(asset.filename)}",
            "X-Content-Type-Options": "nosniff",
        },
    )
    _headers(response, link.noindex)
    return response
