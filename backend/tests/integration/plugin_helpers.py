"""A test hook for plugin tests: `test.widgets` takes a list of names."""

from typing import Any

import pytest

from radicle.platform.services import plugins


def widgets(value: Any) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise plugins.invalid("hooks.test.widgets", "test.widgets is a list of names.")
    return value


@pytest.fixture
def test_hook(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(plugins._hooks, "test.widgets", widgets)


def manifest(**extra: Any) -> dict[str, Any]:
    return {
        "key": "acme.widgets",
        "name": "Widgets",
        "version": "1.0.0",
        "description": "Widgets de prueba",
        "author": "Acme",
        "hooks": {"test.widgets": ["a", "b"]},
    } | extra
