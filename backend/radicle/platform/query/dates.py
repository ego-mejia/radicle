"""RQL dates every app shares: ISO dates and datetimes, relative dates (-7d, +2h) and
date functions (now(), startOfWeek()), resolved in the user's time zone."""

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import ColumnElement, and_

from radicle.platform.query import ast
from radicle.platform.query.errors import RQLError

REL_RE = re.compile(r"^([+-])(\d+)([mhdw])$")
UNITS = {"m": "minutes", "h": "hours", "d": "days", "w": "weeks"}


@dataclass(frozen=True)
class Clock:
    now: datetime
    tz: ZoneInfo

    def moment(self, v: ast.Value) -> tuple[datetime, tuple[datetime, datetime] | None]:
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
            start = datetime.combine(day, time(), self.tz).astimezone(UTC)
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
            moment = moment.replace(tzinfo=self.tz)
        return moment.astimezone(UTC), None

    def day(self, v: ast.Value) -> date:
        moment, whole_day = self.moment(v)
        if whole_day is not None:
            return whole_day[0].astimezone(self.tz).date()
        return moment.astimezone(self.tz).date()

    def relative(self, v: ast.Value) -> datetime:
        match = REL_RE.fullmatch(v.text)
        if match is None:  # pragma: no cover - the grammar only lets valid ones through
            raise RQLError(f"Bad relative date '{v.text}' at {v.pos}.", position=v.pos)
        sign, amount, unit = match.groups()
        delta = timedelta(**{UNITS[unit]: int(amount)})
        return self.now + delta if sign == "+" else self.now - delta

    def function(self, v: ast.Value) -> datetime:
        name = v.raw.lower()
        local = self.now.astimezone(self.tz)
        midnight = local.replace(hour=0, minute=0, second=0, microsecond=0)
        if name == "now()":
            return self.now
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

    def compare(self, column: Any, op: str, v: ast.Value) -> ColumnElement[bool]:
        """A timestamp column against the value; a plain date means its whole day."""
        moment, whole_day = self.moment(v)
        if whole_day is None:
            return apply(column, op, moment)
        start, end = whole_day
        bounds: dict[str, ColumnElement[bool]] = {
            "=": and_(column >= start, column < end),
            ">": column >= end,
            ">=": column >= start,
            "<": column < start,
            "<=": column < end,
        }
        return bounds[op]


def apply(column: Any, op: str, value: object) -> ColumnElement[bool]:
    ops: dict[str, ColumnElement[bool]] = {
        "=": column == value,
        ">": column > value,
        ">=": column >= value,
        "<": column < value,
        "<=": column <= value,
    }
    return ops[op]
