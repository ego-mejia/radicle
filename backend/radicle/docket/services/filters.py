"""Saved filters: private, for a project or for the whole instance."""

import uuid

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.docket.db.models import FilterVisibility, Project, SavedFilter, User, utcnow
from radicle.docket.query import ast
from radicle.docket.query.errors import RQLError
from radicle.docket.query.parser import parse
from radicle.docket.services.access import project_access
from radicle.docket.services.search import visible_project_ids
from radicle.platform.errors import Conflict, Forbidden, NotFound, ValidationFailed

NAME_MAX = 100
MAX_DEPTH = 5


def visible(user: User) -> ColumnElement[bool]:
    """SQL condition: filters this user can see."""
    return or_(
        SavedFilter.owner_id == user.id,
        SavedFilter.visibility == FilterVisibility.instance,
        (SavedFilter.visibility == FilterVisibility.project)
        & SavedFilter.project_id.in_(visible_project_ids(user)),
    )


def _name(value: str) -> str:
    name = " ".join(value.split())
    if not 1 <= len(name) <= NAME_MAX:
        raise ValidationFailed(
            f"Filter names are 1 to {NAME_MAX} characters.",
            errors=[{"field": "name", "message": "invalid length"}],
        )
    return name


def _rql(value: str) -> str:
    try:
        parse(value)
    except RQLError as exc:
        raise ValidationFailed(
            f"The query is not valid RQL: {exc.detail}",
            errors=[{"field": "rql", "message": "invalid"}],
        ) from None
    return value.strip()


async def list_filters(
    db: AsyncSession, user: User, project_key: str | None = None
) -> list[SavedFilter]:
    query = select(SavedFilter).where(visible(user))
    if project_key:
        query = query.join(Project, Project.id == SavedFilter.project_id, isouter=True).where(
            or_(
                SavedFilter.visibility != FilterVisibility.project,
                Project.key == project_key,
            )
        )
    return list(
        await db.scalars(query.order_by(SavedFilter.visibility, func.lower(SavedFilter.name)))
    )


async def get_filter(db: AsyncSession, user: User, filter_id: uuid.UUID) -> SavedFilter:
    row = await db.scalar(select(SavedFilter).where(SavedFilter.id == filter_id, visible(user)))
    if row is None:
        raise NotFound(f"Filter {filter_id} not found.", code="filter_not_found")
    return row


async def find_by_name(db: AsyncSession, user: User, name: str) -> SavedFilter | None:
    """Own filters win over shared ones with the same name."""
    rows = await db.scalars(
        select(SavedFilter)
        .where(visible(user), func.lower(SavedFilter.name) == name.strip().lower())
        .order_by((SavedFilter.owner_id != user.id), SavedFilter.created_at)
    )
    return rows.first()


async def _project_for(
    db: AsyncSession, user: User, visibility: FilterVisibility, project: str | None
) -> uuid.UUID | None:
    if visibility is not FilterVisibility.project:
        return None
    if not project:
        raise ValidationFailed(
            "Project filters need `project`.", errors=[{"field": "project", "message": "required"}]
        )
    return (await project_access(db, user, project)).project.id


async def create_filter(
    db: AsyncSession,
    user: User,
    *,
    name: str,
    rql: str,
    visibility: FilterVisibility = FilterVisibility.private,
    project: str | None = None,
) -> SavedFilter:
    if visibility is FilterVisibility.instance and not user.is_instance_admin:
        raise Forbidden("Only instance admins can share filters with the whole instance.")
    row = SavedFilter(
        owner_id=user.id,
        name=_name(name),
        rql=_rql(rql),
        visibility=visibility,
        project_id=await _project_for(db, user, visibility, project),
    )
    taken = await db.scalar(
        select(SavedFilter.id).where(
            SavedFilter.owner_id == user.id, func.lower(SavedFilter.name) == row.name.lower()
        )
    )
    if taken:
        raise Conflict(f"You already have a filter called '{row.name}'.", code="duplicate_name")
    db.add(row)
    await db.flush()
    await db.refresh(row, ["owner"])
    return row


async def update_filter(
    db: AsyncSession,
    user: User,
    row: SavedFilter,
    *,
    name: str | None = None,
    rql: str | None = None,
    visibility: FilterVisibility | None = None,
    project: str | None = None,
) -> SavedFilter:
    if row.owner_id != user.id:
        raise Forbidden("Only the owner edits a filter; duplicate it to change it.")
    if name is not None:
        row.name = _name(name)
    if rql is not None:
        row.rql = _rql(rql)
    if visibility is not None:
        if visibility is FilterVisibility.instance and not user.is_instance_admin:
            raise Forbidden("Only instance admins can share filters with the whole instance.")
        row.visibility = visibility
        row.project_id = await _project_for(db, user, visibility, project)
    row.updated_at = utcnow()
    await db.flush()
    return row


async def delete_filter(db: AsyncSession, user: User, row: SavedFilter) -> None:
    if row.owner_id != user.id:
        raise Forbidden("Only the owner deletes a filter.")
    await db.delete(row)
    await db.flush()


def referenced(node: ast.Node | None) -> list[tuple[str, int]]:
    """Names used in `filter = "<name>"` clauses, with their positions."""
    if node is None:
        return []
    if isinstance(node, ast.And | ast.Or):
        return [r for item in node.items for r in referenced(item)]
    if isinstance(node, ast.Not):
        return referenced(node.item)
    if isinstance(node, ast.Compare) and node.field.lower() == "filter":
        return [(node.value.text.strip(), node.value.pos)]
    if isinstance(node, ast.InList) and node.field.lower() == "filter":
        return [(v.text.strip(), v.pos) for v in node.values]
    return []


async def expand(db: AsyncSession, user: User, query: ast.Query) -> dict[str, ast.Node | None]:
    """Every saved filter the query refers to (also inside other filters), by lowercase
    name. Unknown names map to None; a filter that refers to itself is an error."""
    found: dict[str, ast.Node | None] = {}

    async def visit(node: ast.Node | None, chain: tuple[str, ...]) -> None:
        for name, position in referenced(node):
            key = name.lower()
            if key in chain:
                raise RQLError(
                    f"Filter '{name}' refers to itself (at {position}).", position=position
                )
            if len(chain) >= MAX_DEPTH:
                raise RQLError(f"Filters nest too deep (at {position}).", position=position)
            if key in found:
                continue
            row = await find_by_name(db, user, name)
            if row is None:
                found[key] = None
                continue
            where = parse(row.rql).where
            found[key] = where
            await visit(where, (*chain, key))

    await visit(query.where, ())
    return found
