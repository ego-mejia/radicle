"""Core ticket tools: projects, search, tickets, transitions, comments, links."""

from datetime import date
from typing import Annotated, Any, Literal

from mcp.server.mcpserver import Context, MCPServer
from pydantic import BaseModel, ConfigDict, Field

from radicle.docket.mcp.tools.common import (
    APIErrorMessage,
    Key,
    LinkType,
    Priority,
    Resolution,
    TicketType,
    _search_out,
    comment_out,
    compact,
    detailed,
    project_schema,
)
from radicle.platform.mcp.api import APIError, api


class TicketChanges(BaseModel):
    """Fields to change. Omit a field to keep it; send null to clear it."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    description: str | None = Field(default=None, description="Markdown; checklist lines too")
    priority: Priority | None = None
    area: str | None = Field(default=None, description="Area name")
    milestone: str | None = Field(default=None, description="Open milestone name")
    parent: str | None = Field(default=None, description="Parent ticket key")
    assignee: str | None = Field(default=None, description="Handle of a member or agent")
    start_date: date | None = None
    due_date: date | None = None
    estimate_hours: float | None = None
    tags: list[str] | None = None
    custom_fields: dict[str, Any] | None = Field(
        default=None,
        description='By key, e.g. {"environment": "prod"}; null clears one. See get_project.',
    )


def register(server: MCPServer) -> None:

    @server.tool()
    async def whoami(ctx: Context) -> dict[str, Any]:
        """Who you are connected as (user or agent) and your projects with role.

        Call this first to learn your handle and which projects you can work in.
        """
        async with api(ctx) as client:
            me = await client.call("GET", "/me")
        return {
            "handle": me["handle"],
            "display_name": me["display_name"],
            "kind": me["kind"],
            "projects": me["projects"],
        }

    @server.tool()
    async def list_projects(ctx: Context) -> list[dict[str, Any]]:
        """Projects you can see, with key, name, your role and open ticket count."""
        async with api(ctx) as client:
            page = await client.call("GET", "/projects")
        return [
            {
                "key": p["key"],
                "name": p["name"],
                "role": p["role"],
                "open_tickets": p["open_tickets"],
            }
            for p in page["items"]
        ]

    @server.tool()
    async def get_project(
        ctx: Context, project: Annotated[str, Field(description="Project key, e.g. PA")]
    ) -> dict[str, Any]:
        """Areas, open milestones, statuses and transitions per type, and member handles.

        Use it before creating or moving tickets to know valid names.
        """
        async with api(ctx) as client:
            p = await client.call("GET", f"/projects/{project}")
        return project_schema(p)

    @server.tool()
    async def search_tickets(
        ctx: Context,
        query: Annotated[str, Field(description="RQL, e.g. 'project = PA AND category != done'")],
        limit: Annotated[int, Field(ge=1, le=200)] = 20,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """Search tickets with RQL (see resource radicle://guide/rql).

        Examples: `assignee = currentUser() AND category != done`,
        `project = PA AND priority >= high ORDER BY due ASC`, `#backlog AND area = Legal`.
        """
        async with api(ctx) as client:
            page = await client.call(
                "GET", "/tickets", params={"q": query, "limit": limit, "cursor": cursor}
            )
        return _search_out(page)

    @server.tool()
    async def my_tickets(ctx: Context, include_done: bool = False) -> dict[str, Any]:
        """Tickets assigned to you, most urgent first (priority, then due date)."""
        q = "assignee = currentUser()"
        if not include_done:
            q += " AND category != done"
        async with api(ctx) as client:
            page = await client.call(
                "GET",
                "/tickets",
                params={"q": q + " ORDER BY priority DESC, due ASC", "limit": 100},
            )
        return _search_out(page)

    @server.tool()
    async def get_ticket(
        ctx: Context, key: Key, comments: Annotated[int, Field(ge=0, le=100)] = 10
    ) -> dict[str, Any]:
        """Everything about a ticket: fields, checklist with indexes, links, subtickets,
        latest comments and `version` (pass it to update_ticket to avoid overwriting)."""
        async with api(ctx) as client:
            ticket = await client.call("GET", f"/tickets/{key}")
            children = await client.call("GET", f"/tickets/{key}/children")
            out = detailed(ticket)
            out["children"] = [compact(c) for c in children["items"]]
            if comments:
                page = await client.call(
                    "GET", f"/tickets/{key}/comments", params={"order": "desc", "limit": comments}
                )
                out["latest_comments"] = [comment_out(c) for c in reversed(page["items"])]
        return out

    @server.tool()
    async def create_ticket(
        ctx: Context,
        project: Annotated[str, Field(description="Project key, e.g. PA")],
        type: TicketType,
        title: str,
        description: Annotated[str | None, Field(description="Markdown")] = None,
        area: Annotated[str | None, Field(description="Required for task and bug")] = None,
        milestone: str | None = None,
        priority: Priority | None = None,
        assignee: Annotated[str | None, Field(description="Handle")] = None,
        collaborators: list[str] | None = None,
        parent: Annotated[str | None, Field(description="Parent ticket key")] = None,
        start_date: date | None = None,
        due_date: date | None = None,
        estimate_hours: float | None = None,
        tags: list[str] | None = None,
        custom_fields: Annotated[
            dict[str, Any] | None,
            Field(description='By key, e.g. {"environment": "prod"}. See get_project.'),
        ] = None,
        classification: Annotated[
            Literal["idea", "experiment", "complaint", "suggestion"] | None,
            Field(description="Drafts only, and required for them"),
        ] = None,
    ) -> dict[str, Any]:
        """Create a ticket and return it. Write checklists as `- [ ] item @handle` lines.
        Drafts (inbox items) need a classification."""
        body = {
            "type": type,
            "title": title,
            "description_md": description,
            "area": area,
            "milestone": milestone,
            "priority": priority,
            "assignee": assignee,
            "collaborators": collaborators,
            "parent": parent,
            "start_date": start_date.isoformat() if start_date else None,
            "due_date": due_date.isoformat() if due_date else None,
            "estimate_hours": estimate_hours,
            "tags": tags,
            "custom_fields": custom_fields,
            "classification": classification,
        }
        async with api(ctx) as client:
            ticket = await client.call(
                "POST",
                f"/projects/{project}/tickets",
                json={k: v for k, v in body.items() if v is not None},
            )
        return detailed(ticket)

    @server.tool()
    async def update_ticket(
        ctx: Context,
        key: Key,
        changes: TicketChanges,
        expected_version: Annotated[
            int | None,
            Field(
                description="Version you read; if it changed meanwhile the update fails. "
                "Omit it and the last change wins."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Change only the fields you send; null clears a field. Status changes use
        transition_ticket, and checklist items use set_checklist_item."""
        body = changes.model_dump(mode="json", exclude_unset=True)
        if "description" in body:
            body["description_md"] = body.pop("description")
        if not body:
            raise APIErrorMessage("Send at least one field in `changes`.")
        async with api(ctx) as client:
            for attempt in range(2):
                version = expected_version
                if version is None:
                    version = (await client.call("GET", f"/tickets/{key}"))["version"]
                try:
                    ticket = await client.call(
                        "PATCH", f"/tickets/{key}", json={**body, "expected_version": version}
                    )
                    return detailed(ticket)
                except APIError as exc:
                    # Without an explicit version the last change wins: reread and retry once.
                    if exc.status != 409 or expected_version is not None or attempt:
                        raise
        raise APIErrorMessage("Could not update the ticket.")  # pragma: no cover

    @server.tool()
    async def get_ticket_schema(
        ctx: Context,
        project: Annotated[str, Field(description="Project key, e.g. PA")],
        type: TicketType,
        operation: Literal["create", "edit", "transition"] = "create",
        transition: Annotated[
            str | None, Field(description="Transition name, for operation=transition")
        ] = None,
    ) -> dict[str, Any]:
        """Fields a form needs before you create, edit or move a ticket: which are
        required and their valid options. Call it before create_ticket when unsure."""
        async with api(ctx) as client:
            schema = await client.call(
                "GET",
                f"/projects/{project}/schema",
                params={"type": type, "operation": operation, "transition": transition},
            )
        return {
            "type": schema["type"],
            "operation": schema["operation"],
            "transition": schema["transition"],
            "fields": [
                {k: v for k, v in f.items() if v is not None and k != "label"}
                | {"label": f["label"]}
                for f in schema["fields"]
            ],
        }

    @server.tool()
    async def get_transitions(ctx: Context, key: Key) -> list[dict[str, Any]]:
        """Statuses this ticket can move to now, and the resolutions each one accepts."""
        async with api(ctx) as client:
            result: list[dict[str, Any]] = await client.call("GET", f"/tickets/{key}/transitions")
        return result

    @server.tool()
    async def transition_ticket(
        ctx: Context,
        key: Key,
        to_status: Annotated[str, Field(description="Target status name, e.g. 'In Progress'")],
        resolution: Annotated[
            Resolution | None, Field(description="Needed when the target is a done status")
        ] = None,
        comment: Annotated[
            str | None,
            Field(description="Saved as a comment; some transitions require one"),
        ] = None,
        fields: Annotated[
            dict[str, Any] | None,
            Field(
                description="Values the transition's screen asks for, e.g. "
                '{"cf.environment": "prod"}. See get_ticket_schema.'
            ),
        ] = None,
        log_minutes: Annotated[
            int | None, Field(ge=1, le=1440, description="Log time worked in the same move")
        ] = None,
    ) -> dict[str, Any]:
        """Move a ticket through its workflow. The result includes `warnings`, e.g. when
        the ticket is still blocked by unfinished tickets. If the transition has rules
        (checklist complete, a field required...), the error lists the ones that failed."""
        body: dict[str, Any] = {"to_status": to_status, "resolution": resolution}
        if comment:
            body["comment"] = comment
        if fields:
            body["fields"] = fields
        if log_minutes:
            body["log_minutes"] = log_minutes
        async with api(ctx) as client:
            ticket = await client.call("POST", f"/tickets/{key}/transitions", json=body)
        out = compact(ticket)
        out["resolution"] = ticket["resolution"]
        out["version"] = ticket["version"]
        out["warnings"] = ticket.get("warnings", [])
        return out

    @server.tool()
    async def change_ticket_type(
        ctx: Context,
        key: Key,
        type: TicketType,
        area: Annotated[
            str | None, Field(description="Required to become task or bug without an area")
        ] = None,
    ) -> dict[str, Any]:
        """Change the type, e.g. Draft to Task. The ticket restarts in the new workflow."""
        async with api(ctx) as client:
            ticket = await client.call(
                "POST", f"/tickets/{key}/type", json={"type": type, "area": area}
            )
        return compact(ticket)

    @server.tool()
    async def set_checklist_item(
        ctx: Context,
        key: Key,
        index: Annotated[int, Field(ge=0, description="0-based index from get_ticket")],
        checked: bool,
    ) -> dict[str, Any]:
        """Check or uncheck one checklist item of the ticket description."""
        async with api(ctx) as client:
            ticket = await client.call(
                "PATCH", f"/tickets/{key}/checklist/{index}", json={"checked": checked}
            )
        return {
            "key": ticket["key"],
            "checklist": ticket["checklist"],
            "version": ticket["version"],
        }

    @server.tool()
    async def add_comment(
        ctx: Context, key: Key, body: Annotated[str, Field(description="Markdown, @handles")]
    ) -> dict[str, Any]:
        """Comment on a ticket, e.g. to report progress. @handle mentions people."""
        async with api(ctx) as client:
            comment = await client.call("POST", f"/tickets/{key}/comments", json={"body_md": body})
        return comment_out(comment)

    @server.tool()
    async def list_comments(
        ctx: Context,
        key: Key,
        limit: Annotated[int, Field(ge=1, le=200)] = 20,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """Comments of a ticket, newest first."""
        async with api(ctx) as client:
            page = await client.call(
                "GET",
                f"/tickets/{key}/comments",
                params={"order": "desc", "limit": limit, "cursor": cursor},
            )
        return {
            "items": [comment_out(c) for c in page["items"]],
            "next_cursor": page["next_cursor"],
        }

    @server.tool()
    async def link_tickets(
        ctx: Context,
        source: Key,
        type: LinkType,
        target: Key,
    ) -> list[dict[str, Any]]:
        """Link two tickets. `source blocks target` means target waits for source."""
        async with api(ctx) as client:
            links = await client.call(
                "POST", f"/tickets/{source}/links", json={"type": type, "target": target}
            )
        return [
            {"id": link["id"], "label": link["label"], "key": link["ticket"]["key"]}
            for link in links
        ]

    @server.tool()
    async def unlink_tickets(
        ctx: Context, link_id: Annotated[str, Field(description="Link id from get_ticket")]
    ) -> str:
        """Remove a link between two tickets."""
        async with api(ctx) as client:
            await client.call("DELETE", f"/links/{link_id}")
        return "Link removed."

    @server.tool()
    async def add_collaborator(ctx: Context, key: Key, handle: str) -> dict[str, Any]:
        """Add a member or agent as collaborator on a ticket."""
        async with api(ctx) as client:
            ticket = await client.call("PUT", f"/tickets/{key}/collaborators/{handle}")
        return {
            "key": ticket["key"],
            "collaborators": [c["handle"] for c in ticket["collaborators"]],
        }

    @server.tool()
    async def remove_collaborator(ctx: Context, key: Key, handle: str) -> dict[str, Any]:
        """Remove a collaborator from a ticket."""
        async with api(ctx) as client:
            ticket = await client.call("DELETE", f"/tickets/{key}/collaborators/{handle}")
        return {
            "key": ticket["key"],
            "collaborators": [c["handle"] for c in ticket["collaborators"]],
        }

    @server.tool()
    async def get_history(
        ctx: Context, key: Key, limit: Annotated[int, Field(ge=1, le=200)] = 50
    ) -> list[dict[str, Any]]:
        """Who changed what on a ticket, newest first, with old and new values."""
        async with api(ctx) as client:
            page = await client.call("GET", f"/tickets/{key}/history", params={"limit": limit})
        return [
            {
                "at": e["created_at"],
                "actor": e["actor"]["handle"],
                "actor_kind": e["actor"]["kind"],
                "event": e["event_type"],
                "field": e["field"],
                "old": e["old_value"],
                "new": e["new_value"],
            }
            for e in page["items"]
        ]
