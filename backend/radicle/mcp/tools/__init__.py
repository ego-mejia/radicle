"""MCP tools. Each one validates input, calls the REST API in-process and trims the result."""

from mcp.server.mcpserver import MCPServer

from radicle.mcp.tools import bulk, core, files, planning, sprints, time, work
from radicle.mcp.tools.common import project_schema

__all__ = ["project_schema", "register"]


def register(server: MCPServer) -> None:
    for module in (core, files, time, bulk, work, planning, sprints):
        module.register(server)
