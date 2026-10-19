"""RQL syntax tree to SQLAlchemy. Pure: no database access, so the SQL can be unit tested.

Every clause compiles to an expression that is never NULL, so NOT and != behave the
way people read them: `assignee != luis` includes unassigned tickets.
"""

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import (
    ColumnElement,
    Numeric,
    Select,
    Text,
    and_,
    case,
    exists,
    false,
    func,
    literal,
    literal_column,
    not_,
    or_,
    select,
    true,
)
from sqlalchemy.orm import aliased

from radicle.db.models import (
    PRIORITY_ORDER,
    Area,
    LinkType,
    Milestone,
    Priority,
    Project,
    Sprint,
    SprintState,
    SprintTicket,
    Status,
    StatusCategory,
    Ticket,
    TicketCollaborator,
    TicketLink,
    User,
)
from radicle.query import ast
from radicle.query.errors import RQLError
from radicle.query.fields import Field, Kind, check_empty, check_in, check_op, check_sort, lookup

KEY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9]{1,9})-(\d{1,9})$")
REL_RE = re.compile(r"^([+-])(\d+)([mhdw])$")
UNITS = {"m": "minutes", "h": "hours", "d": "days", "w": "weeks"}
_ENGLISH: ColumnElement[Any] = literal_column("'english'::regconfig")
_SPANISH: ColumnElement[Any] = literal_column("'spanish'::regconfig")


@dataclass(frozen=True)
class Context:
    user_id: uuid.UUID
    now: datetime
    tz: ZoneInfo = field(default_factory=lambda: ZoneInfo("UTC"))
    # cf.<key> -> custom field type of the fields the user can query.
    custom_fields: dict[str, str] = field(default_factory=dict)
    # Saved filters by lowercase name: their where clause, or None when unknown.
    filters: dict[str, "ast.Node | None"] = field(default_factory=dict)


@dataclass
class Compiled:
    where: ColumnElement[bool]
    order_by: list[Any]
    # (kind, value, position) of every name the query refers to, to warn about missing ones.
    references: list[tuple[str, str, int]] = field(default_factory=list)


def compile_query(query: ast.Query, ctx: Context) -> Compiled:
    compiler = _Compiler(ctx)
    where = compiler.node(query.where) if query.where is not None else true()
    return Compiled(where=where, order_by=_order_by(query.order), references=compiler.references)


def _nn(expr: ColumnElement[bool]) -> ColumnElement[bool]:
    """Never NULL: unknown counts as false."""
    return func.coalesce(expr, false())


