"""Audit log: who did what administrative or security action, from where, before and after.
Insert only; a database trigger rejects changes and only the retention job deletes."""

import json
import uuid
from contextvars import ContextVar
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.config import get_settings
from radicle.platform.db.models import AuditApp, AuditEntry, User, utcnow
from radicle.platform.services import queue

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
    "folio.grant_set",
    "folio.grant_remove",
    "folio.space_grants_change",
    "folio.submission_approve",
    "folio.submission_reject",
    "folio.restrictions_change",
    "folio.public_link_create",
    "folio.public_link_revoke",
    "folio.export_create",
    "folio.import_run",
    "webhook.create",
    "webhook.update",
    "webhook.delete",
)
# Actions on what every app shares; the rest belong to the app that records them.
PLATFORM_PREFIXES = ("user.", "token.", "agent.", "group.", "sso.", "settings.", "webhook.")
RETENTION_JOB = "audit_retention"
RETENTION_ROLE = "radicle_audit_retention"

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
    app: AuditApp | None = None,
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
    if app is None:
        app = AuditApp.platform if action.startswith(PLATFORM_PREFIXES) else AuditApp.docket
    entry = AuditEntry(
        app=app,
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
