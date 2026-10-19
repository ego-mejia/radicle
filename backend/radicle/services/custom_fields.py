"""Custom fields: per-project definitions and the values tickets hold for them.

Values live in `tickets.custom_fields` keyed by field key. User fields store the user id
and are shown as handles. Archiving a field keeps its values but hides them.
"""

import math
import re
import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.core.errors import Conflict, NotFound, ValidationFailed
from radicle.db.models import (
    Area,
    CustomFieldDefinition,
    CustomFieldType,
    Project,
    ProjectMember,
    TicketType,
    User,
    utcnow,
)
from radicle.services.projects import normalize_name

KEY_RE = re.compile(r"^[a-z][a-z0-9_]{1,39}$")
COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
NAME_MAX = 80
TEXT_MAX = 2000
OPTION_MAX = 100
OPTIONS_MAX = 100
FIELDS_MAX = 100

FieldDef = CustomFieldDefinition


def invalid(field: str, detail: str, message: str = "invalid") -> ValidationFailed:
    return ValidationFailed(detail, errors=[{"field": field, "message": message}])


# --- definitions -------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldSpec:
    key: str
    name: str
    field_type: CustomFieldType
    options: list[dict[str, Any]] | None = None
    applies_to_types: list[TicketType] | None = None  # None = every type
    applies_to_areas: list[str] | None = None  # area names; None = every area
    template_ref: str | None = None


@dataclass(frozen=True)
class FieldChanges:
    name: str | None = None
    options: list[dict[str, Any]] | None = None
    applies_to_types: list[TicketType] | None = None
    applies_to_areas: list[str] | None = None
    all_areas: bool = False  # True clears the area restriction
    position: int | None = None
    archived: bool | None = None


def normalize_key(key: str) -> str:
    value = key.strip().removeprefix("cf.").lower()
    if not KEY_RE.fullmatch(value):
        raise invalid(
            "key",
            f"Invalid field key '{key}'. Use 2 to 40 characters: a lowercase letter, then "
            "lowercase letters, digits or '_', like environment or requires_signature.",
        )
    return value


def normalize_options(
    field_type: CustomFieldType, options: list[dict[str, Any]] | None
) -> list[dict[str, Any]]:
    if field_type is not CustomFieldType.select:
        if options:
            raise invalid("options", "Only select fields have options.")
        return []
    if not options:
        raise invalid("options", "A select field needs at least one option.", "required")
    if len(options) > OPTIONS_MAX:
        raise invalid("options", f"A select field can have at most {OPTIONS_MAX} options.")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in options:
        value = str(raw.get("value") or "").strip()
        if not value or len(value) > OPTION_MAX:
            raise invalid("options", f"Option values must be 1 to {OPTION_MAX} characters.")
        if value.lower() in seen:
            raise invalid("options", f"Option '{value}' is repeated.", "duplicate")
        seen.add(value.lower())
        label = str(raw.get("label") or value).strip()[:OPTION_MAX]
        color = raw.get("color") or None
        if color is not None and not COLOR_RE.fullmatch(str(color)):
            raise invalid("options", f"Invalid color '{color}'. Use a hex color like #4D7C0F.")
        result.append({"value": value, "label": label, "color": color.upper() if color else None})
    return result


def _types(types: list[TicketType] | None) -> list[TicketType]:
    if types is None:
        return list(TicketType)
    if not types:
        raise invalid("applies_to_types", "Pick at least one ticket type.", "required")
    return [t for t in TicketType if t in set(types)]


async def _area_ids(
    db: AsyncSession, project: Project, names: list[str] | None
) -> list[uuid.UUID] | None:
    if names is None:
        return None
    ids: list[uuid.UUID] = []
    for name in names:
        area = await db.scalar(
            select(Area).where(
                Area.project_id == project.id, func.lower(Area.name) == name.strip().lower()
            )
        )
        if area is None:
            valid = await db.scalars(
                select(Area.name)
                .where(Area.project_id == project.id, Area.archived_at.is_(None))
                .order_by(Area.position)
            )
            raise invalid(
                "applies_to_areas",
                f"Area '{name}' does not exist in {project.key}. "
                f"Valid areas: {', '.join(valid) or 'none yet'}.",
            )
        if area.id not in ids:
            ids.append(area.id)
    return ids


async def ensure_editable(db: AsyncSession, project: Project) -> None:
    """Projects linked to a template get their fields from it (see templates)."""
    return None


async def list_fields(
    db: AsyncSession, project_id: uuid.UUID, *, include_archived: bool = False
) -> list[FieldDef]:
    query = select(FieldDef).where(FieldDef.project_id == project_id)
    if not include_archived:
        query = query.where(FieldDef.archived_at.is_(None))
    return list(await db.scalars(query.order_by(FieldDef.position, FieldDef.key)))