class _Compiler:
    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx
        self.references: list[tuple[str, str, int]] = []

    # --- structure -------------------------------------------------------------------------

    def node(self, node: ast.Node) -> ColumnElement[bool]:
        if isinstance(node, ast.And):
            return and_(*(self.node(i) for i in node.items))
        if isinstance(node, ast.Or):
            return or_(*(self.node(i) for i in node.items))
        if isinstance(node, ast.Not):
            return not_(self.node(node.item))
        if isinstance(node, ast.IsEmpty):
            f = self.lookup(node.field, node.field_pos)
            check_empty(f, node.field_pos)
            empty: ColumnElement[bool]
            if f.custom:
                empty = not_(Ticket.custom_fields.has_key(_cf_key(f)))
            elif f.name == "sprint":
                empty = not_(exists().where(_open_sprint_row()))
            else:
                empty = _column(f).is_(None)
            return not_(empty) if node.negated else empty
        if isinstance(node, ast.InList):
            f = self.lookup(node.field, node.field_pos)
            check_in(f, node.field_pos)
            matches = [self.equals(f, v) for v in node.values]
            any_match = or_(*matches)
            return not_(any_match) if node.negated else any_match
        f = self.lookup(node.field, node.field_pos)
        check_op(f, node.op, node.op_pos)
        return self.compare(f, node.op, node.value)

    def lookup(self, name: str, position: int) -> Field:
        return lookup(name, position, self.ctx.custom_fields)

    def compare(self, f: Field, op: str, value: ast.Value) -> ColumnElement[bool]:
        if op == "=":
            return self.equals(f, value)
        if op == "!=":
            return not_(self.equals(f, value))
        if op in ("~", "!~"):
            matched = self.matches(f, value)
            return matched if op == "~" else not_(matched)
        return self.ordered(f, op, value)

    # --- equality --------------------------------------------------------------------------

    def equals(self, f: Field, v: ast.Value) -> ColumnElement[bool]:
        text = v.text.strip()
        if f.custom:
            return self.custom_equals(f, v)
        if f.name == "filter":
            node = self.ctx.filters.get(text.lower())
            if node is None:
                self.references.append(("filter", text, v.pos))
                return false()
            return _nn(self.node(node))
        if f.name == "category":
            return _nn(Status.category == StatusCategory(self.enum_value(f, v)))
        if f.kind is Kind.enum:
            return _nn(_column(f) == self.enum_value(f, v))
        if f.kind is Kind.ordinal:
            return _nn(Ticket.priority == Priority(self.enum_value(f, v)))
        if f.name == "project":
            self.references.append(("project", text, v.pos))
            return _nn(Project.key == text)
        if f.name == "status":
            self.references.append(("status", text, v.pos))
            return _nn(func.lower(Status.name) == text.lower())
        if f.name == "sprint":
            return self.sprint_equals(v)
        if f.name in ("area", "milestone"):
            self.references.append((f.name, text, v.pos))
            model = Area if f.name == "area" else Milestone
            ids = select(model.id).where(func.lower(model.name) == text.lower())
            return _nn(_column(f).in_(ids))
        if f.kind is Kind.handle:
            return self.handle_equals(f, v)
        if f.name == "tag":
            return _nn(Ticket.tags.contains([text.lstrip("#").lower()]))
        if f.name == "key":
            project_key, number = self.key(v)
            return _nn(and_(Project.key == project_key, Ticket.number == number))
        if f.name == "parent":
            return _nn(Ticket.parent_id.in_(self.ticket_ids(v)))
        if f.name == "linked":
            other = self.ticket_ids(v)
            return exists().where(
                or_(
                    and_(TicketLink.source_id == Ticket.id, TicketLink.target_id.in_(other)),
                    and_(TicketLink.target_id == Ticket.id, TicketLink.source_id.in_(other)),
                )
            )
        if f.kind is Kind.boolean:
            flag = text.lower()
            if flag not in ("true", "false"):
                raise RQLError(f"'{f.name}' takes true or false (at {v.pos}).", position=v.pos)
            if f.name == "converted":
                converted = Ticket.converted_at.is_not(None)
                return converted if flag == "true" else not_(converted)
            return _blocked() if flag == "true" else not_(_blocked())
        return self.ordered(f, "=", v)

    def sprint_equals(self, v: ast.Value) -> ColumnElement[bool]:
        """`active` and `future` (unquoted) are states; anything else is a sprint name."""
        text = v.text.strip()
        if v.kind == "word" and text.lower() in ("active", "future"):
            sprint_match: ColumnElement[bool] = Sprint.state == SprintState(text.lower())
            row = _open_sprint_row()
        else:
            self.references.append(("sprint", text, v.pos))
            sprint_match = func.lower(Sprint.name) == text.lower()
            row = and_(SprintTicket.ticket_id == Ticket.id, SprintTicket.removed_at.is_(None))
        return exists().where(row, Sprint.id == SprintTicket.sprint_id, sprint_match)

    def handle_equals(self, f: Field, v: ast.Value) -> ColumnElement[bool]:
        if v.kind == "func":
            if v.raw.lower() != "currentuser()":
                raise RQLError(
                    f"'{f.name}' only accepts handles or currentUser() (at {v.pos}).",
                    position=v.pos,
                )
            user_ids = select(literal(self.ctx.user_id, type_=User.id.type))
        else:
            handle = v.text.strip().lstrip("@").lower()
            self.references.append(("handle", handle, v.pos))
            user_ids = select(User.id).where(User.handle == handle)
        if f.name == "collaborator":
            return exists().where(
                TicketCollaborator.ticket_id == Ticket.id, TicketCollaborator.user_id.in_(user_ids)
            )
        return _nn(_column(f).in_(user_ids))

    def enum_value(self, f: Field, v: ast.Value) -> str:
        value = v.text.strip().lower()
        if value not in f.values:
            raise RQLError(
                f"'{v.text}' is not a valid {f.name} (at {v.pos}). Use one of: "
                f"{', '.join(f.values)}.",
                position=v.pos,
                expected=list(f.values),
            )
        return value

    def key(self, v: ast.Value) -> tuple[str, int]:
        match = KEY_RE.fullmatch(v.text.strip())
        if not match:
            raise RQLError(
                f"'{v.text}' is not a ticket key (at {v.pos}). Keys look like PA-4.",
                position=v.pos,
            )
        return match.group(1).upper(), int(match.group(2))

    def ticket_ids(self, v: ast.Value) -> Select[Any]:
        project_key, number = self.key(v)
        other = aliased(Ticket)
        return (
            select(other.id)
            .join(Project, Project.id == other.project_id)
            .where(Project.key == project_key, other.number == number, other.deleted_at.is_(None))
        )

    # --- custom fields ---------------------------------------------------------------------

    def custom_equals(self, f: Field, v: ast.Value) -> ColumnElement[bool]:
        key = _cf_key(f)
        stored = Ticket.custom_fields[key]
        text = v.text.strip()
        if f.custom == "checkbox":
            flag = text.lower()
            if flag not in ("true", "false"):
                raise RQLError(f"'{f.name}' takes true or false (at {v.pos}).", position=v.pos)
            checked = _nn(Ticket.custom_fields.contains({key: True}))
            return checked if flag == "true" else not_(checked)
        if f.custom == "user":
            if v.kind == "func":
                if v.raw.lower() != "currentuser()":
                    raise RQLError(
                        f"'{f.name}' only accepts handles or currentUser() (at {v.pos}).",
                        position=v.pos,
                    )
                return _nn(stored.astext == str(self.ctx.user_id))
            handle = text.lstrip("@").lower()
            self.references.append(("handle", handle, v.pos))
            ids = select(User.id.cast(Text)).where(User.handle == handle)
            return _nn(stored.astext.in_(ids))
        if f.custom in ("number", "date"):
            return self.custom_ordered(f, "=", v)
        return _nn(func.lower(stored.astext) == text.lower())

    def custom_ordered(self, f: Field, op: str, v: ast.Value) -> ColumnElement[bool]:
        key = _cf_key(f)
        stored = Ticket.custom_fields[key]
        if f.custom == "number":
            try:
                number = Decimal(v.text)
            except InvalidOperation:
                raise RQLError(
                    f"'{v.text}' is not a number (at {v.pos}).", position=v.pos
                ) from None
            numeric = case(
                (func.jsonb_typeof(stored) == "number", stored.astext.cast(Numeric)),
                else_=None,
            )
            return _nn(_apply(numeric, op, number))
        if f.custom != "date":
            raise RQLError(f"'{f.name}' cannot be compared with {op} (at {v.pos}).", position=v.pos)
        day = self.as_date(v).isoformat()
        return _nn(_apply(stored.astext, op, day))

    # --- text ------------------------------------------------------------------------------

    def matches(self, f: Field, v: ast.Value) -> ColumnElement[bool]:
        text = v.text.strip()
        if not text:
            raise RQLError(f"Empty search text at {v.pos}.", position=v.pos)
        if f.custom:
            value = Ticket.custom_fields[_cf_key(f)].astext
            return _nn(value.ilike(f"%{_escape_like(text)}%"))
        if f.kind is Kind.fulltext:
            query = func.websearch_to_tsquery(_ENGLISH, text).op("||")(
                func.websearch_to_tsquery(_SPANISH, text)
            )
            return _nn(Ticket.search_vector.op("@@")(query))
        return _nn(Ticket.title.ilike(f"%{_escape_like(text)}%"))

    # --- ordered values --------------------------------------------------------------------

    def ordered(self, f: Field, op: str, v: ast.Value) -> ColumnElement[bool]:
        if f.custom:
            return self.custom_ordered(f, op, v)
        if f.kind is Kind.ordinal:
            wanted = PRIORITY_ORDER[Priority(self.enum_value(f, v))]
            levels = [p for p, rank in PRIORITY_ORDER.items() if _cmp(rank, op, wanted)]
            return _nn(Ticket.priority.in_(levels))
        if f.kind is Kind.number:
            try:
                number = Decimal(v.text)
            except InvalidOperation:
                raise RQLError(
                    f"'{v.text}' is not a number (at {v.pos}).", position=v.pos
                ) from None
            return _nn(_apply(_column(f), op, number))
        if f.kind is Kind.date:
            day = self.as_date(v)
            return _nn(_apply(_column(f), op, day))
        return self.datetime_compare(f, op, v)

    def datetime_compare(self, f: Field, op: str, v: ast.Value) -> ColumnElement[bool]:
        column = _column(f)
        moment, whole_day = self.as_datetime(v)
        if whole_day is None:
            return _nn(_apply(column, op, moment))
        start, end = whole_day
        bounds = {
            "=": and_(column >= start, column < end),
            ">": column >= end,
            ">=": column >= start,
            "<": column < start,
            "<=": column < end,
        }
        return _nn(bounds[op])

    def as_datetime(self, v: ast.Value) -> tuple[datetime, tuple[datetime, datetime] | None]:
        """A moment, plus the [start, end) of the day when the value is a plain date."""
        text = v.text.strip()
        if v.kind == "reldate":
            return self.relative(v), None
        if v.kind == "func":
            return self.function(v), None
        try:
            day = date.fromisoformat(text)
        except ValueError:
            day = None
        if day is not None:
            start = datetime.combine(day, time(), self.ctx.tz).astimezone(UTC)
            return start, (start, start + timedelta(days=1))
        try:
            moment = datetime.fromisoformat(text)
        except ValueError:
            raise RQLError(
                f"'{v.text}' is not a date (at {v.pos}). Use YYYY-MM-DD, a relative date "
                "like -7d or a function like startOfWeek().",
                position=v.pos,
            ) from None
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=self.ctx.tz)
        return moment.astimezone(UTC), None

    def as_date(self, v: ast.Value) -> date:
        moment, whole_day = self.as_datetime(v)
        if whole_day is not None:
            return whole_day[0].astimezone(self.ctx.tz).date()
        return moment.astimezone(self.ctx.tz).date()

    def relative(self, v: ast.Value) -> datetime:
        match = REL_RE.fullmatch(v.text)
        if match is None:  # pragma: no cover - the grammar only lets valid ones through
            raise RQLError(f"Bad relative date '{v.text}' at {v.pos}.", position=v.pos)
        sign, amount, unit = match.groups()
        delta = timedelta(**{UNITS[unit]: int(amount)})
        return self.ctx.now + delta if sign == "+" else self.ctx.now - delta

    def function(self, v: ast.Value) -> datetime:
        name = v.raw.lower()
        local = self.ctx.now.astimezone(self.ctx.tz)
        midnight = local.replace(hour=0, minute=0, second=0, microsecond=0)
        if name == "now()":
            return self.ctx.now
        if name == "startofday()":
            return midnight.astimezone(UTC)
        if name == "startofweek()":
            return (midnight - timedelta(days=midnight.weekday())).astimezone(UTC)
        if name == "startofmonth()":
            return midnight.replace(day=1).astimezone(UTC)
        raise RQLError(
            f"'{v.raw}' is not a date function (at {v.pos}). Use now(), startOfDay(), "
            "startOfWeek() or startOfMonth().",
            position=v.pos,
        )


