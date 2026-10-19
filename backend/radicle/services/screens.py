"""Screens: which fields a form asks for, per ticket type and operation.

Without a screen the stage 1 defaults apply. Checks live here so the UI, the API and
the MCP get the same answer and the same message.
"""

import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.core.errors import ValidationFailed
from radicle.db.models import (
    PRIORITY_ORDER,
    Area,
    CustomFieldDefinition,
    CustomFieldType,
    Milestone,
    MilestoneStatus,
    Project,
    ProjectMember,
    ProjectRole,
    Screen,
    ScreenOperation,
    Ticket,
    TicketCollaborator,
    TicketType,
    Transition,
    User,
)
from radicle.services import custom_fields

SCREEN_FIELDS: dict[str, str] = {
    "title": "text",
    "description_md": "markdown",
    "priority": "enum",
    "area": "area",
    "milestone": "milestone",
    "assignee": "user",
    "collaborators": "users",
    "parent": "ticket",
    "due_date": "date",
    "estimate_hours": "number",
    "tags": "tags",
}
LABELS = {
    "title": "Title",
    "description_md": "Description",
    "priority": "Priority",
    "area": "Area",
    "milestone": "Milestone",
    "assignee": "Assignee",
    "collaborators": "Collaborators",
    "parent": "Parent",
    "due_date": "Due date",
    "estimate_hours": "Estimate",
    "tags": "Tags",
}
CUSTOM_RE = re.compile(r"^cf\.[a-z][a-z0-9_]{1,39}$")
DEFAULT_ORDER = list(SCREEN_FIELDS)


@dataclass(frozen=True)
class SchemaField:
    field: str
    label: str
    kind: str
    required: bool
    options: list[str] | None = None
    areas: list[str] | None = None  # custom fields limited to some areas


@dataclass
class FormSchema:
    ticket_type: TicketType
    operation: ScreenOperation
    transition: str | None
    from_screen: bool
    fields: list[SchemaField] = field(default_factory=list)

    def required(self) -> list[SchemaField]:
        return [f for f in self.fields if f.required]

    def names(self) -> set[str]:
        return {f.field for f in self.fields}


def check_fields(raw: list[dict[str, Any]], path: str = "fields") -> list[dict[str, Any]]:
    """Normalize a screen's field list: known names, no repeats."""
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw:
        name = str(item.get("field", "")).strip()
        if name not in SCREEN_FIELDS and not CUSTOM_RE.fullmatch(name):
            raise ValidationFailed(
                f"Unknown screen field '{name}'. Use {', '.join(SCREEN_FIELDS)} or cf.<key>.",
                errors=[{"field": path, "message": "unknown field"}],
            )
        if name in seen:
            raise ValidationFailed(
                f"Field '{name}' is repeated in a screen.",
                errors=[{"field": path, "message": "duplicate"}],
            )
        seen.add(name)
        result.append({"field": name, "required": bool(item.get("required", False))})
    return result


async def find_screen(
    db: AsyncSession,
    project_id: uuid.UUID,
    ticket_type: TicketType,
    operation: ScreenOperation,
    transition_id: uuid.UUID | None = None,
) -> Screen | None:
    query = select(Screen).where(
        Screen.project_id == project_id,
        Screen.ticket_type == ticket_type,
        Screen.operation == operation,
    )
    if operation is ScreenOperation.transition:
        query = query.where(Screen.transition_id == transition_id)
    return await db.scalar(query.limit(1))


async def list_screens(db: AsyncSession, project_id: uuid.UUID) -> list[Screen]:
    return list(
        await db.scalars(
            select(Screen)
            .where(Screen.project_id == project_id)
            .order_by(Screen.ticket_type, Screen.operation, Screen.id)
        )
    )


ScreenRow = tuple[TicketType, ScreenOperation, uuid.UUID | None, list[dict[str, Any]]]


