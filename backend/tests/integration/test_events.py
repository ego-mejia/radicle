"""The event bus and its deliveries (Folio 2.1, ADR 0038)."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.db.models import (
    Channel,
    DeliveryStatus,
    EventDelivery,
    Notification,
    NotificationPreference,
    OutboxEvent,
    User,
)
from radicle.platform.services import events
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


async def test_without_smtp_there_is_no_email(db: AsyncSession, team: Team) -> None:
    await events.emit(db, "test", "ping", actor=None, payload={"to": ["ana"]})
    assert "platform_send_email" not in await run_jobs(db)
    channels = set(await db.scalars(select(EventDelivery.channel)))
    assert channels == {Channel.in_app}
