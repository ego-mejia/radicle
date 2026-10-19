"""Ticket search with RQL, always limited to what the user may see."""

import base64
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.core import permissions
from radicle.core.errors import ValidationFailed
from radicle.db.models import (
    Area,
    Board,
    Milestone,
    Project,
    Sprint,
    Status,
    Ticket,
    User,
    utcnow,
)
from radicle.query.compiler import Compiled, Context, compile_query
from radicle.query.parser import parse
from radicle.services import custom_fields

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


@dataclass(frozen=True)
class SearchWarning:
    code: str
    message: str
    position: int


@dataclass
class SearchResult:
    tickets: list[Ticket]
    total: int
    next_cursor: str | None
    warnings: list[SearchWarning] = field(default_factory=list)


def visible_project_ids(user: User) -> Any:
    return permissions.visible_project_ids(user)


def base_query(user: User, *, include_restricted: bool = False) -> Select[Any]:
    """Tickets the user can see, never soft-deleted ones.

    `include_restricted` keeps tickets of the user's projects that a security level hides
    from them; only aggregate numbers use it (counts in reports), never lists."""
    visible = (
        Ticket.project_id.in_(visible_project_ids(user))
        if include_restricted
        else permissions.visible_tickets_clause(user)
    )
    return (
        select(Ticket)
        .join(Project, Project.id == Ticket.project_id)
        .join(Status, Status.id == Ticket.status_id)
        .where(Ticket.deleted_at.is_(None), visible)
    )


def _encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(json.dumps({"o": offset}).encode()).decode().rstrip("=")


def _decode_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        offset = json.loads(base64.urlsafe_b64decode(padded))["o"]
    except (ValueError, KeyError, TypeError) as exc:
        raise ValidationFailed(
            "Invalid cursor. Use next_cursor from the previous page with the same query."
        ) from exc
    if not isinstance(offset, int) or offset < 0:
        raise ValidationFailed("Invalid cursor.")
    return offset


async def compile_rql(
    db: AsyncSession, user: User, q: str, *, timezone: str = "UTC", now: datetime | None = None
) -> Compiled:
    """Parse and compile RQL for this user: their custom fields and saved filters."""
    query = parse(q)
    from radicle.services import filters

    saved = await filters.expand(db, user, query)
    types = await custom_fields.rql_types(db, visible_project_ids(user))
    ctx = Context(
        user_id=user.id,
        now=now or utcnow(),
        tz=ZoneInfo(timezone),
        custom_fields={k: t.value for k, t in types.items()},
        filters=saved,
    )
    return compile_query(query, ctx)


async def search(
    db: AsyncSession,
    user: User,
    q: str,
    *,
    limit: int = DEFAULT_LIMIT,
    cursor: str | None = None,
    timezone: str = "UTC",
    now: datetime | None = None,
) -> SearchResult:
    compiled = await compile_rql(db, user, q, timezone=timezone, now=now)
    offset = _decode_cursor(cursor)
    limit = max(1, min(limit, MAX_LIMIT))

    filtered = base_query(user).where(compiled.where)
    total = await db.scalar(select(func.count()).select_from(filtered.subquery()))
    rows: list[Ticket] = list(
        await db.scalars(filtered.order_by(*compiled.order_by).offset(offset).limit(limit + 1))
    )
    tickets = rows[:limit]
    next_cursor = _encode_cursor(offset + limit) if len(rows) > limit else None
    warnings = await _missing_names(db, user, compiled.references)
    return SearchResult(tickets, int(total or 0), next_cursor, warnings)


async def _missing_names(
    db: AsyncSession, user: User, references: list[tuple[str, str, int]]
) -> list[SearchWarning]:
    """Names that match nothing are not errors, but deserve a warning."""
    warnings: list[SearchWarning] = []
    visible = visible_project_ids(user)
    for kind, value, position in references:
        if kind == "filter":
            warnings.append(
                SearchWarning(
                    "unknown_name",
                    f"Filter '{value}' does not exist; it matches nothing.",
                    position,
                )
            )
            continue
        if kind == "handle":
            exists = await db.scalar(select(User.id).where(User.handle == value))
            label = f"User @{value}"
        elif kind == "sprint":
            exists = await db.scalar(
                select(Sprint.id)
                .join(Board, Board.id == Sprint.board_id)
                .where(
                    func.lower(Sprint.name) == value.lower(),
                    or_(Board.project_id.is_(None), Board.project_id.in_(visible)),
                )
                .limit(1)
            )
            label = f"Sprint '{value}'"
        elif kind == "project":
            exists = await db.scalar(
                select(Project.id).where(Project.key == value, Project.id.in_(visible))
            )
            label = f"Project {value.upper()}"
        else:
            model: type[Area] | type[Milestone] | type[Status] = (
                Area if kind == "area" else Milestone if kind == "milestone" else Status
            )
            exists = await db.scalar(
                select(model.id)
                .where(func.lower(model.name) == value.lower(), model.project_id.in_(visible))
                .limit(1)
            )
            label = f"{kind.capitalize()} '{value}'"
        if not exists:
            warnings.append(
                SearchWarning(
                    "unknown_name", f"{label} does not exist; it matches nothing.", position
                )
            )
    return warnings
