"""Notices to Slack and Teams channels (Folio 5.4, ADR 0042): each public event that a
route of an active integration asks for is posted once, retried a few times."""

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.db.models import (
    DeliveryStatus,
    Integration,
    IntegrationKind,
    IntegrationNotice,
    OutboxEvent,
    utcnow,
)
from radicle.platform.services import events, integrations, queue, safe_fetch

POST_JOB = "platform_post_chat_notice"
SLACK_API = "https://slack.com/api"
BACKOFF = (60, 600)
MAX_ATTEMPTS = len(BACKOFF) + 1


def _matches(route: integrations.Route, event: events.PublicEvent) -> bool:
    if route.events and event.name not in route.events:
        return False
    return all(event.scope.get(k) == v for k, v in route.filter.items())


def text_for(kind: IntegrationKind, event: events.PublicEvent) -> str:
    summary = event.summary or event.name
    if not event.link:
        return summary
    if kind == IntegrationKind.slack:
        return f"{summary}\n<{event.link}>"
    return f"{summary}\n\n[{event.link}]({event.link})"


@events.subscriber
async def _fan_out(
    db: AsyncSession, event: OutboxEvent, published: list[events.PublicEvent]
) -> None:
    active = await db.scalars(select(Integration).where(Integration.active.is_(True)))
    for integration in active:
        for n, route in enumerate(integrations.routes(integration)):
            match = next((p for p in published if _matches(route, p)), None)
            if match is None:
                continue
            notice_id = await db.scalar(
                insert(IntegrationNotice)
                .values(
                    integration_id=integration.id,
                    event_id=event.id,
                    route=n,
                    event=match.name,
                    text=text_for(integration.kind, match),
                    status=DeliveryStatus.pending,
                )
                .on_conflict_do_nothing()
                .returning(IntegrationNotice.id)
            )
            if notice_id is not None:  # None: an earlier dispatch already queued it
                await queue.enqueue(db, POST_JOB, notice_id=notice_id)


async def slack_call(token: str, method: str, body: dict[str, Any]) -> dict[str, Any]:
    """Call the Slack Web API; raises Blocked with Slack's error when it says no."""
    answer = await safe_fetch.post(
        f"{SLACK_API}/{method}",
        json.dumps(body).encode(),
        {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
    )
    try:
        doc: dict[str, Any] = json.loads(answer.text)
    except ValueError:
        doc = {"ok": False, "error": f"HTTP {answer.status}"}
    if not doc.get("ok"):
        raise safe_fetch.Blocked(f"Slack answered {doc.get('error', 'an error')}.")
    return doc


async def send(integration: Integration, channel: str, text: str) -> None:
    """Post `text` on a channel: a Slack channel id or a Teams incoming webhook URL."""
    if integration.kind == IntegrationKind.slack:
        token = integrations.credentials(integration)["bot_token"]
        await slack_call(token, "chat.postMessage", {"channel": channel, "text": text})
        return
    card = {"@type": "MessageCard", "@context": "https://schema.org/extensions", "text": text}
    answer = await safe_fetch.post(
        channel, json.dumps(card).encode(), {"Content-Type": "application/json"}
    )
    if not 200 <= answer.status < 300:
        raise safe_fetch.Blocked(f"Teams answered HTTP {answer.status}.")


@queue.handler(POST_JOB)
async def post(db: AsyncSession, notice_id: int, **_: Any) -> None:
    notice = await db.get(IntegrationNotice, notice_id, with_for_update=True)
    if notice is None or notice.status == DeliveryStatus.sent:
        return
    integration = await db.get(Integration, notice.integration_id)
    routes = integrations.routes(integration) if integration else []
    if integration is None or notice.route >= len(routes):
        notice.status, notice.last_error = DeliveryStatus.skipped, "The channel was removed."
        return
    notice.attempts += 1
    try:
        await send(integration, routes[notice.route].channel, notice.text)
    except safe_fetch.Blocked as exc:
        notice.last_error = exc.detail
        if notice.attempts < MAX_ATTEMPTS:
            delay = BACKOFF[notice.attempts - 1]
            await queue.enqueue(db, POST_JOB, notice_id=notice.id, delay_seconds=delay)
        else:
            notice.status = DeliveryStatus.failed
    else:
        notice.status, notice.sent_at, notice.last_error = DeliveryStatus.sent, utcnow(), None
    await db.flush()
