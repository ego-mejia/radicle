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
    "list_templates",
    "list_comments",
)

WRITE = (
    "create_page",
    "update_draft",
    "submit_for_publication",
    "list_my_submissions",
    "create_from_template",
    "add_comment",
    "resolve_comment",
)

CATALOG: tuple[Tool, ...] = (
    Tool("whoami", "context", read_only=True),
    *(Tool(name, "folio_read", read_only=True) for name in READ),
    *(Tool(name, "folio_write", read_only=name == "list_my_submissions") for name in WRITE),
)
