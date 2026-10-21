"""The "list by label" block (Folio 3.4): the published pages with a label that the reader
can see, newest first. It is resolved when someone reads, with their visibility, so the
list never shows a page they can't open."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioNode, FolioNodeLabel, FolioSpace
from radicle.folio.services import access
from radicle.platform.db.models import User
from radicle.platform.errors import ValidationFailed

MAX_LIMIT = 50


@dataclass(frozen=True)
class Listed:
    node: FolioNode
    space: str


async def pages_with_label(
    db: AsyncSession, user: User, label: str, *, space: str | None = None, limit: int = 10
) -> list[Listed]:
    wanted = label.strip().lstrip("#").lower()
    if not wanted:
        raise ValidationFailed(
            "Say which label to list, e.g. onboarding.",
            errors=[{"field": "label", "message": "required"}],
        )
    query = (
        select(FolioNode, FolioSpace.key)
        .join(FolioNodeLabel, FolioNodeLabel.node_id == FolioNode.id)
        .join(FolioSpace, FolioSpace.id == FolioNode.space_id)
        .where(
            FolioNodeLabel.label == wanted,
            FolioNode.published_version_id.is_not(None),
            FolioNode.archived_at.is_(None),
            await access.node_filter(db, user),
        )
    )
    if space:
        query = query.where(FolioSpace.key == space.strip().lower())
    rows = await db.execute(
        query.order_by(FolioNode.published_at.desc(), FolioNode.id).limit(
            min(max(limit, 1), MAX_LIMIT)
        )
    )
    return [Listed(node, key) for node, key in rows.all()]
