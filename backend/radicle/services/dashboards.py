"""Dashboards: a grid of widgets, private, shared with a project or with the instance.
Widget data is always computed with the permissions of whoever is looking."""

import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.core.errors import Conflict, Forbidden, NotFound, ValidationFailed
from radicle.db.models import (
    Dashboard,
    DashboardWidget,
    FilterVisibility,
    LinkType,
    Project,
    ProjectRole,
    Status,
    StatusCategory,
    Ticket,
    TicketLink,
    User,
    utcnow,
)
from radicle.query.errors import RQLError
from radicle.query.parser import parse
from radicle.services import boards, filters, search, sprints
from radicle.services.access import project_access, role_in
from radicle.services.reports import agile, general
from radicle.services.reports import common as report_common
from radicle.services.templates import SYSTEM_USER_ID

NAME_MAX = 120
GRID_COLUMNS = 12
REFRESH_SECONDS = 300

# type -> config keys that must be present
WIDGETS: dict[str, tuple[str, ...]] = {
    "filter_results": (),
    "count": ("rql",),
    "distribution": ("rql", "field"),
    "milestone_progress": ("project", "milestone"),
    "created_vs_resolved": ("rql",),
    "sprint_burndown": ("board",),
    "cumulative_flow": ("board",),
    "blocked_tickets": (),
    "my_tickets": (),
    "markdown": ("text",),
}

SUMMARY_NAME = "Summary"


def summary_widgets(key: str) -> list[tuple[str, str, dict[str, Any], dict[str, int]]]:
    """The default "Summary" of a project (the migration keeps a frozen copy)."""
    base = f"project = {key}"
    return [
        ("count", "Open tickets", {"rql": f"{base} AND category != done"}, _at(0, 0, 3, 3)),
        (
            "count",
            "Blocked",
            {"rql": f"{base} AND blocked = true AND category != done"},
            _at(3, 0, 3, 3),
        ),
        ("created_vs_resolved", "Created vs resolved", {"rql": base, "days": 30}, _at(6, 0, 6, 6)),
        (
            "distribution",
            "Open by area",
            {"rql": f"{base} AND category != done", "field": "area", "chart": "bar"},
            _at(0, 3, 6, 6),
        ),
        ("blocked_tickets", "Blocked tickets", {"rql": base}, _at(0, 9, 6, 5)),
        ("my_tickets", "My tickets", {}, _at(6, 6, 6, 5)),
    ]


def _at(x: int, y: int, w: int, h: int) -> dict[str, int]:
    return {"x": x, "y": y, "w": w, "h": h}


def _fail(field_name: str, detail: str) -> ValidationFailed:
    return ValidationFailed(detail, errors=[{"field": field_name, "message": "invalid"}])


def _not_found(dashboard_id: object) -> NotFound:
    return NotFound(f"Dashboard {dashboard_id} not found.", code="dashboard_not_found")


def visible(user: User) -> ColumnElement[bool]:
    return or_(
        Dashboard.owner_id == user.id,
        Dashboard.visibility == FilterVisibility.instance,
        (Dashboard.visibility == FilterVisibility.project)
        & Dashboard.project_id.in_(search.visible_project_ids(user)),
    )


# --- access --------------------------------------------------------------------------------


@dataclass
class DashboardAccess:
    dashboard: Dashboard
    can_edit: bool
    project: Project | None


async def can_edit(db: AsyncSession, user: User, d: Dashboard, project: Project | None) -> bool:
    if d.owner_id == user.id:
        return True
    if d.is_project_default and project is not None:
        return user.is_instance_admin or await role_in(db, user, project) is ProjectRole.admin
    return False


async def load(
    db: AsyncSession, user: User, dashboard_id: uuid.UUID, *, edit: bool = False
) -> DashboardAccess:
    d = await db.scalar(select(Dashboard).where(Dashboard.id == dashboard_id, visible(user)))
    if d is None:
        raise _not_found(dashboard_id)
    project = await db.get(Project, d.project_id) if d.project_id else None
    editable = await can_edit(db, user, d, project)
    if edit and not editable:
        who = "its project's admins" if d.is_project_default else "its owner"
        raise Forbidden(f"Only {who} can change the dashboard '{d.name}'.")
    if edit and project is not None and project.archived_at is not None:
        raise Forbidden(f"Project {project.key} is archived: its dashboards are read-only.")
    return DashboardAccess(d, editable, project)