def _open_sprint_row() -> ColumnElement[bool]:
    """The ticket sits in a sprint that is not closed."""
    return and_(
        SprintTicket.ticket_id == Ticket.id,
        SprintTicket.removed_at.is_(None),
        SprintTicket.sprint_closed.is_(False),
    )


def _cf_key(f: Field) -> str:
    return f.name.split(".", 1)[1]


def _column(f: Field) -> Any:
    columns: dict[str, Any] = {
        "type": Ticket.type,
        "resolution": Ticket.resolution,
        "area": Ticket.area_id,
        "milestone": Ticket.milestone_id,
        "assignee": Ticket.assignee_id,
        "reporter": Ticket.reporter_id,
        "parent": Ticket.parent_id,
        "due": Ticket.due_date,
        "start": Ticket.start_date,
        "created": Ticket.created_at,
        "updated": Ticket.updated_at,
        "resolved": Ticket.resolved_at,
        "estimate": Ticket.estimate_hours,
        "original_estimate": Ticket.original_estimate_hours,
        "remaining": Ticket.remaining_hours,
        "spent": Ticket.time_spent_minutes.cast(Numeric) / literal(60),
        "votes": Ticket.vote_count,
        "origin": Ticket.origin,
        "classification": Ticket.classification,
        "impact": Ticket.impact,
        "effort": Ticket.effort,
    }
    return columns[f.name]


