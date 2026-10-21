"""Reading the audit log: filters, pages and CSV. Project admins see their projects only."""

import base64
import csv
import io
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.docket.core.permissions import admin_project_ids
from radicle.docket.db.models import AuditEntry, Project, User
from radicle.platform.errors import Forbidden, ValidationFailed

PAGE = 50


@dataclass
class Filters:
    actor: str | None = None
    action: str | None = None
    project: str | None = None
    start: date | None = None
    end: date | None = None


def _cursor(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(base64.urlsafe_b64decode(value + "==").decode())
    except ValueError:
        raise ValidationFailed("Invalid cursor.") from None


async def entries(
    db: AsyncSession, user: User, f: Filters, *, cursor: str | None = None, limit: int = PAGE
) -> tuple[list[tuple[AuditEntry, str | None, str | None]], str | None]:
    """Newest first. Instance admins see everything; project admins their projects only."""
    query = (
        select(AuditEntry, User.handle, Project.key)
        .outerjoin(User, User.id == AuditEntry.actor_id)
        .outerjoin(Project, Project.id == AuditEntry.project_id)
    )
    if not user.is_instance_admin:
        admin_of = admin_project_ids(user)
        if not await db.scalar(select(Project.id).where(Project.id.in_(admin_of)).limit(1)):
            raise Forbidden("The audit log is for instance admins and project admins.")
        query = query.where(AuditEntry.project_id.in_(admin_of))
    if f.actor:
        query = query.where(User.handle == f.actor.lstrip("@").lower())
    if f.action:
        query = query.where(
            or_(AuditEntry.action == f.action, AuditEntry.action.startswith(f"{f.action}."))
        )
    if f.project:
        query = query.where(Project.key == f.project.upper())
    if f.start:
        query = query.where(AuditEntry.created_at >= datetime.combine(f.start, datetime.min.time()))
    if f.end:
        query = query.where(
            AuditEntry.created_at < datetime.combine(f.end + timedelta(days=1), datetime.min.time())
        )
    before = _cursor(cursor)
    if before is not None:
        query = query.where(AuditEntry.id < before)
    rows = list((await db.execute(query.order_by(AuditEntry.id.desc()).limit(limit + 1))).all())
    page: list[tuple[AuditEntry, str | None, str | None]] = [(e, h, k) for e, h, k in rows[:limit]]
    next_cursor = (
        base64.urlsafe_b64encode(str(page[-1][0].id).encode()).decode().rstrip("=")
        if len(rows) > limit
        else None
    )
    return page, next_cursor


def to_csv(rows: list[tuple[AuditEntry, str | None, str | None]]) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(
        [
            "id",
            "created_at",
            "actor",
            "actor_kind",
            "action",
            "target_type",
            "target_id",
            "project",
            "ip",
            "user_agent",
            "details",
        ]
    )
    for e, handle, key in rows:
        writer.writerow(
            [
                e.id,
                e.created_at.isoformat(),
                handle or "",
                e.actor_kind,
                e.action,
                e.target_type,
                e.target_id or "",
                key or "",
                e.ip or "",
                e.user_agent or "",
                json.dumps(e.details, ensure_ascii=False),
            ]
        )
    return out.getvalue()