async def list_visible(db: AsyncSession, user: User) -> list[Dashboard]:
    rows = await db.scalars(
        select(Dashboard)
        .where(visible(user))
        .order_by(Dashboard.is_project_default, func.lower(Dashboard.name))
    )
    return list(rows)


async def project_summary(db: AsyncSession, user: User, project_key: str) -> DashboardAccess:
    access = await project_access(db, user, project_key)
    d = await db.scalar(
        select(Dashboard).where(
            Dashboard.project_id == access.project.id, Dashboard.is_project_default.is_(True)
        )
    )
    if d is None:  # pragma: no cover - created with every project
        raise _not_found(project_key)
    return DashboardAccess(d, await can_edit(db, user, d, access.project), access.project)


# --- changes -------------------------------------------------------------------------------


def _name(value: str) -> str:
    name = " ".join(value.split())
    if not 1 <= len(name) <= NAME_MAX:
        raise _fail("name", f"Dashboard names are 1 to {NAME_MAX} characters.")
    return name


async def _sharing(
    db: AsyncSession, user: User, visibility: FilterVisibility, project: str | None
) -> uuid.UUID | None:
    if visibility is FilterVisibility.instance and not user.is_instance_admin:
        raise Forbidden("Only instance admins can share dashboards with the whole instance.")
    if visibility is not FilterVisibility.project:
        return None
    if not project:
        raise _fail("project", "Dashboards shared with a project need `project`.")
    return (await project_access(db, user, project)).project.id


async def create(
    db: AsyncSession,
    user: User,
    *,
    name: str,
    visibility: FilterVisibility = FilterVisibility.private,
    project: str | None = None,
) -> Dashboard:
    d = Dashboard(
        owner_id=user.id,
        name=_name(name),
        visibility=visibility,
        project_id=await _sharing(db, user, visibility, project),
        is_project_default=False,
    )
    db.add(d)
    await db.flush()
    return d


async def create_project_summary(db: AsyncSession, project: Project) -> Dashboard:
    d = Dashboard(
        owner_id=SYSTEM_USER_ID,
        name=SUMMARY_NAME,
        visibility=FilterVisibility.project,
        project_id=project.id,
        is_project_default=True,
    )
    db.add(d)
    await db.flush()
    for kind, title, config, layout in summary_widgets(project.key):
        db.add(
            DashboardWidget(
                dashboard_id=d.id, widget_type=kind, title=title, config=config, layout=layout
            )
        )
    await db.flush()
    return d


async def update(
    db: AsyncSession, user: User, da: DashboardAccess, changes: dict[str, Any]
) -> Dashboard:
    d = da.dashboard
    if "name" in changes and changes["name"] is not None:
        d.name = _name(changes["name"])
    if "visibility" in changes and changes["visibility"] is not None:
        if d.is_project_default:
            raise Conflict("A project's Summary is always shared with the project.")
        visibility = FilterVisibility(changes["visibility"])
        d.project_id = await _sharing(db, user, visibility, changes.get("project"))
        d.visibility = visibility
    if changes.get("layout") is not None:
        widgets = {w.id: w for w in await widgets_of(db, d)}
        for item in changes["layout"]:
            widget = widgets.get(uuid.UUID(str(item["id"])))
            if widget is None:
                raise _fail("layout", f"Widget {item['id']} is not on this dashboard.")
            widget.layout = _layout(item)
    d.updated_at = utcnow()
    await db.flush()
    return d


async def delete(db: AsyncSession, da: DashboardAccess) -> None:
    if da.dashboard.is_project_default:
        raise Conflict("A project's Summary cannot be deleted; edit its widgets instead.")
    await db.delete(da.dashboard)
    await db.flush()


async def widgets_of(db: AsyncSession, d: Dashboard) -> list[DashboardWidget]:
    rows = await db.scalars(select(DashboardWidget).where(DashboardWidget.dashboard_id == d.id))
    return sorted(rows, key=lambda w: (w.layout.get("y", 0), w.layout.get("x", 0)))


