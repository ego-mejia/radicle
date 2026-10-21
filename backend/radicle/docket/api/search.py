from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from radicle.docket.api.deps import AppSettings, CurrentPrincipal, Db
from radicle.docket.api.schemas.search import (
    FieldInfo,
    ProjectValues,
    SearchFields,
    SearchPage,
    SearchWarningOut,
)
from radicle.docket.api.ticket_views import summaries_out
from radicle.docket.db.models import Area, Milestone, ProjectMember, Status, Ticket, User
from radicle.docket.query.fields import FIELDS, FUNCTIONS, KEYWORDS, SORT_FIELDS, custom_field
from radicle.docket.services import custom_fields, search
from radicle.docket.services.access import project_access

router = APIRouter(tags=["search"])

QueryText = Annotated[
    str,
    Query(
        max_length=2000,
        description="RQL, e.g. `project = PA AND category != done ORDER BY priority DESC`",
    ),
]


@router.get("/tickets", response_model=SearchPage)
async def search_tickets(
    principal: CurrentPrincipal,
    db: Db,
    settings: AppSettings,
    q: QueryText = "",
    limit: Annotated[int, Query(ge=1, le=search.MAX_LIMIT)] = search.DEFAULT_LIMIT,
    cursor: str | None = None,
) -> SearchPage:
    """Search tickets you can see with RQL. Errors point at the character position."""
    result = await search.search(
        db, principal.user, q, limit=limit, cursor=cursor, timezone=settings.timezone
    )
    return SearchPage(
        items=await summaries_out(db, result.tickets, viewer=principal.user),
        total=result.total,
        next_cursor=result.next_cursor,
        warnings=[
            SearchWarningOut(code=w.code, message=w.message, position=w.position)
            for w in result.warnings
        ],
    )


@router.get("/search/fields", response_model=SearchFields)
async def search_fields(
    principal: CurrentPrincipal, db: Db, project: str | None = None
) -> SearchFields:
    """RQL fields and operators; with `project`, also its statuses, areas, people and tags."""
    fields = [
        FieldInfo(
            name=f.name,
            type=f.kind.value,
            operators=list(f.ops),
            supports_in=f.in_list,
            supports_empty=f.empty,
            description=f.description,
            values=list(f.values),
        )
        for f in FIELDS.values()
    ]
    values = None
    if project:
        access = await project_access(db, principal.user, project)
        pid = access.project.id
        statuses = await db.scalars(
            select(Status.name)
            .where(Status.project_id == pid)
            .group_by(Status.name)
            .order_by(func.min(Status.position), Status.name)
        )
        areas = await db.scalars(
            select(Area.name)
            .where(Area.project_id == pid, Area.archived_at.is_(None))
            .order_by(Area.position)
        )
        milestones = await db.scalars(
            select(Milestone.name).where(Milestone.project_id == pid).order_by(Milestone.position)
        )
        handles = await db.scalars(
            select(User.handle)
            .join(ProjectMember, ProjectMember.user_id == User.id)
            .where(ProjectMember.project_id == pid)
            .order_by(User.handle)
        )
        tag = func.unnest(Ticket.tags).label("tag")
        tag_rows = (
            select(tag).where(Ticket.project_id == pid, Ticket.deleted_at.is_(None)).subquery()
        )
        tags = await db.scalars(
            select(tag_rows.c.tag)
            .group_by(tag_rows.c.tag)
            .order_by(func.count().desc(), tag_rows.c.tag)
            .limit(30)
        )
        custom = []
        for d in await custom_fields.list_fields(db, pid):
            f = custom_field(d.key, d.field_type.value)
            custom.append(
                FieldInfo(
                    name=f.name,
                    type=d.field_type.value,
                    operators=list(f.ops),
                    supports_in=f.in_list,
                    supports_empty=f.empty,
                    description=d.name,
                    values=[str(o["value"]) for o in d.options] or list(f.values),
                )
            )
        values = ProjectValues(
            project=access.project.key,
            statuses=list(statuses),
            areas=list(areas),
            milestones=list(milestones),
            handles=list(handles),
            tags=list(tags),
            custom_fields=custom,
        )
    return SearchFields(
        fields=fields,
        sort_fields=list(SORT_FIELDS),
        functions=list(FUNCTIONS),
        keywords=list(KEYWORDS),
        values=values,
    )
