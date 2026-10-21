"""RQL field catalog: types, operators and sort keys. Also feeds autocompletion."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from radicle.platform.query.errors import RQLError, suggest


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
    custom: str | None = None  # custom field type for cf.<key>


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
        Field("start", Kind.date, ("=", *ORDER), empty=True, description="Start date"),
        Field(
            "sprint",
            Kind.name,
            EQ,
            in_list=True,
            empty=True,
            values=("active", "future"),
            description='active, future or a name like "Sprint 4"; EMPTY = in no open sprint',
        ),
        Field("created", Kind.datetime, ("=", *ORDER)),
        Field("updated", Kind.datetime, ("=", *ORDER)),
        Field("resolved", Kind.datetime, ("=", *ORDER)),
        Field("estimate", Kind.number, ("=", *ORDER), empty=True, description="Hours"),
        Field("original_estimate", Kind.number, ("=", *ORDER), empty=True, description="Hours"),
        Field("remaining", Kind.number, ("=", *ORDER), empty=True, description="Hours"),
        Field("spent", Kind.number, ("=", *ORDER), description="Hours logged"),
        Field("votes", Kind.number, ("=", *ORDER), description="🙋 count"),
        Field("blocked", Kind.boolean, ("=",), values=("true", "false")),
        Field(
            "origin",
            Kind.enum,
            EQ,
            in_list=True,
            empty=True,
            values=("team", "user"),
            description="Inbox: team or user (public form)",
        ),
        Field(
            "classification",
            Kind.enum,
            EQ,
            in_list=True,
            empty=True,
            values=("idea", "experiment", "complaint", "suggestion"),
        ),
        Field("impact", Kind.number, ("=", *ORDER), empty=True, description="Inbox, 1 to 5"),
        Field("effort", Kind.number, ("=", *ORDER), empty=True, description="Inbox, 1 to 5"),
        Field(
            "converted",
            Kind.boolean,
            ("=",),
            values=("true", "false"),
            description="Came out of the inbox as a task or bug",
        ),
        Field("linked", Kind.key, ("=",), description="Linked in any direction to this key"),
        Field("filter", Kind.name, ("=",), in_list=True, description="A saved filter, by name"),
    )
}

SORT_FIELDS = (
    "created",
    "updated",
    "due",
    "start",
    "priority",
    "rank",
    "key",
    "status",
    "estimate",
    "votes",
    "spent",
    "remaining",
)
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


# Custom field type -> (operators, IN, IS EMPTY).
CUSTOM_OPS: dict[str, tuple[tuple[str, ...], bool, bool]] = {
    "text": (EQ + MATCH, True, True),
    "number": (EQ + ORDER, False, True),
    "date": (EQ + ORDER, False, True),
    "select": (EQ, True, True),
    "checkbox": (EQ, False, False),
    "user": (EQ, True, True),
    "url": (EQ + MATCH, False, True),
}
CUSTOM_PREFIX = "cf."


def custom_field(key: str, field_type: str) -> Field:
    ops, in_list, empty = CUSTOM_OPS[field_type]
    values = ("true", "false") if field_type == "checkbox" else ()
    return Field(
        f"{CUSTOM_PREFIX}{key}",
        Kind.text,
        ops,
        in_list=in_list,
        empty=empty,
        description=f"Custom field ({field_type})",
        values=values,
        custom=field_type,
    )


def lookup(name: str, position: int, custom: Mapping[str, str] | None = None) -> Field:
    if name.lower().startswith(CUSTOM_PREFIX):
        key = name[len(CUSTOM_PREFIX) :].lower()
        known = custom or {}
        if key not in known:
            options = [f"{CUSTOM_PREFIX}{k}" for k in sorted(known)]
            raise RQLError(
                f"Unknown custom field '{name}' at {position}."
                f"{suggest(name, options)} Custom fields: {', '.join(options) or 'none'}.",
                position=position,
                expected=options,
            )
        return custom_field(key, known[key])
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