def _layout(raw: dict[str, Any]) -> dict[str, int]:
    try:
        x, y, w, h = (int(raw[k]) for k in ("x", "y", "w", "h"))
    except (KeyError, TypeError, ValueError):
        raise _fail("layout", "A layout is {x, y, w, h} in grid units.") from None
    if not (0 <= x < GRID_COLUMNS and 1 <= w <= GRID_COLUMNS and x + w <= GRID_COLUMNS):
        raise _fail("layout", f"Widgets fit in {GRID_COLUMNS} columns: 0 <= x and x + w <= 12.")
    if not (0 <= y and 1 <= h <= 24):
        raise _fail("layout", "Height is 1 to 24 rows and y cannot be negative.")
    return {"x": x, "y": y, "w": w, "h": h}


def _config(kind: str, config: dict[str, Any]) -> dict[str, Any]:
    if kind not in WIDGETS:
        raise _fail("widget_type", f"Unknown widget '{kind}'. Widgets: {', '.join(WIDGETS)}.")
    missing = [k for k in WIDGETS[kind] if not config.get(k)]
    if missing:
        raise _fail("config", f"The {kind} widget needs {', '.join(missing)} in its config.")
    if kind == "filter_results" and not (config.get("rql") or config.get("filter")):
        raise _fail("config", "The filter_results widget needs a saved `filter` or an `rql`.")
    if config.get("rql"):
        try:
            parse(str(config["rql"]))
        except RQLError as exc:
            raise _fail("config", f"The widget's RQL is not valid: {exc.detail}") from None
    if kind == "distribution" and config["field"] not in general.DISTRIBUTION_FIELDS:
        if not str(config["field"]).startswith("cf."):
            raise _fail("config", f"Distribution fields: {', '.join(general.DISTRIBUTION_FIELDS)}.")
    return config


async def add_widget(
    db: AsyncSession,
    d: Dashboard,
    *,
    kind: str,
    title: str,
    config: dict[str, Any],
    layout: dict[str, Any] | None,
) -> DashboardWidget:
    if layout is None:
        bottom = max(
            (w.layout.get("y", 0) + w.layout.get("h", 0) for w in await widgets_of(db, d)),
            default=0,
        )
        layout = _at(0, bottom, 6, 4)
    widget = DashboardWidget(
        dashboard_id=d.id,
        widget_type=kind,
        title=_name(title),
        config=_config(kind, config),
        layout=_layout(layout),
    )
    db.add(widget)
    d.updated_at = utcnow()
    await db.flush()
    return widget


async def get_widget(db: AsyncSession, d: Dashboard, widget_id: uuid.UUID) -> DashboardWidget:
    widget = await db.get(DashboardWidget, widget_id)
    if widget is None or widget.dashboard_id != d.id:
        raise NotFound(f"Widget {widget_id} not found.", code="widget_not_found")
    return widget


async def update_widget(
    db: AsyncSession, widget: DashboardWidget, changes: dict[str, Any]
) -> DashboardWidget:
    if changes.get("title") is not None:
        widget.title = _name(changes["title"])
    if changes.get("config") is not None:
        widget.config = _config(widget.widget_type, changes["config"])
    if changes.get("layout") is not None:
        widget.layout = _layout(changes["layout"])
    await db.flush()
    return widget


# --- data ----------------------------------------------------------------------------------


@dataclass
class WidgetData:
    """`data` is JSON-ready; `tickets` are turned into summaries by the API."""

    data: dict[str, Any] = field(default_factory=dict)
    tickets: list[Ticket] = field(default_factory=list)
    total: int | None = None
    blockers: dict[uuid.UUID, list[str]] = field(default_factory=dict)


async def _where(db: AsyncSession, user: User, rql: str, tz: str) -> Any:
    return (await search.compile_rql(db, user, rql, timezone=tz)).where


async def load_widget(
    db: AsyncSession, user: User, widget_id: uuid.UUID
) -> tuple[DashboardAccess, DashboardWidget]:
    """A widget of a dashboard the user can see."""
    widget = await db.get(DashboardWidget, widget_id)
    if widget is None:
        raise NotFound(f"Widget {widget_id} not found.", code="widget_not_found")
    try:
        da = await load(db, user, widget.dashboard_id)
    except NotFound:
        raise NotFound(f"Widget {widget_id} not found.", code="widget_not_found") from None
    return da, widget


