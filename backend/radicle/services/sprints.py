"""Scrum sprints: lifecycle, membership, commitments and the sprint report."""

import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement, and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.core.errors import Conflict, NotFound, ValidationFailed
from radicle.db.models import (
    Board,
    BoardKind,
    EventType,
    Project,
    ProjectRole,
    Sprint,
    SprintCommitment,
    SprintState,
    SprintTicket,
    Status,
    StatusCategory,
    Ticket,
    User,
    utcnow,
)
from radicle.services import history, search, tickets
from radicle.services.boards import BoardAccess, load_board

MAX_DAYS = 28
BACKLOG_TAG = "backlog"
BACKLOG_LIMIT = 500


def _fail(field_name: str, detail: str) -> ValidationFailed:
    return ValidationFailed(detail, errors=[{"field": field_name, "message": "invalid"}])


def _not_found(sprint_id: object) -> NotFound:
    return NotFound(f"Sprint {sprint_id} not found.", code="sprint_not_found")


def _state_error(sprint: Sprint, action: str) -> Conflict:
    return Conflict(
        f"Sprint '{sprint.name}' is {sprint.state.value}; you cannot {action}.",
        code="sprint_state",
        extra={"state": sprint.state.value},
    )


async def _key(db: AsyncSession, ticket: Ticket) -> str:
    project_key = await db.scalar(select(Project.key).where(Project.id == ticket.project_id))
    return f"{project_key}-{ticket.number}"


# --- access --------------------------------------------------------------------------------


async def load_sprint(
    db: AsyncSession,
    user: User,
    sprint_id: uuid.UUID,
    *,
    need: ProjectRole = ProjectRole.viewer,
    write: bool = False,
) -> tuple[BoardAccess, Sprint]:
    sprint = await db.get(Sprint, sprint_id)
    if sprint is None:
        raise _not_found(sprint_id)
    try:
        access = await load_board(db, user, sprint.board_id, need=need, write=write)
    except NotFound:
        raise _not_found(sprint_id) from None
    return access, sprint


def require_scrum(board: Board) -> None:
    if board.kind is not BoardKind.scrum:
        raise ValidationFailed(
            f"Board '{board.name}' is Kanban. Sprints live in Scrum boards: change its type "
            "in the board settings or create a Scrum board.",
            code="not_scrum",
        )


# --- reading -------------------------------------------------------------------------------


@dataclass
class SprintStats:
    tickets: int = 0
    done: int = 0
    estimate_hours: Decimal = Decimal(0)
    remaining_hours: Decimal = Decimal(0)
    unestimated: int = 0


_STATE_ORDER = {SprintState.active: 0, SprintState.future: 1, SprintState.closed: 2}


async def list_sprints(
    db: AsyncSession, board: Board, state: SprintState | None = None
) -> list[Sprint]:
    """Active first, then future by position, then closed (newest first)."""
    query = select(Sprint).where(Sprint.board_id == board.id)
    if state is not None:
        query = query.where(Sprint.state == state)
    rows = list(await db.scalars(query))
    return sorted(
        rows,
        key=lambda s: (
            _STATE_ORDER[s.state],
            s.position if s.state is not SprintState.closed else 0,
            -(s.completed_at.timestamp() if s.completed_at else 0),
        ),
    )


def _in_sprint(sprint_id: uuid.UUID) -> ColumnElement[bool]:
    return and_(SprintTicket.sprint_id == sprint_id, SprintTicket.removed_at.is_(None))


async def sprint_tickets(db: AsyncSession, user: User, sprint: Sprint) -> list[Ticket]:
    """Tickets in the sprint the user can see, by rank."""
    ids = select(SprintTicket.ticket_id).where(_in_sprint(sprint.id))
    query = search.base_query(user).where(Ticket.id.in_(ids)).order_by(Ticket.rank, Ticket.id)
    return list(await db.scalars(query))


