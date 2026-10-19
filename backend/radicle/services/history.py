"""Append-only ticket history. Every ticket mutation goes through `record`."""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.db.models import EventType, Project, Ticket, TicketEvent, User, utcnow


def record(
    db: AsyncSession,
    ticket: Ticket,
    actor: User,
    event_type: EventType,
    *,
    field: str | None = None,
    old: Any = None,
    new: Any = None,
) -> TicketEvent:
    event = TicketEvent(
        ticket_id=ticket.id,
        actor_id=actor.id,
        event_type=event_type.value,
        field=field,
        old_value=old,
        new_value=new,
        created_at=utcnow(),  # set now so status periods can reuse the exact moment
    )
    db.add(event)
    return event


async def list_events(
    db: AsyncSession, ticket_id: uuid.UUID, *, limit: int, before_id: int | None = None
) -> list[TicketEvent]:
    """Newest first."""
    query = select(TicketEvent).where(TicketEvent.ticket_id == ticket_id)
    if before_id is not None:
        query = query.where(TicketEvent.id < before_id)
    return list(await db.scalars(query.order_by(TicketEvent.id.desc()).limit(limit)))


# Fields whose values name other tickets by key.
_TICKET_FIELDS = {"links", "parent", "clone"}
RESTRICTED = "restricted"


def _keys_in(value: Any) -> set[str]:
    if isinstance(value, str):
        return {value}
    if isinstance(value, dict):
        return {v for k, v in value.items() if k in ("ticket", "from") and isinstance(v, str)}
    return set()


def _mask(value: Any, hidden: set[str]) -> Any:
    if isinstance(value, str):
        return RESTRICTED if value in hidden else value
    if isinstance(value, dict):
        return {
            k: (RESTRICTED if k in ("ticket", "from") and v in hidden else v)
            for k, v in value.items()
        }
    return value


async def hide_restricted_keys(
    db: AsyncSession, user: User, events: list[TicketEvent]
) -> dict[int, tuple[Any, Any]]:
    """Old and new values with the keys of tickets the user may not see replaced by
    "restricted" (links, parent and clone events)."""
    from radicle.core.permissions import visible_tickets_clause

    keys: set[str] = set()
    for e in events:
        if e.field in _TICKET_FIELDS:
            keys |= _keys_in(e.old_value) | _keys_in(e.new_value)
    hidden: set[str] = set()
    if keys:
        visible = {
            f"{k}-{n}"
            for k, n in await db.execute(
                # Deleted tickets keep their key in history: only security hides it.
                select(Project.key, Ticket.number)
                .join(Ticket, Ticket.project_id == Project.id)
                .where(
                    func.concat(Project.key, "-", Ticket.number).in_(keys),
                    visible_tickets_clause(user),
                )
            )
        }
        hidden = keys - visible
    return {
        e.id: (_mask(e.old_value, hidden), _mask(e.new_value, hidden))
        if e.field in _TICKET_FIELDS
        else (e.old_value, e.new_value)
        for e in events
    }
