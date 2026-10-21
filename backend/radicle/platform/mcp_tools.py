"""MCP tools an agent can be limited to (ADR 0031). Each app registers its catalog at
startup, so user management does not depend on any app's tools."""

from collections.abc import Iterable

_tools: list[str] = []


def register(names: Iterable[str]) -> None:
    """Add an app's tools, keeping catalog order. Registering again changes nothing."""
    _tools.extend(n for n in names if n not in _tools)


def known() -> tuple[str, ...]:
    return tuple(_tools)
