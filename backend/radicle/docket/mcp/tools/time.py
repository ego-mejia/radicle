"""Time tracking tools."""

from typing import Annotated, Any

from mcp.server.mcpserver import Context, MCPServer
from pydantic import Field

from radicle.docket.mcp.api import api
from radicle.docket.mcp.tools.common import Key


def worklog_brief(w: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": w["id"],
        "user": w["user"]["handle"],
        "minutes": w["minutes"],
        "started_at": w["started_at"],
        "description": w["description"],
    }


def register(server: MCPServer) -> None:
    @server.tool()
    async def log_work(
        ctx: Context,
        key: Key,
        minutes: Annotated[int, Field(ge=1, le=1440, description="Time worked, in minutes")],
        description: str | None = None,
        started_at: Annotated[
            str | None, Field(description="ISO datetime when the work started; default now")
        ] = None,
    ) -> dict[str, Any]:
        """Log time spent on a ticket. Returns the ticket's spent and remaining hours."""
        async with api(ctx) as client:
            worklog = await client.call(
                "POST",
                f"/tickets/{key}/worklogs",
                json={
                    k: v
                    for k, v in {
                        "minutes": minutes,
                        "description": description,
                        "started_at": started_at,
                    }.items()
                    if v is not None
                },
            )
            ticket = await client.call("GET", f"/tickets/{key}")
        return {
            "worklog": worklog_brief(worklog),
            "spent_hours": ticket["spent_hours"],
            "remaining_hours": ticket["remaining_hours"],
            "estimate_hours": ticket["estimate_hours"],
            "original_estimate_hours": ticket["original_estimate_hours"],
        }

    @server.tool()
    async def list_worklogs(ctx: Context, key: Key) -> dict[str, Any]:
        """Time logged on a ticket, newest first, with totals."""
        async with api(ctx) as client:
            page = await client.call("GET", f"/tickets/{key}/worklogs")
            ticket = await client.call("GET", f"/tickets/{key}")
        return {
            "spent_hours": ticket["spent_hours"],
            "remaining_hours": ticket["remaining_hours"],
            "items": [worklog_brief(w) for w in page["items"]],
        }
