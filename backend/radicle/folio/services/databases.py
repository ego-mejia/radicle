"""Databases (Folio 3.6): typed columns and saved views, as a node of kind database.

Columns are `{key, name, type, options}`; a key never changes once given, so rows keep
their values when a column is renamed. Changing a column's type converts what it can and
clears the rest, saying how many values were cleared. Views keep their filters and sort;
db_rows applies them on the server. The format is in docs/folio/databases.md.
"""

import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.databases import FolioDatabase, FolioDbRow
from radicle.folio.db.models import FolioNode, NodeKind
from radicle.folio.services import access
from radicle.folio.services.nodes import slugify
from radicle.platform.db.models import User
from radicle.platform.errors import ValidationFailed

TYPES = ("text", "number", "date", "select", "multi_select", "person", "checkbox", "url", "page")
VIEW_KINDS = ("table", "cards", "board")
OPS = ("eq", "neq", "contains", "gt", "gte", "lt", "lte", "empty", "not_empty")
COLORS = ("grey", "blue", "green", "yellow", "red", "purple")
MAX_COLUMNS = 50
MAX_VIEWS = 20
MAX_ROWS = 10_000


def _invalid(field: str, message: str) -> ValidationFailed:
    return ValidationFailed(message, errors=[{"field": field, "message": "invalid"}])


def default_columns() -> list[dict[str, Any]]:
    return [{"key": "name", "name": "Name", "type": "text", "options": {}}]


def default_views() -> list[dict[str, Any]]:
    return [
        {
            "id": "table",
            "name": "Table",
            "kind": "table",
            "group_by": None,
            "filters": [],
            "sort": [],
            "visible_columns": ["name"],
        }
    ]


def _require_database(node: FolioNode) -> None:
    if node.kind != NodeKind.database:
        raise _invalid("node", f"'{node.title}' is not a database.")


async def get_database(db: AsyncSession, node: FolioNode) -> FolioDatabase:
    """The node's columns and views, created with one Name column the first time."""
    _require_database(node)
    found = await db.get(FolioDatabase, node.id)
    if found is None:
        found = FolioDatabase(node_id=node.id, columns=default_columns(), views=default_views())
        db.add(found)
        await db.flush()
    return found


# --- columns and views ---------------------------------------------------------------


def _key(name: str, taken: set[str]) -> str:
    base = slugify(name).replace("-", "_")[:40] or "column"
    key, n = base, 2
    while key in taken:
        key, n = f"{base}_{n}", n + 1
    return key


def _choices(column: dict[str, Any], i: int) -> list[dict[str, str]]:
    raw = (column.get("options") or {}).get("choices", [])
    if not isinstance(raw, list):
        raise _invalid(f"columns.{i}.options", "options.choices is a list of {value, color}.")
    out: list[dict[str, str]] = []
    for choice in raw:
        value = str((choice or {}).get("value", "")).strip()
        color = str((choice or {}).get("color") or "grey")
        if not value or len(value) > 100:
            raise _invalid(f"columns.{i}.options", "Each choice needs a value of 1 to 100 chars.")
        if color not in COLORS:
            raise _invalid(f"columns.{i}.options", f"Choice colors: {', '.join(COLORS)}.")
        if value in {c["value"] for c in out}:
            raise _invalid(f"columns.{i}.options", f"The choice '{value}' is repeated.")
        out.append({"value": value, "color": color})
    return out


