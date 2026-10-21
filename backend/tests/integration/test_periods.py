import uuid
from datetime import UTC, date, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.db.models import DailyStatusCount, Ticket, TicketEvent, TicketStatusPeriod
from radicle.platform.config import get_settings
from radicle.services import period_builder, periods
from tests.conftest import Team, make_project, new_ticket, run_jobs

API = "/api/v1"


async def snapshot_of_periods(db: AsyncSession) -> list[tuple]:
    rows = await db.execute(
        select(
            TicketStatusPeriod.ticket_id,
            TicketStatusPeriod.status_id,
            TicketStatusPeriod.category,
            TicketStatusPeriod.entered_at,
            TicketStatusPeriod.exited_at,
        ).order_by(TicketStatusPeriod.ticket_id, TicketStatusPeriod.entered_at)
    )
    return [tuple(r) for r in rows.all()]


async def move(client: AsyncClient, actor, key: str, to: str, **extra: object):  # type: ignore[no-untyped-def]
    r = await client.post(
        f"{API}/tickets/{key}/transitions", headers=actor.headers, json={"to_status": to, **extra}
    )
    assert r.status_code == 200, r.text


async def test_backfill_rebuilds_exactly_the_live_periods(
    client: AsyncClient, db: AsyncSession, board: Team
) -> None:
    m = board.member
    await new_ticket(client, m)  # PA-1: full cycle, reopened and closed again
    for status in ("In Progress", "In Review"):
        await move(client, m, "PA-1", status)
    await move(client, m, "PA-1", "Done", resolution="done")
    await move(client, m, "PA-1", "To Do")
    await move(client, m, "PA-1", "Done", resolution="wont_do")
    await new_ticket(client, m, type="draft", classification="idea", area=None)  # PA-2: type change
    await move(client, m, "PA-2", "In Review")
    r = await client.post(
        f"{API}/tickets/PA-2/type", headers=m.headers, json={"type": "bug", "area": "Legal"}
    )
    assert r.status_code == 200
    await move(client, m, "PA-2", "In Progress")
    await make_project(client, board.instance, "PB")  # PA-3 moves to PB
    await client.post(
        f"{API}/projects/PB/areas", headers=board.instance.headers, json={"name": "Backend"}
    )
    await new_ticket(client, m)
    await move(client, m, "PA-3", "In Progress")
    r = await client.post(
        f"{API}/tickets/PA-3/move", headers=board.instance.headers, json={"target_project": "PB"}
    )
    assert r.status_code == 200

    live = await snapshot_of_periods(db)
    first = await db.scalar(select(Ticket.id).where(Ticket.title == "Ticket", Ticket.number == 1))
    # Ties on entered_at happen when moves land in the same instant: the period that
    # ended first (or at all) goes first.
    pa1 = sorted(
        (p for p in live if p[0] == first), key=lambda p: (p[3], p[4] is None, p[4] or p[3])
    )
    assert [p[2].value for p in pa1] == [
        "todo",
        "in_progress",
        "in_progress",
        "done",
        "todo",
        "done",
    ]
    assert all(p[4] is not None for p in pa1[:-1]) and pa1[-1][4] is None
    assert len({p[0] for p in live}) == 3

    await db.execute(TicketStatusPeriod.__table__.delete())
    rebuilt = await periods.backfill(db)
    assert rebuilt == len(live)
    assert await snapshot_of_periods(db) == live


async def test_backfill_handles_renamed_statuses(db: AsyncSession) -> None:
    at = datetime(2026, 10, 1, tzinfo=UTC)
    events = [
        period_builder.Event("created", None, {"status": "To Do"}, at),
        period_builder.Event("status_changed", None, {"status": "Gone"}, at + timedelta(hours=1)),
        period_builder.Event("status_changed", None, {"status": "Done"}, at + timedelta(hours=2)),
        period_builder.Event("comment_added", None, {"comment_id": "x"}, at + timedelta(hours=3)),
    ]
    known = {"To Do": ("a", "todo"), "Done": ("c", "done")}
    built = period_builder.build(
        events,
        ticket_type="task",
        project_key="PA",
        resolve=lambda _p, _t, name: known.get(name, (None, "todo")),
    )
    assert [(p.status_id, p.category) for p in built] == [
        ("a", "todo"),
        (None, "todo"),
        ("c", "done"),
    ]
    assert built[-1].exited_at is None and built[0].exited_at == at + timedelta(hours=1)


async def test_snapshot_is_idempotent_and_uses_the_time_zone(
    client: AsyncClient, db: AsyncSession, board: Team, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    for _ in range(3):
        await new_ticket(client, board.member, estimate_hours=4)
    await move(client, board.member, "PA-1", "In Progress")
    day = periods.today()
    first = await periods.snapshot(db, day)
    second = await periods.snapshot(db, day)
    assert first == second == 2  # To Do and In Progress
    rows = (
        (await db.execute(select(DailyStatusCount).where(DailyStatusCount.date == day)))
        .scalars()
        .all()
    )
    assert sorted(r.ticket_count for r in rows) == [1, 2]
    assert sum(r.remaining_hours for r in rows) == 12

    # A ticket created at 23:30 in Mexico City belongs to that day there, the next in UTC.
    monkeypatch.setattr(get_settings(), "timezone", "America/Mexico_City")
    late = datetime(2026, 10, 15, 5, 30, tzinfo=UTC)  # 23:30 on the 14th in CDMX
    t4 = await new_ticket(client, board.member, title="Tarde")
    ticket_id = await db.scalar(select(Ticket.id).where(Ticket.number == 4))
    await db.execute(
        update(TicketStatusPeriod)
        .where(TicketStatusPeriod.ticket_id == ticket_id)
        .values(entered_at=late)
    )
    await db.execute(
        TicketStatusPeriod.__table__.update()
        .where(TicketStatusPeriod.ticket_id != ticket_id)
        .values(entered_at=late + timedelta(days=5))
    )
    assert await periods.snapshot(db, date(2026, 10, 14)) == 1
    assert await periods.snapshot(db, date(2026, 10, 13)) == 0
    assert t4["key"] == "PA-4"
    total = await periods.backfill_snapshots(db, date(2026, 10, 13), date(2026, 10, 15))
    assert total == 2


async def test_snapshot_job_runs_from_the_queue(
    db: AsyncSession, board: Team, client: AsyncClient
) -> None:
    await new_ticket(client, board.member)
    from radicle.platform.services import queue

    await queue.enqueue(db, periods.SNAPSHOT_JOB)
    assert await run_jobs(db) == ["daily_snapshot"]
    count = await db.scalar(
        select(DailyStatusCount.ticket_count).where(DailyStatusCount.date == periods.today())
    )
    assert count == 1
    assert uuid.UUID(int=0) in set(await db.scalars(select(DailyStatusCount.sprint_key)))
    assert await db.scalar(select(TicketEvent.id).limit(1)) is not None
