"""Clone, move and bulk tools."""

from typing import Annotated, Any, Literal

from mcp.server.mcpserver import Context, MCPServer
from pydantic import Field

from radicle.docket.mcp.api import api
from radicle.docket.mcp.tools.common import Key, compact

CloneInclude = Literal[
    "description",
    "checklist_state",
    "tags",
    "custom_fields",
    "collaborators",
    "attachments",
    "children",
]


def register(server: MCPServer) -> None:
    @server.tool()
    async def clone_ticket(
        ctx: Context,
        key: Key,
        target_project: Annotated[
            str | None, Field(description="Project key; default the same project")
        ] = None,
        include: list[CloneInclude] | None = None,
        area_mapping: Annotated[
            dict[str, str] | None,
            Field(description='When areas differ: {"Legal": "Compliance"}'),
        ] = None,
    ) -> dict[str, Any]:
        """Copy a ticket. The clone starts in the initial status, unassigned, linked to
        the original. By default only title, type, area and the checklist (unchecked)."""
        async with api(ctx) as client:
            ticket = await client.call(
                "POST",
                f"/tickets/{key}/clone",
                json={
                    "target_project": target_project,
                    "include": include or [],
                    "area_mapping": area_mapping or {},
                },
            )
        return compact(ticket)

    @server.tool()
    async def move_ticket(
        ctx: Context,
        key: Key,
        target_project: Annotated[str, Field(description="Project key, e.g. PB")],
        area_mapping: Annotated[
            dict[str, str] | None,
            Field(description='Required when the area does not exist there: {"Legal": "Ops"}'),
        ] = None,
        status_mapping: Annotated[
            dict[str, str] | None,
            Field(description='{"In Review": "QA"}; by default by name, else the initial'),
        ] = None,
    ) -> dict[str, Any]:
        """Move a ticket (and its subtickets) to another project. It gets a new key; the
        old key keeps working. Needs admin here and member there."""
        async with api(ctx) as client:
            ticket = await client.call(
                "POST",
                f"/tickets/{key}/move",
                json={
                    "target_project": target_project,
                    "area_mapping": area_mapping or {},
                    "status_mapping": status_mapping or {},
                },
            )
        out = compact(ticket)
        out["moved_from"] = ticket.get("moved_from")
        return out

    @server.tool()
    async def bulk_update(
        ctx: Context,
        operations: Annotated[
            list[dict[str, Any]],
            Field(
                description='e.g. [{"op": "set_field", "field": "milestone", "value": "V1"}, '
                '{"op": "remove_tag", "tag": "backlog"}, {"op": "transition", "to_status": '
                '"In Progress"}, {"op": "assign", "handle": "luis"}]'
            ),
        ],
        keys: list[str] | None = None,
        query: Annotated[str | None, Field(description="RQL instead of keys")] = None,
        dry_run: Annotated[
            bool,
            Field(description="True (default) only reports what would happen. Confirm first."),
        ] = True,
    ) -> dict[str, Any]:
        """Apply operations to many tickets (max 500). Runs as a dry run unless you pass
        dry_run=false: check the preview with the person before changing anything."""
        async with api(ctx) as client:
            result = await client.call(
                "POST",
                "/tickets/bulk",
                json={"keys": keys, "query": query, "operations": operations, "dry_run": dry_run},
            )
        out = {
            "dry_run": result["dry_run"],
            "total": result["total"],
            "succeeded": result["succeeded"],
            "failed": [r for r in result["results"] if not r["ok"]],
        }
        if result.get("job"):
            out["job"] = {"id": result["job"]["id"], "status": result["job"]["status"]}
        return out
