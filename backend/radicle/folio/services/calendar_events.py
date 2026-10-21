"""Events in a calendar (Folio 5.8): all-day or timed, with a category and linked people.
People with `create` in the space add events and change their own; `delete_any` changes
anyone's."""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.calendars import EventCategory, FolioCalendar, FolioEvent
from radicle.folio.services import access
from radicle.folio.services.calendars import _invalid, _space
from radicle.platform.db.models import User
from radicle.platform.errors import Forbidden, NotFound

TITLE_MAX = 200
DESCRIPTION_MAX = 5000
PEOPLE_MAX = 50
EVENT_SPAN = timedelta(days=366)


@dataclass
class EventData:
    title: str | None = None
    description: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    all_day: bool | None = None
    category: EventCategory | None = None
    people: list[str] | None = field(default=None)  # handles


def _midnight(day: date) -> datetime:
    return datetime.combine(day, time(), tzinfo=UTC)


async def _people(db: AsyncSession, handles: list[str]) -> list[uuid.UUID]:
    if len(handles) > PEOPLE_MAX:
        raise _invalid("people", f"Link at most {PEOPLE_MAX} people to an event.")
    wanted = [h.strip().lstrip("@") for h in handles if h.strip()]
    if not wanted:
        return []
    found = {
        u.handle.lower(): u.id
        for u in await db.scalars(
            select(User).where(User.handle.in_(wanted), User.is_active.is_(True))
        )
    }
    missing = [h for h in wanted if h.lower() not in found]
    if missing:
        raise _invalid("people", f"No active user @{missing[0]}. Use people's handles.")
    return list(dict.fromkeys(found[h.lower()] for h in wanted))


async def _apply_event(db: AsyncSession, event: FolioEvent, data: EventData) -> None:
    if data.title is not None:
        title = data.title.strip()
        if not 1 <= len(title) <= TITLE_MAX:
            raise _invalid("title", f"An event's title is 1 to {TITLE_MAX} characters.")
        event.title = title
    if data.description is not None:
        if len(data.description) > DESCRIPTION_MAX:
            raise _invalid("description", f"A description is at most {DESCRIPTION_MAX} characters.")
        event.description = data.description
    if data.category is not None:
        event.category = data.category
    if data.all_day is not None:
        event.all_day = data.all_day
    if data.start_at is not None:
        event.start_at = data.start_at
    if data.end_at is not None:
        event.end_at = data.end_at
    for name in ("start_at", "end_at"):
        value = getattr(event, name)
        if value is not None and value.tzinfo is None:
            raise _invalid(name, f"{name} needs a time zone, like 2026-11-03T10:00:00Z.")
    if event.start_at is None or event.end_at is None:
        raise _invalid("start_at", "An event needs start_at and end_at.")
    if event.end_at < event.start_at:
        raise _invalid("end_at", "end_at can't come before start_at.")
    if event.all_day:
        # Whole days in UTC; the end is exclusive, as in iCal.
        first = event.start_at.astimezone(UTC).date()
        last = max(event.end_at.astimezone(UTC).date(), first)
        if _midnight(last) < event.end_at or last == first:
            last += timedelta(days=1)
        event.start_at, event.end_at = _midnight(first), _midnight(last)
    if event.end_at - event.start_at > EVENT_SPAN:
        raise _invalid("end_at", f"An event lasts at most {EVENT_SPAN.days} days.")
    if data.people is not None:
        event.people = await _people(db, data.people)


async def _require_write(db: AsyncSession, user: User, calendar: FolioCalendar) -> frozenset[str]:
    space = await _space(db, calendar)
    perms = await access.space_permissions(db, user, space)
    if "create" not in perms:
        raise Forbidden(
            f"You can't add events in {space.name}: it takes the create permission in the "
            "space. A space admin can give it in the space's permissions.",
            code="space_permission_denied",
        )
    return perms


async def create_event(
    db: AsyncSession, user: User, calendar: FolioCalendar, data: EventData
) -> FolioEvent:
    await _require_write(db, user, calendar)
    if data.title is None:
        raise _invalid("title", "Give the event a title.")
    event = FolioEvent(
        calendar_id=calendar.id,
        created_by=user.id,
        all_day=False,
        category=EventCategory.event,
        description="",
        people=[],
    )
    await _apply_event(db, event, data)
    db.add(event)
    await db.flush()
    return event


async def get_event(
    db: AsyncSession, user: User, calendar: FolioCalendar, event_id: uuid.UUID
) -> FolioEvent:
    event = await db.get(FolioEvent, event_id)
    if event is None or event.calendar_id != calendar.id:
        raise NotFound(f"No event {event_id} in {calendar.name}.", code="event_not_found")
    return event


async def _require_change(
    db: AsyncSession, user: User, calendar: FolioCalendar, event: FolioEvent
) -> None:
    perms = await _require_write(db, user, calendar)
    if event.created_by != user.id and "delete_any" not in perms:
        raise Forbidden(
            "Only who added this event, or someone with delete_any in the space, can change it.",
            code="event_not_yours",
        )


async def update_event(
    db: AsyncSession, user: User, calendar: FolioCalendar, event: FolioEvent, data: EventData
) -> FolioEvent:
    await _require_change(db, user, calendar, event)
    await _apply_event(db, event, data)
    await db.flush()
    return event


async def delete_event(
    db: AsyncSession, user: User, calendar: FolioCalendar, event: FolioEvent
) -> None:
    await _require_change(db, user, calendar, event)
    await db.delete(event)
    await db.flush()


def people_of(events: list[FolioEvent]) -> set[uuid.UUID]:
    """Everyone linked to or who added these events."""
    return {p for e in events for p in e.people} | {e.created_by for e in events if e.created_by}


async def handles(db: AsyncSession, ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not ids:
        return {}
    rows = await db.execute(select(User.id, User.handle).where(User.id.in_(ids)))
    return {i: h for i, h in rows.all()}
