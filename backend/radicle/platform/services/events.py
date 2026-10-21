"""The event bus (ADR 0038): apps emit events in their own transaction; the worker turns
them into notifications for whoever each app's resolver says, once per user and channel.

    await events.emit(db, "folio", "comment_mention", actor=user, payload={...})

    @events.resolver("folio", "comment_mention")
    async def mentioned(db, event) -> list[events.Notice]: ...

Events can also leave Radicle (webhooks, chat channels, automation rules): an app's
publisher turns its internal event into public ones with stable names such as
`page.published`, and every subscriber gets them.
"""

import logging
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.config import get_settings
from radicle.platform.db.models import (
    Channel,
    DeliveryStatus,
    EventDelivery,
    Notification,
    NotificationPreference,
    OutboxEvent,
    User,
    utcnow,
)
from radicle.platform.services import queue

log = logging.getLogger("radicle.events")

DISPATCH_JOB = "platform_dispatch_events"
EMAIL_JOB = "platform_send_email"
CHANNEL = "radicle_notifications"  # Postgres NOTIFY channel for the SSE stream
# Rules whose actions run now (ADR 0042); events they cause carry it, against loops.
automation_chain: ContextVar[tuple[str, ...]] = ContextVar("automation_chain", default=())
CHAIN_KEY = "_automation"
BATCH = 100
MAX_ATTEMPTS = 5


@dataclass(frozen=True)
class Notice:
    """Who should hear about an event, why, and what they read."""

    user_id: uuid.UUID
    reason: str
    title: str
    body: str = ""
    link: str | None = None
    # What the title says, for the web app to write it in the reader's language: `actor`
    # and `page` mostly, and `variant` when one type has more than one wording.
    params: dict[str, str] = field(default_factory=dict)


Resolver = Callable[[AsyncSession, OutboxEvent], Awaitable[list[Notice]]]


@dataclass(frozen=True)
class EventType:
    app: str
    type: str
    resolve: Resolver
    label: str
    # Channels on unless the user turns them off.
    defaults: frozenset[Channel]


_types: dict[tuple[str, str], EventType] = {}


def resolver(
    app: str,
    type: str,
    *,
    label: str,
    defaults: frozenset[Channel] = frozenset({Channel.in_app, Channel.email}),
) -> Callable[[Resolver], Resolver]:
    """Register who hears about `app.type`; `label` names it in the preferences."""

    def register(fn: Resolver) -> Resolver:
        _types[(app, type)] = EventType(app, type, fn, label, defaults)
        return fn

    return register


@dataclass(frozen=True)
class PublicEvent:
    """An event as it leaves Radicle: a stable name and data that is safe to send outside.
    `scope` says where it happened (`{"app": "folio", "space": "eng"}`) for filters."""

    name: str
    data: dict[str, Any]
    scope: dict[str, str] = field(default_factory=dict)
    # For chat channels: one line a person reads, and where to go.
    summary: str = ""
    link: str | None = None


Publisher = Callable[[AsyncSession, OutboxEvent], Awaitable[list[PublicEvent]]]
Subscriber = Callable[[AsyncSession, OutboxEvent, list[PublicEvent]], Awaitable[None]]

_publishers: dict[tuple[str, str], Publisher] = {}
_public: dict[str, str] = {}  # name -> label
_subscribers: list[Subscriber] = []


def publisher(app: str, type: str) -> Callable[[Publisher], Publisher]:
    """Register how `app.type` is told outside Radicle."""

    def register(fn: Publisher) -> Publisher:
        _publishers[(app, type)] = fn
        return fn

    return register


def public_event(name: str, label: str) -> None:
    """Declare a public event name, so admins can pick it (webhooks, rules)."""
    _public[name] = label


def public_events() -> dict[str, str]:
    return dict(sorted(_public.items()))


def subscriber(fn: Subscriber) -> Subscriber:
    """Hear every public event (webhooks, chat channels, automation)."""
    if fn not in _subscribers:
        _subscribers.append(fn)
    return fn


async def _publish(db: AsyncSession, event: OutboxEvent) -> None:
    publish = _publishers.get((event.app, event.type))
    if publish is None or not _subscribers:
        return
    published = await publish(db, event)
    if published:
        for fn in _subscribers:
            await fn(db, event, published)


def event_types() -> list[EventType]:
    return list(_types.values())


def email_enabled() -> bool:
    return bool(get_settings().smtp_host)


