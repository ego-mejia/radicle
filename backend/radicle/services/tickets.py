"""Ticket lifecycle: create, read, edit, soft delete, collaborators and checklist."""

import uuid
from dataclasses import asdict, dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.core.errors import Conflict, NotFound, ValidationFailed
from radicle.db.models import (
    Area,
    EventType,
    Mention,
    Milestone,
    Priority,
    Project,
    ProjectRole,
    RemainingMode,
    Ticket,
    TicketCollaborator,
    TicketKeyAlias,
    TicketType,
    User,
    utcnow,
)
from radicle.services import custom_fields, history, markdown, periods, rank, screens
from radicle.services import ticket_fields as fields
from radicle.services.access import ProjectAccess, project_access
from radicle.services.remaining import estimate_changed
from radicle.services.workflows import load_workflows

UPDATABLE = (
    "title",
    "description_md",
    "priority",
    "area",
    "milestone",
    "parent",
    "assignee",
    "due_date",
    "start_date",
    "estimate_hours",
    "tags",
    "custom_fields",
    "remaining_hours",
    "remaining_mode",
)


class VersionConflict(Conflict):
    code = "version_conflict"

    def __init__(self, key: str, ticket: Ticket, expected: int) -> None:
        super().__init__(
            f"Someone else changed {key} (now version {ticket.version}, you "
            f"sent {expected}). Reload it, reapply your change and send the new version.",
            extra={"current_version": ticket.version},
        )
        self.ticket = ticket


@dataclass
class NewTicket:
    type: TicketType
    title: str
    description_md: str = ""
    area: str | None = None
    milestone: str | None = None
    priority: Priority = Priority.medium
    assignee: str | None = None
    collaborators: list[str] = field(default_factory=list)
    parent: str | None = None
    due_date: date | None = None
    start_date: date | None = None
    estimate_hours: float | Decimal | None = None
    tags: list[str] = field(default_factory=list)
    custom_fields: dict[str, Any] = field(default_factory=dict)


def bump(ticket: Ticket) -> None:
    ticket.version += 1
    ticket.updated_at = utcnow()


# --- loading -----------------------------------------------------------------------------


async def load_ticket(
    db: AsyncSession,
    user: User,
    key: str,
    *,
    need: ProjectRole = ProjectRole.viewer,
    write: bool = False,
    include_deleted: bool = False,
) -> tuple[ProjectAccess, Ticket]:
    """Find a ticket by key and check the caller's role in its project.

    Writes lock the row so concurrent edits serialise and the version check holds.
    """
    project_key, number = fields.parse_key(key)
    current = await resolve_alias(db, project_key, number)
    if current is not None:
        project_key, number = current
    try:
        access = await project_access(db, user, project_key, need=need, write=write)
    except NotFound as exc:
        raise _ticket_not_found(key) from exc
    query = select(Ticket).where(Ticket.project_id == access.project.id, Ticket.number == number)
    if write:
        query = query.with_for_update(of=Ticket)
    ticket = await db.scalar(query)
    if ticket is None or (ticket.deleted_at is not None and not include_deleted):
        raise _ticket_not_found(key)
    return access, ticket


async def resolve_alias(db: AsyncSession, project_key: str, number: int) -> tuple[str, int] | None:
    """Where a moved ticket lives now, if `project_key-number` is an old key of it."""
    exists = await db.scalar(
        select(Ticket.id)
        .join(Project, Project.id == Ticket.project_id)
        .where(Project.key == project_key, Ticket.number == number)
    )
    if exists is not None:
        return None
    row = (
        await db.execute(
            select(Project.key, Ticket.number)
            .join(Ticket, Ticket.project_id == Project.id)
            .join(TicketKeyAlias, TicketKeyAlias.ticket_id == Ticket.id)
            .where(TicketKeyAlias.old_key == f"{project_key}-{number}")
        )
    ).first()
    return (row[0], row[1]) if row else None


def _ticket_not_found(key: str) -> NotFound:
    return NotFound(f"Ticket {key.strip().upper()} not found.", code="ticket_not_found")


# --- create ------------------------------------------------------------------------------


