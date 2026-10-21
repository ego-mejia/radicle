import pytest

from radicle.platform.query import ast
from radicle.platform.query.errors import RQLError
from radicle.platform.query.parser import parse

C = ast.Compare

FIELD_OPS = [
    ("project = PA", "project", "=", "PA"),
    ("project != PB", "project", "!=", "PB"),
    ("key = PA-1", "key", "=", "PA-1"),
    ("key != PA-1", "key", "!=", "PA-1"),
    ("type = bug", "type", "=", "bug"),
    ("type != draft", "type", "!=", "draft"),
    ('status = "In Review"', "status", "=", "In Review"),
    ("status != Done", "status", "!=", "Done"),
    ("category = in_progress", "category", "=", "in_progress"),
    ("category != done", "category", "!=", "done"),
    ("resolution = wont_do", "resolution", "=", "wont_do"),
    ("resolution != done", "resolution", "!=", "done"),
    ("priority = high", "priority", "=", "high"),
    ("priority != low", "priority", "!=", "low"),
    ("priority > medium", "priority", ">", "medium"),
    ("priority >= high", "priority", ">=", "high"),
    ("priority < high", "priority", "<", "high"),
    ("priority <= low", "priority", "<=", "low"),
    ("area = Legal", "area", "=", "Legal"),
    ("area != Legal", "area", "!=", "Legal"),
    ('milestone = "V1"', "milestone", "=", "V1"),
    ("milestone != V2", "milestone", "!=", "V2"),
    ("assignee = currentUser()", "assignee", "=", "currentUser()"),
    ("assignee != luis", "assignee", "!=", "luis"),
    ("assignee = agent-backend", "assignee", "=", "agent-backend"),
    ("collaborator = luis", "collaborator", "=", "luis"),
    ("collaborator != luis", "collaborator", "!=", "luis"),
    ("reporter = ana", "reporter", "=", "ana"),
    ("reporter != @ana", "reporter", "!=", "@ana"),
    ("tag = backlog", "tag", "=", "backlog"),
    ("tag != backlog", "tag", "!=", "backlog"),
    ("parent = PA-4", "parent", "=", "PA-4"),
    ('text ~ "pagos"', "text", "~", "pagos"),
    ("text !~ pagos", "text", "!~", "pagos"),
    ("title ~ checkout", "title", "~", "checkout"),
    ("title !~ checkout", "title", "!~", "checkout"),
    ("due = 2026-11-15", "due", "=", "2026-11-15"),
    ("due > 2026-11-15", "due", ">", "2026-11-15"),
    ("due < +3d", "due", "<", "+3d"),
    ("due <= startOfWeek()", "due", "<=", "startOfWeek()"),
    ("created >= -7d", "created", ">=", "-7d"),
    ("created < 2026-10-18T10:00:00", "created", "<", "2026-10-18T10:00:00"),
    ("updated >= -2h", "updated", ">=", "-2h"),
    ("updated > -30m", "updated", ">", "-30m"),
    ("resolved >= startOfMonth()", "resolved", ">=", "startOfMonth()"),
    ("resolved < now()", "resolved", "<", "now()"),
    ("estimate > 8", "estimate", ">", "8"),
    ("estimate <= 2.5", "estimate", "<=", "2.5"),
    ("blocked = true", "blocked", "=", "true"),
    ("linked = PA-4", "linked", "=", "PA-4"),
    ("created >= startOfDay()", "created", ">=", "startOfDay()"),
    ("due >= -1w", "due", ">=", "-1w"),
]


@pytest.mark.parametrize(("q", "field", "op", "value"), FIELD_OPS)
def test_field_with_operator(q: str, field: str, op: str, value: str) -> None:
    node = parse(q).where
    assert isinstance(node, C)
    assert (node.field, node.op, node.value.text) == (field, op, value)


@pytest.mark.parametrize(
    ("q", "kind"),
    [
        ("due < +3d", "reldate"),
        ("due < 2026-01-01", "word"),
        ('area = "Legal y más"', "string"),
        ("assignee = currentUser()", "func"),
    ],
)
def test_value_kinds(q: str, kind: str) -> None:
    node = parse(q).where
    assert isinstance(node, C) and node.value.kind == kind


def test_and_binds_tighter_than_or() -> None:
    node = parse("type = bug OR type = task AND priority = high").where
    assert isinstance(node, ast.Or)
    assert isinstance(node.items[0], C) and isinstance(node.items[1], ast.And)


def test_parentheses_override_precedence() -> None:
    node = parse("(type = bug OR type = task) AND priority = high").where
    assert isinstance(node, ast.And) and isinstance(node.items[0], ast.Or)


