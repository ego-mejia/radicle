"""Folio's entries in platform's audit log (5.9): permission changes, approvals, public
links, imports and exports, all with app = folio. Use `record` instead of `audit.record`."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.db.models import AuditApp, AuditEntry, User
from radicle.platform.services import audit


def record(
    db: AsyncSession,
    actor: User | None,
    action: str,
    *,
    target_type: str,
    target_id: object = None,
    before: Any = None,
    after: Any = None,
    **extra: Any,
) -> AuditEntry:
    """`action` without its prefix, e.g. "public_link_create" for folio.public_link_create
    (listed in platform's audit.ACTIONS)."""
    return audit.record(
        db,
        actor,
        f"folio.{action}",
        target_type=target_type,
        target_id=target_id,
        before=before,
        after=after,
        app=AuditApp.folio,
        **extra,
    )
