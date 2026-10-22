"""The home editor (Folio 3.2): a 12-column grid of blocks that a Folio admin arranges,
previews and publishes. Each publish keeps a row, so any earlier layout can come back.

A layout is {"columns": 12, "blocks": [{"id", "type", "x", "y", "w", "h", "config"}]}.
Blocks and their config:

- featured, announcement: {"node": id or null}; null picks the newest labelled one.
- posts: {"title", "space"?, "label"?, "kind": "posts" | "all", "limit": 1-12}
- query: {"title", "rql", "limit": 1-20}
- for_you, most_read: {"title"?, "limit": 1-12}
- spaces: {"title"?}
- text: {"markdown"} up to 5,000 characters
- search: {} and chat: {} (the docs chat, shown only when it is on: Folio 4.5)
- calendar: {"calendar": id, "view": "month" | "week"} (Folio 5.8)
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.calendars import FolioCalendar
from radicle.folio.db.models import FolioNode
from radicle.folio.db.templates import FolioHomeLayout
from radicle.folio.query.compiler import Context, compile_query
from radicle.platform import authz
from radicle.platform.db.models import User, utcnow
from radicle.platform.errors import Conflict, NotFound, ValidationFailed
from radicle.platform.query.errors import RQLError
from radicle.platform.query.parser import parse

COLUMNS = 12
MAX_BLOCKS = 40
MAX_HEIGHT = 12
MAX_TEXT = 5000
TYPES = (
    "featured",
    "announcement",
    "posts",
    "query",
    "for_you",
    "most_read",
    "spaces",
    "text",
    "search",
    "chat",
    "calendar",
)
LIMITS = {"posts": (6, 12), "query": (6, 20), "for_you": (5, 12), "most_read": (5, 12)}


def _block(id: str, type: str, x: int, y: int, w: int, h: int, **config: Any) -> dict[str, Any]:
    return {"id": id, "type": type, "x": x, "y": y, "w": w, "h": h, "config": config}


# The bento of the approved canvas design.
DEFAULT: dict[str, Any] = {
    "columns": COLUMNS,
    "blocks": [
        _block("featured", "featured", 0, 0, 7, 4, node=None),
        _block("announcement", "announcement", 7, 0, 5, 2, node=None),
        _block(
            "ai-tools",
            "posts",
            7,
            2,
            5,
            2,
            title="AI Tools",
            space="ai-tools",
            label=None,
            kind="all",
            limit=3,
        ),
        _block(
            "latest", "posts", 0, 4, 5, 4, title="", space=None, label=None, kind="posts", limit=6
        ),
        _block("for-you", "for_you", 5, 4, 4, 4, title="", limit=5),
        _block("spaces", "spaces", 9, 4, 3, 4, title=""),
        _block("most-read", "most_read", 0, 8, 6, 4, title="", limit=5),
        _block("chat", "chat", 6, 8, 6, 4),
    ],
}


class _Errors:
    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []

    def add(self, field: str, message: str, **extra: Any) -> None:
        self.items.append({"field": field, "message": message, **extra})


def _int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _text(value: Any, limit: int = 120) -> str:
    return str(value or "").strip()[:limit]


async def _config(
    db: AsyncSession, kind: str, raw: dict[str, Any], where: str, errors: _Errors
) -> dict[str, Any]:
    """The block's config, normalized; problems go to `errors` under `where`."""
    if kind in ("featured", "announcement"):
        node = raw.get("node")
        if node is None:
            return {"node": None}
        try:
            node_id = uuid.UUID(str(node))
        except ValueError:
            errors.add(f"{where}.node", "Pick a published post or page.")
            return {"node": None}
        found = await db.get(FolioNode, node_id)
        if found is None or found.published_version_id is None or found.deleted_at:
            errors.add(f"{where}.node", "That page is not published.")
        return {"node": str(node_id)}
    out: dict[str, Any] = {}
    if kind in LIMITS:
        default, most = LIMITS[kind]
        limit = _int(raw.get("limit", default))
        if limit is None or not 1 <= limit <= most:
            errors.add(f"{where}.limit", f"Show between 1 and {most}.")
            limit = default
        out["limit"] = limit
    if kind in ("posts", "query", "for_you", "most_read", "spaces"):
        out["title"] = _text(raw.get("title"))
    if kind == "posts":
        out["space"] = _text(raw.get("space"), 40).lower() or None
        out["label"] = _text(raw.get("label"), 50).lstrip("#").lower() or None
        out["kind"] = "all" if raw.get("kind") == "all" else "posts"
    elif kind == "query":
        rql = _text(raw.get("rql"), 2000)
        out["rql"] = rql
        if not rql:
            errors.add(f"{where}.rql", "Write the RQL query, e.g. space = ai-tools.")
        else:
            try:
                compile_query(parse(rql), Context(user_id=uuid.uuid4(), now=utcnow()))
            except RQLError as exc:
                errors.add(f"{where}.rql", exc.detail, position=exc.position)
    elif kind == "calendar":
        out["view"] = "week" if raw.get("view") == "week" else "month"
        try:
            calendar_id = uuid.UUID(str(raw.get("calendar")))
        except ValueError:
            errors.add(f"{where}.calendar", "Pick one of the spaces' calendars.")
            return out | {"calendar": None}
        if await db.get(FolioCalendar, calendar_id) is None:
            errors.add(f"{where}.calendar", "That calendar doesn't exist anymore.")
        out["calendar"] = str(calendar_id)
    elif kind == "text":
        markdown = str(raw.get("markdown") or "")
        if len(markdown) > MAX_TEXT:
            errors.add(f"{where}.markdown", f"Text blocks hold up to {MAX_TEXT} characters.")
        out["markdown"] = markdown[:MAX_TEXT]
    return out


