"""The RQL guide served as an MCP resource, generated from the field catalog."""

from radicle.query.fields import FIELDS, FUNCTIONS, SORT_FIELDS

EXAMPLES = [
    (
        'project = PA AND type = bug AND priority >= high AND milestone = "V1" AND tag != backlog',
        "High-priority V1 bugs outside the backlog",
    ),
    (
        "assignee = currentUser() AND category != done ORDER BY priority DESC, due ASC",
        "My open work, most urgent first",
    ),
    ("#backlog AND area = Legal", "Legal backlog"),
    ('text ~ "pagos" AND updated >= -7d', "Mentions 'pagos', touched this week"),
    ('blocked = true AND milestone = "V1"', "Blocked tickets in V1"),
    ("parent = PA-4 AND category = done", "Finished subtickets of PA-4"),
    (
        "(type = bug OR type = draft) AND reporter = ana AND NOT #backlog",
        "Bugs and drafts reported by ana, not in backlog",
    ),
]


def rql_guide() -> str:
    lines = [
        "# RQL: Radicle Query Language",
        "",
        "`field operator value`, combined with AND, OR, NOT and parentheses. AND binds tighter "
        "than OR. Keywords are case-insensitive. Quote values with spaces: "
        '`status = "In Review"`. `#tag` is short for `tag = tag`.',
        "",
        "Lists: `field IN (a, b)`, `field NOT IN (a, b)`. Empty: `field IS EMPTY`, "
        "`field IS NOT EMPTY`. Sort: `ORDER BY priority DESC, due ASC`.",
        "",
        "`!=` and NOT include tickets where the field is empty. Unknown names match nothing "
        "and return a warning.",
        "",
        "## Fields",
        "",
        "| Field | Operators | IN | EMPTY | Notes |",
        "| --- | --- | --- | --- | --- |",
    ]
    for f in FIELDS.values():
        notes = f.description or (", ".join(f.values) if f.values else "")
        if f.values and f.description:
            notes = f"{f.description}. Values: {', '.join(f.values)}"
        lines.append(
            f"| `{f.name}` | {' '.join(f.ops)} | {'yes' if f.in_list else ''} | "
            f"{'yes' if f.empty else ''} | {notes} |"
        )
    lines += [
        "",
        "## Values",
        "",
        "- Dates: `2026-11-15`, relative `-7d`, `+3d`, `-2h`, `-30m`, `-1w`.",
        f"- Functions: {', '.join(f'`{fn}`' for fn in FUNCTIONS)}. "
        "`currentUser()` is you; date functions use the instance time zone; weeks start Monday.",
        "- People by handle (`luis`, `agent-backend`), areas, milestones and statuses by name, "
        "tickets by key (`PA-4`).",
        "",
        f"Sortable: {', '.join(f'`{s}`' for s in SORT_FIELDS)}. Default: `updated DESC`.",
        "",
        "## Examples",
        "",
    ]
    lines += [f"- `{q}`: {why}" for q, why in EXAMPLES]
    return "\n".join(lines) + "\n"
