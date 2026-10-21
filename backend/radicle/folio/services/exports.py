"""Exports (Folio 5.2): a page or a space to PDF, Word, HTML or Markdown.

- Exporting needs the space's `export` permission (admins have it) and sees what its
  author sees: their visible pages, as published. Drafts and pages never published stay out.
- The worker writes the file (`exporting/`) into storage; its author downloads it.
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.exports import ExportFormat, ExportScope, ExportStatus, FolioExport
from radicle.folio.db.models import FolioNode, FolioSpace, NodeKind
from radicle.folio.services import access
from radicle.folio.services.exporting import writers
from radicle.folio.services.exporting.pages import collect
from radicle.platform.db.models import User, utcnow
from radicle.platform.errors import Forbidden, NotFound, ValidationFailed
from radicle.platform.services import queue
from radicle.platform.storage import get_storage

EXPORT_JOB = "folio_export"
READABLE = (NodeKind.page, NodeKind.blog_post)


async def create_export(
    db: AsyncSession, user: User, target: FolioNode | FolioSpace, fmt: ExportFormat
) -> FolioExport:
    space = (
        target if isinstance(target, FolioSpace) else await db.get_one(FolioSpace, target.space_id)
    )
    if "export" not in await access.space_permissions(db, user, space):
        raise Forbidden(
            f"Exporting from {space.name} needs its export permission; ask a space admin.",
            code="export_permission",
        )
    if isinstance(target, FolioNode):
        if target.kind not in READABLE:
            raise ValidationFailed(
                "Only pages and blog posts are exported one by one; export the space instead.",
                errors=[{"field": "node", "message": "not a page"}],
            )
        if target.published_version_id is None:
            raise ValidationFailed(
                "Publish the page first: exports hold the published version.",
                errors=[{"field": "node", "message": "not published"}],
            )
    row = FolioExport(
        format=fmt,
        scope=ExportScope.node if isinstance(target, FolioNode) else ExportScope.space,
        space_id=space.id,
        node_id=target.id if isinstance(target, FolioNode) else None,
        created_by=user.id,
    )
    db.add(row)
    await db.flush()
    await queue.enqueue(db, EXPORT_JOB, export_id=str(row.id))
    return row


async def get_export(db: AsyncSession, user: User, export_id: uuid.UUID) -> FolioExport:
    """Only its author sees an export."""
    row = await db.get(FolioExport, export_id)
    if row is None or row.created_by != user.id:
        raise NotFound("No export with that id among yours.")
    return row


async def list_exports(db: AsyncSession, user: User, limit: int = 20) -> list[FolioExport]:
    rows = await db.scalars(
        select(FolioExport)
        .where(FolioExport.created_by == user.id)
        .order_by(FolioExport.created_at.desc())
        .limit(limit)
    )
    return list(rows)


async def download(db: AsyncSession, user: User, export_id: uuid.UUID) -> tuple[FolioExport, bytes]:
    row = await get_export(db, user, export_id)
    if row.status != ExportStatus.done or row.file_key is None:
        raise ValidationFailed(
            f"This export is {row.status.value}; download it once it is done.",
            errors=[{"field": "status", "message": row.status.value}],
        )
    return row, await get_storage().get(row.file_key)


async def run(db: AsyncSession, row: FolioExport) -> None:
    """Write the file. Failures are reported on the export instead of retried."""
    user = await db.get(User, row.created_by)
    space = await db.get(FolioSpace, row.space_id)
    if user is None or space is None:
        row.status, row.finished_at = ExportStatus.failed, utcnow()
        row.stats = {"error": "The space or the person who asked for it is gone."}
        return
    row.status = ExportStatus.running
    try:
        pages = await collect(db, user, space, row.node_id)
        if not pages:
            raise ValueError("there is nothing published here that you can see")
        out = await writers.write(db, row, space, pages)
    except Exception as e:  # report it; a retry would fail the same way
        row.status, row.finished_at = ExportStatus.failed, utcnow()
        row.stats = {"error": f"The export stopped: {e}"}
        return
    key = f"folio/exports/{row.id}/{out.filename}"
    await get_storage().put(key, out.data, out.mime_type)
    row.file_key, row.filename = key, out.filename
    row.stats = {"pages": len(pages), "bytes": len(out.data)}
    row.status, row.finished_at = ExportStatus.done, utcnow()


@queue.handler(EXPORT_JOB)
async def run_export(db: AsyncSession, export_id: str, **_: Any) -> None:
    row = await db.get(FolioExport, uuid.UUID(export_id))
    if row is not None and row.status == ExportStatus.queued:
        await run(db, row)
