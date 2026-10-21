"""Admin, Integrations, Slack and Teams (Folio 5.4, shared with Docket; ADR 0042)."""

import uuid
from typing import Literal

from fastapi import APIRouter, Response
from pydantic import Field

from radicle.platform.api.deps import Db, InstanceAdmin
from radicle.platform.api.schemas import Input, Output
from radicle.platform.db.models import IntegrationKind
from radicle.platform.errors import ValidationFailed
from radicle.platform.services import audit, chat_notices, integrations, safe_fetch

router = APIRouter(tags=["integrations"])


class NoticeRoute(Input):
    channel: str = Field(
        max_length=2000, description="Slack channel id (C0123…), or the Teams incoming webhook URL"
    )
    events: list[str] = Field(default_factory=list, description="Empty means every event")
    filter: dict[str, str] = Field(default_factory=dict, description='e.g. {"space": "anuncios"}')


class NoticeRouteOut(Output):
    channel: str = Field(description="Teams URLs show only their host")
    events: list[str]
    filter: dict[str, str]


class IntegrationOut(Output):
    id: uuid.UUID
    kind: Literal["slack", "teams"]
    name: str
    active: bool
    notices: list[NoticeRouteOut]
    command_url: str = Field(description="Where Slack or Teams sends /radicle commands")


class IntegrationIn(Input):
    kind: Literal["slack", "teams"]
    name: str = Field(min_length=1, max_length=120)
    credentials: dict[str, str] | None = Field(
        default=None,
        description="Slack: bot_token, signing_secret. Teams: secret. Omit on update to keep.",
    )
    notices: list[NoticeRoute] | None = Field(default=None, description="Omit on update to keep")
    active: bool = True


class IntegrationTestIn(Input):
    route: int = Field(ge=0, description="Which notice route to post the test on")


class IntegrationTestOut(Output):
    ok: bool
    message: str


def _out(integration: integrations.Integration) -> IntegrationOut:
    view = integrations.view(integration)
    return IntegrationOut(
        id=integration.id,
        kind=view["kind"],
        name=view["name"],
        active=view["active"],
        notices=[NoticeRouteOut(**r) for r in view["notices"]],
        command_url=integrations.command_url(integration),
    )


def _data(body: IntegrationIn) -> integrations.IntegrationData:
    routes = None
    if body.notices is not None:
        routes = [integrations.Route(r.channel, r.events, r.filter) for r in body.notices]
    return integrations.IntegrationData(
        IntegrationKind(body.kind), body.name, body.credentials, routes, body.active
    )


@router.get("/integrations", response_model=list[IntegrationOut])
async def list_integrations(_: InstanceAdmin, db: Db) -> list[IntegrationOut]:
    return [_out(i) for i in await integrations.list_all(db)]


@router.post("/integrations", response_model=IntegrationOut, status_code=201)
async def create_integration(body: IntegrationIn, admin: InstanceAdmin, db: Db) -> IntegrationOut:
    """Credentials are stored encrypted and never returned."""
    integration = await integrations.create(db, admin, _data(body))
    audit.record(
        db,
        admin,
        "integration.create",
        target_type="integration",
        target_id=integration.id,
        after=integrations.view(integration),
    )
    return _out(integration)


@router.get("/integrations/{integration_id}", response_model=IntegrationOut)
async def get_integration(integration_id: uuid.UUID, _: InstanceAdmin, db: Db) -> IntegrationOut:
    return _out(await integrations.get(db, integration_id))


@router.put("/integrations/{integration_id}", response_model=IntegrationOut)
async def update_integration(
    integration_id: uuid.UUID, body: IntegrationIn, admin: InstanceAdmin, db: Db
) -> IntegrationOut:
    integration = await integrations.get(db, integration_id)
    if body.kind != integration.kind.value:
        raise ValidationFailed(
            "An integration can't change kind; create a new one.",
            errors=[{"field": "kind", "message": "fixed"}],
        )
    before = integrations.view(integration)
    await integrations.update(db, integration, _data(body))
    audit.record(
        db,
        admin,
        "integration.update",
        target_type="integration",
        target_id=integration.id,
        before=before,
        after=integrations.view(integration),
    )
    return _out(integration)


@router.delete("/integrations/{integration_id}", status_code=204)
async def delete_integration(integration_id: uuid.UUID, admin: InstanceAdmin, db: Db) -> Response:
    integration = await integrations.get(db, integration_id)
    audit.record(
        db,
        admin,
        "integration.delete",
        target_type="integration",
        target_id=integration.id,
        before=integrations.view(integration),
    )
    await db.delete(integration)
    return Response(status_code=204)


@router.post("/integrations/{integration_id}/test", response_model=IntegrationTestOut)
async def test_integration(
    integration_id: uuid.UUID, body: IntegrationTestIn, _: InstanceAdmin, db: Db
) -> IntegrationTestOut:
    """Post a test message on one route now and say what Slack or Teams answered."""
    integration = await integrations.get(db, integration_id)
    routes = integrations.routes(integration)
    if body.route >= len(routes):
        raise ValidationFailed(
            f"This integration has {len(routes)} notice routes; use 0 to {len(routes) - 1}.",
            errors=[{"field": "route", "message": "out of range"}],
        )
    try:
        await chat_notices.send(integration, routes[body.route].channel, "Radicle is connected.")
    except safe_fetch.Blocked as exc:
        return IntegrationTestOut(ok=False, message=exc.detail)
    return IntegrationTestOut(ok=True, message="Posted a test message.")
