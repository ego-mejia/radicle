"""Folio's events as they leave Radicle (Folio 5.5, ADR 0042): webhooks, chat channels and
automation rules hear these names. What goes out is ids, title, space, version, status,
link and who acted, never the content."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioNode, FolioSpace
from radicle.folio.services.notices import node_link
from radicle.platform.config import get_settings
from radicle.platform.db.models import OutboxEvent, User
from radicle.platform.services import events
from radicle.platform.services.events import PublicEvent

APP = "folio"
NAMES = {
    "page.published": "A page is published for the first time",
    "page.updated": "A published page gets a new version",
    "page.archived": "A page is archived",
    "page.commented": "Someone comments on a page",
    "page.status_changed": "A page's review status changes",
    "page.outdated": "A verified page turns Outdated",
    "submission.created": "An agent sends a page for approval",
    "submission.decided": "An agent's page is approved or rejected",
}


def register() -> None:
    """Declare Folio's public events (the publishers register on import)."""
    for name, label in NAMES.items():
        events.public_event(name, label)


async def _page(
    db: AsyncSession, event: OutboxEvent
) -> tuple[dict[str, Any], dict[str, str]] | None:
    node = await db.get(FolioNode, uuid.UUID(event.payload["node_id"]))
    if node is None or node.deleted_at is not None:
        return None
    space = await db.get(FolioSpace, node.space_id)
    actor = await db.get(User, event.actor_id) if event.actor_id else None
    data = {
        "page": {
            "id": str(node.id),
            "title": node.title,
            "kind": node.kind.value,
            "space": space.key if space else None,
            "status": node.status.value,
            "url": get_settings().base_url.rstrip("/") + node_link(node),
        },
        "actor": actor.handle if actor else None,
    }
    return data, {"app": APP, "space": space.key if space else ""}


SUMMARIES = {
    "page.published": "{actor} published “{title}” in {space}",
    "page.updated": "{actor} published a new version of “{title}” in {space}",
    "page.archived": "{actor} archived “{title}” in {space}",
    "page.commented": "{actor} commented on “{title}” in {space}",
    "page.status_changed": "“{title}” in {space} is now {after}",
    "page.outdated": "“{title}” in {space} is outdated: its verification expired",
    "submission.created": "{actor} sent “{title}” in {space} for approval",
    "submission.decided": "“{title}” in {space} was {decision}",
}


def _summary(name: str, data: dict[str, Any]) -> str:
    page = data["page"]
    return SUMMARIES[name].format(
        actor=data["actor"] or "Radicle",
        title=page["title"],
        space=page["space"],
        after=data.get("after", ""),
        decision=data.get("decision", ""),
    )


def _one(
    name: str, page: tuple[dict[str, Any], dict[str, str]] | None, **more: Any
) -> list[PublicEvent]:
    if page is None:
        return []
    data, scope = page
    data = data | more
    return [PublicEvent(name, data, scope, _summary(name, data), data["page"]["url"])]


@events.publisher(APP, "page_published")
async def _published(db: AsyncSession, event: OutboxEvent) -> list[PublicEvent]:
    version = int(event.payload["version"])
    name = "page.published" if version == 1 else "page.updated"
    return _one(name, await _page(db, event), version=version, note=event.payload.get("note"))


@events.publisher(APP, "page_archived")
async def _archived(db: AsyncSession, event: OutboxEvent) -> list[PublicEvent]:
    return _one("page.archived", await _page(db, event))


@events.publisher(APP, "comment")
async def _commented(db: AsyncSession, event: OutboxEvent) -> list[PublicEvent]:
    return _one("page.commented", await _page(db, event), comment_id=event.payload["comment_id"])


@events.publisher(APP, "page_status_changed")
async def _status(db: AsyncSession, event: OutboxEvent) -> list[PublicEvent]:
    before, after = event.payload["before"], event.payload["after"]
    return _one("page.status_changed", await _page(db, event), before=before, after=after)


@events.publisher(APP, "page_outdated")
async def _outdated(db: AsyncSession, event: OutboxEvent) -> list[PublicEvent]:
    page = await _page(db, event)
    until = event.payload.get("until")
    return _one("page.outdated", page, verified_until=until) + _one(
        "page.status_changed", page, before="verified", after="outdated"
    )


@events.publisher(APP, "submission_pending")
async def _submitted(db: AsyncSession, event: OutboxEvent) -> list[PublicEvent]:
    submission = event.payload["submission_id"]
    return _one("submission.created", await _page(db, event), submission_id=submission)


@events.publisher(APP, "submission_decided")
async def _decided(db: AsyncSession, event: OutboxEvent) -> list[PublicEvent]:
    return _one(
        "submission.decided",
        await _page(db, event),
        submission_id=event.payload["submission_id"],
        decision=event.payload["decision"],
    )