async def create_ticket(db: AsyncSession, access: ProjectAccess, data: NewTicket) -> Ticket:
    project = access.project
    title = fields.normalize_title(data.title)
    description = fields.check_description(data.description_md)
    area = await fields.resolve_area(db, project, data.area) if data.area else None
    if not await screens.check_create(db, project, data.type, asdict(data)):
        fields.require_area(data.type, area)
    milestone = (
        await fields.resolve_milestone(db, project, data.milestone) if data.milestone else None
    )
    parent = await fields.resolve_parent(db, project, data.parent) if data.parent else None
    assignee = (
        await fields.resolve_assignable(db, project, data.assignee, field="assignee")
        if data.assignee
        else None
    )
    collaborators = [
        await fields.resolve_assignable(db, project, h, field="collaborators")
        for h in dict.fromkeys(h.strip().lstrip("@").lower() for h in data.collaborators)
    ]
    tags = fields.normalize_tags(data.tags)
    estimate = fields.normalize_estimate(data.estimate_hours)
    custom_values, custom_diffs = await custom_fields.apply_values(
        db, project, data.type, area.id if area else None, {}, data.custom_fields or {}
    )
    workflows = await load_workflows(db, project.id)

    # Locks the project row: numbers are gapless and the rank read below sees prior inserts.
    number = await db.scalar(
        update(Project)
        .where(Project.id == project.id)
        .values(ticket_seq=Project.ticket_seq + 1)
        .returning(Project.ticket_seq)
    )
    last_rank = await db.scalar(
        select(func.max(Ticket.rank)).where(Ticket.project_id == project.id)
    )
    ticket = Ticket(
        id=uuid.uuid4(),
        project_id=project.id,
        number=number,
        type=data.type,
        title=title,
        description_md=description,
        status_id=workflows[data.type].initial.id,
        priority=data.priority,
        area_id=area.id if area else None,
        milestone_id=milestone.id if milestone else None,
        parent_id=parent.id if parent else None,
        assignee_id=assignee.id if assignee else None,
        reporter_id=access.user.id,
        due_date=data.due_date,
        start_date=data.start_date,
        estimate_hours=estimate,
        tags=tags,
        custom_fields=custom_values,
        rank=rank.after(last_rank),
        time_spent_minutes=0,
        remaining_mode=RemainingMode.auto,
    )
    estimate_changed(ticket)
    db.add(ticket)
    await db.flush()
    for user in collaborators:
        db.add(TicketCollaborator(ticket_id=ticket.id, user_id=user.id))
    created_event = history.record(
        db,
        ticket,
        access.user,
        EventType.created,
        new={"type": data.type.value, "title": title, "status": workflows[data.type].initial.name},
    )
    for key, _, new in custom_diffs:
        history.record(
            db, ticket, access.user, EventType.custom_field_changed, field=f"cf.{key}", new=new
        )
    await periods.track(db, ticket, created_event)
    await sync_mentions(db, ticket.id, None, description)
    await db.flush()
    await db.refresh(ticket)
    return ticket


# --- update ------------------------------------------------------------------------------


