from datetime import date
from typing import Any

from fastapi import APIRouter, Query, Response

from radicle.docket.api.deps import CurrentPrincipal, Db
from radicle.docket.api.schemas.common import Output, Page, UtcDatetime
from radicle.docket.services import audit_view

router = APIRouter(tags=["audit"])


class AuditOut(Output):
    id: int
    created_at: UtcDatetime
    actor: str | None
    actor_kind: str
    action: str
    target_type: str
    target_id: str | None
    project: str | None
    details: dict[str, Any]
    ip: str | None
    user_agent: str | None


def _filters(
    actor: str | None, action: str | None, project: str | None, from_: date | None, to: date | None
) -> audit_view.Filters:
    return audit_view.Filters(actor=actor, action=action, project=project, start=from_, end=to)


@router.get("/audit", response_model=Page[AuditOut])
async def list_audit(
    principal: CurrentPrincipal,
    db: Db,
    actor: str | None = Query(default=None, description="Handle"),
    action: str | None = Query(default=None, description="e.g. user.login or a group: user"),
    project: str | None = None,
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = None,
    cursor: str | None = None,
) -> Page[AuditOut]:
    """Newest first. Instance admins see everything; project admins, their projects."""
    rows, next_cursor = await audit_view.entries(
        db, principal.user, _filters(actor, action, project, from_, to), cursor=cursor
    )
    return Page(
        items=[
            AuditOut(
                id=e.id,
                created_at=e.created_at,
                actor=handle,
                actor_kind=e.actor_kind,
                action=e.action,
                target_type=e.target_type,
                target_id=e.target_id,
                project=key,
                details=e.details,
                ip=e.ip,
                user_agent=e.user_agent,
            )
            for e, handle, key in rows
        ],
        next_cursor=next_cursor,
    )


@router.get("/audit.csv", response_class=Response)
async def audit_csv(
    principal: CurrentPrincipal,
    db: Db,
    actor: str | None = None,
    action: str | None = None,
    project: str | None = None,
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = None,
) -> Response:
    """The same filters, every matching entry (up to 50,000)."""
    rows, _ = await audit_view.entries(
        db, principal.user, _filters(actor, action, project, from_, to), limit=50_000
    )
    return Response(
        audit_view.to_csv(rows),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="audit.csv"'},
    )
