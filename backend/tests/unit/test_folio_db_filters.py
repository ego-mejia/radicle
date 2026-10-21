"""Database views: matching rows against a filter."""

from typing import Any

import pytest

from radicle.folio.services.db_rows import _matches


@pytest.mark.parametrize(
    ("value", "op", "wanted", "kind", "expected"),
    [
        (None, "empty", None, "text", True),
        ("x", "not_empty", None, "text", True),
        (None, "eq", "x", "text", False),
        (None, "neq", "x", "text", True),
        ("Claude", "eq", "claude", "text", True),
        ("Claude", "neq", "claude", "text", False),
        (["ai", "ml"], "eq", "ml", "multi_select", True),
        ("Claude Code", "contains", "code", "text", True),
        (["ai"], "contains", "ml", "multi_select", False),
        (10, "gt", "9", "number", True),
        (10, "lte", 10, "number", True),
        ("2026-01-01", "lt", "2026-02-01", "date", True),
        (10, "gt", "nueve", "number", False),
    ],
)
def test_matches(value: Any, op: str, wanted: Any, kind: str, expected: bool) -> None:
    assert _matches(value, op, wanted, kind) is expected
