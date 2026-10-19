"""Clone a ticket (optionally with its subtree) and move tickets between projects."""

import re
import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.core.errors import ValidationFailed
from radicle.db.models import (
    Area,
    Attachment,
    CustomFieldDefinition,
    EventType,
    LinkType,
    Milestone,
    MilestoneStatus,
    Project,
    ProjectMember,
    ProjectRole,
    Resolution,
    StatusCategory,
    Ticket,
    TicketCollaborator,
    TicketKeyAlias,
    TicketLink,
    TicketType,
    User,
    utcnow,
)
from radicle.services import history, periods, rank
from radicle.services.access import ProjectAccess, project_access
from radicle.services.tickets import NewTicket, bump, create_ticket
from radicle.services.workflows import load_workflows
from radicle.storage import get_storage

CLONE_INCLUDES = (
    "description",
    "checklist_state",
    "tags",
    "custom_fields",
    "collaborators",
    "attachments",
    "children",
)
CHECKED = re.compile(r"^([ \t]*[-*+][ \t]+)\[[xX]\]", re.MULTILINE)
CHECKLIST_LINE = re.compile(r"^[ \t]*[-*+][ \t]+\[[ xX]\][ \t]+.*$", re.MULTILINE)


def _key(project: Project, ticket: Ticket) -> str:
    return f"{project.key}-{ticket.number}"


async def _area_name(db: AsyncSession, area_id: uuid.UUID | None) -> str | None:
    return await db.scalar(select(Area.name).where(Area.id == area_id)) if area_id else None


async def _target_area(
    db: AsyncSession,
    target: Project,
    ticket: Ticket,
    area_mapping: dict[str, str],
    key: str,
) -> str | None:
    """Area name in the target project, or a 422 that says which mapping is missing."""
    name = await _area_name(db, ticket.area_id)
    if name is None:
        return None
    wanted = area_mapping.get(name, name)
    found = await db.scalar(
        select(Area.name).where(
            Area.project_id == target.id,
            func.lower(Area.name) == wanted.lower(),
            Area.archived_at.is_(None),
        )
    )
    if found is not None:
        return found
    if ticket.type is TicketType.draft and name not in area_mapping:
        return None
    names = await db.scalars(
        select(Area.name)
        .where(Area.project_id == target.id, Area.archived_at.is_(None))
        .order_by(Area.position)
    )
    raise ValidationFailed(
        f"Area '{name}' of {key} does not exist in {target.key}. Send area_mapping like "
        f'{{"{name}": "<area>"}} with one of: {", ".join(names) or "none yet"}.',
        code="area_mapping_required",
        errors=[{"field": "area_mapping", "message": f"missing for {name}"}],
    )


# --- clone ---------------------------------------------------------------------------------


def _clone_description(text: str, include: set[str]) -> str:
    if "description" not in include:
        text = "\n".join(CHECKLIST_LINE.findall(text))
    if "checklist_state" not in include:
        text = CHECKED.sub(r"\1[ ]", text)
    return text


