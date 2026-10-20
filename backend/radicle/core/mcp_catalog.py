"""The MCP tools by group, and which ones only read. Agents can be limited to a subset."""

GROUPS: dict[str, tuple[str, ...]] = {
    "context": ("whoami", "list_projects", "get_project", "get_ticket_schema"),
    "find_work": (
        "search_tickets",
        "my_tickets",
        "next_ticket",
        "list_filters",
        "run_filter",
        "save_filter",
    ),
    "tickets": (
        "get_ticket",
        "create_ticket",
        "update_ticket",
        "get_transitions",
        "transition_ticket",
        "change_ticket_type",
        "set_checklist_item",
        "clone_ticket",
        "move_ticket",
        "bulk_update",
        "rank_ticket",
        "get_history",
    ),
    "collaboration": (
        "add_comment",
        "list_comments",
        "link_tickets",
        "unlink_tickets",
        "add_collaborator",
        "remove_collaborator",
    ),
    "files_and_time": (
        "upload_attachment",
        "list_attachments",
        "read_attachment",
        "log_work",
        "list_worklogs",
    ),
    "planning": (
        "list_boards",
        "get_board",
        "list_sprints",
        "get_sprint",
        "add_to_sprint",
        "remove_from_sprint",
        "start_sprint",
        "complete_sprint",
        "get_milestone_progress",
        "get_report",
    ),
    "inbox": (
        "list_inbox",
        "score_inbox_item",
        "approve_inbox_item",
        "discard_inbox_item",
        "mark_inbox_duplicate",
    ),
}

TOOLS: tuple[str, ...] = tuple(name for names in GROUPS.values() for name in names)
GROUP_OF: dict[str, str] = {name: group for group, names in GROUPS.items() for name in names}

# Tools that never change anything (next_ticket can claim, so it is not here).
READ_ONLY: frozenset[str] = frozenset(
    {
        "whoami",
        "list_projects",
        "get_project",
        "get_ticket_schema",
        "search_tickets",
        "my_tickets",
        "list_filters",
        "run_filter",
        "get_ticket",
        "get_transitions",
        "get_history",
        "list_comments",
        "list_attachments",
        "read_attachment",
        "list_worklogs",
        "list_boards",
        "get_board",
        "list_sprints",
        "get_sprint",
        "get_milestone_progress",
        "get_report",
        "list_inbox",
    }
)