def _apply(column: Any, op: str, value: object) -> ColumnElement[bool]:
    ops: dict[str, ColumnElement[bool]] = {
        "=": column == value,
        ">": column > value,
        ">=": column >= value,
        "<": column < value,
        "<=": column <= value,
    }
    return ops[op]


def _cmp(a: int, op: str, b: int) -> bool:
    return {"=": a == b, ">": a > b, ">=": a >= b, "<": a < b, "<=": a <= b}[op]


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _blocked() -> ColumnElement[bool]:
    blocker = aliased(Ticket)
    blocker_status = aliased(Status)
    return exists().where(
        TicketLink.type == LinkType.blocks,
        TicketLink.target_id == Ticket.id,
        blocker.id == TicketLink.source_id,
        blocker.deleted_at.is_(None),
        blocker_status.id == blocker.status_id,
        blocker_status.category != StatusCategory.done,
    )


_CATEGORY_ORDER = {StatusCategory.todo: 0, StatusCategory.in_progress: 1, StatusCategory.done: 2}


def _priority_rank() -> ColumnElement[int]:
    return case({p: r for p, r in PRIORITY_ORDER.items()}, value=Ticket.priority)


def _order_by(sorts: tuple[ast.Sort, ...]) -> list[Any]:
    if not sorts:
        return [Ticket.updated_at.desc(), Ticket.id.desc()]
    order: list[Any] = []
    for sort in sorts:
        name = check_sort(sort.field, sort.pos)
        columns: list[Any]
        if name == "priority":
            columns = [_priority_rank()]
        elif name == "key":
            columns = [Project.key, Ticket.number]
        elif name == "status":
            category = case({c: r for c, r in _CATEGORY_ORDER.items()}, value=Status.category)
            columns = [category, Status.position]
        else:
            columns = [
                {
                    "created": Ticket.created_at,
                    "updated": Ticket.updated_at,
                    "due": Ticket.due_date,
                    "start": Ticket.start_date,
                    "rank": Ticket.rank,
                    "estimate": Ticket.estimate_hours,
                    "votes": Ticket.vote_count,
                    "spent": Ticket.time_spent_minutes,
                    "remaining": Ticket.remaining_hours,
                }[name]
            ]
        for column in columns:
            order.append(
                column.desc().nulls_last() if sort.descending else column.asc().nulls_last()
            )
    order.append(Ticket.id.desc())
    return order
