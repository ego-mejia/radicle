"""Folio's RQL fields: what each one means, its operators and whether it sorts."""

from dataclasses import dataclass
from enum import StrEnum

from radicle.platform.query.errors import RQLError, suggest


class Kind(StrEnum):
    space = "space"
    enum = "enum"
    meta = "meta"  # one value in the published version's metadata
    meta_list = "meta_list"  # one of a list in the published version's metadata
    handle = "handle"
    text = "text"
    fulltext = "fulltext"
    node = "node"
    datetime = "datetime"
    flag = "flag"
    status = "status"
    relation = "relation"  # someone watches or starred it


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
        Field("space", Kind.space, EQ, in_list=True, description="Space key, e.g. ai-tools"),
        Field(
            "kind",
            Kind.enum,
            EQ,
            in_list=True,
            values=("page", "folder", "blog_post", "live_doc", "database"),
        ),
        Field("doc_type", Kind.meta, EQ, in_list=True, empty=True, description="e.g. how-to"),
        Field("label", Kind.meta_list, EQ, in_list=True, empty=True, description="Also #label"),
        Field("owner", Kind.handle, EQ, in_list=True, description="Handle or currentUser()"),
        Field("author", Kind.handle, EQ, in_list=True, description="Who published it"),
        Field("audience", Kind.meta_list, EQ, in_list=True, empty=True),
        Field("language", Kind.meta, EQ, in_list=True, empty=True, description="e.g. es"),
        Field("title", Kind.text, MATCH, description="Title contains"),
        Field("text", Kind.fulltext, MATCH, description="Full text, English and Spanish"),
        Field("parent", Kind.node, ("=",), in_list=True, empty=True, description="Id or prefix"),
        Field("created", Kind.datetime, ("=", *ORDER)),
        Field("updated", Kind.datetime, ("=", *ORDER)),
        Field("published", Kind.datetime, ("=", *ORDER), empty=True),
        Field("archived", Kind.flag, EQ, values=("true", "false"), description="Default false"),
        Field(
            "status",
            Kind.status,
            EQ,
            in_list=True,
            values=("draft", "published", "in_review", "verified", "outdated"),
        ),
        Field("watched_by", Kind.relation, EQ, description="Handle or currentUser()"),
        Field("favorite_of", Kind.relation, EQ, description="Handle or currentUser()"),
        Field(
            "has_open_tasks",
            Kind.flag,
            EQ,
            values=("true", "false"),
            description="Unchecked action items in the page",
        ),
    )
}
ALIASES = {"tag": "label", "type": "doc_type", "labels": "label", "audiences": "audience"}
SORT_FIELDS = ("title", "created", "updated", "published")
METADATA_KEY = {"doc_type": "doc_type", "language": "language", "label": "labels"} | {
    "audience": "audiences"
}


def lookup(name: str, position: int) -> Field:
    key = ALIASES.get(name.lower(), name.lower())
    field = FIELDS.get(key)
    if field is None:
        raise RQLError(
            f"Unknown field '{name}' at {position}.{suggest(name, tuple(FIELDS))} "
            f"Docs fields: {', '.join(FIELDS)}.",
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
