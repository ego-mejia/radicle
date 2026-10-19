import uuid
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.dialects import postgresql

from radicle.query.compiler import Context, compile_query
from radicle.query.errors import RQLError
from radicle.query.parser import parse

USER = uuid.UUID("00000000-0000-0000-0000-000000000001")
NOW = datetime(2026, 10, 18, 15, 0, tzinfo=UTC)
CTX = Context(user_id=USER, now=NOW, tz=ZoneInfo("UTC"))


def sql(q: str, ctx: Context = CTX) -> str:
    compiled = compile_query(parse(q), ctx)
    return str(
        compiled.where.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    )


def order_sql(q: str) -> list[str]:
    compiled = compile_query(parse(q), CTX)
    return [str(o.compile(dialect=postgresql.dialect())) for o in compiled.order_by]


def test_not_equal_includes_nulls() -> None:
    out = sql("assignee != luis")
    assert out.startswith("NOT coalesce(tickets.assignee_id IN")
    assert "users.handle = 'luis'" in out


def test_priority_is_ordinal() -> None:
    out = sql("priority >= high")
    assert "tickets.priority IN ('high', 'highest')" in out
    assert "IN ('lowest', 'low')" in sql("priority < medium")


def test_current_user() -> None:
    assert str(USER) in sql("assignee = currentUser()")


def test_tag_and_tag_shortcut_match() -> None:
    assert sql("#Backlog") == sql("tag = backlog")
    assert "tickets.tags @>" in sql("#backlog")


def test_fulltext_uses_both_languages() -> None:
    out = sql('text ~ "pagos"')
    assert "websearch_to_tsquery('english'::regconfig, 'pagos')" in out
    assert "websearch_to_tsquery('spanish'::regconfig, 'pagos')" in out
    assert "tickets.search_vector @@" in out


def test_title_contains_escapes_wildcards() -> None:
    assert "50\\%%" in sql('title ~ "50%"')


def test_relative_and_absolute_dates() -> None:
    assert "2026-10-11 15:00:00" in sql("updated >= -7d")
    assert "2026-10-21" in sql("due < +3d")
    day = sql("created = 2026-10-01")
    assert "2026-10-01 00:00:00" in day and "2026-10-02 00:00:00" in day
    assert "2026-10-12 00:00:00" in sql("created >= startOfWeek()")
    assert "2026-10-01 00:00:00" in sql("created >= startOfMonth()")


def test_timezone_shifts_day_boundaries() -> None:
    ctx = Context(user_id=USER, now=NOW, tz=ZoneInfo("America/Mexico_City"))
    assert "2026-10-01 06:00:00" in sql("created = 2026-10-01", ctx)


def test_blocked_and_linked() -> None:
    assert "ticket_links.type = 'blocks'" in sql("blocked = true")
    assert sql("blocked = false").startswith("NOT (EXISTS")
    assert "ticket_links.source_id = tickets.id" in sql("linked = PA-4")


def test_in_and_empty() -> None:
    assert " OR " in sql("type IN (bug, task)")
    assert sql("area IS EMPTY") == "tickets.area_id IS NULL"
    assert sql("area IS NOT EMPTY") == "tickets.area_id IS NOT NULL"


def test_references_collected() -> None:
    compiled = compile_query(parse('area = Legal AND milestone = "V1" AND reporter = ana'), CTX)
    assert compiled.references == [
        ("area", "Legal", 7),
        ("milestone", "V1", 29),
        ("handle", "ana", 49),
    ]


def test_default_order_and_custom() -> None:
    assert order_sql("") == ["tickets.updated_at DESC", "tickets.id DESC"]
    out = order_sql("ORDER BY priority DESC, key")
    assert out[0].startswith("CASE tickets.priority") and out[0].endswith("DESC NULLS LAST")
    assert out[1] == "projects.key ASC NULLS LAST"


@pytest.mark.parametrize(
    ("q", "position", "fragment"),
    [
        ("prioridad = high", 0, "Did you mean 'priority'"),
        ("type ~ bug", 5, "Operator '~' does not work with 'type'"),
        ("type = epic", 7, "not a valid type"),
        ("priority > urgent", 11, "not a valid priority"),
        ("collaborator IN (a, b)", 0, "does not support IN"),
        ("title IS EMPTY", 0, "cannot be EMPTY"),
        ("key = PA", 6, "not a ticket key"),
        ("due < tomorrow", 6, "not a date"),
        ("estimate > lots", 11, "not a number"),
        ("blocked = maybe", 10, "true or false"),
        ("assignee = now()", 11, "only accepts handles"),
        ("created > currentUser()", 10, "not a date function"),
        ("ORDER BY title", 9, "Cannot sort by 'title'"),
        ("ORDER BY priorty", 9, "Did you mean 'priority'"),
        ('text ~ ""', 7, "Empty search text"),
    ],
)
def test_semantic_errors_have_position(q: str, position: int, fragment: str) -> None:
    with pytest.raises(RQLError) as exc:
        compile_query(parse(q), CTX)
    assert exc.value.position == position, exc.value.detail
    assert fragment in exc.value.detail