async def stats(
    db: AsyncSession, user: User, sprints: list[Sprint]
) -> dict[uuid.UUID, SprintStats]:
    result = {s.id: SprintStats() for s in sprints}
    if not sprints:
        return result
    visible = search.base_query(user).with_only_columns(Ticket.id).subquery()
    rows = await db.execute(
        select(
            SprintTicket.sprint_id,
            Status.category,
            Ticket.estimate_hours,
            Ticket.remaining_hours,
        )
        .join(Ticket, Ticket.id == SprintTicket.ticket_id)
        .join(Status, Status.id == Ticket.status_id)
        .where(
            SprintTicket.sprint_id.in_([s.id for s in sprints]),
            SprintTicket.removed_at.is_(None),
            Ticket.id.in_(select(visible.c.id)),
        )
    )
    for sprint_id, category, estimate, remaining in rows:
        s = result[sprint_id]
        s.tickets += 1
        done = category is StatusCategory.done
        s.done += int(done)
        s.estimate_hours += estimate or 0
        s.remaining_hours += 0 if done else (remaining or 0)
        s.unestimated += int(estimate is None)
    return result


async def backlog(
    db: AsyncSession,
    user: User,
    ba: BoardAccess,
    *,
    extra: str | None = None,
    timezone: str = "UTC",
) -> tuple[list[Ticket], int]:
    """Tickets of the board's source in no open sprint and not done, by rank."""
    parts = [f"({ba.board.source_rql})"] if ba.board.source_rql.strip() else []
    if extra and extra.strip():
        parts.append(f"({extra})")
    compiled = await search.compile_rql(db, user, " AND ".join(parts), timezone=timezone)
    in_open = select(SprintTicket.ticket_id).where(
        SprintTicket.removed_at.is_(None), SprintTicket.sprint_closed.is_(False)
    )
    query = search.base_query(user).where(
        compiled.where,
        Status.category != StatusCategory.done,
        Ticket.id.not_in(in_open),
    )
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    rows = await db.scalars(query.order_by(Ticket.rank, Ticket.id).limit(BACKLOG_LIMIT))
    return list(rows), int(total or 0)


async def active_sprint(db: AsyncSession, board: Board) -> Sprint | None:
    result: Sprint | None = await db.scalar(
        select(Sprint).where(Sprint.board_id == board.id, Sprint.state == SprintState.active)
    )
    return result


# --- lifecycle -----------------------------------------------------------------------------


def _check_dates(start: date | None, end: date | None, *, required: bool) -> None:
    if required and (start is None or end is None):
        raise _fail("start_date", "A sprint needs a start and an end date to start.")
    if start is not None and end is not None:
        days = (end - start).days + 1
        if not 1 <= days <= MAX_DAYS:
            raise _fail(
                "end_date",
                f"A sprint lasts between 1 and {MAX_DAYS} days; this one is {days}. "
                "Move the end date.",
            )


def _check_capacity(value: Decimal | None) -> None:
    if value is not None and value < 0:
        raise _fail("capacity_hours", "Capacity is hours and cannot be negative.")


@dataclass
class SprintSpec:
    name: str | None = None
    goal: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    capacity_hours: Decimal | None = None


async def create_sprint(db: AsyncSession, ba: BoardAccess, spec: SprintSpec) -> Sprint:
    require_scrum(ba.board)
    _check_dates(spec.start_date, spec.end_date, required=False)
    _check_capacity(spec.capacity_hours)
    count = await db.scalar(select(func.count()).where(Sprint.board_id == ba.board.id))
    position = await db.scalar(
        select(func.coalesce(func.max(Sprint.position), -1)).where(Sprint.board_id == ba.board.id)
    )
    name = (spec.name or "").strip() or f"Sprint {int(count or 0) + 1}"
    sprint = Sprint(
        board_id=ba.board.id,
        name=name,
        goal=spec.goal,
        state=SprintState.future,
        start_date=spec.start_date,
        end_date=spec.end_date,
        capacity_hours=spec.capacity_hours,
        position=int(position if position is not None else -1) + 1,
    )
    db.add(sprint)
    await db.flush()
    return sprint


