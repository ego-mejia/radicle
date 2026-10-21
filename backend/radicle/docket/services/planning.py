"""Areas and milestones of a project. Both are referenced by name in the API and RQL."""

import re
import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.docket.db.models import Area, Milestone, MilestoneStatus, Project, utcnow
from radicle.docket.services.projects import check_description, normalize_name
from radicle.platform.errors import Conflict, NotFound, ValidationFailed

COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
# Icons are names from the web app's fixed set; the server never stores SVG markup.
ICON_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ICON_MAX = 40
NAME_MAX = 80


def _name(value: str) -> str:
    return normalize_name(value, limit=NAME_MAX)


def _color(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    if not COLOR_RE.fullmatch(value):
        raise ValidationFailed(
            f"Invalid color '{value}'. Use a hex color like #4D7C0F.",
            errors=[{"field": "color", "message": "invalid hex color"}],
        )
    return value.upper()


def _icon(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    if len(value) > ICON_MAX or not ICON_RE.fullmatch(value):
        raise ValidationFailed(
            f"Invalid icon '{value}'. Use an icon name in kebab case, like rocket or bar-chart.",
            errors=[{"field": "icon", "message": "invalid icon name"}],
        )
    return value


# --- areas -------------------------------------------------------------------------------


async def list_areas(
    db: AsyncSession, project: Project, *, include_archived: bool = False
) -> list[Area]:
    query = select(Area).where(Area.project_id == project.id)
    if not include_archived:
        query = query.where(Area.archived_at.is_(None))
    return list(await db.scalars(query.order_by(Area.position, Area.name)))


async def get_area(db: AsyncSession, project: Project, name: str) -> Area:
    area = await _find_by_name(db, Area, project.id, name)
    if area is None:
        raise NotFound(f"Area '{name}' not found in {project.key}.", code="area_not_found")
    return area


async def create_area(
    db: AsyncSession,
    project: Project,
    *,
    name: str,
    color: str | None = None,
    icon: str | None = None,
) -> Area:
    name = _name(name)
    await _ensure_free_name(db, Area, project, name)
    position = await _next_position(db, Area, project.id)
    area = Area(
        project_id=project.id, name=name, color=_color(color), icon=_icon(icon), position=position
    )
    db.add(area)
    await db.flush()
    return area


@dataclass(frozen=True)
class AreaChanges:
    name: str | None = None
    color: str | None = None
    clear_color: bool = False
    icon: str | None = None
    clear_icon: bool = False
    position: int | None = None
    archived: bool | None = None


async def update_area(db: AsyncSession, project: Project, area: Area, ch: AreaChanges) -> Area:
    if ch.name is not None and ch.name.strip().lower() != area.name.lower():
        name = _name(ch.name)
        await _ensure_free_name(db, Area, project, name)
        area.name = name
    elif ch.name is not None:
        area.name = _name(ch.name)
    if ch.clear_color:
        area.color = None
    elif ch.color is not None:
        area.color = _color(ch.color)
    if ch.clear_icon:
        area.icon = None
    elif ch.icon is not None:
        area.icon = _icon(ch.icon)
    if ch.position is not None:
        area.position = ch.position
    if ch.archived is not None:
        area.archived_at = utcnow() if ch.archived else None
    await db.flush()
    return area


def archive_area(area: Area) -> Area:
    if area.archived_at is not None:
        raise Conflict(f"Area '{area.name}' is already archived.", code="already_archived")
    area.archived_at = utcnow()
    return area


# --- milestones --------------------------------------------------------------------------


async def list_milestones(
    db: AsyncSession, project: Project, *, status: MilestoneStatus | None = None
) -> list[Milestone]:
    query = select(Milestone).where(Milestone.project_id == project.id)
    if status is not None:
        query = query.where(Milestone.status == status)
    order = (Milestone.target_date.asc().nulls_last(), Milestone.position, Milestone.name)
    return list(await db.scalars(query.order_by(*order)))


async def get_milestone(db: AsyncSession, project: Project, name: str) -> Milestone:
    milestone = await _find_by_name(db, Milestone, project.id, name)
    if milestone is None:
        raise NotFound(
            f"Milestone '{name}' not found in {project.key}.", code="milestone_not_found"
        )
    return milestone


async def create_milestone(
    db: AsyncSession,
    project: Project,
    *,
    name: str,
    description_md: str = "",
    target_date: date | None = None,
) -> Milestone:
    name = _name(name)
    await _ensure_free_name(db, Milestone, project, name)
    milestone = Milestone(
        project_id=project.id,
        name=name,
        description_md=check_description(description_md),
        target_date=target_date,
        position=await _next_position(db, Milestone, project.id),
    )
    db.add(milestone)
    await db.flush()
    return milestone


@dataclass(frozen=True)
class MilestoneChanges:
    name: str | None = None
    description_md: str | None = None
    target_date: date | None = None
    clear_target_date: bool = False
    status: MilestoneStatus | None = None
    position: int | None = None


async def update_milestone(
    db: AsyncSession, project: Project, milestone: Milestone, ch: MilestoneChanges
) -> Milestone:
    if ch.name is not None:
        name = _name(ch.name)
        if name.lower() != milestone.name.lower():
            await _ensure_free_name(db, Milestone, project, name)
        milestone.name = name
    if ch.description_md is not None:
        milestone.description_md = check_description(ch.description_md)
    if ch.clear_target_date:
        milestone.target_date = None
    elif ch.target_date is not None:
        milestone.target_date = ch.target_date
    if ch.position is not None:
        milestone.position = ch.position
    if ch.status is not None and ch.status is not milestone.status:
        milestone.status = ch.status
        milestone.closed_at = utcnow() if ch.status is MilestoneStatus.closed else None
    await db.flush()
    return milestone


# --- helpers -----------------------------------------------------------------------------


async def _find_by_name[M: (Area, Milestone)](
    db: AsyncSession, model: type[M], project_id: uuid.UUID, name: str
) -> M | None:
    value = name.strip()
    try:
        as_id = uuid.UUID(value)
    except ValueError:
        as_id = None
    condition = func.lower(model.name) == value.lower()
    if as_id is not None:
        condition = model.id == as_id
    return await db.scalar(select(model).where(model.project_id == project_id, condition))


async def _ensure_free_name(
    db: AsyncSession, model: type[Area] | type[Milestone], project: Project, name: str
) -> None:
    taken = await db.scalar(
        select(model.id).where(
            model.project_id == project.id, func.lower(model.name) == name.lower()
        )
    )
    if taken:
        kind = "Area" if model is Area else "Milestone"
        raise Conflict(
            f"{kind} '{name}' already exists in {project.key}.",
            code="duplicate_name",
            errors=[{"field": "name", "message": "already exists"}],
        )


async def _next_position(
    db: AsyncSession, model: type[Area] | type[Milestone], project_id: uuid.UUID
) -> int:
    current = await db.scalar(
        select(func.max(model.position)).where(model.project_id == project_id)
    )
    return 0 if current is None else int(current) + 1
