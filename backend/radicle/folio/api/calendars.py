"""Calendars over REST (Folio 5.8): a space's calendars, their events and the Docket
milestones they show. The iCal feed itself is `ical.py`, outside /api and without auth."""

import uuid
from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Query, Response
from pydantic import Field

from radicle.folio.db.calendars import EventCategory, FolioCalendar, FolioEvent
from radicle.folio.db.models import FolioSpace
from radicle.folio.services import access, calendar_events, calendars, spaces
from radicle.folio.services.calendar_events import EventData
from radicle.folio.services.calendars import CalendarData
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Input, Output, UtcDatetime
from radicle.platform.db.models import User

router = APIRouter(tags=["folio"])

Color = Literal["blue", "green", "purple", "orange", "red", "teal", "gray"]
Category = Literal["vacation", "release", "event", "oncall", "other"]


class CalendarOut(Output):
    id: uuid.UUID
    space: str
    name: str
    color: Color
    docket_projects: list[str]
    ical_path: str = Field(description="The read-only iCal feed; anyone with the link can read it")
    can_manage: bool = Field(description="You may rename it, delete it or rotate its feed link")
    can_add: bool = Field(description="You may add events")
    created_at: UtcDatetime


class CalendarsOut(Output):
    items: list[CalendarOut]


class CalendarIn(Input):
    space: str
    name: str
    color: Color = "blue"
    docket_projects: list[str] = Field(
        default_factory=list, description="Keys of Docket projects whose milestones it shows"
    )


class CalendarPatch(Input):
    name: str | None = None
    color: Color | None = None
    docket_projects: list[str] | None = None


class CalendarEventOut(Output):
    id: uuid.UUID
    title: str
    description: str
    start_at: UtcDatetime
    end_at: UtcDatetime = Field(description="Exclusive; all-day events end at a midnight UTC")
    all_day: bool
    category: Category
    people: list[str] = Field(description="Handles")
    created_by: str | None
    can_edit: bool


class CalendarMilestoneOut(Output):
    project: str
    name: str
    status: str
    due: date


class AgendaOut(Output):
    events: list[CalendarEventOut]
    milestones: list[CalendarMilestoneOut]


class CalendarEventIn(Input):
    title: str
    description: str = ""
    start_at: datetime
    end_at: datetime
    all_day: bool = False
    category: Category = "event"
    people: list[str] = Field(default_factory=list, description="Handles")


class CalendarEventPatch(Input):
    title: str | None = None
    description: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    all_day: bool | None = None
    category: Category | None = None
    people: list[str] | None = None


async def _reader(db: Db, principal: CurrentPrincipal) -> User:
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    return principal.user


async def _out(db: Db, user: User, calendar: FolioCalendar) -> CalendarOut:
    space = await db.get(FolioSpace, calendar.space_id)
    perms = await access.space_permissions(db, user, space) if space else frozenset()
    return CalendarOut(
        id=calendar.id,
        space=space.key if space else "",
        name=calendar.name,
        color=calendar.color,
        docket_projects=list(calendar.docket_projects),
        ical_path=f"/ical/{calendar.ical_token}.ics",
        can_manage="admin" in perms,
        can_add="create" in perms,
        created_at=calendar.created_at,
    )


async def _events(
    db: Db, user: User, calendar: FolioCalendar, events: list[FolioEvent]
) -> list[CalendarEventOut]:
    space = await db.get(FolioSpace, calendar.space_id)
    perms = await access.space_permissions(db, user, space) if space else frozenset()
    handles = await calendar_events.handles(db, calendar_events.people_of(events))
    return [
        CalendarEventOut(
            id=e.id,
            title=e.title,
            description=e.description,
            start_at=e.start_at,
            end_at=e.end_at,
            all_day=e.all_day,
            category=e.category.value,
            people=[handles[p] for p in e.people if p in handles],
            created_by=handles.get(e.created_by) if e.created_by else None,
            can_edit="create" in perms and (e.created_by == user.id or "delete_any" in perms),
        )
        for e in events
    ]


@router.get("/calendars", response_model=CalendarsOut)
async def list_calendars(
    principal: CurrentPrincipal,
    db: Db,
    space: str | None = Query(default=None, description="The space's key; default every space"),
) -> CalendarsOut:
    """A space's calendars, or those of every space you can see, by name."""
    user = await _reader(db, principal)
    found = await spaces.get_space(db, user, space) if space else None
    rows = await calendars.list_calendars(db, user, found)
    return CalendarsOut(items=[await _out(db, user, c) for c in rows])


@router.post("/calendars", response_model=CalendarOut, status_code=201)
async def create_calendar(body: CalendarIn, principal: CurrentPrincipal, db: Db) -> CalendarOut:
    """A new calendar in the space. Space admins only."""
    user = await _reader(db, principal)
    space = await spaces.get_space(db, user, body.space)
    data = CalendarData(name=body.name, color=body.color, docket_projects=body.docket_projects)
    return await _out(db, user, await calendars.create_calendar(db, user, space, data))


