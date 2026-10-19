"""Append-only ticket history. Every ticket mutation goes through `record`."""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.db.models import EventType, Ticket, TicketEvent, User, utcnow


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
