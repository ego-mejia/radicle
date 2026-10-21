"""Folio's REST API under /api/v1/folio (Folio 0.5): health, who you are, global roles."""

import uuid
from typing import Literal

from fastapi import APIRouter, Response
from pydantic import Field

from radicle.folio.api import assets as assets_api
from radicle.folio.api import catalogs as catalogs_api
from radicle.folio.api import collab as collab_api
from radicle.folio.api import comments as comments_api
from radicle.folio.api import databases as databases_api
from radicle.folio.api import drafts as drafts_api
from radicle.folio.api import home as home_api
from radicle.folio.api import home_layouts as home_layouts_api
from radicle.folio.api import links as links_api
from radicle.folio.api import livedocs as livedocs_api
from radicle.folio.api import organize as organize_api
from radicle.folio.api import page_list as page_list_api
from radicle.folio.api import people as people_api
from radicle.folio.api import publishing as publishing_api
from radicle.folio.api import query as query_api
from radicle.folio.api import search as search_api
from radicle.folio.api import sharing as sharing_api
from radicle.folio.api import social as social_api
from radicle.folio.api import spaces as spaces_api
from radicle.folio.api import submissions as submissions_api
from radicle.folio.api import tasks as tasks_api
from radicle.folio.api import templates as templates_api
from radicle.folio.db.models import FolioRole, GranteeType
from radicle.folio.services import roles
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Input, Output, Page
from radicle.platform.db.models import AuditApp, User
from radicle.platform.services import audit

router = APIRouter(prefix="/folio", tags=["folio"])

Role = Literal["reader", "creator", "admin"]
Grantee = Literal["user", "group", "everyone"]


class FolioHealthOut(Output):
    status: Literal["ok"]


class FolioMeOut(Output):
    handle: str
    display_name: str
    kind: str
    role: Role = Field(description="Highest of the direct, group and everyone grants")


class GrantOut(Output):
    id: uuid.UUID
    grantee_type: Grantee
    grantee: str | None = Field(description="Handle or group name; null for everyone")
    role: Role


class GrantIn(Input):
    grantee_type: Grantee
    grantee: str | None = Field(default=None, description="Handle or group name; omit for everyone")
    role: Role


@router.get("/health", response_model=FolioHealthOut)
async def health() -> FolioHealthOut:
    return FolioHealthOut(status="ok")


@router.get("/me", response_model=FolioMeOut)
async def me(principal: CurrentPrincipal, db: Db) -> FolioMeOut:
    """Your effective Folio role. 404 when no grant reaches you: Folio is hidden then."""
    user = principal.user
    (await authz.authorize(db, user, "folio", "folio.read")).raise_if_denied()
    role = await roles.effective_role(db, user) or FolioRole.reader
    return FolioMeOut(
        handle=user.handle, display_name=user.display_name, kind=user.kind.value, role=role.value
    )


async def _admin(db: Db, user: User) -> None:
    (await authz.authorize(db, user, "folio", "folio.admin")).raise_if_denied()


def _out(g: roles.Grant) -> GrantOut:
    return GrantOut(
        id=g.id, grantee_type=g.grantee_type.value, grantee=g.grantee, role=g.role.value
    )


@router.get("/admin/grants", response_model=Page[GrantOut])
async def list_grants(principal: CurrentPrincipal, db: Db) -> Page[GrantOut]:
    """Global Folio roles: everyone first, then groups and users. Folio admins only."""
    await _admin(db, principal.user)
    return Page(items=[_out(g) for g in await roles.list_grants(db)])


@router.post("/admin/grants", response_model=GrantOut, status_code=201)
async def set_grant(body: GrantIn, principal: CurrentPrincipal, db: Db) -> GrantOut:
    """Give a user, a group or everyone a global role; it replaces their previous one."""
    await _admin(db, principal.user)
    grant, previous = await roles.set_grant(
        db, principal.user, GranteeType(body.grantee_type), body.grantee, FolioRole(body.role)
    )
    audit.record(
        db,
        principal.user,
        "folio.grant_set",
        target_type="folio_grant",
        target_id=grant.id,
        before={"role": previous.value} if previous else None,
        after={"grantee_type": body.grantee_type, "grantee": grant.grantee, "role": body.role},
        app=AuditApp.folio,
    )
    return _out(grant)


@router.delete("/admin/grants/{grant_id}", status_code=204)
async def delete_grant(grant_id: uuid.UUID, principal: CurrentPrincipal, db: Db) -> Response:
    await _admin(db, principal.user)
    row = await roles.remove_grant(db, grant_id)
    audit.record(
        db,
        principal.user,
        "folio.grant_remove",
        target_type="folio_grant",
        target_id=grant_id,
        before={"grantee_type": row.grantee_type.value, "role": row.role.value},
        app=AuditApp.folio,
    )
    return Response(status_code=204)


router.include_router(spaces_api.router)
router.include_router(drafts_api.router)
router.include_router(assets_api.router)
router.include_router(catalogs_api.router)
router.include_router(publishing_api.router)
router.include_router(sharing_api.router)
router.include_router(submissions_api.router)
router.include_router(search_api.router)
router.include_router(query_api.router)
router.include_router(home_api.router)
router.include_router(home_layouts_api.router)
router.include_router(organize_api.router)
router.include_router(social_api.router)
router.include_router(templates_api.router)
router.include_router(collab_api.router)
router.include_router(comments_api.router)
router.include_router(tasks_api.router)
router.include_router(people_api.router)
router.include_router(livedocs_api.router)
router.include_router(links_api.router)
router.include_router(page_list_api.router)
router.include_router(databases_api.router)