async def validate(db: AsyncSession, raw: Any) -> dict[str, Any]:
    """The layout, normalized, or ValidationFailed listing every block that's wrong."""
    errors = _Errors()
    blocks = raw.get("blocks") if isinstance(raw, dict) else None
    if not isinstance(blocks, list):
        raise ValidationFailed(
            'A layout is {"columns": 12, "blocks": [...]}.',
            errors=[{"field": "blocks", "message": "a list of blocks"}],
        )
    if len(blocks) > MAX_BLOCKS:
        errors.add("blocks", f"A home holds up to {MAX_BLOCKS} blocks.")
    seen: set[str] = set()
    out = []
    for i, block in enumerate(blocks[:MAX_BLOCKS]):
        where = f"blocks[{i}]"
        if not isinstance(block, dict):
            errors.add(where, "Each block is an object.")
            continue
        block_id = _text(block.get("id"), 40)
        if not block_id or block_id in seen:
            errors.add(f"{where}.id", "Each block needs its own id.")
        seen.add(block_id)
        kind = block.get("type")
        if kind not in TYPES:
            errors.add(f"{where}.type", f"Unknown block. Use one of: {', '.join(TYPES)}.")
            continue
        x, y, w, h = (_int(block.get(k)) for k in ("x", "y", "w", "h"))
        if x is None or y is None or w is None or h is None:
            errors.add(where, "x, y, w and h are whole numbers.")
            continue
        if not (1 <= w <= COLUMNS and 0 <= x and x + w <= COLUMNS):
            errors.add(where, f"The block must fit in the {COLUMNS} columns.")
        if not (1 <= h <= MAX_HEIGHT and y >= 0):
            errors.add(where, f"A block is 1 to {MAX_HEIGHT} rows tall, from row 0.")
        raw_config = block.get("config") or {}
        if not isinstance(raw_config, dict):
            errors.add(f"{where}.config", "config is an object.")
            raw_config = {}
        config = await _config(db, str(kind), raw_config, f"{where}.config", errors)
        out.append({"id": block_id, "type": kind, "x": x, "y": y, "w": w, "h": h, "config": config})
    if errors.items:
        raise ValidationFailed(
            "The layout has problems: " + "; ".join(e["message"] for e in errors.items[:3]),
            errors=errors.items,
        )
    return {"columns": COLUMNS, "blocks": out}


