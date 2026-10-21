"""Folio's MCP tools by group, for limiting agents (Admin → Users → MCP permissions)."""

from radicle.platform.mcp_tools import Tool

READ = (
    "list_spaces",
    "get_space_tree",
    "search_docs",
    "query_docs",
    "get_page",
    "get_metadata_schema",
    "get_versions",
)

CATALOG: tuple[Tool, ...] = (
    Tool("whoami", "context", read_only=True),
    *(Tool(name, "folio_read", read_only=True) for name in READ),
)