async def update_ticket(
    db: AsyncSession,
    access: ProjectAccess,
    ticket: Ticket,
    changes: dict[str, Any],
    *,
    expected_version: int | None,
    enforce_screen: bool = True,
) -> Ticket:
    """Apply only the fields present in `changes`; None clears a field.

    One `field_changed` event per field that actually changed. The edit screen limits
    which fields people can change; post-functions skip it (`enforce_screen=False`).
    """
    unknown = set(changes) - set(UPDATABLE)
    if unknown:
        raise ValidationFailed(f"Fields cannot be edited here: {', '.join(sorted(unknown))}.")
    if expected_version is not None and expected_version != ticket.version:
        raise VersionConflict(f"{access.project.key}-{ticket.number}", ticket, expected_version)
    project = access.project
    if enforce_screen:
        await screens.check_edit(db, project, access.role, ticket, changes)
    diffs: list[tuple[str, Any, Any]] = []

    if "title" in changes:
        _require_value(changes, "title")
        new_title = fields.normalize_title(changes["title"])
        if new_title != ticket.title:
            diffs.append(("title", ticket.title, new_title))
            ticket.title = new_title
    if "description_md" in changes:
        new_description = fields.check_description(changes["description_md"] or "")
        if new_description != ticket.description_md:
            diffs.append(("description_md", ticket.description_md, new_description))
            ticket.description_md = new_description
            await sync_mentions(db, ticket.id, None, new_description)
    if "priority" in changes:
        _require_value(changes, "priority")
        new_priority = Priority(changes["priority"])
        if new_priority is not ticket.priority:
            diffs.append(("priority", ticket.priority.value, new_priority.value))
            ticket.priority = new_priority
    if "area" in changes:
        old_area = await _area_name(db, ticket.area_id)
        area = await fields.resolve_area(db, project, changes["area"]) if changes["area"] else None
        fields.require_area(ticket.type, area)
        if (area.id if area else None) != ticket.area_id:
            diffs.append(("area", old_area, area.name if area else None))
            ticket.area_id = area.id if area else None
    if "milestone" in changes:
        old_milestone = await _milestone_name(db, ticket.milestone_id)
        milestone = (
            await fields.resolve_milestone(db, project, changes["milestone"])
            if changes["milestone"]
            else None
        )
        if (milestone.id if milestone else None) != ticket.milestone_id:
            diffs.append(("milestone", old_milestone, milestone.name if milestone else None))
            ticket.milestone_id = milestone.id if milestone else None
    if "parent" in changes:
        old_parent = await _ticket_key(db, project, ticket.parent_id)
        parent = (
            await fields.resolve_parent(db, project, changes["parent"], child=ticket)
            if changes["parent"]
            else None
        )
        if (parent.id if parent else None) != ticket.parent_id:
            diffs.append(
                ("parent", old_parent, f"{project.key}-{parent.number}" if parent else None)
            )
            ticket.parent_id = parent.id if parent else None
    if "assignee" in changes:
        old_assignee = ticket.assignee.handle if ticket.assignee else None
        assignee = (
            await fields.resolve_assignable(db, project, changes["assignee"], field="assignee")
            if changes["assignee"]
            else None
        )
        if (assignee.id if assignee else None) != ticket.assignee_id:
            diffs.append(("assignee", old_assignee, assignee.handle if assignee else None))
            ticket.assignee_id = assignee.id if assignee else None
            ticket.assignee = assignee
    if "due_date" in changes:
        new_due = changes["due_date"]
        if new_due != ticket.due_date:
            diffs.append(("due_date", fields.iso(ticket.due_date), fields.iso(new_due)))
            ticket.due_date = new_due
    if "start_date" in changes:
        new_start = changes["start_date"]
        if new_start != ticket.start_date:
            diffs.append(("start_date", fields.iso(ticket.start_date), fields.iso(new_start)))
            ticket.start_date = new_start
    remaining_before = ticket.remaining_hours
    if "estimate_hours" in changes:
        new_estimate = fields.normalize_estimate(changes["estimate_hours"])
        if new_estimate != ticket.estimate_hours:
            diffs.append(
                (
                    "estimate_hours",
                    fields.estimate_json(ticket.estimate_hours),
                    fields.estimate_json(new_estimate),
                )
            )
            ticket.estimate_hours = new_estimate
            estimate_changed(ticket)
    if "remaining_hours" in changes:
        new_remaining = fields.normalize_estimate(changes["remaining_hours"])
        if new_remaining != ticket.remaining_hours:
            diffs.append(
                (
                    "remaining_hours",
                    fields.estimate_json(ticket.remaining_hours),
                    fields.estimate_json(new_remaining),
                )
            )
            ticket.remaining_hours = new_remaining
        ticket.remaining_mode = RemainingMode.manual
    if changes.get("remaining_mode") == RemainingMode.auto.value:
        if ticket.remaining_mode is not RemainingMode.auto:
            diffs.append(("remaining_mode", ticket.remaining_mode.value, "auto"))
        ticket.remaining_mode = RemainingMode.auto
        estimate_changed(ticket)
    if "tags" in changes:
        new_tags = fields.normalize_tags(changes["tags"] or [])
        if new_tags != list(ticket.tags):
            diffs.append(("tags", list(ticket.tags), new_tags))
            ticket.tags = new_tags

    if "custom_fields" in changes:
        new_values, custom_diffs = await custom_fields.apply_values(
            db,
            project,
            ticket.type,
            ticket.area_id,
            dict(ticket.custom_fields or {}),
            changes["custom_fields"] or {},
        )
        if custom_diffs:
            ticket.custom_fields = new_values
        for key, old, new in custom_diffs:
            history.record(
                db,
                ticket,
                access.user,
                EventType.custom_field_changed,
                field=f"cf.{key}",
                old=old,
                new=new,
            )
        changed_custom = bool(custom_diffs)
    else:
        changed_custom = False

    if ticket.remaining_hours != remaining_before and all(d[0] != "remaining_hours" for d in diffs):
        # A side effect of the estimate: recorded so burndowns can replay any day.
        diffs.append(
            (
                "remaining_hours",
                fields.estimate_json(remaining_before),
                fields.estimate_json(ticket.remaining_hours),
            )
        )
    for name, old, new in diffs:
        history.record(
            db, ticket, access.user, EventType.field_changed, field=name, old=old, new=new
        )
    if diffs or changed_custom:
        bump(ticket)
    await db.flush()
    return ticket


def _require_value(changes: dict[str, Any], name: str) -> None:
    if changes[name] is None:
        raise fields.invalid(name, "required", f"{name} cannot be cleared.")


async def _area_name(db: AsyncSession, area_id: uuid.UUID | None) -> str | None:
    return await db.scalar(select(Area.name).where(Area.id == area_id)) if area_id else None


async def _milestone_name(db: AsyncSession, milestone_id: uuid.UUID | None) -> str | None:
    if milestone_id is None:
        return None
    return await db.scalar(select(Milestone.name).where(Milestone.id == milestone_id))


async def _ticket_key(
    db: AsyncSession, project: Project, ticket_id: uuid.UUID | None
) -> str | None:
    if ticket_id is None:
        return None
    number = await db.scalar(select(Ticket.number).where(Ticket.id == ticket_id))
    return f"{project.key}-{number}"


