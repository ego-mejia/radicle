"""Database rows (Folio 3.6): add, change, move and delete them, checked against their
columns, and the rows a view shows, with its filters and sort applied on the server.

Rows follow the database node: who can see it reads them, who can edit it writes them.
"""

import re
import uuid
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.databases import FolioDatabase, FolioDbRow
from radicle.folio.db.models import FolioNode
from radicle.folio.services import access
from radicle.folio.services.databases import (
    MAX_ROWS,
    _invalid,
    _number,
    _rows,
    get_database,
)
from radicle.platform.db.models import User, utcnow
from radicle.platform.errors import NotFound
from radicle.platform.services import rank

MAX_TEXT = 10_000


async def _value(
    db: AsyncSession, user: User, column: dict[str, Any], value: Any, field: str
) -> Any:
    """The value checked against its column; None clears it."""
    if value is None or value == "" or value == []:
        return None
    kind, name = column["type"], column["name"]
    choices = [c["value"] for c in column["options"].get("choices", [])]
    if kind == "text":
        if not isinstance(value, str) or len(value) > MAX_TEXT:
            raise _invalid(field, f"{name} is text of at most {MAX_TEXT} characters.")
        return value
    if kind == "number":
        try:
            return _number(value)
        except (TypeError, ValueError):
            raise _invalid(field, f"{name} is a number.") from None
    if kind == "date":
        try:
            return date.fromisoformat(str(value)).isoformat()
        except ValueError:
            raise _invalid(field, f"{name} is a date, YYYY-MM-DD.") from None
    if kind == "select":
        if value not in choices:
            raise _invalid(field, f"{name} is one of: {', '.join(choices) or 'no choices yet'}.")
        return value
    if kind == "multi_select":
        if not isinstance(value, list) or any(v not in choices for v in value):
            raise _invalid(field, f"{name} is a list of: {', '.join(choices) or 'no choices'}.")
        return list(dict.fromkeys(value))
    if kind == "checkbox":
        if not isinstance(value, bool):
            raise _invalid(field, f"{name} is true or false.")
        return value
    if kind == "url":
        if not isinstance(value, str) or not re.match(r"^https?://\S+$", value):
            raise _invalid(field, f"{name} is an http or https link.")
        return value
    if kind == "person":
        handle = str(value).strip().lstrip("@").lower()
        person = await db.scalar(select(User).where(User.handle == handle, User.is_active))
        if person is None:
            raise _invalid(field, f"{name} is the handle of an active person; @{handle} isn't.")
        return handle
    try:  # page
        page_id = uuid.UUID(str(value))
    except ValueError:
        raise _invalid(field, f"{name} is a page id.") from None
    if not await access.can_view(db, user, page_id):
        raise _invalid(field, f"{name}: page {page_id} not found.")
    return str(page_id)


async def _values(
    db: AsyncSession, user: User, database: FolioDatabase, values: dict[str, Any]
) -> dict[str, Any]:
    columns = {c["key"]: c for c in database.columns}
    unknown = sorted(set(values) - set(columns))
    if unknown:
        raise _invalid(
            "values",
            f"Unknown columns: {', '.join(unknown)}. Columns: {', '.join(columns)}.",
        )
    return {k: await _value(db, user, columns[k], v, f"values.{k}") for k, v in values.items()}


