"""Rebuild status periods from ticket history. Pure: no database access.

Used by the stage 3 migration (sync connection) and by `radicle backfill-periods`, so
both produce exactly what the live code writes on each transition.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

# (project key or None, ticket type, status name) -> (status id or None, category)
Resolver = Callable[[str | None, str, str], tuple[Any, str]]

STATUS_EVENTS = {"created", "status_changed", "status_remapped", "moved"}


@dataclass(frozen=True)
class Event:
    event_type: str
    old: Any
    new: Any
    at: datetime


@dataclass
class Period:
    status_id: Any
    category: str
    entered_at: datetime
    exited_at: datetime | None = None


def _project(key: str | None) -> str | None:
    return key.rsplit("-", 1)[0].upper() if key else None


def build(
    events: Iterable[Event], *, ticket_type: str, project_key: str, resolve: Resolver
) -> list[Period]:
    """Periods of one ticket, oldest first. `ticket_type` and `project_key` are the
    ticket's current ones; earlier values are recovered from type and move events."""
    ordered = list(events)
    # Walk back to the type and project the ticket was created with.
    first_type = ticket_type
    first_project = project_key
    for e in ordered:
        if e.event_type == "type_changed" and e.old:
            first_type = str(e.old)
            break
    for e in ordered:
        if e.event_type == "moved" and isinstance(e.old, dict):
            first_project = _project(e.old.get("key")) or project_key
            break
    current_type, current_project = first_type, first_project
    periods: list[Period] = []
    for e in ordered:
        if e.event_type == "type_changed" and e.new:
            current_type = str(e.new)
            continue
        if e.event_type not in STATUS_EVENTS or not isinstance(e.new, dict):
            continue
        if e.event_type == "moved":
            current_project = _project(e.new.get("key")) or current_project
        name = e.new.get("status")
        if not name:
            continue
        status_id, category = resolve(current_project, current_type, str(name))
        if periods and periods[-1].exited_at is None:
            if periods[-1].status_id == status_id and status_id is not None:
                continue  # e.g. a move that kept the same status id (cannot happen) or noise
            periods[-1].exited_at = e.at
        periods.append(Period(status_id, category, e.at))
    return periods
