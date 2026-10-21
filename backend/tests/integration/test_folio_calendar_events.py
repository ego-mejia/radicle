"""Calendar events (Folio 5.8): all-day or timed, with people. `create` adds them; only who
added one, or `delete_any`, changes it."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.calendars import EventCategory, FolioCalendar
from radicle.folio.services import calendar_events, calendars
from radicle.folio.services.calendar_events import EventData
from radicle.platform.errors import Forbidden, NotFound, ValidationFailed
from tests.conftest import Team
from tests.integration.folio_calendar_helpers import at, releases, user

__all__ = ["releases"]


async def test_add_events(db: AsyncSession, board: Team, releases: FolioCalendar) -> None:
    ana, luis, vera = [await user(db, h) for h in ("ana", "luis", "vera")]
    data = EventData(
        title=" Lanzamiento ",
        start_at=at(10, 15),
        end_at=at(10, 16),
        category=EventCategory.release,
        people=["@luis", "ana", "luis"],
    )
    launch = await calendar_events.create_event(db, ana, releases, data)
    assert launch.title == "Lanzamiento" and launch.created_by == ana.id
    assert launch.people == [luis.id, ana.id]
    data = EventData(
        title="Vacaciones",
        start_at=at(14, 9),
        end_at=at(15, 18),
        all_day=True,
        category=EventCategory.vacation,
    )
    trip = await calendar_events.create_event(db, luis, releases, data)
    # Whole days in UTC, the end exclusive as in iCal.
    assert (trip.start_at, trip.end_at) == (at(14), at(16))
    one = EventData(title="Corte", start_at=at(20, 10), end_at=at(20, 10), all_day=True)
    assert (await calendar_events.create_event(db, luis, releases, one)).end_at == at(21)
    december = await calendars.agenda(db, vera, releases, at(1), at(31))
    assert [e.title for e in december.events] == ["Lanzamiento", "Vacaciones", "Corte"]
    handles = await calendar_events.handles(db, calendar_events.people_of(december.events))
    assert handles == {ana.id: "ana", luis.id: "luis"}
    assert await calendar_events.handles(db, set()) == {}


async def test_who_changes_an_event(db: AsyncSession, board: Team, releases: FolioCalendar) -> None:
    ana, luis, vera = [await user(db, h) for h in ("ana", "luis", "vera")]
    data = EventData(title="Demo", start_at=at(3, 10), end_at=at(3, 11))
    with pytest.raises(Forbidden):
        await calendar_events.create_event(db, vera, releases, data)
    event = await calendar_events.create_event(db, ana, releases, data)
    with pytest.raises(Forbidden, match="Only who added"):
        await calendar_events.update_event(db, luis, releases, event, EventData(title="Mía"))
    await calendar_events.update_event(db, ana, releases, event, EventData(title="Demo final"))
    assert event.title == "Demo final"
    admin = await user(db, board.instance.handle)
    assert (await calendar_events.get_event(db, admin, releases, event.id)).id == event.id
    change = EventData(category=EventCategory.oncall)
    await calendar_events.update_event(db, admin, releases, event, change)
    await calendar_events.delete_event(db, admin, releases, event)
    with pytest.raises(NotFound):
        await calendar_events.get_event(db, admin, releases, event.id)


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (EventData(start_at=at(1), end_at=at(2)), "title"),
        (EventData(title="x" * 201, start_at=at(1), end_at=at(2)), "title"),
        (EventData(title="X", description="x" * 5001, start_at=at(1), end_at=at(2)), "descr"),
        (EventData(title="X", start_at=at(1)), "start_at and end_at"),
        (EventData(title="X", start_at=at(2), end_at=at(1)), "before"),
        (EventData(title="X", start_at=at(1), end_at=at(1) + timedelta(days=400)), "at most"),
        (EventData(title="X", start_at=datetime(2026, 1, 1), end_at=at(2)), "time zone"),
        (EventData(title="X", start_at=at(1), end_at=at(2), people=["nadie"]), "@nadie"),
        (EventData(title="X", start_at=at(1), end_at=at(2), people=["a"] * 51), "at most"),
    ],
)
async def test_event_errors(
    db: AsyncSession, board: Team, releases: FolioCalendar, data: EventData, message: str
) -> None:
    with pytest.raises(ValidationFailed, match=message):
        await calendar_events.create_event(db, await user(db, "ana"), releases, data)
