"""Webhooks (Folio 5.5, shared with Docket; ADR 0042): public events POSTed to a receiver,
signed with HMAC-SHA256, retried with backoff and logged per delivery.

Each request carries:

    Radicle-Event: page.published
    Radicle-Delivery: 42
    Radicle-Signature: t=1760000000,v1=<hex HMAC-SHA256(secret, f"{t}.{body}")>

The receiver recomputes the HMAC over the raw body and rejects old timestamps.
"""

import hashlib
import hmac
import json
import secrets
import time
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform import crypto
from radicle.platform.db.models import (
    DeliveryStatus,
    OutboxEvent,
    User,
    Webhook,
    WebhookDelivery,
    utcnow,
)
from radicle.platform.errors import NotFound, ValidationFailed
from radicle.platform.services import events, queue, safe_fetch

DELIVER_JOB = "platform_deliver_webhook"
# Seconds before each retry; after the last one the delivery stays failed.
BACKOFF = (60, 300, 1800, 7200, 21600)
MAX_ATTEMPTS = len(BACKOFF) + 1
USER_AGENT = "Radicle webhooks (+https://github.com/ego-mejia/radicle)"


def sign(secret: str, timestamp: int, body: bytes) -> str:
    mac = hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256)
    return f"t={timestamp},v1={mac.hexdigest()}"


def verify(secret: str, header: str, body: bytes, *, tolerance: int = 300) -> bool:
    """What a receiver does; Radicle's own tests use it."""
    parts = dict(p.split("=", 1) for p in header.split(",") if "=" in p)
    try:
        timestamp = int(parts["t"])
    except (KeyError, ValueError):
        return False
    if abs(time.time() - timestamp) > tolerance:
        return False
    return hmac.compare_digest(sign(secret, timestamp, body), header)


@dataclass(frozen=True)
class WebhookData:
    name: str
    url: str
    events: list[str]
    filter: dict[str, str]
    active: bool = True


def _invalid(field: str, message: str) -> ValidationFailed:
    return ValidationFailed(message, errors=[{"field": field, "message": "invalid"}])


async def _check(data: WebhookData) -> None:
    if not data.name.strip():
        raise _invalid("name", "Give the webhook a name.")
    known = events.public_events()
    unknown = sorted(set(data.events) - set(known))
    if unknown:
        raise _invalid(
            "events", f"Unknown events: {', '.join(unknown)}. Valid ones: {', '.join(known)}."
        )
    try:
        await safe_fetch.check(data.url)
    except safe_fetch.Blocked as exc:
        raise _invalid("url", exc.detail) from None


async def create(db: AsyncSession, admin: User, data: WebhookData) -> tuple[Webhook, str]:
    """The new webhook and its secret, which is shown this once."""
    await _check(data)
    secret = "whsec_" + secrets.token_urlsafe(32)
    hook = Webhook(
        name=data.name.strip(),
        url=data.url,
        secret_encrypted=crypto.encrypt(secret),
        events=sorted(set(data.events)),
        filter=data.filter,
        active=data.active,
        created_by=admin.id,
    )
    db.add(hook)
    await db.flush()
    return hook, secret


async def get(db: AsyncSession, webhook_id: uuid.UUID) -> Webhook:
    hook = await db.get(Webhook, webhook_id)
    if hook is None:
        raise NotFound("Webhook not found. List them with GET /api/v1/webhooks.")
    return hook


async def list_all(db: AsyncSession) -> list[Webhook]:
    return list(await db.scalars(select(Webhook).order_by(Webhook.created_at)))


async def deliveries(db: AsyncSession, hook: Webhook, limit: int = 50) -> list[WebhookDelivery]:
    return list(
        await db.scalars(
            select(WebhookDelivery)
            .where(WebhookDelivery.webhook_id == hook.id)
            .order_by(WebhookDelivery.id.desc())
            .limit(limit)
        )
    )


def _matches(hook: Webhook, event: events.PublicEvent) -> bool:
    if hook.events and event.name not in hook.events:
        return False
    return all(event.scope.get(k) == v for k, v in hook.filter.items())


async def _queue(
    db: AsyncSession, hook: Webhook, name: str, data: dict[str, Any], event_id: int | None
) -> WebhookDelivery:
    delivery = WebhookDelivery(
        webhook_id=hook.id, event_id=event_id, event=name, payload=data, attempts=0
    )
    db.add(delivery)
    await db.flush()
    await queue.enqueue(db, DELIVER_JOB, delivery_id=delivery.id)
    return delivery


@events.subscriber
async def _fan_out(
    db: AsyncSession, event: OutboxEvent, published: list[events.PublicEvent]
) -> None:
    hooks = list(await db.scalars(select(Webhook).where(Webhook.active.is_(True))))
    for hook in hooks:
        for public in published:
            if not _matches(hook, public):
                continue
            seen = await db.scalar(
                select(WebhookDelivery.id).where(
                    WebhookDelivery.webhook_id == hook.id,
                    WebhookDelivery.event_id == event.id,
                    WebhookDelivery.event == public.name,
                )
            )
            if seen is None:  # a repeated dispatch must not send it twice
                await _queue(db, hook, public.name, public.data, event.id)


def body(delivery: WebhookDelivery) -> bytes:
    created = delivery.created_at or utcnow()
    doc = {
        "id": delivery.id,
        "event": delivery.event,
        "occurred_at": created.isoformat(),
        "data": delivery.payload,
    }
    return json.dumps(doc, separators=(",", ":"), default=str).encode()


@queue.handler(DELIVER_JOB)
async def deliver(db: AsyncSession, delivery_id: int, **_: Any) -> None:
    delivery = await db.get(WebhookDelivery, delivery_id, with_for_update=True)
    if delivery is None or delivery.status == DeliveryStatus.sent:
        return
    hook = await db.get(Webhook, delivery.webhook_id)
    if hook is None:
        return
    content = body(delivery)
    headers = {
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
        "Radicle-Event": delivery.event,
        "Radicle-Delivery": str(delivery.id),
        "Radicle-Signature": sign(crypto.decrypt(hook.secret_encrypted), int(time.time()), content),
    }
    delivery.attempts += 1
    try:
        answer = await safe_fetch.post(hook.url, content, headers)
        delivery.response_status = answer.status
        ok = 200 <= answer.status < 300
        delivery.last_error = None if ok else f"HTTP {answer.status}: {answer.text[:300]}"
    except safe_fetch.Blocked as exc:
        ok, delivery.last_error = False, exc.detail
    if ok:
        delivery.status, delivery.delivered_at = DeliveryStatus.sent, utcnow()
    elif delivery.attempts < MAX_ATTEMPTS:
        delivery.status = DeliveryStatus.pending
        delay = BACKOFF[delivery.attempts - 1]
        await queue.enqueue(db, DELIVER_JOB, delivery_id=delivery.id, delay_seconds=delay)
    else:
        delivery.status = DeliveryStatus.failed
    await db.flush()