# --- delete / restore --------------------------------------------------------------------


async def delete_ticket(db: AsyncSession, access: ProjectAccess, ticket: Ticket) -> None:
    """Soft delete: hidden everywhere, history kept. Children lose their parent."""
    key = f"{access.project.key}-{ticket.number}"
    children = await db.scalars(
        select(Ticket).where(Ticket.parent_id == ticket.id, Ticket.deleted_at.is_(None))
    )
    for child in children:
        child.parent_id = None
        history.record(db, child, access.user, EventType.field_changed, field="parent", old=key)
        bump(child)
    ticket.deleted_at = utcnow()
    history.record(db, ticket, access.user, EventType.deleted)
    bump(ticket)
    await db.flush()


async def restore_ticket(db: AsyncSession, access: ProjectAccess, ticket: Ticket) -> Ticket:
    if ticket.deleted_at is None:
        raise Conflict(f"{access.project.key}-{ticket.number} is not deleted.", code="not_deleted")
    ticket.deleted_at = None
    history.record(db, ticket, access.user, EventType.restored)
    bump(ticket)
    await db.flush()
    return ticket


# --- collaborators -----------------------------------------------------------------------


async def list_collaborators(
    db: AsyncSession, ticket_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[User]]:
    rows = await db.scalars(
        select(TicketCollaborator)
        .where(TicketCollaborator.ticket_id.in_(ticket_ids))
        .order_by(TicketCollaborator.created_at)
    )
    result: dict[uuid.UUID, list[User]] = {}
    for row in rows:
        result.setdefault(row.ticket_id, []).append(row.user)
    return result


async def add_collaborator(
    db: AsyncSession, access: ProjectAccess, ticket: Ticket, handle: str
) -> Ticket:
    user = await fields.resolve_assignable(db, access.project, handle, field="collaborators")
    if await db.get(TicketCollaborator, (ticket.id, user.id)) is None:
        db.add(TicketCollaborator(ticket_id=ticket.id, user_id=user.id))
        history.record(db, ticket, access.user, EventType.collaborator_added, new=user.handle)
        bump(ticket)
        await db.flush()
    return ticket


async def remove_collaborator(
    db: AsyncSession, access: ProjectAccess, ticket: Ticket, handle: str
) -> Ticket:
    value = handle.strip().lstrip("@").lower()
    user = await db.scalar(select(User).where(User.handle == value))
    row = await db.get(TicketCollaborator, (ticket.id, user.id)) if user else None
    if row is None:
        raise fields.invalid(
            "handle", "not a collaborator", f"@{value} is not a collaborator on this ticket."
        )
    await db.delete(row)
    history.record(db, ticket, access.user, EventType.collaborator_removed, old=value)
    bump(ticket)
    await db.flush()
    return ticket


# --- checklist ---------------------------------------------------------------------------


async def set_checklist_item(
    db: AsyncSession, access: ProjectAccess, ticket: Ticket, index: int, checked: bool
) -> Ticket:
    try:
        new_md, item = markdown.set_checklist_item(ticket.description_md, index, checked)
    except IndexError as exc:
        count = len(markdown.parse_checklist(ticket.description_md))
        raise NotFound(
            f"Checklist item {index} does not exist; this ticket has {count} items "
            f"(0 to {max(count - 1, 0)}).",
            code="checklist_item_not_found",
        ) from exc
    if item.checked == checked:
        return ticket
    ticket.description_md = new_md
    history.record(
        db,
        ticket,
        access.user,
        EventType.checklist_item_toggled,
        field="checklist",
        old={"index": index, "text": item.text, "checked": item.checked},
        new={"index": index, "text": item.text, "checked": checked},
    )
    bump(ticket)
    await db.flush()
    return ticket


# --- mentions and children ---------------------------------------------------------------


async def sync_mentions(
    db: AsyncSession, ticket_id: uuid.UUID, comment_id: uuid.UUID | None, text_md: str
) -> None:
    """Recompute stored mentions for a description (comment_id None) or a comment."""
    condition = (
        Mention.comment_id.is_(None) if comment_id is None else Mention.comment_id == comment_id
    )
    await db.execute(delete(Mention).where(Mention.ticket_id == ticket_id, condition))
    handles = markdown.extract_mentions(text_md)
    if not handles:
        return
    users = await db.scalars(select(User.id).where(User.handle.in_(handles)))
    for user_id in users:
        db.add(Mention(ticket_id=ticket_id, comment_id=comment_id, mentioned_user_id=user_id))


async def list_children(db: AsyncSession, ticket: Ticket) -> list[Ticket]:
    return list(
        await db.scalars(
            select(Ticket)
            .where(Ticket.parent_id == ticket.id, Ticket.deleted_at.is_(None))
            .order_by(Ticket.rank)
        )
    )