EDITABLE = {
    SprintState.future: {"name", "goal", "start_date", "end_date", "capacity_hours", "position"},
    SprintState.active: {"goal", "end_date", "capacity_hours", "goal_met"},
    SprintState.closed: {"goal_met"},
}


async def update_sprint(db: AsyncSession, sprint: Sprint, changes: dict[str, Any]) -> Sprint:
    allowed = EDITABLE[sprint.state]
    blocked = sorted(set(changes) - allowed)
    if blocked:
        raise _state_error(sprint, f"change {', '.join(blocked)}")
    if "name" in changes:
        name = (changes["name"] or "").strip()
        if not name:
            raise _fail("name", "The sprint needs a name.")
        sprint.name = name
    if "goal" in changes:
        sprint.goal = changes["goal"]
    start = changes.get("start_date", sprint.start_date)
    end = changes.get("end_date", sprint.end_date)
    _check_dates(start, end, required=sprint.state is SprintState.active)
    sprint.start_date, sprint.end_date = start, end
    if "capacity_hours" in changes:
        _check_capacity(changes["capacity_hours"])
        sprint.capacity_hours = changes["capacity_hours"]
    if "position" in changes and changes["position"] is not None:
        sprint.position = int(changes["position"])
    if "goal_met" in changes:
        sprint.goal_met = changes["goal_met"]
        if sprint.report is not None:
            sprint.report = {**sprint.report, "goal_met": changes["goal_met"]}
    await db.flush()
    return sprint


async def delete_sprint(db: AsyncSession, user: User, sprint: Sprint) -> None:
    if sprint.state is not SprintState.future:
        raise _state_error(sprint, "delete it (only future sprints can be deleted)")
    for ticket in await _tickets_of(db, sprint):
        history.record(db, ticket, user, EventType.sprint_removed, field="sprint", old=sprint.name)
    await db.delete(sprint)
    await db.flush()


async def _tickets_of(db: AsyncSession, sprint: Sprint) -> list[Ticket]:
    ids = select(SprintTicket.ticket_id).where(_in_sprint(sprint.id))
    return list(await db.scalars(select(Ticket).where(Ticket.id.in_(ids))))


async def start_sprint(db: AsyncSession, sprint: Sprint, spec: SprintSpec) -> Sprint:
    if sprint.state is not SprintState.future:
        raise _state_error(sprint, "start it again")
    current = await db.scalar(
        select(Sprint).where(Sprint.board_id == sprint.board_id, Sprint.state == SprintState.active)
    )
    if current is not None:
        raise Conflict(
            f"'{current.name}' is still active on this board. Close it before starting "
            f"'{sprint.name}'.",
            code="sprint_already_active",
        )
    if spec.name is not None and spec.name.strip():
        sprint.name = spec.name.strip()
    if spec.goal is not None:
        sprint.goal = spec.goal
    sprint.start_date = spec.start_date or sprint.start_date
    sprint.end_date = spec.end_date or sprint.end_date
    _check_dates(sprint.start_date, sprint.end_date, required=True)
    if spec.capacity_hours is not None:
        _check_capacity(spec.capacity_hours)
        sprint.capacity_hours = spec.capacity_hours
    sprint.state = SprintState.active
    sprint.started_at = utcnow()
    for ticket in await _tickets_of(db, sprint):
        db.add(
            SprintCommitment(
                sprint_id=sprint.id,
                ticket_id=ticket.id,
                estimate_hours=ticket.estimate_hours,
                remaining_hours=ticket.remaining_hours,
            )
        )
    await db.flush()
    return sprint


@dataclass
class Completion:
    sprint: Sprint
    moved_to: Sprint | None
    unfinished: list[str] = field(default_factory=list)