async def get_field(db: AsyncSession, project: Project, key: str) -> FieldDef:
    value = key.strip().removeprefix("cf.").lower()
    field = await db.scalar(
        select(FieldDef).where(FieldDef.project_id == project.id, FieldDef.key == value)
    )
    if field is None:
        keys = [f.key for f in await list_fields(db, project.id)]
        raise NotFound(
            f"Custom field '{key}' not found in {project.key}. "
            f"Fields: {', '.join(keys) or 'none yet'}.",
            code="field_not_found",
        )
    return field


async def create_field(db: AsyncSession, project: Project, spec: FieldSpec) -> FieldDef:
    key = normalize_key(spec.key)
    if await db.scalar(
        select(FieldDef.id).where(FieldDef.project_id == project.id, FieldDef.key == key)
    ):
        raise Conflict(
            f"Field key '{key}' is already used in {project.key} (maybe by an archived field).",
            code="duplicate_key",
            errors=[{"field": "key", "message": "already taken"}],
        )
    count = await db.scalar(
        select(func.count()).select_from(FieldDef).where(FieldDef.project_id == project.id)
    )
    if (count or 0) >= FIELDS_MAX:
        raise ValidationFailed(f"A project can have at most {FIELDS_MAX} custom fields.")
    position = await db.scalar(
        select(func.max(FieldDef.position)).where(FieldDef.project_id == project.id)
    )
    field = FieldDef(
        project_id=project.id,
        key=key,
        name=normalize_name(spec.name, limit=NAME_MAX),
        field_type=spec.field_type,
        options=normalize_options(spec.field_type, spec.options),
        applies_to_types=_types(spec.applies_to_types),
        applies_to_area_ids=await _area_ids(db, project, spec.applies_to_areas),
        template_ref=spec.template_ref,
        position=0 if position is None else position + 1,
    )
    db.add(field)
    await db.flush()
    return field


async def update_field(
    db: AsyncSession, project: Project, field: FieldDef, ch: FieldChanges
) -> FieldDef:
    """The type and key never change. Changing select options keeps old values."""
    if ch.name is not None:
        field.name = normalize_name(ch.name, limit=NAME_MAX)
    if ch.options is not None:
        field.options = normalize_options(field.field_type, ch.options)
    if ch.applies_to_types is not None:
        field.applies_to_types = _types(ch.applies_to_types)
    if ch.all_areas:
        field.applies_to_area_ids = None
    elif ch.applies_to_areas is not None:
        field.applies_to_area_ids = await _area_ids(db, project, ch.applies_to_areas)
    if ch.position is not None:
        field.position = ch.position
    if ch.archived is not None:
        field.archived_at = utcnow() if ch.archived else None
    await db.flush()
    return field


async def area_names(db: AsyncSession, fields: list[FieldDef]) -> dict[uuid.UUID, str]:
    ids = {a for f in fields for a in f.applies_to_area_ids or []}
    if not ids:
        return {}
    rows = await db.execute(select(Area.id, Area.name).where(Area.id.in_(ids)))
    return {aid: name for aid, name in rows.all()}


# --- values ------------------------------------------------------------------------------


def applies(field: FieldDef, ticket_type: TicketType, area_id: uuid.UUID | None) -> bool:
    if ticket_type not in field.applies_to_types:
        return False
    return field.applies_to_area_ids is None or area_id in field.applies_to_area_ids


async def _check_value(
    db: AsyncSession, project: Project, field: FieldDef, raw: Any
) -> tuple[Any, Any]:
    """(stored value, value shown to people) or a 422 that says what is accepted."""
    name = f"cf.{field.key}"
    kind = field.field_type
    if kind is CustomFieldType.text:
        if not isinstance(raw, str):
            raise invalid(name, f"{field.name} takes text.")
        value = raw.strip()
        if len(value) > TEXT_MAX:
            raise invalid(name, f"{field.name} must be at most {TEXT_MAX} characters.")
        return value, value
    if kind is CustomFieldType.number:
        if isinstance(raw, bool) or not isinstance(raw, int | float | str | Decimal):
            raise invalid(name, f"{field.name} takes a number.")
        try:
            number = float(raw)
        except ValueError:
            raise invalid(name, f"{field.name} takes a number, not '{raw}'.") from None
        if not math.isfinite(number):
            raise invalid(name, f"{field.name} must be a finite number.")
        stored: int | float = int(number) if number.is_integer() else number
        return stored, stored
    if kind is CustomFieldType.date:
        try:
            day = date.fromisoformat(str(raw))
        except ValueError:
            raise invalid(name, f"{field.name} takes a date as YYYY-MM-DD, not '{raw}'.") from None
        return day.isoformat(), day.isoformat()
    if kind is CustomFieldType.select:
        values = {str(o["value"]).lower(): str(o["value"]) for o in field.options}
        match = values.get(str(raw).strip().lower())
        if match is None:
            raise invalid(
                name,
                f"'{raw}' is not an option of {field.name}. Options: {', '.join(values.values())}.",
            )
        return match, match
    if kind is CustomFieldType.checkbox:
        if not isinstance(raw, bool):
            raise invalid(name, f"{field.name} takes true or false.")
        return raw, raw
    if kind is CustomFieldType.user:
        handle = str(raw).strip().lstrip("@").lower()
        user = await db.scalar(
            select(User)
            .join(ProjectMember, ProjectMember.user_id == User.id)
            .where(ProjectMember.project_id == project.id, User.handle == handle)
        )
        if user is None:
            raise invalid(name, f"{field.name} takes a member of {project.key}; @{handle} is not.")
        return str(user.id), user.handle
    url = str(raw).strip()
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc or len(url) > TEXT_MAX:
        raise invalid(name, f"{field.name} takes an http or https URL.")
    return url, url


