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
    "list_my_tasks",
    "get_feed",
    "list_notifications",
    "query_database",
)

WRITE = (
    "create_page",
    "update_draft",
    "submit_for_publication",
    "list_my_submissions",
    "create_from_template",
    "add_comment",
    "resolve_comment",
    "set_task_done",
    "watch",
    "create_live_doc",
    "append_to_live_doc",
    "add_database_rows",
)

CATALOG: tuple[Tool, ...] = (
    Tool("whoami", "context", read_only=True),
    *(Tool(name, "folio_read", read_only=True) for name in READ),
    *(Tool(name, "folio_write", read_only=name == "list_my_submissions") for name in WRITE),
)
