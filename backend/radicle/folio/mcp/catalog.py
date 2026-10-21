"""Folio's MCP tools by group, for limiting agents (Admin → Users → MCP permissions)."""

from radicle.platform.mcp_tools import Tool

CATALOG: tuple[Tool, ...] = (Tool("whoami", "context", read_only=True),)