async def apply_values(
    db: AsyncSession,
    project: Project,
    ticket_type: TicketType,
    area_id: uuid.UUID | None,
    current: dict[str, Any],
    changes: dict[str, Any],
) -> tuple[dict[str, Any], list[tuple[str, Any, Any]]]:
    """Merge `changes` into `current`. None removes a value. Returns the new values and
    (key, old shown value, new shown value) for each key that changed."""
    if not changes:
        return current, []
    fields = {f.key: f for f in await list_fields(db, project.id)}
    usable = sorted(k for k, f in fields.items() if applies(f, ticket_type, area_id))
    result = dict(current)
    diffs: list[tuple[str, Any, Any]] = []
    for raw_key, raw in changes.items():
        key = raw_key.strip().removeprefix("cf.").lower()
        field = fields.get(key)
        if field is None:
            raise invalid(
                f"cf.{key}",
                f"Unknown custom field '{raw_key}' in {project.key}. Fields for "
                f"{ticket_type.value} tickets here: {', '.join(usable) or 'none'}.",
                "unknown",
            )
        if raw is not None and not applies(field, ticket_type, area_id):
            raise invalid(
                f"cf.{key}",
                f"{field.name} does not apply to this {ticket_type.value} (its type or area). "
                f"Fields that apply: {', '.join(usable) or 'none'}.",
                "not applicable",
            )
        old_shown = await shown_value(db, field, current.get(key))
        if raw is not None and key in current and raw in (current[key], old_shown):
            continue  # unchanged: an option removed since is not revalidated
        if raw is None or raw == "":
            if key in result:
                del result[key]
                diffs.append((key, old_shown, None))
            continue
        stored, shown = await _check_value(db, project, field, raw)
        if current.get(key) != stored:
            result[key] = stored
            diffs.append((key, old_shown, shown))
    return result, diffs


async def shown_value(db: AsyncSession, field: FieldDef, stored: Any) -> Any:
    if stored is None or field.field_type is not CustomFieldType.user:
        return stored
    handles = await user_handles(db, [stored])
    return handles.get(str(stored))


async def user_handles(db: AsyncSession, ids: list[Any]) -> dict[str, str]:
    parsed = set()
    for value in ids:
        try:
            parsed.add(uuid.UUID(str(value)))
        except ValueError:
            continue
    if not parsed:
        return {}
    rows = await db.execute(select(User.id, User.handle).where(User.id.in_(parsed)))
    return {str(uid): handle for uid, handle in rows.all()}


def visible_values(
    fields: list[FieldDef],
    values: dict[str, Any],
    ticket_type: TicketType,
    area_id: uuid.UUID | None,
    handles: dict[str, str],
) -> dict[str, Any]:
    """Values of active fields that apply to the ticket, with users as handles."""
    out: dict[str, Any] = {}
    for field in fields:
        if field.key not in values or not applies(field, ticket_type, area_id):
            continue
        value = values[field.key]
        if field.field_type is CustomFieldType.user:
            value = handles.get(str(value))
        out[field.key] = value
    return out


async def rql_types(db: AsyncSession, project_ids: Any) -> dict[str, CustomFieldType]:
    """Key to type of the active fields in the given projects, for `cf.<key>` in RQL."""
    rows = await db.execute(
        select(FieldDef.key, FieldDef.field_type)
        .where(FieldDef.project_id.in_(project_ids), FieldDef.archived_at.is_(None))
        .order_by(FieldDef.created_at)
    )
    types: dict[str, CustomFieldType] = {}
    for key, field_type in rows.all():
        types.setdefault(key, field_type)
    return types
