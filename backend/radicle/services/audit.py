"""Audit log: who did what administrative or security action, from where, before and after.
Insert only; a database trigger rejects changes and only the retention job deletes."""

import base64
import csv
import io
import json
import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import and_, delete, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.core.config import get_settings
from radicle.core.errors import Forbidden, ValidationFailed
from radicle.core.permissions import admin_project_ids
from radicle.db.models import AuditEntry, Project, User, utcnow
from radicle.services import queue

ACTIONS = (
    "user.create",
    "user.update",
    "user.deactivate",
    "user.make_admin",
    "user.login",
    "user.login_failed",
    "token.create",
    "token.revoke",
    "agent.create",
    "agent.update",
    "project.create",
    "project.update",
    "project.archive",
    "project.unarchive",
    "member.add",
    "member.remove",
    "member.role_change",
    "group_role.add",
    "group_role.remove",
    "group.create",
    "group.update",
    "group.delete",
    "group.member_add",
    "group.member_remove",
    "permission.change",
    "security_level.create",
    "security_level.update",
    "security_level.delete",
    "ticket.security_change",
    "template.update",
    "workflow.change",
    "inbox.settings_change",
    "sso.create",
    "sso.update",
    "settings.change",
    "ticket.delete",
    "ticket.restore",
    "ticket.move",
    "ticket.bulk_edit",
)
RETENTION_JOB = "audit_retention"
RETENTION_ROLE = "radicle_audit_retention"
PAGE = 50

# Set per request by a middleware: (ip, user agent).
request_info: ContextVar[tuple[str | None, str | None]] = ContextVar(
    "request_info", default=(None, None)
)


class RequestInfoMiddleware:
    """Plain ASGI (streaming-safe): keeps the client IP and user agent for `record`."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        client = scope.get("client")
        agent = next(
            (v.decode("latin-1") for k, v in scope.get("headers", []) if k == b"user-agent"),
            None,
        )
        token = request_info.set((client[0] if client else None, agent))
        try:
            await self.app(scope, receive, send)
        finally:
            request_info.reset(token)


def _json(value: Any) -> Any:
    """JSON-safe copy (UUIDs, dates and enums as text)."""
    return json.loads(json.dumps(value, default=str))


def record(
    db: AsyncSession,
    actor: User | None,
    action: str,
    *,
    target_type: str,
    target_id: object = None,
    project_id: uuid.UUID | None = None,
    before: Any = None,
    after: Any = None,
    **extra: Any,
) -> AuditEntry:
    if action not in ACTIONS:  # pragma: no cover - programming error
        raise ValueError(f"Unknown audit action {action}")
    ip, agent = request_info.get()
    details: dict[str, Any] = {**extra}
    if before is not None:
        details["before"] = before
    if after is not None:
        details["after"] = after
    entry = AuditEntry(
        actor_id=actor.id if actor else None,
        actor_kind=actor.kind.value if actor else "system",
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        project_id=project_id,
        details=_json(details),
        ip=ip,
        user_agent=(agent or "")[:500] or None,
    )
    db.add(entry)
    return entry


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


async def purge(db: AsyncSession, now: datetime | None = None) -> int:
    """Delete entries older than RADICLE_AUDIT_RETENTION_DAYS, as the only role allowed to."""
    cutoff = (now or utcnow()) - timedelta(days=get_settings().audit_retention_days)
    await db.execute(text(f"SET LOCAL ROLE {RETENTION_ROLE}"))
    try:
        result = await db.execute(delete(AuditEntry).where(and_(AuditEntry.created_at < cutoff)))
    finally:
        await db.execute(text("RESET ROLE"))
    return int(result.rowcount or 0)  # type: ignore[attr-defined]


@queue.handler(RETENTION_JOB)
async def audit_retention(db: AsyncSession, **_: Any) -> None:
    await purge(db)
