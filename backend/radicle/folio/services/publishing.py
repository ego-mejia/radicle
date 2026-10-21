"""Publishing (Folio 1.3): a draft with complete metadata (rules in `metadata`) becomes
the next immutable version."""

from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import (
    FolioDraft,
    FolioNode,
    FolioNodeLabel,
    FolioVersion,
    NodeKind,
    NodeStatus,
)
from radicle.folio.services import access, comments, convert, nodes, rag, schema
from radicle.folio.services.metadata import validate_metadata
from radicle.platform.db.models import User, UserKind, utcnow
from radicle.platform.errors import Conflict, Forbidden, ValidationFailed


async def current_version(db: AsyncSession, node: FolioNode) -> FolioVersion | None:
    if node.published_version_id is None:
        return None
    return await db.get(FolioVersion, node.published_version_id)


async def _next_number(db: AsyncSession, node: FolioNode) -> int:
    last = await db.scalar(
        select(func.max(FolioVersion.number)).where(FolioVersion.node_id == node.id)
    )
    return int(last or 0) + 1


async def create_version(
    db: AsyncSession,
    node: FolioNode,
    *,
    author: User,
    content_json: dict[str, Any],
    metadata: dict[str, Any],
    change_note: str | None,
    approved_by: User | None = None,
    restored_from: FolioVersion | None = None,
) -> FolioVersion:
    """Write version n + 1 and make it the published one."""
    content = schema.validate(content_json)
    version = FolioVersion(
        node_id=node.id,
        number=await _next_number(db, node),
        title=metadata["title"],
        content_json=content,
        content_md=convert.to_markdown(content),
        content_text=convert.to_text(content),
        metadata_=metadata,
        change_note=(change_note or "").strip() or None,
        author_id=author.id,
        approved_by=approved_by.id if approved_by else None,
        restored_from=restored_from.id if restored_from else None,
    )
    db.add(version)
    await db.flush()
    node.published_version_id = version.id
    await comments.reanchor(db, node, content)
    node.title = metadata["title"]
    node.slug = nodes.slugify(node.title)
    if node.published_at is None:
        node.published_at = utcnow()
    if node.status == NodeStatus.draft:
        node.status = NodeStatus.published
    node.updated_at = utcnow()
    await db.execute(delete(FolioNodeLabel).where(FolioNodeLabel.node_id == node.id))
    db.add_all(FolioNodeLabel(node_id=node.id, label=label) for label in metadata["labels"])
    draft = await db.get(FolioDraft, node.id)
    if draft is not None:
        draft.base_version_id = version.id
    event = "restored" if restored_from else "published"
    nodes.record(db, node, author, event, version=version.number)
    await db.flush()
    await rag.schedule(db, [node.id])
    return version


async def publish(
    db: AsyncSession,
    user: User,
    node: FolioNode,
    *,
    change_note: str | None = None,
    confirm: bool = False,
) -> FolioVersion:
    """Publish the draft. Agents never publish directly: their work goes to approval
    (Folio 1.5). If someone published after this draft started, `confirm` is needed."""
    await access.require_edit(db, user, node)
    if user.kind != UserKind.human:
        raise Forbidden(
            "Agents don't publish directly: send the page for approval and a Folio admin "
            "will publish it.",
            code="agents_need_approval",
        )
    if node.kind == NodeKind.folder:
        raise ValidationFailed(
            "Folders aren't published; publish their pages.",
            errors=[{"field": "node", "message": "folder"}],
        )
    draft = await db.get(FolioDraft, node.id)
    if draft is None:
        raise ValidationFailed(
            "There is no draft to publish. Write the page first (PUT /nodes/{id}/draft).",
            errors=[{"field": "draft", "message": "missing"}],
        )
    metadata = await validate_metadata(db, node, draft.metadata_)
    current = await current_version(db, node)
    if current is not None and draft.base_version_id != current.id and not confirm:
        raise Conflict(
            f"Version {current.number} was published after this draft started. Compare them "
            "and publish again with confirm to replace it.",
            code="published_meanwhile",
            extra={"current_version": current.number},
        )
    return await create_version(
        db,
        node,
        author=user,
        content_json=draft.content_json,
        metadata=metadata,
        change_note=change_note,
    )
