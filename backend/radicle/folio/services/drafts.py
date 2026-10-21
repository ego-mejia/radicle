"""Drafts (Folio 1.2): the live content of a page or blog post, saved as you type. The web
editor sends TipTap JSON; agents and imports send Markdown. Publishing (1.3) turns a draft
into an immutable version."""

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioDraft, FolioNode, FolioNodeEvent, NodeKind
from radicle.folio.services import access, collab, comments, convert, nodes, schema, ydoc
from radicle.folio.services.parse_markdown import from_markdown
from radicle.platform.db.models import User, utcnow
from radicle.platform.errors import ValidationFailed

# Saves closer than this to the same person's last one belong to the same editing session
# and add no new history entry.
SESSION = timedelta(minutes=10)
MAX_METADATA_KEYS = 50


@dataclass(frozen=True)
class Draft:
    content_json: dict[str, Any]
    metadata: dict[str, Any]
    exists: bool
    draft: FolioDraft | None

    @property
    def content_md(self) -> str:
        return convert.to_markdown(self.content_json)


def _invalid(field: str, message: str) -> ValidationFailed:
    return ValidationFailed(message, errors=[{"field": field, "message": "invalid"}])


def _require_content(node: FolioNode) -> None:
    if node.kind == NodeKind.folder:
        raise _invalid("node", "Folders have no content; write in a page or blog post.")


async def get_draft(db: AsyncSession, node: FolioNode) -> Draft:
    """The node's draft, or an empty one if nobody has written yet."""
    _require_content(node)
    row = await db.get(FolioDraft, node.id)
    if row is None:
        return Draft(schema.empty(), {}, exists=False, draft=None)
    return Draft(row.content_json, row.metadata_, exists=True, draft=row)


def _metadata(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _invalid("metadata", "metadata must be an object")
    if len(value) > MAX_METADATA_KEYS:
        raise _invalid("metadata", f"metadata has at most {MAX_METADATA_KEYS} fields")
    return value


async def _new_session(db: AsyncSession, node: FolioNode, user: User) -> bool:
    last = await db.scalar(
        select(FolioNodeEvent)
        .where(FolioNodeEvent.node_id == node.id, FolioNodeEvent.event_type == "draft_saved")
        .order_by(FolioNodeEvent.id.desc())
        .limit(1)
    )
    return last is None or last.actor_id != user.id or utcnow() - last.created_at > SESSION


async def save_draft(
    db: AsyncSession,
    user: User,
    node: FolioNode,
    *,
    content_json: dict[str, Any] | None = None,
    content_md: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Draft:
    """Replace the content (JSON or Markdown, not both) and/or the metadata."""
    await access.require_edit(db, user, node)
    _require_content(node)
    if content_json is not None and content_md is not None:
        raise _invalid("content_md", "Send content_json or content_md, not both.")
    row = await db.get(FolioDraft, node.id)
    if row is None:
        row = FolioDraft(node_id=node.id, content_json=schema.empty(), metadata_={})
        db.add(row)
    content = None
    if content_json is not None:
        content = schema.validate(content_json)
    elif content_md is not None:
        content = from_markdown(content_md)
    if content is not None:
        # Through the Y.Doc, so whoever is editing sees it arrive (Folio 2.2).
        await db.flush()
        await collab.apply_change(
            db, node, user, lambda doc: ydoc.write(ydoc.fragment(doc), content)
        )
        row.content_json = content
    if metadata is not None:
        row.metadata_ = _metadata(metadata)
    row.updated_by = user.id
    row.updated_at = utcnow()
    if await _new_session(db, node, user):
        nodes.record(db, node, user, "draft_saved")
    await db.flush()
    if content_json is not None or content_md is not None:
        await comments.reanchor(db, node, row.content_json)
    return Draft(row.content_json, row.metadata_, exists=True, draft=row)
