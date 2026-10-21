"""Action items (Folio 2.4). The document is the source of truth: each save rebuilds the
node's rows in folio_action_items from its actionItem blocks, by their stable ids. Marking
one done from Mis tareas changes the document (live, if someone has it open).
"""

import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

import pycrdt
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.collab import FolioActionItem
from radicle.folio.db.models import FolioNode
from radicle.folio.services import access, collab, convert, quality, ydoc
from radicle.folio.services.notices import APP, node_link
from radicle.platform.db.models import OutboxEvent, User, utcnow
from radicle.platform.errors import Forbidden, NotFound
from radicle.platform.services import events

Status = Literal["open", "done", "all"]
Bucket = Literal["overdue", "today", "upcoming", "no_date"]


@dataclass(frozen=True)
class Item:
    key: str
    text: str
    assignee: str | None
    due: date | None
    done: bool


def _due(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value)) if value else None
    except ValueError:
        return None


def extract(doc: dict[str, Any] | None) -> list[Item]:
    """The document's action items in order; a repeated id keeps its first block."""
    found: dict[str, Item] = {}

    def walk(node: Any) -> None:
        if not isinstance(node, dict):
            return
        if node.get("type") == "actionItem":
            attrs = node.get("attrs") or {}
            key = str(attrs.get("id") or "")
            if key and key not in found:
                found[key] = Item(
                    key=key,
                    text=convert.inline(node.get("content") or []).strip(),
                    assignee=(str(attrs.get("assignee") or "").lstrip("@").lower() or None),
                    due=_due(attrs.get("due")),
                    done=bool(attrs.get("done")),
                )
            return
        for child in node.get("content") or []:
            walk(child)

    walk(doc)
    return list(found.values())


async def sync(db: AsyncSession, node: FolioNode, doc: dict[str, Any], actor: User | None) -> None:
    """Make the node's rows match its document; a new or changed assignee hears about it."""
    items = extract(doc)
    rows = {
        r.item_key: r
        for r in await db.scalars(select(FolioActionItem).where(FolioActionItem.node_id == node.id))
    }
    handles = {i.assignee for i in items if i.assignee}
    people = {
        u.handle.lower(): u
        for u in await db.scalars(select(User).where(User.handle.in_(handles)))
        if u.is_active
    }
    for item in items:
        assignee = people.get(item.assignee or "")
        row = rows.pop(item.key, None)
        if row is None:
            row = FolioActionItem(node_id=node.id, item_key=item.key, text=item.text)
            db.add(row)
        before = row.assignee_id
        changed = (row.text, row.assignee_id, row.due_date, row.done) != (
            item.text,
            assignee.id if assignee else None,
            item.due,
            item.done,
        )
        row.text, row.due_date, row.done = item.text, item.due, item.done
        row.assignee_id = assignee.id if assignee else None
        if changed:
            row.updated_at = utcnow()
        if assignee is not None and assignee.id != before and not item.done:
            payload = {"node_id": str(node.id), "item_key": item.key, "user_id": str(assignee.id)}
            await events.emit(db, APP, "task_assigned", actor=actor, payload=payload)
    if rows:
        await db.execute(
            delete(FolioActionItem).where(
                FolioActionItem.node_id == node.id,
                FolioActionItem.item_key.in_(list(rows)),
            )
        )
    await db.flush()


@dataclass(frozen=True)
class Task:
    item: FolioActionItem
    node: FolioNode
    bucket: Bucket


def bucket(due: date | None, today: date) -> Bucket:
    if due is None:
        return "no_date"
    if due < today:
        return "overdue"
    return "today" if due == today else "upcoming"


async def my_tasks(db: AsyncSession, user: User, status: Status = "open") -> list[Task]:
    """The user's action items in documents they can see, by due date (no date last)."""
    query = (
        select(FolioActionItem, FolioNode)
        .join(FolioNode, FolioNode.id == FolioActionItem.node_id)
        .where(
            FolioActionItem.assignee_id == user.id,
            FolioNode.archived_at.is_(None),
            await access.node_filter(db, user),
        )
    )
    if status != "all":
        query = query.where(FolioActionItem.done.is_(status == "done"))
    rows = await db.execute(
        query.order_by(
            FolioActionItem.due_date.asc().nulls_last(), FolioNode.title, FolioActionItem.id
        )
    )
    today = quality.today()
    return [Task(i, n, bucket(i.due_date, today)) for i, n in rows.all()]


def _set_done(key: str, done: bool) -> Any:
    """An edit for collab.apply_change: the item's checkbox, wherever it is."""

    def edit(doc: pycrdt.Doc[Any]) -> None:
        def walk(parent: Any) -> bool:
            for child in parent.children:
                if isinstance(child, pycrdt.XmlElement):
                    if child.tag == "actionItem" and child.attributes.get("id") == key:
                        child.attributes["done"] = done
                        return True
                    if walk(child):
                        return True
            return False

        with doc.transaction():
            walk(ydoc.fragment(doc))

    return edit


async def set_done(db: AsyncSession, user: User, item_id: uuid.UUID, done: bool) -> Task:
    """The assignee, or anyone who can edit the page, checks or unchecks an item."""
    item = await db.get(FolioActionItem, item_id)
    node = await db.get(FolioNode, item.node_id) if item else None
    if item is None or node is None or not await access.can_view(db, user, node.id):
        raise NotFound(f"Action item {item_id} not found.", code="action_item_not_found")
    if item.assignee_id != user.id and not await access.may_edit(db, user, node):
        raise Forbidden(
            f"Only the person it's assigned to, or someone who can edit '{node.title}', can "
            "check it off.",
            code="action_item_forbidden",
        )
    await collab.apply_change(db, node, user, _set_done(item.item_key, done))
    item.done = done
    item.updated_at = utcnow()
    await db.flush()
    return Task(item, node, bucket(item.due_date, quality.today()))


@events.resolver(APP, "task_assigned", label="A task is assigned to you")
async def _assigned(db: AsyncSession, event: OutboxEvent) -> list[events.Notice]:
    node = await db.get(FolioNode, uuid.UUID(event.payload["node_id"]))
    user = await db.get(User, uuid.UUID(event.payload["user_id"]))
    if node is None or user is None or not await access.can_view(db, user, node.id):
        return []
    item = await db.scalar(
        select(FolioActionItem).where(
            FolioActionItem.node_id == node.id,
            FolioActionItem.item_key == event.payload["item_key"],
        )
    )
    if item is None or item.assignee_id != user.id:
        return []  # reassigned or removed before the notice went out
    actor = await db.get(User, event.actor_id) if event.actor_id else None
    who = actor.display_name if actor else "Someone"
    due = f" (due {item.due_date.isoformat()})" if item.due_date else ""
    title = f"{who} assigned you a task in '{node.title}'"
    params = {"page": node.title} | ({"actor": actor.display_name} if actor else {})
    return [events.Notice(user.id, "assignee", title, item.text + due, node_link(node), params)]
