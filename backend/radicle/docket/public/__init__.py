"""Docket's public side: the server-rendered inbox pages (`router`) and the interface other
apps use (`interface`, re-exported here). Folio imports only this package."""

from radicle.docket.public.interface import (
    MAX_KEYS,
    MilestoneSummary,
    NewTicket,
    SearchResult,
    TicketSummary,
    create_ticket,
    get_area,
    get_milestone,
    get_project,
    get_tickets,
    get_tickets_by_id,
    list_milestones,
    parse_key,
    search,
)

__all__ = [
    "MAX_KEYS",
    "MilestoneSummary",
    "NewTicket",
    "SearchResult",
    "TicketSummary",
    "create_ticket",
    "get_area",
    "get_milestone",
    "get_project",
    "get_tickets",
    "get_tickets_by_id",
    "list_milestones",
    "parse_key",
    "search",
]
