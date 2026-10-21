"""Scrum tools: sprints of a board, their tickets, start and close."""

from datetime import date
from typing import Annotated, Any, Literal

from mcp.server.mcpserver import Context, MCPServer
from pydantic import Field

from radicle.docket.mcp.tools.common import Key, compact
from radicle.platform.mcp.api import api

Sprint = Annotated[str, Field(description="Sprint id, from list_sprints")]
Keys = Annotated[list[Key], Field(min_length=1, description="Ticket keys")]


def _summary(s: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": s["id"],
        "name": s["name"],
        "state": s["state"],
        "goal": s["goal"],
        "start_date": s["start_date"],
        "end_date": s["end_date"],
        "tickets": s["ticket_count"],
        "done": s["done_count"],
        "estimate_hours": s["estimate_hours"],
        "remaining_hours": s["remaining_hours"],
        "capacity_hours": s["capacity_hours"],
        "over_capacity": s["over_capacity"],
        "unestimated": s["unestimated_count"],
    }


def register(server: MCPServer) -> None:
    @server.tool()
    async def list_sprints(
        ctx: Context,
        board: Annotated[str, Field(description="Scrum board id, from list_boards")],
        state: Literal["future", "active", "closed"] | None = None,
    ) -> list[dict[str, Any]]:
        """Sprints with dates, goal and progress: active first, then future, then closed."""
        async with api(ctx) as client:
            page = await client.call(
                "GET", f"/boards/{board}/sprints", params={"state": state} if state else None
            )
        return [_summary(s) for s in page["items"]]

    @server.tool()
    async def get_sprint(ctx: Context, sprint: Sprint) -> dict[str, Any]:
        """Goal, tickets, hours committed at start and hours still remaining."""
        async with api(ctx) as client:
            detail = await client.call("GET", f"/sprints/{sprint}")
            report = await client.call("GET", f"/sprints/{sprint}/report")
        return {
            **_summary(detail),
            "committed_hours": report["committed_hours"],
            "completed_hours": report["completed_hours"],
            "added_after_start": [i["key"] for i in report["added_after_start"]],
            "removed": [i["key"] for i in report["removed"]],
            "ticket_list": [compact(t) for t in detail["tickets"]],
        }

    @server.tool()
    async def add_to_sprint(ctx: Context, sprint: Sprint, keys: Keys) -> dict[str, Any]:
        """Put tickets in a sprint. They leave any other open sprint and lose #backlog;
        adding to the active sprint counts as a scope change."""
        async with api(ctx) as client:
            out = await client.call("POST", f"/sprints/{sprint}/tickets", json={"keys": keys})
        return {"added": out["keys"]}

    @server.tool()
    async def remove_from_sprint(ctx: Context, sprint: Sprint, keys: Keys) -> dict[str, Any]:
        """Take tickets out of a sprint that is not closed."""
        async with api(ctx) as client:
            out = await client.call("DELETE", f"/sprints/{sprint}/tickets", json={"keys": keys})
        return {"removed": out["keys"]}

    @server.tool()
    async def start_sprint(
        ctx: Context,
        sprint: Sprint,
        start_date: date | None = None,
        end_date: date | None = None,
        goal: str | None = None,
        capacity_hours: float | None = None,
    ) -> dict[str, Any]:
        """Start a future sprint (project admins). Needs dates, 1 to 28 days; only one active
        sprint per board. Saves the commitment."""
        body = {
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "goal": goal,
            "capacity_hours": capacity_hours,
        }
        async with api(ctx) as client:
            out = await client.call(
                "POST", f"/sprints/{sprint}/start", json={k: v for k, v in body.items() if v}
            )
        return _summary(out)

    @server.tool()
    async def complete_sprint(
        ctx: Context,
        sprint: Sprint,
        move_unfinished_to: Annotated[
            str, Field(description="A future sprint id of the same board, or 'backlog'")
        ] = "backlog",
        tag_backlog: bool = True,
    ) -> dict[str, Any]:
        """Close the active sprint (project admins). Unfinished tickets go to the next sprint
        or back to the backlog with #backlog."""
        async with api(ctx) as client:
            out = await client.call(
                "POST",
                f"/sprints/{sprint}/complete",
                json={"move_unfinished_to": move_unfinished_to, "tag_backlog": tag_backlog},
            )
        return {
            "sprint": _summary(out["sprint"]),
            "unfinished": out["unfinished"],
            "moved_to": out["moved_to"]["name"] if out["moved_to"] else "backlog",
        }
