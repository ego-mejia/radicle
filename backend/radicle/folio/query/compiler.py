"""Compiles Folio's RQL to SQL over nodes and their published version.

The statement selects from `folio_nodes` outer-joined to the published `folio_versions`,
so metadata fields read the version people see; a node never published has none.
"""

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import (
    ColumnElement,
    Text,
    and_,
    cast,
    exists,
    false,
    func,
    literal_column,
    not_,
    or_,
    select,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import aliased

from radicle.folio.db.models import FolioChunk, FolioNode, FolioSpace, FolioVersion, NodeKind
from radicle.folio.query.fields import (
    METADATA_KEY,
    Field,
    Kind,
    check_empty,
    check_in,
    check_op,
    check_sort,
    lookup,
)
from radicle.platform.db.models import User
from radicle.platform.query import ast
from radicle.platform.query.dates import Clock
from radicle.platform.query.errors import RQLError, suggest

Published = aliased(FolioVersion, name="published")
ID_PREFIX_RE = re.compile(r"^[0-9a-f-]{4,36}$")
_ENGLISH: ColumnElement[Any] = literal_column("'english'::regconfig")
_SPANISH: ColumnElement[Any] = literal_column("'spanish'::regconfig")


@dataclass(frozen=True)
class Context:
    user_id: uuid.UUID
    now: datetime
    tz: ZoneInfo = field(default_factory=lambda: ZoneInfo("UTC"))


@dataclass
class Compiled:
    where: ColumnElement[bool]
    order_by: list[Any]
    # Field names the query uses, so callers can add defaults (archived = false).
    fields: set[str] = field(default_factory=set)


def compile_query(query: ast.Query, ctx: Context) -> Compiled:
    compiler = _Compiler(ctx)
    where = compiler.node(query.where) if query.where is not None else true()
    return Compiled(where=where, order_by=_order_by(query.order), fields=compiler.fields)


def _nn(expr: ColumnElement[bool]) -> ColumnElement[bool]:
    """Never NULL: unknown counts as false."""
    return func.coalesce(expr, false())


def _meta(f: Field) -> Any:
    return Published.metadata_[METADATA_KEY[f.name]]


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class _Compiler:
    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx
        self.clock = Clock(ctx.now, ctx.tz)
        self.fields: set[str] = set()

    def node(self, node: ast.Node) -> ColumnElement[bool]:
        if isinstance(node, ast.And):
            return and_(*(self.node(i) for i in node.items))
        if isinstance(node, ast.Or):
            return or_(*(self.node(i) for i in node.items))
        if isinstance(node, ast.Not):
            return not_(self.node(node.item))
        f = lookup(node.field, node.field_pos)
        self.fields.add(f.name)
        if isinstance(node, ast.IsEmpty):
            check_empty(f, node.field_pos)
            empty = self.empty(f)
            return not_(empty) if node.negated else empty
        if isinstance(node, ast.InList):
            check_in(f, node.field_pos)
            any_match = or_(*(self.equals(f, v) for v in node.values))
            return not_(any_match) if node.negated else any_match
        check_op(f, node.op, node.op_pos)
        if f.kind is Kind.datetime:
            return _nn(self.clock.compare(self.moment(f), node.op, node.value))
        if node.op == "=":
            return self.equals(f, node.value)
        if node.op == "!=":
            return not_(self.equals(f, node.value))
        if node.op in ("~", "!~"):
            matched = self.matches(f, node.value)
            return matched if node.op == "~" else not_(matched)
        raise AssertionError(node.op)  # pragma: no cover - check_op allows no other

    def empty(self, f: Field) -> ColumnElement[bool]:
        if f.kind is Kind.node:
            return FolioNode.parent_id.is_(None)
        if f.kind is Kind.datetime:
            return FolioNode.published_at.is_(None)
        value = _meta(f)
        if f.kind is Kind.meta_list:
            return func.coalesce(func.jsonb_array_length(value), 0) == 0
        return func.coalesce(value.astext, "") == ""

    def equals(self, f: Field, v: ast.Value) -> ColumnElement[bool]:
        text = v.text.strip()
        if f.kind is Kind.space:
            keys = select(FolioSpace.id).where(func.lower(FolioSpace.key) == text.lower())
            return FolioNode.space_id.in_(keys)
        if f.kind is Kind.enum:
            if text.lower() not in f.values:
                raise RQLError(
                    f"'{text}' is not a {f.name} (at {v.pos}).{suggest(text, f.values)} "
                    f"Use {', '.join(f.values)}.",
                    position=v.pos,
                    expected=list(f.values),
                )
            return FolioNode.kind == NodeKind(text.lower())
        if f.kind is Kind.meta:
            return _nn(func.lower(_meta(f).astext) == text.lower())
        if f.kind is Kind.meta_list:
            wanted = text.lstrip("#").lower() if f.name == "label" else text
            return _nn(_meta(f).contains(cast([wanted], JSONB)))
        if f.kind is Kind.handle:
            return self.handle_equals(f, v)
        if f.kind is Kind.flag:
            if text.lower() not in f.values:
                raise RQLError(
                    f"'{text}' is not true or false (at {v.pos}).",
                    position=v.pos,
                    expected=list(f.values),
                )
            archived = FolioNode.archived_at.is_not(None)
            return archived if text.lower() == "true" else not_(archived)
        return self.parent_equals(v)

    def handle_equals(self, f: Field, v: ast.Value) -> ColumnElement[bool]:
        if v.kind == "func":
            if v.raw.lower() != "currentuser()":
                raise RQLError(
                    f"'{v.raw}' is not a person (at {v.pos}). Use a handle or currentUser().",
                    position=v.pos,
                )
            user_id: Any = self.ctx.user_id
        else:
            handle = v.text.strip().lstrip("@").lower()
            user_id = select(User.id).where(User.handle == handle).scalar_subquery()
        if f.name == "author":
            return _nn(Published.author_id == user_id)
        handles = select(User.handle).where(User.id == user_id).scalar_subquery()
        return _nn(Published.metadata_["owner"].astext == handles)

    def parent_equals(self, v: ast.Value) -> ColumnElement[bool]:
        text = v.text.strip().lower()
        if not ID_PREFIX_RE.fullmatch(text):
            raise RQLError(
                f"'{v.text}' is not a node id (at {v.pos}). Use the id or its first "
                "characters, e.g. parent = 9f3c.",
                position=v.pos,
            )
        return _nn(cast(FolioNode.parent_id, Text).startswith(text, autoescape=True))

    def matches(self, f: Field, v: ast.Value) -> ColumnElement[bool]:
        text = v.text.strip()
        if not text:
            raise RQLError(f"Empty search text at {v.pos}.", position=v.pos)
        if f.kind is Kind.text:
            return FolioNode.title.ilike(f"%{_escape_like(text)}%")
        query = func.websearch_to_tsquery(_ENGLISH, text).op("||")(
            func.websearch_to_tsquery(_SPANISH, text)
        )
        return exists().where(
            FolioChunk.node_id == FolioNode.id, FolioChunk.search_vector.op("@@")(query)
        )

    def moment(self, f: Field) -> Any:
        return {
            "created": FolioNode.created_at,
            "updated": FolioNode.updated_at,
            "published": FolioNode.published_at,
        }[f.name]


def _order_by(sorts: tuple[ast.Sort, ...]) -> list[Any]:
    columns = {
        "title": func.lower(FolioNode.title),
        "created": FolioNode.created_at,
        "updated": FolioNode.updated_at,
        "published": FolioNode.published_at,
    }
    order: list[Any] = []
    for s in sorts:
        column = columns[check_sort(s.field, s.pos)]
        order.append(column.desc().nulls_last() if s.descending else column.asc().nulls_last())
    return [*order, FolioNode.updated_at.desc(), FolioNode.id]