def check_columns(
    columns: list[dict[str, Any]], previous: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Columns normalized: new ones get a key from their name; keys never change."""
    if not columns:
        raise _invalid("columns", "A database needs at least one column.")
    if len(columns) > MAX_COLUMNS:
        raise _invalid("columns", f"A database has at most {MAX_COLUMNS} columns.")
    known = {c["key"] for c in previous}
    taken: set[str] = set()
    out = []
    for i, column in enumerate(columns):
        name = str(column.get("name", "")).strip()
        if not name or len(name) > 100:
            raise _invalid(f"columns.{i}.name", "Each column needs a name of 1 to 100 chars.")
        kind = column.get("type")
        if kind not in TYPES:
            raise _invalid(f"columns.{i}.type", f"Column types: {', '.join(TYPES)}.")
        key = column.get("key")
        if key is None:
            key = _key(name, taken | known)
        elif not isinstance(key, str) or not re.fullmatch(r"[a-z0-9_]{1,40}", key):
            raise _invalid(f"columns.{i}.key", "Keys are 1 to 40 lowercase letters, digits or _.")
        if key in taken:
            raise _invalid(f"columns.{i}.key", f"The column key '{key}' is repeated.")
        taken.add(key)
        options: dict[str, Any] = {}
        if kind in ("select", "multi_select"):
            options["choices"] = _choices(column, i)
        out.append({"key": key, "name": name, "type": kind, "options": options})
    return out


def check_views(views: list[dict[str, Any]], columns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not views:
        raise _invalid("views", "A database needs at least one view.")
    if len(views) > MAX_VIEWS:
        raise _invalid("views", f"A database has at most {MAX_VIEWS} views.")
    by_key = {c["key"]: c for c in columns}
    ids: set[str] = set()
    out = []
    for i, view in enumerate(views):
        name = str(view.get("name", "")).strip()
        if not name or len(name) > 100:
            raise _invalid(f"views.{i}.name", "Each view needs a name of 1 to 100 chars.")
        kind = view.get("kind", "table")
        if kind not in VIEW_KINDS:
            raise _invalid(f"views.{i}.kind", f"View kinds: {', '.join(VIEW_KINDS)}.")
        view_id = str(view.get("id") or _key(name, ids))
        if view_id in ids:
            raise _invalid(f"views.{i}.id", f"The view id '{view_id}' is repeated.")
        ids.add(view_id)
        group_by = view.get("group_by")
        if kind == "board":
            if group_by not in by_key or by_key[group_by]["type"] != "select":
                raise _invalid(f"views.{i}.group_by", "A board groups by a select column.")
        elif group_by is not None and group_by not in by_key:
            group_by = None
        filters = []
        for j, f in enumerate(view.get("filters") or []):
            if f.get("column") not in by_key or f.get("op") not in OPS:
                raise _invalid(
                    f"views.{i}.filters.{j}",
                    f"A filter is {{column, op, value}} on a column of this database; ops: "
                    f"{', '.join(OPS)}.",
                )
            filters.append({"column": f["column"], "op": f["op"], "value": f.get("value")})
        sort = []
        for j, s in enumerate(view.get("sort") or []):
            if s.get("column") not in by_key or s.get("direction", "asc") not in ("asc", "desc"):
                raise _invalid(f"views.{i}.sort.{j}", "Sort by a column, asc or desc.")
            sort.append({"column": s["column"], "direction": s.get("direction", "asc")})
        visible = [k for k in view.get("visible_columns") or list(by_key) if k in by_key]
        out.append(
            {
                "id": view_id,
                "name": name,
                "kind": kind,
                "group_by": group_by,
                "filters": filters,
                "sort": sort,
                "visible_columns": visible,
            }
        )
    return out


def convert(value: Any, column: dict[str, Any]) -> Any:
    """A value in the column's new type, or None when it doesn't fit."""
    if value is None:
        return None
    kind = column["type"]
    choices = [c["value"] for c in column["options"].get("choices", [])]
    as_text = ", ".join(map(str, value)) if isinstance(value, list) else str(value)
    try:
        if kind == "text":
            return as_text
        if kind == "number":
            return _number(value)
        if kind == "date":
            return date.fromisoformat(as_text).isoformat()
        if kind == "select":
            return as_text if as_text in choices else None
        if kind == "multi_select":
            items = value if isinstance(value, list) else [as_text]
            kept = [str(v) for v in items if str(v) in choices]
            return kept or None
        if kind == "checkbox":
            return value if isinstance(value, bool) else as_text.lower() in ("true", "yes", "1")
        if kind == "url":
            return as_text if re.match(r"^https?://\S+$", as_text) else None
        if kind in ("person", "page"):
            return as_text if isinstance(value, str) else None
    except ValueError:
        return None
    return None  # pragma: no cover - every type is handled above


def _number(value: Any) -> float | int:
    if isinstance(value, bool):
        raise ValueError("not a number")
    number = float(value)
    return int(number) if number.is_integer() else number


@dataclass(frozen=True)
class SchemaChange:
    database: FolioDatabase
    cleared: int  # values that didn't fit a column's new type or choices


async def update_schema(
    db: AsyncSession,
    user: User,
    node: FolioNode,
    *,
    columns: list[dict[str, Any]] | None = None,
    views: list[dict[str, Any]] | None = None,
) -> SchemaChange:
    await access.require_edit(db, user, node)
    database = await get_database(db, node)
    cleared = 0
    if columns is not None:
        old = {c["key"]: c for c in database.columns}
        new_columns = check_columns(columns, database.columns)
        changed = [
            c
            for c in new_columns
            if c["key"] in old
            and (c["type"] != old[c["key"]]["type"] or c["options"] != old[c["key"]]["options"])
        ]
        kept = {c["key"] for c in new_columns}
        if changed or set(old) - kept:
            for row in await _rows(db, node):
                values = {k: v for k, v in row.values.items() if k in kept}
                for column in changed:
                    before = values.get(column["key"])
                    after = convert(before, column)
                    cleared += before is not None and after is None
                    values[column["key"]] = after
                row.values = {k: v for k, v in values.items() if v is not None}
        database.columns = new_columns
        if views is None:
            views = database.views
    if views is not None:
        database.views = check_views(views, database.columns)
    await db.flush()
    return SchemaChange(database, cleared)


async def _rows(db: AsyncSession, node: FolioNode) -> list[FolioDbRow]:
    found = await db.scalars(
        select(FolioDbRow)
        .where(FolioDbRow.node_id == node.id, FolioDbRow.deleted_at.is_(None))
        .order_by(FolioDbRow.rank, FolioDbRow.id)
    )
    return list(found)