async def replace_screens(db: AsyncSession, project: Project, screens: list[ScreenRow]) -> None:
    current = [
        (s.ticket_type, s.operation, s.transition_id, s.fields)
        for s in await list_screens(db, project.id)
    ]
    wanted = sorted(screens, key=lambda s: (s[0].value, s[1].value, str(s[2])))
    if sorted(current, key=lambda s: (s[0].value, s[1].value, str(s[2]))) == wanted:
        return
    await db.execute(delete(Screen).where(Screen.project_id == project.id))
    for ticket_type, operation, transition_id, fields in wanted:
        db.add(
            Screen(
                project_id=project.id,
                ticket_type=ticket_type,
                operation=operation,
                transition_id=transition_id,
                fields=fields,
            )
        )
    await db.flush()


# --- schema --------------------------------------------------------------------------------


async def form_schema(
    db: AsyncSession,
    project: Project,
    ticket_type: TicketType,
    operation: ScreenOperation,
    transition: Transition | None = None,
) -> FormSchema:
    screen = await find_screen(
        db, project.id, ticket_type, operation, transition.id if transition else None
    )
    definitions = {
        f.key: f
        for f in await custom_fields.list_fields(db, project.id)
        if ticket_type in f.applies_to_types
    }
    schema = FormSchema(
        ticket_type=ticket_type,
        operation=operation,
        transition=transition.name if transition else None,
        from_screen=screen is not None,
    )
    if screen is not None:
        entries = [(item["field"], bool(item["required"])) for item in screen.fields]
    elif operation is ScreenOperation.transition:
        entries = []
    else:
        entries = [
            (
                name,
                name == "title"
                or (name == "area" and _area_default_required(ticket_type, operation)),
            )
            for name in DEFAULT_ORDER
        ]
        entries += [(f"cf.{key}", False) for key in definitions]
    options = _Options(db, project)
    for name, required in entries:
        if name.startswith("cf."):
            definition = definitions.get(name[3:])
            if definition is None:
                continue  # archived or not for this type
            schema.fields.append(await _custom_field(db, project, definition, required, options))
            continue
        schema.fields.append(
            SchemaField(
                field=name,
                label=LABELS[name],
                kind=SCREEN_FIELDS[name],
                required=required,
                options=await options.for_field(name),
            )
        )
    return schema


def _area_default_required(ticket_type: TicketType, operation: ScreenOperation) -> bool:
    return ticket_type is not TicketType.draft and operation is ScreenOperation.create


class _Options:
    def __init__(self, db: AsyncSession, project: Project) -> None:
        self.db = db
        self.project = project
        self._members: list[str] | None = None

    async def members(self, *, assignable: bool) -> list[str]:
        query = (
            select(User.handle, ProjectMember.role)
            .join(ProjectMember, ProjectMember.user_id == User.id)
            .where(ProjectMember.project_id == self.project.id, User.is_active.is_(True))
            .order_by(User.handle)
        )
        rows = (await self.db.execute(query)).all()
        if assignable:
            return [h for h, role in rows if role is not ProjectRole.viewer]
        return [h for h, _ in rows]

    async def for_field(self, name: str) -> list[str] | None:
        if name == "priority":
            return [
                p.value
                for p in sorted(PRIORITY_ORDER, key=PRIORITY_ORDER.__getitem__, reverse=True)
            ]
        if name == "area":
            return list(
                await self.db.scalars(
                    select(Area.name)
                    .where(Area.project_id == self.project.id, Area.archived_at.is_(None))
                    .order_by(Area.position)
                )
            )
        if name == "milestone":
            return list(
                await self.db.scalars(
                    select(Milestone.name)
                    .where(
                        Milestone.project_id == self.project.id,
                        Milestone.status == MilestoneStatus.open,
                    )
                    .order_by(Milestone.target_date.asc().nulls_last(), Milestone.position)
                )
            )
        if name in ("assignee", "collaborators"):
            return await self.members(assignable=True)
        return None


async def _custom_field(
    db: AsyncSession,
    project: Project,
    definition: CustomFieldDefinition,
    required: bool,
    options: _Options,
) -> SchemaField:
    values: list[str] | None = None
    if definition.field_type is CustomFieldType.select:
        values = [str(o["value"]) for o in definition.options]
    elif definition.field_type is CustomFieldType.user:
        values = await options.members(assignable=False)
    areas = None
    if definition.applies_to_area_ids is not None:
        names = await custom_fields.area_names(db, [definition])
        areas = [names[a] for a in definition.applies_to_area_ids if a in names]
    return SchemaField(
        field=f"cf.{definition.key}",
        label=definition.name,
        kind=definition.field_type.value,
        required=required,
        options=values,
        areas=areas,
    )