def test_chains_flatten() -> None:
    node = parse("a = 1 AND b = 2 AND c = 3 AND d = 4").where
    assert isinstance(node, ast.And) and len(node.items) == 4
    node = parse("a = 1 OR b = 2 OR c = 3").where
    assert isinstance(node, ast.Or) and len(node.items) == 3


def test_not_and_double_not() -> None:
    node = parse("NOT #backlog").where
    assert isinstance(node, ast.Not) and isinstance(node.item, C) and node.item.field == "tag"
    node = parse("NOT NOT type = bug").where
    assert isinstance(node, ast.Not) and isinstance(node.item, ast.Not)


def test_not_parenthesized() -> None:
    node = parse("NOT (type = bug OR type = task)").where
    assert isinstance(node, ast.Not) and isinstance(node.item, ast.Or)


def test_tag_shortcut() -> None:
    node = parse("#backlog").where
    assert isinstance(node, C) and (node.field, node.op, node.value.text) == ("tag", "=", "backlog")


def test_in_and_not_in() -> None:
    node = parse("key IN (PA-1, PA-4)").where
    assert isinstance(node, ast.InList) and not node.negated
    assert [v.text for v in node.values] == ["PA-1", "PA-4"]
    node = parse('status NOT IN ("In Review", Done)').where
    assert isinstance(node, ast.InList) and node.negated
    assert [v.text for v in node.values] == ["In Review", "Done"]


def test_is_empty() -> None:
    node = parse("area IS EMPTY").where
    assert isinstance(node, ast.IsEmpty) and not node.negated
    node = parse("milestone is not empty").where
    assert isinstance(node, ast.IsEmpty) and node.negated


def test_order_by_multiple() -> None:
    q = parse("assignee = currentUser() ORDER BY priority DESC, due ASC, created")
    assert [(s.field, s.descending) for s in q.order] == [
        ("priority", True),
        ("due", False),
        ("created", False),
    ]


def test_order_by_alone_and_empty_query() -> None:
    assert parse("ORDER BY created DESC").where is None
    assert parse("") == ast.Query(None, ())
    assert parse("   ") == ast.Query(None, ())


def test_lowercase_keywords() -> None:
    q = parse("type = bug and not #x or area is empty order by due desc")
    assert isinstance(q.where, ast.Or) and q.order[0].descending


def test_keyword_like_values_are_values() -> None:
    node = parse("status = order").where
    assert isinstance(node, C) and node.value.text == "order"
    node = parse("area = Android").where
    assert isinstance(node, C) and node.value.text == "Android"


def test_escaped_quotes() -> None:
    node = parse(r'title ~ "say \"hi\""').where
    assert isinstance(node, C) and node.value.text == 'say "hi"'


def test_positions() -> None:
    node = parse("type = bug AND area = Legal").where
    assert isinstance(node, ast.And)
    second = node.items[1]
    assert isinstance(second, C) and second.field_pos == 15 and second.value.pos == 22


SPEC_EXAMPLES = [
    'project = PA AND type = bug AND priority >= high AND milestone = "V1" AND tag != backlog',
    "assignee = currentUser() AND category != done ORDER BY priority DESC, due ASC",
    "#backlog AND area = Legal",
    'text ~ "pagos" AND updated >= -7d',
    'blocked = true AND milestone = "V1"',
    "parent = PA-4 AND category = done",
    "(type = bug OR type = draft) AND reporter = ana AND NOT #backlog",
]


@pytest.mark.parametrize("q", SPEC_EXAMPLES)
def test_spec_examples_parse(q: str) -> None:
    assert parse(q).where is not None


# --- errors ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("q", "position", "fragment"),
    [
        ("(type = bug", 11, "parenthesis is not closed"),
        ("type =", 6, "Expected"),
        ("type == bug", 6, "Unexpected '='"),
        ("= bug", 0, "Unexpected '='"),
        ("type = bug AND", 14, "end of query"),
        ("type = bug $", 11, "Unexpected '$'"),
        ("type bug", 5, "Unexpected 'bug'"),
        ("key IN (PA-1,", 13, "end of query"),
        ("ORDER created", 6, "Unexpected"),
    ],
)
def test_syntax_errors_have_position(q: str, position: int, fragment: str) -> None:
    with pytest.raises(RQLError) as exc:
        parse(q)
    assert exc.value.position == position
    assert fragment in exc.value.detail
    assert exc.value.extra["position"] == position


def test_expected_tokens_listed() -> None:
    with pytest.raises(RQLError) as exc:
        parse("type =")
    assert "a field or value" in exc.value.expected


def test_too_long() -> None:
    with pytest.raises(RQLError, match="too long") as exc:
        parse("type = bug AND " * 200)
    assert exc.value.position == 2000
    parse("title ~ " + "x" * 1990)
