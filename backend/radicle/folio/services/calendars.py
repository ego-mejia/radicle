"""Calendars (Folio 5.8): each space keeps calendars of events (vacations, releases, on-call)
and may show the milestones of Docket projects, read through `docket.public` with the
reader's own access. A calendar's token opens its read-only iCal feed without signing in.

Viewers read a calendar and space admins manage it; events are in `calendar_events`."""

import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import radicle.docket.public as docket
from radicle.folio.db.calendars import FolioCalendar, FolioEvent
from radicle.folio.db.models import FolioSpace
from radicle.folio.services import access
from radicle.platform.db.models import User
from radicle.platform.errors import NotFound, ValidationFailed

COLORS = ("blue", "green", "purple", "orange", "red", "teal", "gray")
NAME_MAX = 80
PROJECTS_MAX = 10
RANGE_MAX = timedelta(days=400)
# What the iCal feed covers, around today.
FEED_PAST = timedelta(days=365)
FEED_AHEAD = timedelta(days=730)


def _invalid(field_name: str, message: str) -> ValidationFailed:
    return ValidationFailed(message, errors=[{"field": field_name, "message": "invalid"}])


def new_token() -> str:
    return secrets.token_urlsafe(32)


async def _space(db: AsyncSession, calendar: FolioCalendar) -> FolioSpace:
    space = await db.get(FolioSpace, calendar.space_id)
    if space is None:  # the foreign key cascades, so only mid-delete
        raise NotFound("This calendar's space is gone.", code="calendar_not_found")
    return space


async def get_calendar(db: AsyncSession, user: User, calendar_id: uuid.UUID) -> FolioCalendar:
    """A calendar of a space the user may see; any other is not found."""
    calendar = await db.get(FolioCalendar, calendar_id)
    if calendar is None or calendar.space_id not in await access.visible_space_ids(db, user):
        raise NotFound(
            f"No calendar {calendar_id}. List a space's calendars with "
            "GET /api/v1/folio/calendars?space=KEY.",
            code="calendar_not_found",
        )
    return calendar


async def list_calendars(
    db: AsyncSession, user: User, space: FolioSpace | None = None
) -> list[FolioCalendar]:
    """A space's calendars, or with no space those of every space the user may see."""
    visible = await access.visible_space_ids(db, user)
    if space is not None:
        visible &= {space.id}
    rows = await db.scalars(
        select(FolioCalendar)
        .where(FolioCalendar.space_id.in_(visible))
        .order_by(FolioCalendar.name, FolioCalendar.id)
    )
    return list(rows)


@dataclass
class CalendarData:
    name: str | None = None
    color: str | None = None
    docket_projects: list[str] | None = None


async def _apply_calendar(
    db: AsyncSession, user: User, calendar: FolioCalendar, data: CalendarData
) -> None:
    if data.name is not None:
        name = data.name.strip()
        if not 1 <= len(name) <= NAME_MAX:
            raise _invalid("name", f"A calendar's name is 1 to {NAME_MAX} characters.")
        calendar.name = name
    if data.color is not None:
        if data.color not in COLORS:
            raise _invalid("color", f"Pick one of these colors: {', '.join(COLORS)}.")
        calendar.color = data.color
    if data.docket_projects is not None:
        if len(data.docket_projects) > PROJECTS_MAX:
            raise _invalid("docket_projects", f"Show at most {PROJECTS_MAX} Docket projects.")
        keys: list[str] = []
        for key in data.docket_projects:
            found = await docket.get_project(db, key, user)
            if found is None:
                raise _invalid(
                    "docket_projects",
                    f"No Docket project {key.strip().upper()} you can see. Use a project's key, "
                    "like PA.",
                )
            if found not in keys:
                keys.append(found)
        calendar.docket_projects = keys


async def create_calendar(
    db: AsyncSession, user: User, space: FolioSpace, data: CalendarData
) -> FolioCalendar:
    await access.require_admin(db, user, space)
    if data.name is None:
        raise _invalid("name", "Give the calendar a name.")
    calendar = FolioCalendar(space_id=space.id, ical_token=new_token(), created_by=user.id)
    await _apply_calendar(db, user, calendar, data)
    db.add(calendar)
    await db.flush()
    return calendar


async def update_calendar(
    db: AsyncSession, user: User, calendar: FolioCalendar, data: CalendarData
) -> FolioCalendar:
    await access.require_admin(db, user, await _space(db, calendar))
    await _apply_calendar(db, user, calendar, data)
    await db.flush()
    return calendar


async def rotate_token(db: AsyncSession, user: User, calendar: FolioCalendar) -> FolioCalendar:
    """A new feed link; the old one stops working."""
    await access.require_admin(db, user, await _space(db, calendar))
    calendar.ical_token = new_token()
    await db.flush()
    return calendar


async def delete_calendar(db: AsyncSession, user: User, calendar: FolioCalendar) -> None:
    await access.require_admin(db, user, await _space(db, calendar))
    await db.delete(calendar)
    await db.flush()


@dataclass(frozen=True)
class Milestone:
    id: uuid.UUID
    project: str
    name: str
    status: str
    due: date


@dataclass(frozen=True)
class Agenda:
    events: list[FolioEvent]
    milestones: list[Milestone]


def _check_range(start: datetime, end: datetime) -> None:
    if end <= start:
        raise _invalid("end", "end must come after start.")
    if end - start > RANGE_MAX:
        raise _invalid("end", f"Ask for at most {RANGE_MAX.days} days at a time.")


async def agenda(
    db: AsyncSession, user: User, calendar: FolioCalendar, start: datetime, end: datetime
) -> Agenda:
    """Events that overlap [start, end) and the milestones due in it the user may see."""
    _check_range(start, end)
    return await _agenda(db, user, calendar, start, end)


async def _agenda(
    db: AsyncSession, user: User | None, calendar: FolioCalendar, start: datetime, end: datetime
) -> Agenda:
    rows = await db.scalars(
        select(FolioEvent)
        .where(
            FolioEvent.calendar_id == calendar.id,
            FolioEvent.start_at < end,
            FolioEvent.end_at > start,
        )
        .order_by(FolioEvent.start_at, FolioEvent.id)
    )
    milestones: list[Milestone] = []
    if user is not None:
        for key in calendar.docket_projects:
            found = await docket.list_milestones(
                db, key, user, start=start.date(), end=(end - timedelta(microseconds=1)).date()
            )
            milestones += [
                Milestone(m.id, m.project, m.name, m.status, m.target_date)
                for m in found
                if m.target_date is not None
            ]
    milestones.sort(key=lambda m: (m.due, m.project, m.name))
    return Agenda(list(rows), milestones)


async def feed(db: AsyncSession, token: str) -> tuple[FolioCalendar, Agenda]:
    """What the iCal feed shows: the calendar's events and the milestones its creator may
    see. An unknown or rotated token is not found."""
    calendar = await db.scalar(select(FolioCalendar).where(FolioCalendar.ical_token == token))
    if calendar is None or (await _space(db, calendar)).deleted_at is not None:
        raise NotFound("No calendar feed at this link.", code="calendar_not_found")
    creator = await db.get(User, calendar.created_by) if calendar.created_by else None
    if creator is not None and not creator.is_active:
        creator = None
    now = datetime.now(UTC)
    return calendar, await _agenda(db, creator, calendar, now - FEED_PAST, now + FEED_AHEAD)
