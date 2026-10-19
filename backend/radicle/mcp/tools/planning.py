"""Planning tools: boards, sprints, milestone progress and reports."""

from typing import Annotated, Any

from mcp.server.mcpserver import Context, MCPServer
from pydantic import Field

from radicle.mcp.api import api
from radicle.mcp.tools.common import compact

Board = Annotated[str, Field(description="Board id, from list_boards")]


def register(server: MCPServer) -> None:
    @server.tool()
    async def list_boards(
        ctx: Context, project: Annotated[str, Field(description="Project key, e.g. PA")]
    ) -> list[dict[str, Any]]:
        """Boards of a project with their kind (kanban or scrum) and columns."""
        async with api(ctx) as client:
            page = await client.call("GET", f"/projects/{project}/boards")
        return [
            {
                "id": b["id"],
                "name": b["name"],
                "kind": b["kind"],
                "columns": [{"name": c["name"], "wip_limit": c["wip_limit"]} for c in b["columns"]],
                "quick_filters": [q["name"] for q in b["quick_filters"]],
            }
            for b in page["items"]
        ]

    @server.tool()
    async def get_board(
        ctx: Context,
        board: Board,
        quick_filters: Annotated[
            list[str] | None, Field(description="Quick filter names to apply (AND)")
        ] = None,
    ) -> dict[str, Any]:
        """Columns with their tickets (summarized) and the count against each WIP limit."""
        async with api(ctx) as client:
            config = await client.call("GET", f"/boards/{board}")
            wanted = {n.lower() for n in quick_filters or []}
            ids = [q["id"] for q in config["quick_filters"] if q["name"].lower() in wanted]
            data = await client.call(
                "GET", f"/boards/{board}/data", params={"quick_filters": ids or None}
            )
        return {
            "name": config["name"],
            "columns": [
                {
                    "name": c["name"],
                    "count": c["count"],
                    "wip_limit": c["wip_limit"],
                    "over_limit": c["over_limit"],
                    "tickets": [compact(t) for t in c["tickets"]],
                }
                for c in data["columns"]
            ],
        }
