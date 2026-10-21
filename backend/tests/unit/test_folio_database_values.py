"""Database columns: converting values between types and matching view filters."""

from typing import Any

import pytest

from radicle.folio.services.databases import convert

CHOICES = {"choices": [{"value": "Idea", "color": "grey"}, {"value": "Trial", "color": "blue"}]}


def col(kind: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"key": "k", "name": "K", "type": kind, "options": options or {}}


@pytest.mark.parametrize(
    ("value", "kind", "options", "expected"),
    [
        (None, "text", None, None),
        (12, "text", None, "12"),
        (["a", "b"], "text", None, "a, b"),
        ("3.5", "number", None, 3.5),
        ("4", "number", None, 4),
        ("cuatro", "number", None, None),
        (True, "number", None, None),
        ("2026-10-21", "date", None, "2026-10-21"),
        ("ayer", "date", None, None),
        ("Idea", "select", CHOICES, "Idea"),
        ("Otra", "select", CHOICES, None),
        (["Idea", "Nope"], "multi_select", CHOICES, ["Idea"]),
        ("Trial", "multi_select", CHOICES, ["Trial"]),
        ("Nope", "multi_select", CHOICES, None),
        ("yes", "checkbox", None, True),
        ("no", "checkbox", None, False),
        (False, "checkbox", None, False),
        ("https://x.dev", "url", None, "https://x.dev"),
        ("x.dev", "url", None, None),
        ("ana", "person", None, "ana"),
        (3, "page", None, None),
    ],
)
def test_convert(value: Any, kind: str, options: dict[str, Any] | None, expected: Any) -> None:
    assert convert(value, col(kind, options)) == expected
