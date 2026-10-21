"""Folio's notifications (Folio 2.4): which events Folio emits and who hears about each.

Every resolver keeps only people who can still see the page; the event bus then drops
the actor and inactive users (ADR 0038).
"""

import uuid
from collections.abc import Iterable, Iterator
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioNode, FolioRole
from radicle.folio.services import access, roles, social
from radicle.platform.db.models import OutboxEvent, User
from radicle.platform.services import events

APP = "folio"


def node_link(node: FolioNode) -> str:
    return f"/folio/p/{node.id}-{node.slug}"


def mentions(doc: dict[str, Any] | None) -> set[str]:
    """Handles mentioned anywhere in a TipTap document, lowercased."""

    def walk(node: Any) -> Iterator[str]:
        if not isinstance(node, dict):
            return
        if node.get("type") == "mention":
            handle = str((node.get("attrs") or {}).get("handle") or "").lstrip("@").lower()
            if handle:
                yield handle
        for child in node.get("content") or []:
            yield from walk(child)

    return set(walk(doc))


async def _actor_name(db: AsyncSession, event: OutboxEvent) -> str:
    actor = await db.get(User, event.actor_id) if event.actor_id else None
    return actor.display_name if actor else "Someone"


async def _visible(db: AsyncSession, node: FolioNode, user_ids: Iterable[uuid.UUID]) -> list[User]:
    """The users, among these, who can see the node."""
    ids = set(user_ids)
    if not ids:
        return []
    users = await db.scalars(select(User).where(User.id.in_(ids)))
    return [u for u in users if await access.can_view(db, u, node.id)]


async def _node(db: AsyncSession, event: OutboxEvent) -> FolioNode | None:
    node = await db.get(FolioNode, uuid.UUID(event.payload["node_id"]))
    return node if node is not None and node.deleted_at is None else None


async def published(
    db: AsyncSession,
    actor: User,
    node: FolioNode,
    *,
    version: int,
    content: dict[str, Any],
    previous: dict[str, Any] | None,
    change_note: str | None,
) -> None:
    """A version went live: watchers hear about it, and people mentioned for the first
    time in this version are told (mentions while writing a draft wait for this)."""
    payload = {"node_id": str(node.id), "version": version, "note": change_note or ""}
    await events.emit(db, APP, "page_published", actor=actor, payload=payload)
    await mentioned(db, actor, node, mentions(content) - mentions(previous))


async def mentioned(db: AsyncSession, actor: User, node: FolioNode, handles: Iterable[str]) -> None:
    """Tell these people they were mentioned in the page's content. Publishing calls it;
    live docs call it after 10 s without typing (Folio 2.5)."""
    handles = sorted(set(handles))
    if handles:
        payload = {"node_id": str(node.id), "handles": handles}
        await events.emit(db, APP, "page_mention", actor=actor, payload=payload)


async def submission_pending(
    db: AsyncSession, agent: User, node: FolioNode, submission_id: uuid.UUID
) -> None:
    payload = {"node_id": str(node.id), "submission_id": str(submission_id)}
    await events.emit(db, APP, "submission_pending", actor=agent, payload=payload)


@events.resolver(APP, "page_published", label="A page you follow is published")
async def _published(db: AsyncSession, event: OutboxEvent) -> list[events.Notice]:
    node = await _node(db, event)
    if node is None:
        return []
    who = await _actor_name(db, event)
    readers = await _visible(db, node, await social.watchers(db, node, with_space=True))
    note = event.payload.get("note") or ""
    title = f"{who} published '{node.title}' (v{event.payload['version']})"
    return [events.Notice(u.id, "watching", title, note, node_link(node)) for u in readers]


@events.resolver(APP, "page_mention", label="You are mentioned in a page")
async def _mention(db: AsyncSession, event: OutboxEvent) -> list[events.Notice]:
    node = await _node(db, event)
    if node is None:
        return []
    handles = event.payload["handles"]
    ids = await db.scalars(select(User.id).where(User.handle.in_(handles)))
    who = await _actor_name(db, event)
    title = f"{who} mentioned you in '{node.title}'"
    readers = await _visible(db, node, ids)
    return [events.Notice(u.id, "mentioned", title, "", node_link(node)) for u in readers]


@events.resolver(APP, "submission_pending", label="An agent's page waits for approval")
async def _pending(db: AsyncSession, event: OutboxEvent) -> list[events.Notice]:
    node = await _node(db, event)
    if node is None:
        return []
    people = await db.scalars(select(User).where(User.is_active.is_(True)))
    admins = [u.id for u in people if await roles.effective_role(db, u) == FolioRole.admin]
    who = await _actor_name(db, event)
    title = f"{who} sent '{node.title}' for approval"
    readers = await _visible(db, node, admins)
    return [events.Notice(u.id, "folio_admin", title, "", "/folio/approvals") for u in readers]
