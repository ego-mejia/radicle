"""Space grants and page restrictions over REST (Folio 1.4)."""

import uuid
from typing import Literal

from fastapi import APIRouter
from pydantic import Field

from radicle.folio.db.models import GranteeType
from radicle.folio.services import access, audit_log, nodes, sharing, spaces
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Input, Output
from radicle.platform.db.models import AuditApp
from radicle.platform.services import audit

router = APIRouter(tags=["folio"])

Permission = Literal["view", "create", "comment", "delete_own", "delete_any", "admin", "export"]


class GranteeIO(Input):
    grantee_type: Literal["user", "group", "everyone"]
    grantee: str | None = Field(default=None, description="Handle or group name; none for everyone")


class GrantIO(GranteeIO):
    permissions: list[Permission] = Field(description="admin includes all the others")


class GrantsOut(Output):
    grants: list[GrantIO]


class GrantsIn(Input):
    grants: list[GrantIO]


class RestrictionsIO(Input):
    view: list[GranteeIO] = Field(
        default_factory=list, description="Hides the page and its children"
    )
    edit: list[GranteeIO] = Field(default_factory=list, description="Only this page")


def _grantee(g: GranteeIO) -> sharing.Grantee:
    return sharing.Grantee(GranteeType(g.grantee_type), g.grantee)


def _io(g: sharing.Grantee) -> GranteeIO:
    return GranteeIO(grantee_type=g.type.value, grantee=g.name)


def _grants(rows: list[sharing.GrantRow]) -> GrantsOut:
    return GrantsOut(
        grants=[
            GrantIO(
                grantee_type=r.grantee.type.value, grantee=r.grantee.name, permissions=r.permissions
            )
            for r in rows
        ]
    )


def _restrictions(r: dict[str, list[sharing.Grantee]]) -> RestrictionsIO:
    return RestrictionsIO(view=[_io(g) for g in r["view"]], edit=[_io(g) for g in r["edit"]])


@router.get("/spaces/{key}/grants", response_model=GrantsOut)
async def get_grants(key: str, principal: CurrentPrincipal, db: Db) -> GrantsOut:
    """Who may do what in the space. Space admins only."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    space = await spaces.get_space(db, principal.user, key)
    await access.require_admin(db, principal.user, space)
    return _grants(await sharing.space_grants(db, space))


@router.put("/spaces/{key}/grants", response_model=GrantsOut)
async def put_grants(key: str, body: GrantsIn, principal: CurrentPrincipal, db: Db) -> GrantsOut:
    """Replace the space's grants; at least one user or group keeps admin."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    space = await spaces.get_space(db, principal.user, key)
    before = _grants(await sharing.space_grants(db, space)).model_dump()
    rows = [sharing.GrantRow(_grantee(g), list(g.permissions)) for g in body.grants]
    after = _grants(await sharing.set_space_grants(db, principal.user, space, rows))
    audit.record(
        db,
        principal.user,
        "folio.space_grants_change",
        target_type="folio_space",
        target_id=space.id,
        before=before,
        after=after.model_dump(),
        app=AuditApp.folio,
    )
    return after


@router.get("/nodes/{node_id}/restrictions", response_model=RestrictionsIO)
async def get_restrictions(
    node_id: uuid.UUID, principal: CurrentPrincipal, db: Db
) -> RestrictionsIO:
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    node = await nodes.get_node(db, principal.user, node_id)
    return _restrictions(await sharing.restrictions(db, node))


@router.put("/nodes/{node_id}/restrictions", response_model=RestrictionsIO)
async def put_restrictions(
    node_id: uuid.UUID, body: RestrictionsIO, principal: CurrentPrincipal, db: Db
) -> RestrictionsIO:
    """Replace who may view (with its children) and edit (this page) it; empty lifts them."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    node = await nodes.get_node(db, principal.user, node_id)
    before = _restrictions(await sharing.restrictions(db, node)).model_dump()
    result = await sharing.set_restrictions(
        db,
        principal.user,
        node,
        view=[_grantee(g) for g in body.view],
        edit=[_grantee(g) for g in body.edit],
    )
    out = _restrictions(result)
    audit_log.record(
        db,
        principal.user,
        "restrictions_change",
        target_type="folio_node",
        target_id=node.id,
        before=before,
        after=out.model_dump(),
    )
    return out