async def emit(
    db: AsyncSession,
    app: str,
    type: str,
    *,
    actor: User | None,
    payload: dict[str, Any],
) -> OutboxEvent:
    """Record an event in the caller's transaction and wake the dispatcher."""
    chain = automation_chain.get()
    if chain:
        payload = payload | {CHAIN_KEY: list(chain)}
    event = OutboxEvent(app=app, type=type, actor_id=actor.id if actor else None, payload=payload)
    db.add(event)
    await db.flush()
    await queue.enqueue(db, DISPATCH_JOB, queueing_lock="platform-dispatch")
    return event


async def _enabled(db: AsyncSession, user_id: uuid.UUID, kind: EventType) -> set[Channel]:
    rows = await db.execute(
        select(NotificationPreference.channel, NotificationPreference.enabled).where(
            NotificationPreference.user_id == user_id,
            NotificationPreference.app == kind.app,
            NotificationPreference.type == kind.type,
        )
    )
    chosen = {channel: enabled for channel, enabled in rows.all()}
    return {c for c in Channel if chosen.get(c, c in kind.defaults)}


async def _deliver(db: AsyncSession, event: OutboxEvent, kind: EventType, notice: Notice) -> None:
    on = await _enabled(db, notice.user_id, kind)
    for channel in Channel:
        if channel == Channel.email and not email_enabled():
            continue
        status = DeliveryStatus.pending if channel in on else DeliveryStatus.skipped
        inserted = await db.scalar(
            insert(EventDelivery)
            .values(
                event_id=event.id,
                user_id=notice.user_id,
                channel=channel,
                status=status,
                reason=notice.reason,
            )
            .on_conflict_do_nothing()
            .returning(EventDelivery.id)
        )
        if inserted is None or status == DeliveryStatus.skipped:
            continue  # already delivered by an earlier run, or turned off
        if channel == Channel.in_app:
            db.add(
                Notification(
                    user_id=notice.user_id,
                    event_id=event.id,
                    app=event.app,
                    type=event.type,
                    title=notice.title,
                    body=notice.body,
                    link=notice.link,
                    params=notice.params,
                    actor_id=event.actor_id,
                    # The clock, not now(): one dispatch writes many, newest last.
                    created_at=utcnow(),
                )
            )
            await db.execute(
                update(EventDelivery)
                .where(EventDelivery.id == inserted)
                .values(status=DeliveryStatus.sent, sent_at=utcnow())
            )
            await db.execute(
                text("SELECT pg_notify(:channel, :user)"),
                {"channel": CHANNEL, "user": str(notice.user_id)},
            )
        else:
            await queue.enqueue(
                db,
                EMAIL_JOB,
                delivery_id=inserted,
                subject=notice.title,
                body=notice.body,
                link=notice.link,
            )


async def _recipients(db: AsyncSession, event: OutboxEvent, kind: EventType) -> list[Notice]:
    """The resolver's notices minus the actor, inactive users and repeats."""
    notices = await kind.resolve(db, event)
    ids = {n.user_id for n in notices} - {event.actor_id}
    active = set(
        await db.scalars(select(User.id).where(User.id.in_(ids), User.is_active.is_(True)))
    )
    seen: set[uuid.UUID] = set()
    out = []
    for n in notices:
        if n.user_id in active and n.user_id not in seen:
            seen.add(n.user_id)
            out.append(n)
    return out


@queue.handler(DISPATCH_JOB)
async def dispatch(db: AsyncSession, **_: Any) -> None:
    await dispatch_pending(db)


async def dispatch_pending(db: AsyncSession) -> int:
    """Turn pending events into deliveries; returns how many events it handled. Safe to
    run twice or in parallel: rows are locked and deliveries are unique."""
    handled = 0
    tried: set[int] = set()  # a failed event waits for the next run, not this loop
    while True:
        batch = list(
            await db.scalars(
                select(OutboxEvent)
                .where(OutboxEvent.dispatched_at.is_(None), OutboxEvent.id.not_in(tried))
                .order_by(OutboxEvent.id)
                .limit(BATCH)
                .with_for_update(skip_locked=True)
            )
        )
        if not batch:
            return handled
        for event in batch:
            tried.add(event.id)
            kind = _types.get((event.app, event.type))
            try:
                async with db.begin_nested():
                    if kind is not None:
                        for notice in await _recipients(db, event, kind):
                            await _deliver(db, event, kind, notice)
                    await _publish(db, event)
                event.dispatched_at = utcnow()
            except Exception as exc:  # one bad event must not block the rest
                log.exception("Dispatching event %s failed", event.id)
                event.attempts += 1
                event.last_error = f"{type(exc).__name__}: {exc}"[:500]
                if event.attempts >= MAX_ATTEMPTS:
                    event.dispatched_at = utcnow()
            handled += 1
        await db.flush()