async def clone_ticket(
    db: AsyncSession,
    access: ProjectAccess,
    ticket: Ticket,
    *,
    target: ProjectAccess | None = None,
    area_mapping: dict[str, str] | None = None,
    include: list[str] | None = None,
    parent: Ticket | None = None,
) -> Ticket:
    """A new ticket like `ticket`: initial status, no assignee, reporter = caller, and a
    `clones` link to the original."""
    unknown = set(include or []) - set(CLONE_INCLUDES)
    if unknown:
        raise ValidationFailed(
            f"Unknown include: {', '.join(sorted(unknown))}. Use {', '.join(CLONE_INCLUDES)}.",
            errors=[{"field": "include", "message": "unknown"}],
        )
    wanted = set(include or [])
    target = target or access
    source_key = _key(access.project, ticket)
    same_project = target.project.id == access.project.id
    milestone = None
    if ticket.milestone_id:
        name = await db.scalar(select(Milestone.name).where(Milestone.id == ticket.milestone_id))
        milestone = await db.scalar(
            select(Milestone.name).where(
                Milestone.project_id == target.project.id,
                func.lower(Milestone.name) == (name or "").lower(),
                Milestone.status == MilestoneStatus.open,
            )
        )
    custom: dict[str, object] = {}
    if "custom_fields" in wanted and ticket.custom_fields:
        keys = set(
            await db.scalars(
                select(CustomFieldDefinition.key).where(
                    CustomFieldDefinition.project_id == target.project.id,
                    CustomFieldDefinition.archived_at.is_(None),
                )
            )
        )
        custom = {k: v for k, v in ticket.custom_fields.items() if k in keys}
    collaborators: list[str] = []
    if "collaborators" in wanted:
        collaborators = list(
            await db.scalars(
                select(User.handle)
                .join(TicketCollaborator, TicketCollaborator.user_id == User.id)
                .join(ProjectMember, ProjectMember.user_id == User.id)
                .where(
                    TicketCollaborator.ticket_id == ticket.id,
                    ProjectMember.project_id == target.project.id,
                    ProjectMember.role != ProjectRole.viewer,
                )
            )
        )
    parent_key = None
    if parent is not None:
        parent_key = _key(target.project, parent)
    elif same_project and ticket.parent_id:
        parent_row = await db.get(Ticket, ticket.parent_id)
        if parent_row is not None and parent_row.deleted_at is None:
            parent_key = _key(access.project, parent_row)
    clone = await create_ticket(
        db,
        target,
        NewTicket(
            type=ticket.type,
            title=ticket.title,
            description_md=_clone_description(ticket.description_md, wanted),
            area=await _target_area(db, target.project, ticket, area_mapping or {}, source_key),
            milestone=milestone,
            priority=ticket.priority,
            collaborators=collaborators,
            parent=parent_key,
            due_date=ticket.due_date,
            estimate_hours=ticket.estimate_hours,
            tags=list(ticket.tags) if "tags" in wanted else [],
            custom_fields=custom,
        ),
    )
    db.add(
        TicketLink(
            source_id=clone.id,
            target_id=ticket.id,
            type=LinkType.clones,
            created_by=access.user.id,
        )
    )
    history.record(
        db, clone, access.user, EventType.cloned_from, field="clone", new={"from": source_key}
    )
    if "attachments" in wanted:
        await _copy_attachments(db, ticket, clone, access.user)
    await db.flush()
    if "children" in wanted:
        children = await db.scalars(
            select(Ticket)
            .where(Ticket.parent_id == ticket.id, Ticket.deleted_at.is_(None))
            .order_by(Ticket.rank)
        )
        for child in list(children):
            await clone_ticket(
                db,
                access,
                child,
                target=target,
                area_mapping=area_mapping,
                include=include,
                parent=clone,
            )
    return clone


async def _copy_attachments(db: AsyncSession, source: Ticket, clone: Ticket, user: User) -> None:
    storage = get_storage()
    rows = await db.scalars(
        select(Attachment).where(Attachment.ticket_id == source.id, Attachment.deleted_at.is_(None))
    )
    for original in list(rows):
        copy = Attachment(
            id=uuid.uuid4(),
            ticket_id=clone.id,
            uploader_id=user.id,
            filename=original.filename,
            mime_type=original.mime_type,
            size_bytes=original.size_bytes,
            sha256=original.sha256,
            storage_key="",
            width=original.width,
            height=original.height,
            variants={},
        )
        copy.storage_key = f"{clone.project_id}/{clone.id}/{copy.id}/original"
        await storage.put(copy.storage_key, await storage.get(original.storage_key), copy.mime_type)
        variants = {}
        for name, variant in original.variants.items():
            key = f"{clone.project_id}/{clone.id}/{copy.id}/{name}"
            await storage.put(key, await storage.get(variant["key"]), "image/webp")
            variants[name] = {**variant, "key": key}
        copy.variants = variants
        db.add(copy)


# --- move ----------------------------------------------------------------------------------


async def _subtree(db: AsyncSession, root: Ticket) -> list[Ticket]:
    result = [root]
    frontier = [root.id]
    while frontier:
        children = list(
            await db.scalars(
                select(Ticket)
                .where(Ticket.parent_id.in_(frontier))
                .order_by(Ticket.number)
                .with_for_update(of=Ticket)
            )
        )
        result += children
        frontier = [c.id for c in children]
    return result


