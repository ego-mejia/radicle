"""Version history (Folio 1.3): list, read and compare versions, and restore an old one as
a new version. Nothing is ever overwritten."""

import difflib
import json
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioDraft, FolioNode, FolioVersion
from radicle.folio.services import access, publishing
from radicle.platform.db.models import User, UserKind, utcnow
from radicle.platform.errors import Forbidden, NotFound, ValidationFailed


async def list_versions(db: AsyncSession, node: FolioNode) -> list[FolioVersion]:
    """Newest first."""
    rows = await db.scalars(
        select(FolioVersion)
        .where(FolioVersion.node_id == node.id)
        .order_by(FolioVersion.number.desc())
    )
    return list(rows)


async def get_version(db: AsyncSession, node: FolioNode, number: int) -> FolioVersion:
    version = await db.scalar(
        select(FolioVersion).where(FolioVersion.node_id == node.id, FolioVersion.number == number)
    )
    if version is None:
        raise NotFound(
            f"Version {number} of this page doesn't exist. GET /nodes/{{id}}/versions lists them.",
            code="version_not_found",
        )
    return version


@dataclass(frozen=True)
class BlockChange:
    op: Literal["equal", "added", "removed"]
    block: dict[str, Any]


@dataclass(frozen=True)
class FieldChange:
    field: str
    before: Any
    after: Any


@dataclass(frozen=True)
class Diff:
    blocks: list[BlockChange]
    metadata: list[FieldChange]
    title: FieldChange | None


def _key(block: dict[str, Any]) -> str:
    return json.dumps(block, sort_keys=True, ensure_ascii=False)


def diff_versions(old: FolioVersion, new: FolioVersion) -> Diff:
    """Block by block (a changed block shows as removed then added) and field by field."""
    before = old.content_json.get("content", [])
    after = new.content_json.get("content", [])
    matcher = difflib.SequenceMatcher(
        a=[_key(b) for b in before], b=[_key(b) for b in after], autojunk=False
    )
    blocks: list[BlockChange] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            blocks += [BlockChange("equal", b) for b in before[i1:i2]]
            continue
        blocks += [BlockChange("removed", b) for b in before[i1:i2]]
        blocks += [BlockChange("added", b) for b in after[j1:j2]]
    fields = sorted(set(old.metadata_) | set(new.metadata_))
    metadata = [
        FieldChange(f, old.metadata_.get(f), new.metadata_.get(f))
        for f in fields
        if old.metadata_.get(f) != new.metadata_.get(f)
    ]
    title = FieldChange("title", old.title, new.title) if old.title != new.title else None
    return Diff(blocks, metadata, title)


async def restore(
    db: AsyncSession, user: User, node: FolioNode, number: int, *, change_note: str | None = None
) -> FolioVersion:
    """Publish version `number`'s content and metadata again as a new version. The draft
    follows, so the next edit starts from it."""
    await access.require_edit(db, user, node)
    if user.kind != UserKind.human:
        raise Forbidden("Agents can't restore versions.", code="agents_need_approval")
    old = await get_version(db, node, number)
    current = await publishing.current_version(db, node)
    if current is not None and current.id == old.id:
        raise ValidationFailed(
            f"Version {number} is already the published one.",
            errors=[{"field": "number", "message": "current"}],
        )
    version = await publishing.create_version(
        db,
        node,
        author=user,
        content_json=old.content_json,
        metadata=old.metadata_,
        change_note=change_note or f"Restored version {number}",
        restored_from=old,
    )
    draft = await db.get(FolioDraft, node.id)
    if draft is None:
        draft = FolioDraft(node_id=node.id, content_json=old.content_json, metadata_={})
        db.add(draft)
    draft.content_json = old.content_json
    draft.metadata_ = dict(old.metadata_)
    draft.base_version_id = version.id
    draft.updated_by = user.id
    draft.updated_at = utcnow()
    await db.flush()
    return version
