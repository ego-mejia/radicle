"""MCP tools an agent can be limited to (ADR 0031). Each app registers its catalog and its
server at startup, so user management does not depend on any app's tools."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class Tool:
    name: str
    group: str
    read_only: bool = False


class _Server(Protocol):
    async def list_tools(self) -> Any: ...


_tools: list[Tool] = []
_servers: list[_Server] = []


def register(tools: Iterable[Tool], server: _Server | None = None) -> None:
    """Add an app's tools, keeping catalog order. A name already registered (whoami is on
    every server) keeps its first entry, and one limit covers it everywhere."""
    names = {t.name for t in _tools}
    _tools.extend(t for t in tools if t.name not in names)
    if server is not None and server not in _servers:
        _servers.append(server)


def known() -> tuple[str, ...]:
    return tuple(t.name for t in _tools)


def catalog() -> tuple[Tool, ...]:
    return tuple(_tools)


async def descriptions() -> dict[str, str]:
    """Each tool's description, from the first server that has it."""
    found: dict[str, str] = {}
    for server in _servers:
        for tool in await server.list_tools():
            found.setdefault(tool.name, tool.description or "")
    return found