@router.get("/calendars/{calendar_id}", response_model=CalendarOut)
async def get_calendar(calendar_id: uuid.UUID, principal: CurrentPrincipal, db: Db) -> CalendarOut:
    user = await _reader(db, principal)
    return await _out(db, user, await calendars.get_calendar(db, user, calendar_id))


@router.patch("/calendars/{calendar_id}", response_model=CalendarOut)
async def patch_calendar(
    calendar_id: uuid.UUID, body: CalendarPatch, principal: CurrentPrincipal, db: Db
) -> CalendarOut:
    """Rename, recolor or change the Docket projects it shows. Space admins only."""
    user = await _reader(db, principal)
    calendar = await calendars.get_calendar(db, user, calendar_id)
    data = CalendarData(name=body.name, color=body.color, docket_projects=body.docket_projects)
    return await _out(db, user, await calendars.update_calendar(db, user, calendar, data))


@router.post("/calendars/{calendar_id}/ical-token", response_model=CalendarOut)
async def rotate_ical_token(
    calendar_id: uuid.UUID, principal: CurrentPrincipal, db: Db
) -> CalendarOut:
    """A new feed link; subscriptions to the old one stop updating. Space admins only."""
    user = await _reader(db, principal)
    calendar = await calendars.get_calendar(db, user, calendar_id)
    return await _out(db, user, await calendars.rotate_token(db, user, calendar))


@router.delete("/calendars/{calendar_id}", status_code=204)
async def delete_calendar(calendar_id: uuid.UUID, principal: CurrentPrincipal, db: Db) -> Response:
    """The calendar and its events. Space admins only."""
    user = await _reader(db, principal)
    await calendars.delete_calendar(db, user, await calendars.get_calendar(db, user, calendar_id))
    return Response(status_code=204)


@router.get("/calendars/{calendar_id}/events", response_model=AgendaOut)
async def list_events(
    calendar_id: uuid.UUID,
    principal: CurrentPrincipal,
    db: Db,
    start: datetime = Query(description="From, inclusive (ISO 8601 with a time zone)"),
    end: datetime = Query(description="To, exclusive; at most 400 days after start"),
) -> AgendaOut:
    """Events that overlap the range, and the Docket milestones due in it that you can see."""
    user = await _reader(db, principal)
    calendar = await calendars.get_calendar(db, user, calendar_id)
    found = await calendars.agenda(db, user, calendar, start, end)
    return AgendaOut(
        events=await _events(db, user, calendar, found.events),
        milestones=[
            CalendarMilestoneOut(project=m.project, name=m.name, status=m.status, due=m.due)
            for m in found.milestones
        ],
    )


def _event_data(body: CalendarEventIn | CalendarEventPatch) -> EventData:
    return EventData(
        title=body.title,
        description=body.description,
        start_at=body.start_at,
        end_at=body.end_at,
        all_day=body.all_day,
        category=EventCategory(body.category) if body.category else None,
        people=body.people,
    )


@router.post("/calendars/{calendar_id}/events", response_model=CalendarEventOut, status_code=201)
async def create_event(
    calendar_id: uuid.UUID, body: CalendarEventIn, principal: CurrentPrincipal, db: Db
) -> CalendarEventOut:
    """A new event. Takes the create permission in the space."""
    user = await _reader(db, principal)
    calendar = await calendars.get_calendar(db, user, calendar_id)
    event = await calendar_events.create_event(db, user, calendar, _event_data(body))
    return (await _events(db, user, calendar, [event]))[0]


@router.patch("/calendars/{calendar_id}/events/{event_id}", response_model=CalendarEventOut)
async def patch_event(
    calendar_id: uuid.UUID,
    event_id: uuid.UUID,
    body: CalendarEventPatch,
    principal: CurrentPrincipal,
    db: Db,
) -> CalendarEventOut:
    """Change an event you added (delete_any changes anyone's)."""
    user = await _reader(db, principal)
    calendar = await calendars.get_calendar(db, user, calendar_id)
    event = await calendar_events.get_event(db, user, calendar, event_id)
    await calendar_events.update_event(db, user, calendar, event, _event_data(body))
    return (await _events(db, user, calendar, [event]))[0]


@router.delete("/calendars/{calendar_id}/events/{event_id}", status_code=204)
async def delete_event(
    calendar_id: uuid.UUID, event_id: uuid.UUID, principal: CurrentPrincipal, db: Db
) -> Response:
    user = await _reader(db, principal)
    calendar = await calendars.get_calendar(db, user, calendar_id)
    event = await calendar_events.get_event(db, user, calendar, event_id)
    await calendar_events.delete_event(db, user, calendar, event)
    return Response(status_code=204)
