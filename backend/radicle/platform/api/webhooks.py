"""Admin, Integrations, Webhooks (Folio 5.5, shared with Docket; ADR 0042)."""

import uuid
from typing import Any

from fastapi import APIRouter, Response
from pydantic import Field

from radicle.platform.api.deps import Db, InstanceAdmin
from radicle.platform.api.schemas import Input, Output, UtcDatetime
from radicle.platform.db.models import Webhook, WebhookDelivery
from radicle.platform.services import audit, events, webhooks

router = APIRouter(tags=["webhooks"])


class PublicEventOut(Output):
    name: str
    label: str


class WebhookOut(Output):
    id: uuid.UUID
    name: str
    url: str
    events: list[str] = Field(description="Empty means every event")
    filter: dict[str, str] = Field(description='Scope that must match, e.g. {"space": "eng"}')
    active: bool
    created_at: UtcDatetime


class WebhookCreatedOut(WebhookOut):
    secret: str = Field(description="Shown only now; sign checks use it")


class WebhookSecretOut(Output):
    secret: str


class WebhookIn(Input):
    name: str = Field(min_length=1, max_length=120)
    url: str = Field(max_length=2000)
    events: list[str] = Field(default_factory=list, description="Empty means every event")
    filter: dict[str, str] = Field(default_factory=dict)
    active: bool = True


class WebhookDeliveryOut(Output):
    id: int
    event: str
    status: str
    attempts: int
    response_status: int | None
    last_error: str | None
    created_at: UtcDatetime
    delivered_at: UtcDatetime | None


def _out(hook: Webhook) -> WebhookOut:
    return WebhookOut(
        id=hook.id,
        name=hook.name,
        url=hook.url,
        events=hook.events,
        filter=hook.filter,
        active=hook.active,
        created_at=hook.created_at,
    )


def _delivery(d: WebhookDelivery) -> WebhookDeliveryOut:
    return WebhookDeliveryOut(
        id=d.id,
        event=d.event,
        status=d.status.value,
        attempts=d.attempts,
        response_status=d.response_status,
        last_error=d.last_error,
        created_at=d.created_at,
        delivered_at=d.delivered_at,
    )


def _data(body: WebhookIn) -> webhooks.WebhookData:
    return webhooks.WebhookData(body.name, body.url, body.events, body.filter, body.active)


def _audit_view(hook: Webhook) -> dict[str, Any]:
    return {"name": hook.name, "url": hook.url, "events": hook.events, "active": hook.active}


@router.get("/webhooks/events", response_model=list[PublicEventOut])
async def list_public_events(_: InstanceAdmin) -> list[PublicEventOut]:
    """The events a webhook (or a rule) can subscribe to."""
    return [PublicEventOut(name=n, label=label) for n, label in events.public_events().items()]


@router.get("/webhooks", response_model=list[WebhookOut])
async def list_webhooks(_: InstanceAdmin, db: Db) -> list[WebhookOut]:
    return [_out(h) for h in await webhooks.list_all(db)]


@router.post("/webhooks", response_model=WebhookCreatedOut, status_code=201)
async def create_webhook(body: WebhookIn, admin: InstanceAdmin, db: Db) -> WebhookCreatedOut:
    """The receiver must be a public http(s) address. Keep the secret: it isn't shown again."""
    hook, secret = await webhooks.create(db, admin, _data(body))
    audit.record(
        db,
        admin,
        "webhook.create",
        target_type="webhook",
        target_id=hook.id,
        after=_audit_view(hook),
    )
    return WebhookCreatedOut(**_out(hook).model_dump(), secret=secret)


@router.get("/webhooks/{webhook_id}", response_model=WebhookOut)
async def get_webhook(webhook_id: uuid.UUID, _: InstanceAdmin, db: Db) -> WebhookOut:
    return _out(await webhooks.get(db, webhook_id))


@router.put("/webhooks/{webhook_id}", response_model=WebhookOut)
async def update_webhook(
    webhook_id: uuid.UUID, body: WebhookIn, admin: InstanceAdmin, db: Db
) -> WebhookOut:
    hook = await webhooks.get(db, webhook_id)
    before = _audit_view(hook)
    await webhooks.update(db, hook, _data(body))
    audit.record(
        db,
        admin,
        "webhook.update",
        target_type="webhook",
        target_id=hook.id,
        before=before,
        after=_audit_view(hook),
    )
    return _out(hook)


@router.delete("/webhooks/{webhook_id}", status_code=204)
async def delete_webhook(webhook_id: uuid.UUID, admin: InstanceAdmin, db: Db) -> Response:
    hook = await webhooks.get(db, webhook_id)
    audit.record(
        db,
        admin,
        "webhook.delete",
        target_type="webhook",
        target_id=hook.id,
        before=_audit_view(hook),
    )
    await db.delete(hook)
    return Response(status_code=204)


@router.post("/webhooks/{webhook_id}/secret", response_model=WebhookSecretOut)
async def rotate_webhook_secret(
    webhook_id: uuid.UUID, admin: InstanceAdmin, db: Db
) -> WebhookSecretOut:
    """A new secret; the old one stops working right away."""
    hook = await webhooks.get(db, webhook_id)
    secret = await webhooks.rotate_secret(db, hook)
    audit.record(
        db,
        admin,
        "webhook.update",
        target_type="webhook",
        target_id=hook.id,
        after={"secret": "rotated"},
    )
    return WebhookSecretOut(secret=secret)


@router.post("/webhooks/{webhook_id}/ping", response_model=WebhookDeliveryOut, status_code=202)
async def ping_webhook(webhook_id: uuid.UUID, _: InstanceAdmin, db: Db) -> WebhookDeliveryOut:
    """Send a signed `ping`; its result shows in the deliveries."""
    return _delivery(await webhooks.ping(db, await webhooks.get(db, webhook_id)))


@router.get("/webhooks/{webhook_id}/deliveries", response_model=list[WebhookDeliveryOut])
async def list_webhook_deliveries(
    webhook_id: uuid.UUID, _: InstanceAdmin, db: Db
) -> list[WebhookDeliveryOut]:
    """The latest 50, newest first."""
    hook = await webhooks.get(db, webhook_id)
    return [_delivery(d) for d in await webhooks.deliveries(db, hook)]


@router.post(
    "/webhooks/{webhook_id}/deliveries/{delivery_id}/redeliver",
    response_model=WebhookDeliveryOut,
    status_code=202,
)
async def redeliver_webhook(
    webhook_id: uuid.UUID, delivery_id: int, _: InstanceAdmin, db: Db
) -> WebhookDeliveryOut:
    """Send the same event again, as a new delivery."""
    hook = await webhooks.get(db, webhook_id)
    return _delivery(await webhooks.redeliver(db, hook, delivery_id))
