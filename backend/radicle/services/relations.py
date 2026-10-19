"""Links between tickets and comment counts. Links arrive in 1.5; until then, empty."""

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from radicle.db.models import StatusCategory, Ticket, TicketType


@dataclass(frozen=True)
class LinkedTicket:
    key: str
    title: str
    type: TicketType
    status_name: str
    category: StatusCategory


@dataclass(frozen=True)
class LinkView:
    id: uuid.UUID
    type: str
    label: str
    other: LinkedTicket


async def links_for(db: AsyncSession, ticket: Ticket) -> list[LinkView]:
    del db, ticket
    return []


async def blocked_by(db: AsyncSession, ticket_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[str]]:
    del db, ticket_ids
    return {}


async def comments_count(db: AsyncSession, ticket_id: uuid.UUID) -> int:
    del db, ticket_id
    return 0
