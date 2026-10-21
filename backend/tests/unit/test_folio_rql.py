"""Folio's RQL compiler without a database: every error says where and what works."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.dialects import postgresql

from radicle.folio.query.compiler import Context, compile_query
from radicle.platform.query.errors import RQLError
from radicle.platform.query.parser import parse

CTX = Context(user_id=uuid.uuid4(), now=datetime(2026, 10, 20, 12, tzinfo=UTC))


def sql(q: str) -> str:
    """The SQL with its parameters, to check which columns a query reads."""
    where = compile_query(parse(q), CTX).where.compile(dialect=postgresql.dialect())
    return f"{where} {where.params}"


@pytest.mark.parametrize(
    ("q", "position", "says"),
    [
        ("spaec = docs", 0, "Did you mean 'space'"),
        ("kind = post", 7, "Use page, folder, blog_post"),
        ("title = x", 6, "Use ~, !~"),
        ("published >= ayer", 13, "is not a date"),
        ("owner = today()", 8, "currentUser()"),
        ("parent = zz", 9, "not a node id"),
        ("ORDER BY slug", 9, "Sortable: title"),
        ("text IS EMPTY", 0, "cannot be EMPTY"),
        ("title IN (a, b)", 0, "does not support IN"),
        ('text ~ " "', 7, "Empty search text"),
    ],
)
def test_errors_say_where(q: str, position: int, says: str) -> None:
    with pytest.raises(RQLError) as exc:
        compile_query(parse(q), CTX)
    assert exc.value.position == position and says in exc.value.detail


def test_aliases_and_shapes() -> None:
    assert "labels" in sql("#onboarding") and "labels" in sql("tag = onboarding")
    assert "doc_type" in sql("type = how-to")
    assert "folio_chunks" in sql('text ~ "mcp"')
    assert "parent_id" in sql("parent IS EMPTY") and "LIKE" in sql("parent = 9f3c")
    assert "published_at IS NULL" in sql("published IS EMPTY")
    compiled = compile_query(parse("ORDER BY published DESC, title"), CTX)
    assert len(compiled.order_by) == 4  # both sorts, then updated and id as tie-breakers