async def widget_data(
    db: AsyncSession, user: User, widget: DashboardWidget, *, today: date, tz: str, workdays: str
) -> WidgetData:
    """Data for one widget, as the viewer sees it: tickets they cannot see never count."""
    c = widget.config
    kind = widget.widget_type
    if kind == "markdown":
        return WidgetData({"text": c.get("text", "")})
    if kind == "count":
        where = await _where(db, user, c["rql"], tz)
        n = await db.scalar(
            select(func.count()).select_from(search.base_query(user).where(where).subquery())
        )
        return WidgetData({"count": int(n or 0), "label": c.get("label")})
    if kind in ("filter_results", "my_tickets"):
        if kind == "my_tickets":
            rql = "assignee = currentUser() AND category != done ORDER BY priority DESC, due ASC"
        elif c.get("filter"):
            saved = await filters.get_filter(db, user, uuid.UUID(str(c["filter"])))
            rql = saved.rql
        else:
            rql = str(c["rql"])
        limit = max(1, min(int(c.get("limit", 10)), 50))
        result = await search.search(db, user, rql, limit=limit, timezone=tz)
        return WidgetData(
            {"columns": c.get("columns") or ["key", "title", "status", "assignee"]},
            result.tickets,
            result.total,
        )
    if kind == "blocked_tickets":
        base = f"({c['rql']}) AND " if c.get("rql") else ""
        rql = f"{base}blocked = true AND category != done ORDER BY priority DESC"
        result = await search.search(db, user, rql, limit=50, timezone=tz)
        return WidgetData(
            {}, result.tickets, result.total, await _blockers(db, user, result.tickets)
        )
    if kind == "distribution":
        where = await _where(db, user, c["rql"], tz)
        r = await general.distribution(db, user, ticket_filter=where, field=c["field"])
        return WidgetData({"rows": r.rows, "chart": c.get("chart", "bar"), "field": c["field"]})
    if kind == "created_vs_resolved":
        days = max(7, min(int(c.get("days", 30)), 365))
        where = await _where(db, user, c["rql"], tz)
        r = await general.created_vs_resolved(
            db,
            user,
            ticket_filter=where,
            start=today - timedelta(days=days - 1),
            end=today,
            interval="day" if days <= 45 else "week",
            tz=tz,
        )
        return WidgetData({"rows": r.rows, "summary": r.summary})
    if kind == "milestone_progress":
        from radicle.services import reports

        r = await reports.run(
            db,
            user,
            "milestone_progress",
            reports.Params(project=str(c["project"]), milestone=str(c["milestone"])),
            today=today,
            tz=tz,
            workdays=workdays,
        )
        return WidgetData({"summary": r.summary})
    ba = await boards.load_board(db, user, uuid.UUID(str(c["board"])))
    if kind == "sprint_burndown":
        sprint = await sprints.active_sprint(db, ba.board)
        if sprint is None:
            return WidgetData({"sprint": None, "rows": []})
        r = await agile.burndown(
            db, user, sprint, today=today, tz=tz, workdays=report_common.parse_workdays(workdays)
        )
        return WidgetData({"sprint": sprint.name, "rows": r.rows, "summary": r.summary})
    days = max(7, min(int(c.get("days", 30)), 365))
    r = await agile.cumulative_flow(
        db,
        user,
        ticket_filter=await _where(db, user, ba.board.source_rql.strip(), tz),
        statuses=await boards.scope_statuses(db, ba.board),
        start=today - timedelta(days=days - 1),
        end=today,
        tz=tz,
    )
    return WidgetData({"rows": r.rows, "summary": r.summary})


async def _blockers(
    db: AsyncSession, user: User, tickets: list[Ticket]
) -> dict[uuid.UUID, list[str]]:
    """Open blockers of each ticket the viewer can see, as keys."""
    if not tickets:
        return {}
    visible_blockers = (
        search.base_query(user)
        .where(Status.category != StatusCategory.done)
        .with_only_columns(Ticket.id, Project.key, Ticket.number)
        .subquery()
    )
    rows = await db.execute(
        select(TicketLink.target_id, visible_blockers.c.key, visible_blockers.c.number)
        .join(visible_blockers, visible_blockers.c.id == TicketLink.source_id)
        .where(
            TicketLink.type == LinkType.blocks,
            TicketLink.target_id.in_([t.id for t in tickets]),
        )
    )
    out: dict[uuid.UUID, list[str]] = {}
    for target, key, number in rows:
        out.setdefault(target, []).append(f"{key}-{number}")
    return out