async def add_row(
    db: AsyncSession,
    user: User,
    node: FolioNode,
    values: dict[str, Any],
    *,
    after: uuid.UUID | None = None,
) -> FolioDbRow:
    await access.require_edit(db, user, node)
    database = await get_database(db, node)
    count = await db.scalar(
        select(func.count())
        .select_from(FolioDbRow)
        .where(FolioDbRow.node_id == node.id, FolioDbRow.deleted_at.is_(None))
    )
    if (count or 0) >= MAX_ROWS:
        raise _invalid("node", f"A database holds at most {MAX_ROWS} rows.")
    clean = {k: v for k, v in (await _values(db, user, database, values)).items() if v is not None}
    row = FolioDbRow(
        node_id=node.id,
        values=clean,
        rank=await _rank_after(db, node, after),
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(row)
    await db.flush()
    return row


async def _rank_after(db: AsyncSession, node: FolioNode, after: uuid.UUID | None) -> str:
    rows = await _rows(db, node)
    if after is None:
        return rank.after(rows[-1].rank if rows else None)
    ranks = [r.rank for r in rows]
    ids = [r.id for r in rows]
    if after not in ids:
        raise _invalid("after", f"Row {after} is not in this database.")
    i = ids.index(after)
    return rank.between(ranks[i], ranks[i + 1] if i + 1 < len(ranks) else None)


async def get_row(db: AsyncSession, user: User, row_id: uuid.UUID) -> tuple[FolioDbRow, FolioNode]:
    row = await db.get(FolioDbRow, row_id)
    node = await db.get(FolioNode, row.node_id) if row else None
    if (
        row is None
        or row.deleted_at is not None
        or node is None
        or not await access.can_view(db, user, node.id)
    ):
        raise NotFound(f"Row {row_id} not found.", code="row_not_found")
    return row, node


async def update_row(
    db: AsyncSession,
    user: User,
    row: FolioDbRow,
    node: FolioNode,
    values: dict[str, Any] | None = None,
    *,
    after: uuid.UUID | None = None,
    to_top: bool = False,
) -> FolioDbRow:
    """Change some values (None clears one) and/or move the row after another."""
    await access.require_edit(db, user, node)
    database = await get_database(db, node)
    if values:
        merged = dict(row.values)
        for key, value in (await _values(db, user, database, values)).items():
            if value is None:
                merged.pop(key, None)
            else:
                merged[key] = value
        row.values = merged
    if after is not None:
        if after == row.id:
            raise _invalid("after", "A row can't go after itself.")
        row.rank = await _rank_after(db, node, after)
    elif to_top:
        rows = await _rows(db, node)
        row.rank = rank.before(rows[0].rank if rows else None)
    row.updated_by, row.updated_at = user.id, utcnow()
    await db.flush()
    return row


async def delete_row(db: AsyncSession, user: User, row: FolioDbRow, node: FolioNode) -> None:
    await access.require_edit(db, user, node)
    row.deleted_at = utcnow()
    await db.flush()


# --- views ---------------------------------------------------------------------------


def _matches(value: Any, op: str, wanted: Any, kind: str) -> bool:
    if op == "empty":
        return value is None
    if op == "not_empty":
        return value is not None
    if value is None:
        return op == "neq"
    if op in ("eq", "neq"):
        same = wanted in value if isinstance(value, list) else value == wanted
        if kind == "text" and isinstance(wanted, str):
            same = str(value).casefold() == wanted.casefold()
        return same if op == "eq" else not same
    if op == "contains":
        if isinstance(value, list):
            return wanted in value
        return str(wanted).casefold() in str(value).casefold()
    try:
        left, right = (_number(value), _number(wanted)) if kind == "number" else (value, wanted)
        return {
            "gt": left > right,
            "gte": left >= right,
            "lt": left < right,
            "lte": left <= right,
        }[op]
    except (TypeError, ValueError):
        return False


def apply_view(
    rows: list[FolioDbRow], view: dict[str, Any], columns: list[dict[str, Any]]
) -> list[FolioDbRow]:
    """The rows the view shows: its filters (all of them), then its sort over the rank."""
    kinds = {c["key"]: c["type"] for c in columns}
    shown = [
        r
        for r in rows
        if all(
            _matches(r.values.get(f["column"]), f["op"], f["value"], kinds[f["column"]])
            for f in view["filters"]
        )
    ]
    for s in reversed(view["sort"]):
        key = s["column"]
        present = [r for r in shown if r.values.get(key) is not None]
        missing = [r for r in shown if r.values.get(key) is None]

        def sort_key(r: FolioDbRow, key: str = key) -> Any:
            v = r.values[key]
            return str(v).casefold() if kinds[key] in ("text", "person", "url") else v

        present.sort(key=sort_key, reverse=s["direction"] == "desc")
        shown = present + missing  # empty values last either way
    return shown


async def query(
    db: AsyncSession, user: User, node: FolioNode, view_id: str | None = None
) -> tuple[FolioDatabase, dict[str, Any], list[FolioDbRow]]:
    """The database, the view (its first one by default) and the rows it shows."""
    if not await access.can_view(db, user, node.id):
        raise NotFound(f"Page {node.id} not found.", code="node_not_found")
    database = await get_database(db, node)
    views = {v["id"]: v for v in database.views}
    if view_id is not None and view_id not in views:
        raise _invalid("view", f"Views of this database: {', '.join(views)}.")
    view = views[view_id] if view_id else database.views[0]
    return database, view, apply_view(await _rows(db, node), view, database.columns)