async def complete_sprint(
    db: AsyncSession,
    user: User,
    sprint: Sprint,
    *,
    move_unfinished_to: str = "backlog",
    tag_backlog: bool = True,
) -> Completion:
    """Close the sprint. Unfinished tickets go to a future sprint or back to the backlog."""
    if sprint.state is not SprintState.active:
        raise _state_error(sprint, "close it (only the active sprint can be closed)")
    target: Sprint | None = None
    if move_unfinished_to != "backlog":
        try:
            target_id = uuid.UUID(move_unfinished_to)
        except ValueError:
            raise _fail(
                "move_unfinished_to", "Use a future sprint id of this board or 'backlog'."
            ) from None
        target = await db.get(Sprint, target_id)
        if (
            target is None
            or target.board_id != sprint.board_id
            or target.state is not SprintState.future
        ):
            raise _fail(
                "move_unfinished_to",
                "Unfinished tickets can only go to a future sprint of this board, or to 'backlog'.",
            )
    sprint.report = await build_report(db, sprint)
    now = utcnow()
    unfinished: list[str] = []
    for ticket in await _tickets_of(db, sprint):
        status = await db.get(Status, ticket.status_id)
        if status is not None and status.category is StatusCategory.done:
            continue
        unfinished.append(await _key(db, ticket))
        await db.execute(
            update(SprintTicket)
            .where(_in_sprint(sprint.id), SprintTicket.ticket_id == ticket.id)
            .values(removed_at=now)
        )
        history.record(db, ticket, user, EventType.sprint_removed, field="sprint", old=sprint.name)
        if target is not None:
            db.add(SprintTicket(sprint_id=target.id, ticket_id=ticket.id, added_at=now))
            history.record(
                db, ticket, user, EventType.sprint_added, field="sprint", new=target.name
            )
        elif tag_backlog and BACKLOG_TAG not in ticket.tags:
            await _set_tags(db, user, ticket, [*ticket.tags, BACKLOG_TAG])
    await db.execute(
        update(SprintTicket).where(SprintTicket.sprint_id == sprint.id).values(sprint_closed=True)
    )
    sprint.state = SprintState.closed
    sprint.completed_at = now
    await db.flush()
    return Completion(sprint, target, unfinished)


# --- membership ----------------------------------------------------------------------------


async def _set_tags(db: AsyncSession, user: User, ticket: Ticket, tags: list[str]) -> None:
    access, _ = await tickets.load_ticket(
        db, user, await _key(db, ticket), need=ProjectRole.member, write=True
    )
    await tickets.update_ticket(
        db, access, ticket, {"tags": tags}, expected_version=None, enforce_screen=False
    )


async def add_tickets(db: AsyncSession, user: User, sprint: Sprint, keys: list[str]) -> list[str]:
    """Put tickets in the sprint (taking them out of any other open one). Returns the keys
    that were added; adding to the active sprint counts as a scope change."""
    if sprint.state is SprintState.closed:
        raise _state_error(sprint, "add tickets")
    added: list[str] = []
    now = utcnow()
    for key in keys:
        _, ticket = await tickets.load_ticket(db, user, key, need=ProjectRole.member, write=True)
        current = await db.scalar(
            select(SprintTicket).where(
                SprintTicket.ticket_id == ticket.id,
                SprintTicket.removed_at.is_(None),
                SprintTicket.sprint_closed.is_(False),
            )
        )
        if current is not None and current.sprint_id == sprint.id:
            continue
        if current is not None:
            previous = await db.get(Sprint, current.sprint_id)
            current.removed_at = now
            history.record(
                db,
                ticket,
                user,
                EventType.sprint_removed,
                field="sprint",
                old=previous.name if previous else None,
            )
            await db.flush()
        db.add(
            SprintTicket(
                sprint_id=sprint.id,
                ticket_id=ticket.id,
                added_at=now,
                added_after_start=sprint.state is SprintState.active,
            )
        )
        history.record(db, ticket, user, EventType.sprint_added, field="sprint", new=sprint.name)
        if BACKLOG_TAG in ticket.tags:
            await _set_tags(db, user, ticket, [t for t in ticket.tags if t != BACKLOG_TAG])
        added.append(await _key(db, ticket))
    await db.flush()
    return added


