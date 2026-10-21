"""Manual ranking within a project, and `next_ticket` for agents."""

import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.core.permissions import effective_role, permissions_for
from radicle.db.models import (
    EventType,
    Project,
    StatusCategory,
    Ticket,
    User,
    utcnow,
)
from radicle.platform.errors import Conflict, NotFound, ValidationFailed
from radicle.platform.services import queue
from radicle.query.compiler import Context, compile_query
from radicle.query.parser import parse
from radicle.services import history, rank, search, tickets, transitions
from radicle.services.access import ProjectAccess, project_access

REBALANCE_JOB = "rebalance_ranks"
REBALANCE_AT = 24  # rank length that triggers a rebalance of the project


def _key(access: ProjectAccess, ticket: Ticket) -> str:
    return f"{access.project.key}-{ticket.number}"


async def _neighbor(db: AsyncSession, project_id: uuid.UUID, of: str, *, below: bool) -> str | None:
    query = select(Ticket.rank).where(Ticket.project_id == project_id)
    if below:
        query = query.where(Ticket.rank > of).order_by(Ticket.rank.asc())
    else:
        query = query.where(Ticket.rank < of).order_by(Ticket.rank.desc())
    return await db.scalar(query.limit(1))


async def rank_ticket(
    db: AsyncSession,
    access: ProjectAccess,
    ticket: Ticket,
    *,
    before: str | None = None,
    after: str | None = None,
) -> Ticket:
    """Place the ticket right before or right after another one of the same project."""
    if bool(before) == bool(after):
        raise ValidationFailed(
            "Send exactly one of `before` or `after` (a ticket key).",
            errors=[{"field": "before", "message": "one of before or after"}],
        )
    other_key = str(before or after)
    _, other = await tickets.load_ticket(db, access.user, other_key)
    if other.project_id != ticket.project_id:
        raise ValidationFailed(
            f"{other_key.upper()} is in another project; rank works within one project.",
            errors=[{"field": "before" if before else "after", "message": "other project"}],
        )
    if other.id == ticket.id:
        raise ValidationFailed("A ticket cannot be ranked against itself.")
    low: str | None
    high: str | None
    if before:
        low, high = await _neighbor(db, ticket.project_id, other.rank, below=False), other.rank
    else:
        low, high = other.rank, await _neighbor(db, ticket.project_id, other.rank, below=True)
    # The ticket itself may be one of the neighbours: skip it.
    if low == ticket.rank:
        low = await _neighbor(db, ticket.project_id, ticket.rank, below=False)
    if high == ticket.rank:
        high = await _neighbor(db, ticket.project_id, ticket.rank, below=True)
    old = ticket.rank
    ticket.rank = rank.between(low, high)
    history.record(
        db,
        ticket,
        access.user,
        EventType.rank_changed,
        field="rank",
        old=old,
        new={"rank": ticket.rank, "before" if before else "after": other_key.upper()},
    )
    tickets.bump(ticket)
    await db.flush()
    if len(ticket.rank) >= REBALANCE_AT:
        await queue.enqueue(
            db,
            REBALANCE_JOB,
            queueing_lock=f"rebalance-{ticket.project_id}",
            project_id=str(ticket.project_id),
        )
    return ticket


@queue.handler(REBALANCE_JOB)
async def rebalance(db: AsyncSession, project_id: str) -> None:
    """Rewrite every rank of a project as short, evenly spread keys in the same order."""
    rows = await db.scalars(
        select(Ticket)
        .where(Ticket.project_id == uuid.UUID(project_id))
        .order_by(Ticket.rank, Ticket.id)
        .with_for_update(of=Ticket)
    )
    previous: str | None = None
    for ticket in rows:
        previous = rank.after(previous)
        ticket.rank = previous
    await db.flush()


# --- next ticket ---------------------------------------------------------------------------


def _quote(value: str) -> str:
    return json.dumps(value)


async def next_ticket(
    db: AsyncSession,
    user: User,
    *,
    project: str | None = None,
    area: str | None = None,
    ticket_type: str | None = None,
    claim: bool = False,
) -> tuple[ProjectAccess, Ticket] | None:
    """The top-ranked ticket that is to do, not blocked and unassigned (or yours). With
    `claim`, assign it to you and start it, atomically: two callers never get the same."""
    clauses = [
        "category = todo",
        "blocked = false",
        "(assignee IS EMPTY OR assignee = currentUser())",
    ]
    if project:
        clauses.append(f"project = {_quote(project)}")
    if area:
        clauses.append(f"area = {_quote(area)}")
    if ticket_type:
        clauses.append(f"type = {_quote(ticket_type)}")
    compiled = compile_query(parse(" AND ".join(clauses)), Context(user_id=user.id, now=utcnow()))
    query = search.base_query(user).where(compiled.where)
    if claim and not user.is_instance_admin:
        # Claiming assigns the ticket: only projects where the user may edit tickets.
        writable = []
        for p in await db.scalars(
            select(Project).where(Project.id.in_(search.visible_project_ids(user)))
        ):
            role = await effective_role(db, user, p)
            if "ticket.edit" in await permissions_for(db, p, role):
                writable.append(p.id)
        query = query.where(Ticket.project_id.in_(writable))
    query = query.order_by(Ticket.rank.asc(), Ticket.id).limit(1)
    if claim:
        query = query.with_for_update(of=Ticket, skip_locked=True)
    ticket = await db.scalar(query)
    if ticket is None:
        return None
    key = ticket.number
    project_row = await db.get(Project, ticket.project_id)
    if project_row is None:  # pragma: no cover - foreign key
        raise NotFound("Ticket vanished.")
    access = await project_access(
        db,
        user,
        project_row.key,
        write=claim,
        permission="ticket.edit" if claim else None,
    )
    if not claim:
        return access, ticket
    if ticket.assignee_id != user.id:
        await tickets.update_ticket(
            db,
            access,
            ticket,
            {"assignee": user.handle},
            expected_version=None,
            enforce_screen=False,
        )
    options = await transitions.transition_options(db, access, ticket)
    start = next(
        (
            v.option
            for v in options
            if v.available and v.option.to_status.category is StatusCategory.in_progress
        ),
        None,
    )
    if start is None:
        raise Conflict(
            f"{project_row.key}-{key} has no transition you can run into an in-progress status.",
            code="cannot_start",
        )
    await transitions.transition_ticket(
        db,
        access,
        ticket,
        to_status=start.to_status.name,
        transition=start.transition.name,
    )
    return access, ticket
