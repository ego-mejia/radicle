"""Calendars (Folio 5.8): Docket milestones with the reader's access, the iCal feed's token,
and who manages calendars. Viewers read; space admins manage."""

from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.calendars import FolioCalendar, FolioEvent
from radicle.folio.db.models import FolioSpace
from radicle.folio.services import calendars
from radicle.folio.services.calendars import CalendarData
from radicle.platform.errors import Forbidden, NotFound, ValidationFailed
from tests.conftest import Team
from tests.integration.folio_calendar_helpers import at, eng_space, releases, user

__all__ = ["releases"]


def _event(calendar: FolioCalendar, title: str, start: datetime, hours: int = 1) -> FolioEvent:
    return FolioEvent(
        calendar_id=calendar.id, title=title, start_at=start, end_at=start + timedelta(hours=hours)
    )


async def test_the_agenda(db: AsyncSession, board: Team, releases: FolioCalendar) -> None:
    assert releases.docket_projects == ["PA"] and len(releases.ical_token) >= 40
    db.add_all([_event(releases, "Demo", at(10, 15)), _event(releases, "Corte", at(30, 23), 2)])
    await db.flush()
    vera = await user(db, "vera")
    december = await calendars.agenda(db, vera, releases, at(1), at(31))
    assert [e.title for e in december.events] == ["Demo", "Corte"]
    assert [(m.project, m.name, m.due) for m in december.milestones] == [
        ("PA", "V1", date(2026, 12, 15))
    ]
    # olga can't see project PA: no milestones.
    olga = await user(db, "olga")
    assert (await calendars.agenda(db, olga, releases, at(1), at(31))).milestones == []
    november = await calendars.agenda(db, vera, releases, at(1, month=11), at(30, month=11))
    assert november.events == [] and november.milestones == []


async def test_who_manages(db: AsyncSession, board: Team, releases: FolioCalendar) -> None:
    ana, vera, olga = [await user(db, h) for h in ("ana", "vera", "olga")]
    space = await db.get(FolioSpace, releases.space_id)
    assert space is not None
    assert [c.name for c in await calendars.list_calendars(db, vera, space)] == ["Releases"]
    assert (await calendars.get_calendar(db, vera, releases.id)).id == releases.id
    with pytest.raises(NotFound):
        await calendars.get_calendar(db, olga, releases.id)
    assert await calendars.list_calendars(db, olga, space) == []
    with pytest.raises(Forbidden):
        await calendars.create_calendar(db, ana, space, CalendarData(name="Otro"))
    with pytest.raises(Forbidden):
        await calendars.update_calendar(db, ana, releases, CalendarData(name="Mío"))
    with pytest.raises(Forbidden):
        await calendars.delete_calendar(db, ana, releases)


async def test_the_feed_token(db: AsyncSession, board: Team, releases: FolioCalendar) -> None:
    admin = await user(db, board.instance.handle)
    db.add(_event(releases, "Pronto", datetime.now(UTC) + timedelta(days=3)))
    await db.flush()
    old = releases.ical_token
    calendar, found = await calendars.feed(db, old)
    assert calendar.id == releases.id and [e.title for e in found.events] == ["Pronto"]
    await calendars.rotate_token(db, admin, releases)
    with pytest.raises(NotFound):
        await calendars.feed(db, old)
    assert (await calendars.feed(db, releases.ical_token))[0].id == releases.id
    await calendars.update_calendar(db, admin, releases, CalendarData(name="Lanzamientos"))
    assert releases.name == "Lanzamientos"
    await calendars.delete_calendar(db, admin, releases)
    with pytest.raises(NotFound):
        await calendars.feed(db, releases.ical_token)


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (CalendarData(name=""), "name"),
        (CalendarData(name="X", color="pink"), "colors"),
        (CalendarData(name="X", docket_projects=["ZZ"]), "No Docket project ZZ"),
        (CalendarData(name="X", docket_projects=["PA"] * 11), "at most"),
        (CalendarData(), "name"),
    ],
)
async def test_calendar_errors(
    client: AsyncClient, db: AsyncSession, board: Team, data: CalendarData, message: str
) -> None:
    space = await eng_space(client, db, board)
    with pytest.raises(ValidationFailed, match=message):
        await calendars.create_calendar(db, await user(db, board.instance.handle), space, data)


async def test_range_errors(db: AsyncSession, board: Team, releases: FolioCalendar) -> None:
    vera = await user(db, "vera")
    with pytest.raises(ValidationFailed, match="after start"):
        await calendars.agenda(db, vera, releases, at(2), at(1))
    with pytest.raises(ValidationFailed, match="at most"):
        await calendars.agenda(db, vera, releases, at(1), at(1) + timedelta(days=401))
