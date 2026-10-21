"""The event bus and its deliveries (Folio 2.1, ADR 0038)."""

import smtplib
from email.message import EmailMessage

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.config import Settings
from radicle.platform.db.models import (
    Channel,
    DeliveryStatus,
    EventDelivery,
    Notification,
    NotificationPreference,
    OutboxEvent,
    User,
)
from radicle.platform.services import email, events
from tests.conftest import Team, run_jobs


@events.resolver("test", "ping", label="Test pings")
async def _ping(db: AsyncSession, event: OutboxEvent) -> list[events.Notice]:
    if event.payload.get("boom"):
        raise RuntimeError("resolver failed")
    users = await db.scalars(select(User).where(User.handle.in_(event.payload["to"])))
    return [events.Notice(u.id, "mentioned", f"Ping for {u.handle}", "Hola", "/x") for u in users]


async def _user(db: AsyncSession, handle: str) -> User:
    user = await db.scalar(select(User).where(User.handle == handle))
    assert user is not None
    return user


async def _notifications(db: AsyncSession, user: User) -> list[str]:
    rows = await db.scalars(select(Notification.title).where(Notification.user_id == user.id))
    return list(rows)


async def test_an_event_reaches_whoever_the_app_says_once(db: AsyncSession, team: Team) -> None:
    ana, actor = await _user(db, "ana"), await _user(db, team.instance.handle)
    to = ["ana", actor.handle, "nobody"]
    await events.emit(db, "test", "ping", actor=actor, payload={"to": to})
    assert "platform_dispatch_events" in await run_jobs(db)
    assert await _notifications(db, ana) == ["Ping for ana"]
    assert await _notifications(db, actor) == []  # never the actor
    assert await events.dispatch_pending(db) == 0  # already dispatched
    event = await db.scalar(select(OutboxEvent))
    assert event is not None and event.dispatched_at is not None
    event.dispatched_at = None  # a crashed worker runs it again
    await events.dispatch_pending(db)
    assert await _notifications(db, ana) == ["Ping for ana"]  # no duplicate


async def test_a_rolled_back_change_emits_nothing(db: AsyncSession, team: Team) -> None:
    savepoint = await db.begin_nested()
    await events.emit(db, "test", "ping", actor=None, payload={"to": ["ana"]})
    await savepoint.rollback()
    assert await db.scalar(select(func.count()).select_from(OutboxEvent)) == 0


async def test_inactive_users_and_turned_off_channels(db: AsyncSession, team: Team) -> None:
    ana, luis = await _user(db, "ana"), await _user(db, team.member.handle)
    luis.is_active = False
    db.add(
        NotificationPreference(
            user_id=ana.id, app="test", type="ping", channel=Channel.in_app, enabled=False
        )
    )
    await events.emit(db, "test", "ping", actor=None, payload={"to": ["ana", luis.handle]})
    await run_jobs(db)
    assert await _notifications(db, ana) == [] and await _notifications(db, luis) == []
    delivery = await db.scalar(select(EventDelivery).where(EventDelivery.user_id == ana.id))
    assert delivery is not None and delivery.status == DeliveryStatus.skipped


async def test_a_failing_event_does_not_block_the_others(db: AsyncSession, team: Team) -> None:
    ana = await _user(db, "ana")
    bad = await events.emit(db, "test", "ping", actor=None, payload={"boom": True})
    await events.emit(db, "test", "ping", actor=None, payload={"to": ["ana"]})
    await run_jobs(db)
    assert await _notifications(db, ana) == ["Ping for ana"]
    assert (
        bad.attempts == 1
        and bad.dispatched_at is None
        and "resolver failed" in (bad.last_error or "")
    )
    for _ in range(events.MAX_ATTEMPTS):
        await events.dispatch_pending(db)
    assert bad.dispatched_at is not None and bad.attempts == events.MAX_ATTEMPTS


@pytest.fixture
def smtp(monkeypatch: pytest.MonkeyPatch) -> list[EmailMessage]:
    settings = Settings(smtp_host="smtp.test", base_url="https://radicle.test")
    monkeypatch.setattr(events, "get_settings", lambda: settings)
    monkeypatch.setattr(email, "get_settings", lambda: settings)
    sent: list[EmailMessage] = []
    monkeypatch.setattr(email, "send", lambda _s, message: sent.append(message))
    return sent


async def test_email_goes_out_with_a_full_link(
    db: AsyncSession, team: Team, smtp: list[EmailMessage]
) -> None:
    ana = await _user(db, "ana")
    await events.emit(db, "test", "ping", actor=None, payload={"to": ["ana"]})
    assert "platform_send_email" in await run_jobs(db)
    assert len(smtp) == 1 and smtp[0]["To"] == ana.email and smtp[0]["Subject"] == "Ping for ana"
    assert "https://radicle.test/x" in smtp[0].get_content()
    statuses = set(await db.scalars(select(EventDelivery.status)))
    assert statuses == {DeliveryStatus.sent}


async def test_email_retries_then_keeps_the_error(
    db: AsyncSession, team: Team, smtp: list[EmailMessage], monkeypatch: pytest.MonkeyPatch
) -> None:
    def down(_s: Settings, _m: EmailMessage) -> None:
        raise smtplib.SMTPConnectError(421, "busy")

    monkeypatch.setattr(email, "send", down)
    await events.emit(db, "test", "ping", actor=None, payload={"to": ["ana"]})
    ran = await run_jobs(db)
    assert ran.count("platform_send_email") == email.MAX_ATTEMPTS
    delivery = await db.scalar(select(EventDelivery).where(EventDelivery.channel == Channel.email))
    assert delivery is not None and delivery.status == DeliveryStatus.failed
    assert "busy" in (delivery.last_error or "")


async def test_without_smtp_there_is_no_email(db: AsyncSession, team: Team) -> None:
    await events.emit(db, "test", "ping", actor=None, payload={"to": ["ana"]})
    assert "platform_send_email" not in await run_jobs(db)
    channels = set(await db.scalars(select(EventDelivery.channel)))
    assert channels == {Channel.in_app}


async def test_public_events_reach_every_subscriber_without_users(
    db: AsyncSession, team: Team, monkeypatch: pytest.MonkeyPatch
) -> None:
    heard: list[tuple[int, str, dict[str, str]]] = []

    async def publish(db: AsyncSession, event: OutboxEvent) -> list[events.PublicEvent]:
        return [events.PublicEvent("test.pinged", {"n": 1}, {"space": "eng"})]

    async def listen(
        db: AsyncSession, event: OutboxEvent, published: list[events.PublicEvent]
    ) -> None:
        heard.extend((event.id, p.name, p.scope) for p in published)

    monkeypatch.setitem(events._publishers, ("test", "ping"), publish)
    monkeypatch.setattr(events, "_subscribers", [listen])
    events.public_event("test.pinged", "Test pings")
    assert events.public_events()["test.pinged"] == "Test pings"
    await events.emit(db, "test", "ping", actor=None, payload={"to": []})
    await run_jobs(db)
    assert [(name, scope) for _, name, scope in heard] == [("test.pinged", {"space": "eng"})]
