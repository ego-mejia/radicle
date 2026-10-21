"""Imports (Folio 5.3): upload an export into a space, look at its dry run (the tree, who
each author becomes, labels, files and the problems per page), then run it in the worker.
Only the space's admins import into it."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.imports import FolioImport, ImportSource, ImportStatus
from radicle.folio.db.models import FolioSpace
from radicle.folio.services import access
from radicle.folio.services.importing import bundle as uploads
from radicle.folio.services.importing.confluence import read_confluence
from radicle.folio.services.importing.files import read_markdown
from radicle.folio.services.importing.model import Bundle
from radicle.folio.services.importing.notion import read_notion
from radicle.folio.services.importing.word import read_word
from radicle.platform.db.models import User, UserKind
from radicle.platform.errors import Forbidden, NotFound
from radicle.platform.storage import get_storage

READERS = {
    ImportSource.confluence: read_confluence,
    ImportSource.notion: read_notion,
    ImportSource.word: read_word,
    ImportSource.markdown: read_markdown,
}


async def require_import(db: AsyncSession, user: User, space: FolioSpace) -> None:
    if user.kind != UserKind.human or "admin" not in await access.space_permissions(
        db, user, space
    ):
        raise Forbidden(
            f"Only the admins of {space.name} can import into it. Ask one of them, or import "
            "into a space you administer.",
            code="space_admin_only",
        )


async def create(
    db: AsyncSession,
    user: User,
    space: FolioSpace,
    *,
    source: ImportSource,
    filename: str,
    data: bytes,
) -> FolioImport:
    """Keep the upload; nothing is created in the space until the import runs."""
    await require_import(db, user, space)
    uploads.read(filename, data)  # refuse a bad upload now, not in the worker
    item = FolioImport(
        id=uuid.uuid4(),
        source=source,
        target_space_id=space.id,
        filename=filename[:255],
        upload_key="",
        created_by=user.id,
        status=ImportStatus.uploaded,
        options={},
        report={},
        stats={},
    )
    item.upload_key = f"folio-imports/{space.id}/{item.id}/upload"
    await get_storage().put(item.upload_key, data, "application/octet-stream")
    db.add(item)
    await db.flush()
    return item


async def get(db: AsyncSession, user: User, import_id: uuid.UUID) -> FolioImport:
    item = await db.get(FolioImport, import_id)
    space = await db.get(FolioSpace, item.target_space_id) if item else None
    if item is None or space is None:
        raise NotFound("That import doesn't exist. List them with GET /imports.")
    await require_import(db, user, space)
    return item


async def list_imports(db: AsyncSession, user: User, limit: int = 50) -> list[FolioImport]:
    rows = await db.scalars(select(FolioImport).order_by(FolioImport.created_at.desc()).limit(500))
    out = []
    for item in rows:
        space = await db.get(FolioSpace, item.target_space_id)
        if space is not None and "admin" in await access.space_permissions(db, user, space):
            out.append(item)
        if len(out) >= limit:
            break
    return out


async def read_bundle(item: FolioImport) -> Bundle:
    data = await get_storage().get(item.upload_key)
    return READERS[item.source](uploads.read(item.filename, data))
