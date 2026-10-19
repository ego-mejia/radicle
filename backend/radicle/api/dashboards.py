from uuid import UUID

from fastapi import APIRouter, Response
from sqlalchemy import select

from radicle.api.deps import AppSettings, CurrentPrincipal, Db
from radicle.api.schemas.common import Page
from radicle.api.schemas.dashboards import (
    DashboardCreate,
    DashboardDetail,
    DashboardOut,
    DashboardPatch,
    WidgetCreate,
    WidgetDataOut,
    WidgetOut,
    WidgetPatch,
    WidgetTicket,
)
from radicle.api.ticket_views import summaries_out
from radicle.db.models import DashboardWidget, Project, User
from radicle.services import dashboards, periods

router = APIRouter(tags=["dashboards"])


async def _out(db: Db, da: dashboards.DashboardAccess) -> DashboardOut:
    d = da.dashboard
    owner = await db.scalar(select(User.handle).where(User.id == d.owner_id))
    return DashboardOut(
        id=str(d.id),
        name=d.name,
        owner=owner or "",
        visibility=d.visibility,
        project=da.project.key if da.project else None,
        is_project_default=d.is_project_default,
        can_edit=da.can_edit,
        updated_at=d.updated_at,
    )


def _widget(w: DashboardWidget) -> WidgetOut:
    return WidgetOut(
        id=str(w.id), widget_type=w.widget_type, title=w.title, config=w.config, layout=w.layout
    )


async def _detail(db: Db, da: dashboards.DashboardAccess) -> DashboardDetail:
    base = await _out(db, da)
    widgets = await dashboards.widgets_of(db, da.dashboard)
    return DashboardDetail(
        **base.model_dump(),
        widgets=[_widget(w) for w in widgets],
        refresh_seconds=dashboards.REFRESH_SECONDS,
    )


@router.get("/dashboards", response_model=Page[DashboardOut])
async def list_dashboards(principal: CurrentPrincipal, db: Db) -> Page[DashboardOut]:
    """Yours, the ones shared with your projects and with the instance."""
    items = []
    for d in await dashboards.list_visible(db, principal.user):
        project = await db.get(Project, d.project_id) if d.project_id else None
        can_edit = await dashboards.can_edit(db, principal.user, d, project)
        items.append(await _out(db, dashboards.DashboardAccess(d, can_edit, project)))
    return Page(items=items)


@router.post("/dashboards", response_model=DashboardDetail, status_code=201)
async def create_dashboard(
    body: DashboardCreate, principal: CurrentPrincipal, db: Db
) -> DashboardDetail:
    d = await dashboards.create(
        db, principal.user, name=body.name, visibility=body.visibility, project=body.project
    )
    return await _detail(db, await dashboards.load(db, principal.user, d.id))


@router.get("/dashboards/{dashboard_id}", response_model=DashboardDetail)
async def get_dashboard(dashboard_id: UUID, principal: CurrentPrincipal, db: Db) -> DashboardDetail:
    return await _detail(db, await dashboards.load(db, principal.user, dashboard_id))


@router.get("/projects/{key}/dashboard", response_model=DashboardDetail)
async def project_dashboard(key: str, principal: CurrentPrincipal, db: Db) -> DashboardDetail:
    """The project's "Summary" dashboard; its admins edit it."""
    return await _detail(db, await dashboards.project_summary(db, principal.user, key))


@router.patch("/dashboards/{dashboard_id}", response_model=DashboardDetail)
async def patch_dashboard(
    dashboard_id: UUID, body: DashboardPatch, principal: CurrentPrincipal, db: Db
) -> DashboardDetail:
    """Rename, share, or move several widgets at once with `layout`."""
    da = await dashboards.load(db, principal.user, dashboard_id, edit=True)
    changes = body.model_dump(exclude_unset=True)
    await dashboards.update(db, principal.user, da, changes)
    return await _detail(db, await dashboards.load(db, principal.user, dashboard_id))


@router.delete("/dashboards/{dashboard_id}", status_code=204)
async def delete_dashboard(dashboard_id: UUID, principal: CurrentPrincipal, db: Db) -> Response:
    da = await dashboards.load(db, principal.user, dashboard_id, edit=True)
    await dashboards.delete(db, da)
    return Response(status_code=204)


@router.post("/dashboards/{dashboard_id}/widgets", response_model=WidgetOut, status_code=201)
async def add_widget(
    dashboard_id: UUID, body: WidgetCreate, principal: CurrentPrincipal, db: Db
) -> WidgetOut:
    da = await dashboards.load(db, principal.user, dashboard_id, edit=True)
    widget = await dashboards.add_widget(
        db,
        da.dashboard,
        kind=body.widget_type,
        title=body.title,
        config=body.config,
        layout=body.layout.model_dump() if body.layout else None,
    )
    return _widget(widget)


@router.patch("/dashboards/{dashboard_id}/widgets/{widget_id}", response_model=WidgetOut)
async def patch_widget(
    dashboard_id: UUID, widget_id: UUID, body: WidgetPatch, principal: CurrentPrincipal, db: Db
) -> WidgetOut:
    da = await dashboards.load(db, principal.user, dashboard_id, edit=True)
    widget = await dashboards.get_widget(db, da.dashboard, widget_id)
    return _widget(
        await dashboards.update_widget(db, widget, body.model_dump(mode="json", exclude_unset=True))
    )


@router.delete("/dashboards/{dashboard_id}/widgets/{widget_id}", status_code=204)
async def delete_widget(
    dashboard_id: UUID, widget_id: UUID, principal: CurrentPrincipal, db: Db
) -> Response:
    da = await dashboards.load(db, principal.user, dashboard_id, edit=True)
    await db.delete(await dashboards.get_widget(db, da.dashboard, widget_id))
    return Response(status_code=204)


@router.get("/widgets/{widget_id}/data", response_model=WidgetDataOut)
async def widget_data(
    widget_id: UUID, principal: CurrentPrincipal, db: Db, settings: AppSettings
) -> WidgetDataOut:
    """Computed with your permissions: a shared widget never shows tickets you cannot see."""
    _, widget = await dashboards.load_widget(db, principal.user, widget_id)
    result = await dashboards.widget_data(
        db,
        principal.user,
        widget,
        today=periods.today(settings.timezone),
        tz=settings.timezone,
        workdays=settings.workdays,
    )
    tickets = None
    if result.total is not None:
        summaries = await summaries_out(db, result.tickets)
        tickets = [
            WidgetTicket(**s.model_dump(), blocked_by=result.blockers.get(t.id, []))
            for t, s in zip(result.tickets, summaries, strict=True)
        ]
    return WidgetDataOut(
        widget_id=str(widget.id),
        widget_type=widget.widget_type,
        data=result.data,
        tickets=tickets,
        total=result.total,
    )