async def _require_admin(db: AsyncSession, user: User) -> None:
    (await authz.authorize(db, user, "folio", "folio.admin")).raise_if_denied()


async def active(db: AsyncSession) -> dict[str, Any]:
    """The layout readers see: the active published one, else the default bento."""
    row = await db.scalar(select(FolioHomeLayout).where(FolioHomeLayout.is_active.is_(True)))
    return row.layout if row else DEFAULT


async def _draft_row(db: AsyncSession) -> FolioHomeLayout | None:
    found: FolioHomeLayout | None = await db.scalar(
        select(FolioHomeLayout).where(FolioHomeLayout.is_draft.is_(True))
    )
    return found


@dataclass(frozen=True)
class Draft:
    layout: dict[str, Any]
    saved: bool  # False while it is still the published layout, unedited
    updated_at: datetime | None


async def get_draft(db: AsyncSession, user: User) -> Draft:
    await _require_admin(db, user)
    row = await _draft_row(db)
    if row is not None:
        return Draft(row.layout, True, row.created_at)
    return Draft(await active(db), False, None)


async def checked(db: AsyncSession, user: User, raw: Any) -> dict[str, Any]:
    """A layout validated for the preview, without saving it."""
    await _require_admin(db, user)
    return await validate(db, raw)


async def save_draft(db: AsyncSession, user: User, raw: Any) -> Draft:
    await _require_admin(db, user)
    layout = await validate(db, raw)
    row = await _draft_row(db)
    if row is None:
        row = FolioHomeLayout(layout=layout, is_draft=True, created_by=user.id)
        db.add(row)
    else:
        row.layout, row.created_by, row.created_at = layout, user.id, utcnow()
    await db.flush()
    return Draft(layout, True, row.created_at)


async def _publish(db: AsyncSession, user: User, layout: dict[str, Any]) -> FolioHomeLayout:
    await db.execute(
        update(FolioHomeLayout).where(FolioHomeLayout.is_active.is_(True)).values(is_active=False)
    )
    row = FolioHomeLayout(layout=layout, is_active=True, published_at=utcnow(), created_by=user.id)
    db.add(row)
    await db.flush()
    return row


async def publish(db: AsyncSession, user: User) -> FolioHomeLayout:
    """Publish the draft: readers see it from now on, and the draft is done."""
    await _require_admin(db, user)
    draft = await _draft_row(db)
    if draft is None:
        raise Conflict(
            "There is no draft to publish. Change the layout in the editor first.",
            code="no_home_draft",
        )
    layout = await validate(db, draft.layout)  # pages may have gone since it was saved
    await db.delete(draft)
    await db.flush()
    return await _publish(db, user, layout)


async def history(db: AsyncSession, user: User, limit: int = 50) -> list[FolioHomeLayout]:
    await _require_admin(db, user)
    rows = await db.scalars(
        select(FolioHomeLayout)
        .where(FolioHomeLayout.published_at.is_not(None))
        .order_by(FolioHomeLayout.published_at.desc(), FolioHomeLayout.id)
        .limit(limit)
    )
    return list(rows)


async def restore(db: AsyncSession, user: User, layout_id: uuid.UUID) -> FolioHomeLayout:
    """Publish an earlier layout again, as a new row: the history only grows."""
    await _require_admin(db, user)
    old = await db.get(FolioHomeLayout, layout_id)
    if old is None or old.published_at is None:
        raise NotFound(f"Home layout {layout_id} not found.", code="home_layout_not_found")
    return await _publish(db, user, old.layout)
