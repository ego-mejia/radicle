"""Keeping docs alive (Folio 2.7): status (published, in review, verified, outdated), the
verification that expires after the space's verify_days, and transferring the owner.

A daily job turns expired Verified pages Outdated and tells their owner.
"""

from datetime import date, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioNode, FolioSpace, NodeKind, NodeStatus
from radicle.folio.services import access, publishing, rag
from radicle.folio.services.metadata import validate_metadata
from radicle.folio.services.nodes import record
from radicle.platform.config import get_settings
from radicle.platform.db.models import OutboxEvent, User, utcnow
from radicle.platform.errors import Conflict, Forbidden, ValidationFailed
from radicle.platform.services import events, queue

OUTDATE_JOB = "folio_outdate"
SETTABLE = (NodeStatus.published, NodeStatus.in_review, NodeStatus.verified)


def today() -> date:
    return utcnow().astimezone(ZoneInfo(get_settings().timezone)).date()


async def _owner(db: AsyncSession, node: FolioNode) -> str | None:
    version = await publishing.current_version(db, node)
    owner = version.metadata_.get("owner") if version else None
    return str(owner) if owner else None


async def _require_owner_or_admin(db: AsyncSession, user: User, node: FolioNode) -> FolioSpace:
    space = await db.get(FolioSpace, node.space_id)
    if space is None:  # pragma: no cover - a node always has its space
        raise Conflict("The page has no space.")
    is_admin = "admin" in await access.space_permissions(db, user, space)
    if not is_admin and await _owner(db, node) != user.handle.lower():
        raise Forbidden(
            f"Only the owner of '{node.title}' or an admin of {space.name} can do that.",
            code="owner_only",
        )
    return space


async def set_status(
    db: AsyncSession, user: User, node: FolioNode, status: NodeStatus
) -> FolioNode:
    """Mark a published page in review, verified (until today + verify_days) or back to
    published. Outdated comes only from expiry."""
    if node.kind == NodeKind.live_doc or node.published_version_id is None:
        raise Conflict(
            f"'{node.title}' is not published, so it has no review status yet.",
            code="not_published",
        )
    if status not in SETTABLE:
        valid = ", ".join(s.value for s in SETTABLE)
        raise ValidationFailed(
            f"Status {status.value} can't be set by hand. Use {valid}.",
            errors=[{"field": "status", "message": "not settable"}],
        )
    space = await _require_owner_or_admin(db, user, node)
    before = node.status
    node.status = status
    if status == NodeStatus.verified:
        node.verified_by = user.id
        node.verified_until = today() + timedelta(days=space.verify_days)
    else:
        node.verified_by, node.verified_until = None, None
    record(db, node, user, "status_changed", before=before.value, after=status.value)
    await db.flush()
    await rag.schedule(db, [node.id])  # the status rides in the chunks for search
    return node


async def transfer_owner(db: AsyncSession, user: User, node: FolioNode, owner: str) -> FolioNode:
    """A new version with the same content and the new owner, so the history shows it."""
    await _require_owner_or_admin(db, user, node)
    version = await publishing.current_version(db, node)
    if version is None:
        raise Conflict(
            f"'{node.title}' is not published: set the owner in its draft instead.",
            code="not_published",
        )
    before = version.metadata_.get("owner")
    metadata = await validate_metadata(db, node, version.metadata_ | {"owner": owner})
    await publishing.create_version(
        db,
        node,
        author=user,
        content_json=version.content_json,
        metadata=metadata,
        change_note=f"Owner: @{before} → @{metadata['owner']}",
    )
    record(db, node, user, "owner_transferred", before=before, after=metadata["owner"])
    await db.flush()
    return node


@queue.handler(OUTDATE_JOB)
async def outdate(db: AsyncSession, **_: Any) -> None:
    await outdate_expired(db)


async def outdate_expired(db: AsyncSession) -> int:
    """Verified pages past their date become Outdated; each owner hears about it. Running
    it twice in a day changes nothing the second time."""
    expired = list(
        await db.scalars(
            select(FolioNode)
            .where(
                FolioNode.status == NodeStatus.verified,
                FolioNode.verified_until < today(),
                FolioNode.deleted_at.is_(None),
            )
            .with_for_update(skip_locked=True)
        )
    )
    for node in expired:
        node.status = NodeStatus.outdated
        await events.emit(
            db,
            "folio",
            "page_outdated",
            actor=None,
            payload={"node_id": str(node.id), "until": str(node.verified_until)},
        )
    await db.flush()
    await rag.schedule(db, [n.id for n in expired])
    return len(expired)


@events.resolver("folio", "page_outdated", label="A page you own is outdated")
async def _outdated(db: AsyncSession, event: OutboxEvent) -> list[events.Notice]:
    node = await db.get(FolioNode, event.payload["node_id"])
    handle = await _owner(db, node) if node else None
    owner = await db.scalar(select(User).where(User.handle == handle)) if handle else None
    if node is None or owner is None or not await access.can_view(db, owner, node.id):
        return []
    return [
        events.Notice(
            owner.id,
            "owner",
            f"'{node.title}' is outdated",
            f"Its verification expired on {event.payload['until']}. Review it and verify it again.",
            f"/folio/p/{node.id}-{node.slug}",
            {"page": node.title, "until": str(event.payload["until"])},
        )
    ]