# --- checks --------------------------------------------------------------------------------


def missing_message(ticket_type: TicketType, project: Project, missing: list[SchemaField]) -> str:
    names = ", ".join(
        f"{f.label} ({f.field})" if f.field.startswith("cf.") else f.label for f in missing
    )
    return f"A {ticket_type.value} in {project.key} needs: {names}. Fill them in and try again."


def _raise_missing(ticket_type: TicketType, project: Project, missing: list[SchemaField]) -> None:
    if missing:
        raise ValidationFailed(
            missing_message(ticket_type, project, missing),
            code="required_fields",
            errors=[{"field": f.field, "message": "required"} for f in missing],
        )


def _present(value: Any) -> bool:
    return value not in (None, "", [], {})


async def check_create(
    db: AsyncSession,
    project: Project,
    ticket_type: TicketType,
    values: dict[str, Any],
) -> bool:
    """Required fields of the create screen. Returns whether a screen was found, so the
    stage 1 default (area required) applies only without one."""
    schema = await form_schema(db, project, ticket_type, ScreenOperation.create)
    if not schema.from_screen:
        return False
    custom = values.get("custom_fields") or {}
    missing = [
        f
        for f in schema.required()
        if not _present(
            custom.get(f.field[3:]) if f.field.startswith("cf.") else values.get(f.field)
        )
    ]
    _raise_missing(ticket_type, project, missing)
    return True


async def check_edit(
    db: AsyncSession,
    project: Project,
    role: ProjectRole,
    ticket: Ticket,
    changes: dict[str, Any],
) -> None:
    """Fields outside the edit screen are read-only (admins excepted); required ones
    cannot be cleared."""
    schema = await form_schema(db, project, ticket.type, ScreenOperation.edit)
    if not schema.from_screen:
        return
    allowed = schema.names()
    touched = [name for name in changes if name != "custom_fields"]
    touched += [f"cf.{key}" for key in (changes.get("custom_fields") or {})]
    if role is not ProjectRole.admin:
        blocked = [name for name in touched if name not in allowed]
        if blocked:
            raise ValidationFailed(
                f"These fields are read-only for {ticket.type.value} tickets in {project.key}: "
                f"{', '.join(blocked)}. Editable: {', '.join(sorted(allowed)) or 'none'}.",
                code="read_only_fields",
                errors=[{"field": name, "message": "read-only"} for name in blocked],
            )
    cleared = []
    for f in schema.required():
        if f.field.startswith("cf."):
            custom = changes.get("custom_fields") or {}
            if f.field[3:] in custom and not _present(custom[f.field[3:]]):
                cleared.append(f)
        elif f.field in changes and not _present(changes[f.field]):
            cleared.append(f)
    _raise_missing(ticket.type, project, cleared)


async def check_ticket(
    db: AsyncSession, project: Project, ticket: Ticket, schema: FormSchema
) -> None:
    """Every required field of `schema` has a value on the ticket (transition screens)."""
    missing = [f for f in schema.required() if not await ticket_has(db, ticket, f.field)]
    _raise_missing(ticket.type, project, missing)


async def ticket_has(db: AsyncSession, ticket: Ticket, name: str) -> bool:
    if name.startswith("cf."):
        return _present((ticket.custom_fields or {}).get(name[3:]))
    if name == "collaborators":
        count = await db.scalar(
            select(func.count())
            .select_from(TicketCollaborator)
            .where(TicketCollaborator.ticket_id == ticket.id)
        )
        return bool(count)
    columns: dict[str, Any] = {
        "title": ticket.title,
        "description_md": (ticket.description_md or "").strip(),
        "priority": ticket.priority,
        "area": ticket.area_id,
        "milestone": ticket.milestone_id,
        "assignee": ticket.assignee_id,
        "parent": ticket.parent_id,
        "due_date": ticket.due_date,
        "estimate_hours": ticket.estimate_hours,
        "tags": list(ticket.tags or []),
    }
    return _present(columns.get(name))