async def remove_tickets(
    db: AsyncSession, user: User, sprint: Sprint, keys: list[str]
) -> list[str]:
    if sprint.state is SprintState.closed:
        raise _state_error(sprint, "remove tickets")
    removed: list[str] = []
    for key in keys:
        _, ticket = await tickets.load_ticket(db, user, key, need=ProjectRole.member, write=True)
        row = await db.scalar(
            select(SprintTicket).where(_in_sprint(sprint.id), SprintTicket.ticket_id == ticket.id)
        )
        if row is None:
            raise _fail("keys", f"{key} is not in '{sprint.name}'.")
        row.removed_at = utcnow()
        history.record(db, ticket, user, EventType.sprint_removed, field="sprint", old=sprint.name)
        removed.append(await _key(db, ticket))
    await db.flush()
    return removed


# --- report --------------------------------------------------------------------------------


def _hours(value: Decimal | None) -> float:
    return float(value or 0)


async def build_report(db: AsyncSession, sprint: Sprint) -> dict[str, Any]:
    """Completed, not completed, added after start and removed, with hours. Built from the
    sprint's rows, so it covers every ticket whatever the viewer can see; the API filters."""
    committed = {
        c.ticket_id: c
        for c in await db.scalars(
            select(SprintCommitment).where(SprintCommitment.sprint_id == sprint.id)
        )
    }
    rows = list(await db.scalars(select(SprintTicket).where(SprintTicket.sprint_id == sprint.id)))
    ids = {r.ticket_id for r in rows} | set(committed)
    by_ticket: dict[uuid.UUID, Ticket] = {}
    keys: dict[uuid.UUID, str] = {}
    categories: dict[uuid.UUID, StatusCategory] = {}
    found = await db.execute(
        select(Ticket, Project.key, Status.category)
        .join(Project, Project.id == Ticket.project_id)
        .join(Status, Status.id == Ticket.status_id)
        .where(Ticket.id.in_(ids))
    )
    for ticket, project_key, category in found:
        by_ticket[ticket.id] = ticket
        keys[ticket.id] = f"{project_key}-{ticket.number}"
        categories[ticket.id] = category

    def item(ticket_id: uuid.UUID) -> dict[str, Any]:
        t = by_ticket[ticket_id]
        c = committed.get(ticket_id)
        return {
            "key": keys[ticket_id],
            "title": t.title,
            "estimate_hours": _hours(t.estimate_hours),
            "committed_hours": _hours(c.estimate_hours) if c else 0.0,
            "remaining_hours": _hours(t.remaining_hours),
        }

    open_rows = [r for r in rows if r.removed_at is None]
    completed = [r.ticket_id for r in open_rows if categories[r.ticket_id] is StatusCategory.done]
    not_completed = [r.ticket_id for r in open_rows if r.ticket_id not in set(completed)]
    added = sorted({r.ticket_id for r in rows if r.added_after_start}, key=str)
    removed = sorted(
        {r.ticket_id for r in rows if r.removed_at is not None} - {r.ticket_id for r in open_rows},
        key=str,
    )
    report = {
        "sprint": sprint.name,
        "goal": sprint.goal,
        "goal_met": sprint.goal_met,
        "start_date": sprint.start_date.isoformat() if sprint.start_date else None,
        "end_date": sprint.end_date.isoformat() if sprint.end_date else None,
        "committed_hours": sum(_hours(c.estimate_hours) for c in committed.values()),
        "completed_hours": sum(_hours(by_ticket[i].estimate_hours) for i in completed),
        "completed": [item(i) for i in completed],
        "not_completed": [item(i) for i in not_completed],
        "added_after_start": [item(i) for i in added],
        "removed": [item(i) for i in removed],
    }
    return report


async def report(db: AsyncSession, sprint: Sprint) -> dict[str, Any]:
    if sprint.state is SprintState.closed and sprint.report is not None:
        return sprint.report
    return await build_report(db, sprint)
