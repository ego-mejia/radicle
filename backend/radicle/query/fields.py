"""RQL field catalog: types, operators and sort keys. Also feeds autocompletion."""

import difflib
from dataclasses import dataclass
from enum import StrEnum

from radicle.query.errors import RQLError


class Kind(StrEnum):
    key = "key"
    project = "project"
    enum = "enum"
    ordinal = "ordinal"
    name = "name"
    handle = "handle"
    text = "text"
    fulltext = "fulltext"
    date = "date"
    datetime = "datetime"
    number = "number"
    boolean = "boolean"


EQ = ("=", "!=")
ORDER = (">", ">=", "<", "<=")
MATCH = ("~", "!~")


@dataclass(frozen=True)
class Field:
    name: str
    kind: Kind
    ops: tuple[str, ...]
    in_list: bool = False
    empty: bool = False
    description: str = ""
    values: tuple[str, ...] = ()


FIELDS: dict[str, Field] = {
    f.name: f
    for f in (
        Field("project", Kind.project, EQ, in_list=True, description="Project key, e.g. PA"),
        Field("key", Kind.key, EQ, in_list=True, description="Ticket key, e.g. PA-4"),
        Field("type", Kind.enum, EQ, in_list=True, values=("task", "bug", "draft")),
        Field("status", Kind.name, EQ, in_list=True, description="Status name, any type"),
        Field("category", Kind.enum, EQ, in_list=True, values=("todo", "in_progress", "done")),
        Field(
            "resolution",
            Kind.enum,
            EQ,
            in_list=True,
            empty=True,
            values=("done", "wont_do", "duplicate", "cannot_reproduce"),
        ),
        Field(
            "priority",
            Kind.ordinal,
            EQ + ORDER,
            in_list=True,
            values=("highest", "high", "medium", "low", "lowest"),
            description="highest > high > medium > low > lowest",
        ),
        Field("area", Kind.name, EQ, in_list=True, empty=True),
        Field("milestone", Kind.name, EQ, in_list=True, empty=True),
        Field("assignee", Kind.handle, EQ, in_list=True, empty=True),
        Field("collaborator", Kind.handle, EQ),
        Field("reporter", Kind.handle, EQ, in_list=True),
        Field("tag", Kind.text, EQ, in_list=True, description="Also #tag"),
        Field("parent", Kind.key, ("=",), in_list=True, empty=True),
        Field("text", Kind.fulltext, MATCH, description="Full text over title and description"),
        Field("title", Kind.text, MATCH, description="Title contains"),
        Field("due", Kind.date, ("=", *ORDER), empty=True),
        Field("created", Kind.datetime, ("=", *ORDER)),
        Field("updated", Kind.datetime, ("=", *ORDER)),
        Field("resolved", Kind.datetime, ("=", *ORDER)),
        Field("estimate", Kind.number, ("=", *ORDER), empty=True, description="Hours"),
        Field("blocked", Kind.boolean, ("=",), values=("true", "false")),
        Field("linked", Kind.key, ("=",), description="Linked in any direction to this key"),
    )
}

SORT_FIELDS = ("created", "updated", "due", "priority", "rank", "key", "status", "estimate")
FUNCTIONS = ("currentUser()", "now()", "startOfDay()", "startOfWeek()", "startOfMonth()")
KEYWORDS = (
    "AND",
    "OR",
    "NOT",
    "IN",
    "NOT IN",
    "IS EMPTY",
    "IS NOT EMPTY",
    "ORDER BY",
    "ASC",
    "DESC",
)


def suggest(word: str, options: list[str] | tuple[str, ...]) -> str:
    match = difflib.get_close_matches(word.lower(), list(options), n=1, cutoff=0.6)
    return f" Did you mean '{match[0]}'?" if match else ""


def lookup(name: str, position: int) -> Field:
    field = FIELDS.get(name.lower())
    if field is None:
        raise RQLError(
            f"Unknown field '{name}' at {position}.{suggest(name, tuple(FIELDS))}",
            position=position,
            expected=sorted(FIELDS),
        )
    return field


def check_op(field: Field, op: str, position: int) -> None:
    if op not in field.ops:
        raise RQLError(
            f"Operator '{op}' does not work with '{field.name}' at {position}. "
            f"Use {', '.join(field.ops)}.",
            position=position,
            expected=list(field.ops),
        )


def check_in(field: Field, position: int) -> None:
    if not field.in_list:
        raise RQLError(
            f"'{field.name}' does not support IN at {position}. Use {', '.join(field.ops)}.",
            position=position,
        )


def check_empty(field: Field, position: int) -> None:
    if not field.empty:
        raise RQLError(f"'{field.name}' cannot be EMPTY (at {position}).", position=position)


def check_sort(name: str, position: int) -> str:
    value = name.lower()
    if value not in SORT_FIELDS:
        raise RQLError(
            f"Cannot sort by '{name}' at {position}.{suggest(name, SORT_FIELDS)} "
            f"Sortable: {', '.join(SORT_FIELDS)}.",
            position=position,
            expected=list(SORT_FIELDS),
        )
    return value
