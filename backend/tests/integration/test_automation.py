"""Automation rules (Folio 5.6, ADR 0042): triggers, platform actions, schedules and loop
protection, with a test event and test actions."""

from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.db.models import (
    AutomationRun,
    DeliveryStatus,
    OutboxEvent,
    User,
)
from radicle.platform.errors import ValidationFailed
from radicle.platform.services import automation, events
from tests.conftest import Clock, Team, run_jobs

events.public_event("test.rang", "A test bell rang")


@events.publisher("test", "rang")
async def _rang(db: AsyncSession, event: OutboxEvent) -> list[events.PublicEvent]:
    data = {"page": {"title": event.payload["n"], "url": "https://r.example/p"}}
    return [
        events.PublicEvent(
            "test.rang",
            data,
            {"space": event.payload.get("space", "eng")},
            f"Bell {event.payload['n']}",
        )
    ]


done: list[str] = []


@automation.action("test.note", "Write down what happened")
async def _note(db: AsyncSession, ctx: automation.Context, step: dict[str, Any]) -> str:
    done.append(f"{ctx.actor.handle}:{ctx.data['page']['title']}")
    if step.get("again"):  # an action whose result triggers the same rule
        await events.emit(db, "test", "rang", actor=None, payload={"n": "again"})
    return "noted"


@automation.selector("test.items")
async def _items(db: AsyncSession, actor: User, params: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"target": n, "page": {"title": n, "url": ""}} for n in params["items"]]


@pytest.fixture(autouse=True)
def _fresh() -> None:
    done.clear()


async def _admin(db: AsyncSession, team: Team) -> User:
    user = await db.scalar(select(User).where(User.handle == team.instance.handle))
    assert user is not None
    return user


ON_RANG = {"type": "event", "event": "test.rang"}


async def test_an_event_runs_the_rule_once_with_its_authors_permissions(
    db: AsyncSession, team: Team
) -> None:
    admin = await _admin(db, team)
    await automation.create(db, admin, "Note", ON_RANG, [{"type": "test.note"}], {"space": "eng"})
    off = await automation.create(db, admin, "Off", ON_RANG, [{"type": "test.note"}])
    off.active = False
    await events.emit(db, "test", "rang", actor=None, payload={"n": "1"})
    await events.emit(db, "test", "rang", actor=None, payload={"n": "2", "space": "ops"})
    await run_jobs(db)
    assert done == ["fernando:1"]
    event = await db.scalar(select(OutboxEvent).order_by(OutboxEvent.id))
    assert event is not None
    event.dispatched_at = None  # a crashed worker dispatches again
    await run_jobs(db)
    assert done == ["fernando:1"]
    run = await db.scalar(select(AutomationRun))
    assert run is not None and run.status == DeliveryStatus.sent and run.log == ["noted"]


async def test_a_rule_never_loops(db: AsyncSession, team: Team) -> None:
    admin = await _admin(db, team)
    await automation.create(db, admin, "Echo", ON_RANG, [{"type": "test.note", "again": True}])
    await automation.create(db, admin, "Echo 2", ON_RANG, [{"type": "test.note", "again": True}])
    await events.emit(db, "test", "rang", actor=None, payload={"n": "1"})
    await run_jobs(db)
    # Each rule runs on the first bell and on the bell the other one rang, then stops.
    assert sorted(done) == ["fernando:1", "fernando:1", "fernando:again", "fernando:again"]
    assert await db.scalar(select(func.count()).select_from(AutomationRun)) == 4


async def test_schedules_run_once_per_target_and_period(
    db: AsyncSession, team: Team, clock: Clock
) -> None:
    trigger = {
        "type": "schedule",
        "every": "day",
        "select": "test.items",
        "params": {"items": ["a", "b"]},
    }
    await automation.create(db, await _admin(db, team), "Daily", trigger, [{"type": "test.note"}])
    await automation.schedule(db)
    await run_jobs(db)
    await automation.schedule(db)  # not due again yet
    await run_jobs(db)
    assert sorted(done) == ["fernando:a", "fernando:b"]
    clock.advance(days=1)
    await automation.schedule(db)
    await run_jobs(db)
    assert len(done) == 4


@pytest.mark.parametrize(
    ("trigger", "steps", "says"),
    [
        ({"type": "event", "event": "nope"}, [{"type": "test.note"}], "Pick one of these events"),
        ({"type": "schedule", "every": "week", "select": "test.items"}, [], "every hour or"),
        ({"type": "schedule", "every": "day", "select": "x"}, [], "Pick what it runs on"),
        (ON_RANG, [], "at least one action"),
        (ON_RANG, [{"type": "fly"}], "Pick one of:"),
    ],
)
async def test_bad_rules_say_how_to_fix(
    db: AsyncSession, team: Team, trigger: dict, steps: list, says: str
) -> None:
    with pytest.raises(ValidationFailed, match=says):
        await automation.create(db, await _admin(db, team), "X", trigger, steps)