async def move_ticket(
    db: AsyncSession,
    access: ProjectAccess,
    ticket: Ticket,
    *,
    target_key: str,
    area_mapping: dict[str, str] | None = None,
    milestone: str | None = None,
    status_mapping: dict[str, str] | None = None,
    include_children: bool = True,
) -> Ticket:
    """Give the ticket (and its subtickets) a new number in another project. The old key
    keeps working. Links, comments, attachments, worklogs and history stay."""
    target = await project_access(db, access.user, target_key, need=ProjectRole.member, write=True)
    if target.project.id == access.project.id:
        raise ValidationFailed(
            f"{_key(access.project, ticket)} is already in {target.project.key}.",
            errors=[{"field": "target_project", "message": "same project"}],
        )
    moving = await _subtree(db, ticket) if include_children else [ticket]
    moving_ids = {t.id for t in moving}
    source_flows = await load_workflows(db, access.project.id)
    target_flows = await load_workflows(db, target.project.id)
    target_milestone_id = None
    if milestone:
        target_milestone_id = await db.scalar(
            select(Milestone.id).where(
                Milestone.project_id == target.project.id,
                func.lower(Milestone.name) == milestone.strip().lower(),
            )
        )
        if target_milestone_id is None:
            raise ValidationFailed(
                f"Milestone '{milestone}' does not exist in {target.project.key}.",
                errors=[{"field": "milestone", "message": "unknown"}],
            )
    members = set(
        await db.scalars(
            select(ProjectMember.user_id).where(
                ProjectMember.project_id == target.project.id,
                ProjectMember.role != ProjectRole.viewer,
            )
        )
    )
    field_keys = set(
        await db.scalars(
            select(CustomFieldDefinition.key).where(
                CustomFieldDefinition.project_id == target.project.id,
                CustomFieldDefinition.archived_at.is_(None),
            )
        )
    )
    # Validate every ticket before changing any of them.
    plans = []
    for t in moving:
        key = _key(access.project, t)
        area = await _target_area(db, target.project, t, area_mapping or {}, key)
        plans.append((t, key, area))

    last_rank = await db.scalar(
        select(func.max(Ticket.rank)).where(Ticket.project_id == target.project.id)
    )
    for t, old_key, area_name in plans:
        number = await db.scalar(
            update(Project)
            .where(Project.id == target.project.id)
            .values(ticket_seq=Project.ticket_seq + 1)
            .returning(Project.ticket_seq)
        )
        db.add(TicketKeyAlias(old_key=old_key, ticket_id=t.id))
        old_status = source_flows[t.type].status_by_id(t.status_id)
        flow = target_flows[t.type]
        wanted = (status_mapping or {}).get(old_status.name, old_status.name)
        new_status = flow.status_named(wanted) or flow.initial
        dropped = {k: v for k, v in (t.custom_fields or {}).items() if k not in field_keys}
        old_milestone = t.milestone_id
        t.project_id = target.project.id
        t.number = int(number or 0)
        t.area_id = (
            await db.scalar(
                select(Area.id).where(Area.project_id == target.project.id, Area.name == area_name)
            )
            if area_name
            else None
        )
        if target_milestone_id is not None:
            t.milestone_id = target_milestone_id
        elif old_milestone is not None:
            name = await db.scalar(select(Milestone.name).where(Milestone.id == old_milestone))
            t.milestone_id = await db.scalar(
                select(Milestone.id).where(
                    Milestone.project_id == target.project.id,
                    func.lower(Milestone.name) == (name or "").lower(),
                )
            )
        if t.parent_id is not None and t.parent_id not in moving_ids:
            t.parent_id = None
        if t.assignee_id is not None and t.assignee_id not in members:
            t.assignee_id = None
            t.assignee = None
        t.status_id = new_status.id
        t.status = new_status
        if new_status.category is StatusCategory.done:
            t.resolution = t.resolution or Resolution.done
            t.resolved_at = t.resolved_at or utcnow()
        else:
            t.resolution = None
            t.resolved_at = None
        t.custom_fields = {k: v for k, v in (t.custom_fields or {}).items() if k in field_keys}
        last_rank = rank.after(last_rank)
        t.rank = last_rank
        new_key = f"{target.project.key}-{t.number}"
        event = history.record(
            db,
            t,
            access.user,
            EventType.moved,
            field="project",
            old={"key": old_key, "status": old_status.name},
            new={
                "key": new_key,
                "status": new_status.name,
                "dropped_custom_fields": sorted(dropped) or None,
            },
        )
        await periods.track(db, t, event)
        bump(t)
        await db.flush()
    return ticket
