"""The inbox: a project's Drafts with their origin and score, triage and conversion."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import case, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.docket.db.models import (
    Classification,
    EventType,
    LinkType,
    Origin,
    Priority,
    Project,
    Resolution,
    Status,
    StatusCategory,
    Ticket,
    TicketType,
    TicketVote,
    User,
    utcnow,
)
from radicle.docket.services import history, relations, search, tickets, transitions
from radicle.docket.services.access import ProjectAccess
from radicle.docket.services.workflows import load_workflows
from radicle.platform.errors import ValidationFailed

Tab = Literal["new", "in_review", "approved", "discarded"]
TABS: tuple[Tab, ...] = ("new", "in_review", "approved", "discarded")
Sort = Literal["votes", "age", "score"]


def _tab_where(tab: Tab) -> Any:
    draft = Ticket.type == TicketType.draft
    if tab == "new":
        return draft & (Status.category == StatusCategory.todo)
    if tab == "in_review":
        return draft & (Status.category == StatusCategory.in_progress)
    if tab == "approved":
        return Ticket.converted_at.is_not(None)
    return draft & (Status.category == StatusCategory.done) & Ticket.converted_at.is_(None)


def score_expr() -> Any:
    """impact * 2 - effort; unscored items last."""
    return case(
        (Ticket.impact.is_(None) | Ticket.effort.is_(None), None),
        else_=Ticket.impact * 2 - Ticket.effort,
    )


@dataclass
class InboxView:
    tickets: list[Ticket]
    counts: dict[str, int] = field(default_factory=dict)


async def inbox(
    db: AsyncSession,
    user: User,
    project: Project,
    *,
    tab: Tab = "new",
    classification: Classification | None = None,
    origin: Origin | None = None,
    sort: Sort = "votes",
    limit: int = 200,
) -> InboxView:
    base = search.base_query(user).where(Ticket.project_id == project.id)
    counts: dict[str, int] = {}
    for t in TABS:
        n = await db.scalar(select(func.count()).select_from(base.where(_tab_where(t)).subquery()))
        counts[t] = int(n or 0)
    query = base.where(_tab_where(tab))
    if classification is not None:
        query = query.where(Ticket.classification == classification)
    if origin is not None:
        query = query.where(Ticket.origin == origin)
    orders: dict[str, list[Any]] = {
        "votes": [Ticket.vote_count.desc(), Ticket.created_at.asc()],
        "age": [Ticket.created_at.asc()],
        "score": [score_expr().desc().nulls_last(), Ticket.vote_count.desc()],
    }
    order = orders[sort]
    rows = await db.scalars(query.order_by(*order, Ticket.id).limit(limit))
    return InboxView(list(rows), counts)


def _require_draft(ticket: Ticket, key: str) -> None:
    if ticket.type is not TicketType.draft:
        raise ValidationFailed(
            f"{key} is a {ticket.type.value}, not an inbox draft.",
            errors=[{"field": "key", "message": "not a draft"}],
        )


async def _status(db: AsyncSession, ticket: Ticket) -> Status:
    status = await db.get(Status, ticket.status_id)
    assert status is not None  # noqa: S101 - FK
    return status


async def approve(
    db: AsyncSession,
    access: ProjectAccess,
    ticket: Ticket,
    key: str,
    *,
    to_type: TicketType,
    area: str,
    milestone: str | None = None,
    priority: Priority | None = None,
    assignee: str | None = None,
) -> None:
    """Approve and convert in one go: the Approve transition (resolution done) for the
    record, then the type change, then the fields. Origin, classification, votes,
    comments, files and history stay. Any failure undoes everything."""
    access.require("inbox.triage")
    _require_draft(ticket, key)
    if to_type is TicketType.draft:
        raise ValidationFailed(
            "Convert to task or bug.", errors=[{"field": "type", "message": "invalid"}]
        )
    if not area:
        raise ValidationFailed(
            "Pick the area the work belongs to.", errors=[{"field": "area", "message": "required"}]
        )
    async with db.begin_nested():
        workflow = (await load_workflows(db, ticket.project_id))[TicketType.draft]
        status = await _status(db, ticket)
        if status.category is StatusCategory.todo:
            review = next(
                (
                    t
                    for t in workflow.transitions
                    if t.from_status_id in (None, status.id)
                    and workflow.status_by_id(t.to_status_id).category is StatusCategory.in_progress
                ),
                None,
            )
            if review is not None:
                await transitions.transition_ticket(
                    db,
                    access,
                    ticket,
                    to_status=workflow.status_by_id(review.to_status_id).name,
                    transition=review.name,
                )
                status = await _status(db, ticket)
        approve_t = next(
            (
                t
                for t in workflow.transitions
                if t.from_status_id in (None, status.id)
                and workflow.status_by_id(t.to_status_id).category is StatusCategory.done
                and Resolution.done in (t.allowed_resolutions or [Resolution.done])
            ),
            None,
        )
        if approve_t is None:
            raise ValidationFailed(
                f"{key} has no transition to approve it from '{status.name}'.",
                code="no_approve_transition",
            )
        await transitions.transition_ticket(
            db,
            access,
            ticket,
            to_status=workflow.status_by_id(approve_t.to_status_id).name,
            transition=approve_t.name,
            resolution=Resolution.done,
        )
        await transitions.change_type(db, access, ticket, to_type, area)
        changes: dict[str, Any] = {}
        if milestone:
            changes["milestone"] = milestone
        if priority:
            changes["priority"] = priority.value
        if assignee:
            changes["assignee"] = assignee
        if changes:
            await tickets.update_ticket(
                db, access, ticket, changes, expected_version=None, enforce_screen=False
            )
        ticket.converted_at = utcnow()
        history.record(
            db,
            ticket,
            access.user,
            EventType.converted,
            field="type",
            old=TicketType.draft.value,
            new=to_type.value,
        )
        tickets.bump(ticket)
        await db.flush()


async def _discard_transition(db: AsyncSession, ticket: Ticket, resolution: Resolution) -> str:
    workflow = (await load_workflows(db, ticket.project_id))[ticket.type]
    status = await _status(db, ticket)
    for t in workflow.transitions:
        target = workflow.status_by_id(t.to_status_id)
        if (
            t.from_status_id in (None, status.id)
            and target.category is StatusCategory.done
            and resolution in (t.allowed_resolutions or [])
        ):
            return t.name
    raise ValidationFailed(
        f"There is no transition from '{status.name}' that closes as {resolution.value}.",
        code="no_discard_transition",
    )


async def discard(
    db: AsyncSession,
    access: ProjectAccess,
    ticket: Ticket,
    key: str,
    *,
    public_comment: str | None = None,
) -> None:
    """Close as won't do; the optional comment is shown on the submitter's tracking page."""
    access.require("inbox.triage")
    _require_draft(ticket, key)
    name = await _discard_transition(db, ticket, Resolution.wont_do)
    workflow = (await load_workflows(db, ticket.project_id))[ticket.type]
    target = next(t for t in workflow.transitions if t.name == name)
    await transitions.transition_ticket(
        db,
        access,
        ticket,
        to_status=workflow.status_by_id(target.to_status_id).name,
        transition=name,
        resolution=Resolution.wont_do,
    )
    note = (public_comment or "").strip()
    if len(note) > 2000:
        raise ValidationFailed(
            "The public comment is up to 2,000 characters.",
            errors=[{"field": "public_comment", "message": "too long"}],
        )
    if note:
        ticket.public_comment = note
        history.record(
            db, ticket, access.user, EventType.field_changed, field="public_comment", new=note
        )
    await db.flush()


async def mark_duplicate(
    db: AsyncSession, access: ProjectAccess, ticket: Ticket, key: str, original_key: str
) -> Ticket:
    """Link to the original, close as duplicate and pass the voters on (no repeats)."""
    access.require("inbox.triage")
    _require_draft(ticket, key)
    _, original = await tickets.load_ticket(db, access.user, original_key, write=True)
    if original.id == ticket.id:
        raise ValidationFailed(
            "A ticket cannot duplicate itself.", errors=[{"field": "original", "message": "same"}]
        )
    await relations.add_link(db, access, ticket, LinkType.duplicates, original_key)
    name = await _discard_transition(db, ticket, Resolution.duplicate)
    workflow = (await load_workflows(db, ticket.project_id))[ticket.type]
    target = next(t for t in workflow.transitions if t.name == name)
    await transitions.transition_ticket(
        db,
        access,
        ticket,
        to_status=workflow.status_by_id(target.to_status_id).name,
        transition=name,
        resolution=Resolution.duplicate,
    )
    voters = list(
        await db.scalars(select(TicketVote.user_id).where(TicketVote.ticket_id == ticket.id))
    )
    if voters:
        await db.execute(
            pg_insert(TicketVote)
            .values(
                [{"ticket_id": original.id, "user_id": v, "created_at": utcnow()} for v in voters]
            )
            .on_conflict_do_nothing()
        )
        count = await db.scalar(select(func.count()).where(TicketVote.ticket_id == original.id))
        if int(count or 0) != original.vote_count:
            history.record(
                db,
                original,
                access.user,
                EventType.field_changed,
                field="votes",
                old=original.vote_count,
                new=int(count or 0),
            )
            original.vote_count = int(count or 0)
            tickets.bump(original)
    await db.flush()
    return original


def age_days(ticket: Ticket, now: datetime) -> int:
    return (now - ticket.created_at).days
