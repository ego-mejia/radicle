"""Tools to pick work and organize it: next_ticket, ranking and saved filters."""

from typing import Annotated, Any, Literal

from mcp.server.mcpserver import Context, MCPServer
from pydantic import Field

from radicle.mcp.api import api
from radicle.mcp.tools.common import APIErrorMessage, Key, TicketType, _search_out, compact


def register(server: MCPServer) -> None:
    @server.tool()
    async def next_ticket(
        ctx: Context,
        project: Annotated[str | None, Field(description="Project key, e.g. PA")] = None,
        area: str | None = None,
        type: TicketType | None = None,
        claim: Annotated[
            bool,
            Field(description="Assign it to you and move it to in progress, atomically"),
        ] = False,
    ) -> dict[str, Any]:
        """The top-ranked ticket ready to work on: to do, not blocked, unassigned or yours.
        With claim=true it becomes yours and starts; two agents never get the same one."""
        async with api(ctx) as client:
            result = await client.call(
                "POST",
                "/tickets/next",
                json={"project": project, "area": area, "type": type, "claim": claim},
            )
        ticket = result["ticket"]
        if ticket is None:
            return {"ticket": None, "message": "Nothing is ready to work on with those filters."}
        out = compact(ticket)
        out["description"] = ticket["description_md"]
        out["checklist"] = ticket["checklist"]
        out["version"] = ticket["version"]
        return {"ticket": out}

    @server.tool()
    async def rank_ticket(
        ctx: Context,
        key: Key,
        before: Annotated[str | None, Field(description="Key to place it right above")] = None,
        after: Annotated[str | None, Field(description="Key to place it right below")] = None,
    ) -> dict[str, Any]:
        """Reorder a ticket in its project's backlog, relative to another ticket."""
        async with api(ctx) as client:
            ticket = await client.call(
                "POST", f"/tickets/{key}/rank", json={"before": before, "after": after}
            )
        return {"key": ticket["key"], "rank": ticket["rank"]}

    @server.tool()
    async def list_filters(
        ctx: Context, project: Annotated[str | None, Field(description="Project key")] = None
    ) -> list[dict[str, Any]]:
        """Saved filters you can use: name, RQL, visibility and owner."""
        async with api(ctx) as client:
            page = await client.call("GET", "/filters", params={"project": project})
        return [
            {
                "name": f["name"],
                "rql": f["rql"],
                "visibility": f["visibility"],
                "project": f["project"],
                "owner": f["owner"]["handle"],
            }
            for f in page["items"]
        ]

    @server.tool()
    async def run_filter(
        ctx: Context,
        name: Annotated[str, Field(description="Saved filter name, as in list_filters")],
        limit: Annotated[int, Field(ge=1, le=200)] = 50,
    ) -> dict[str, Any]:
        """Run a saved filter and return its tickets."""
        async with api(ctx) as client:
            page = await client.call(
                "GET",
                "/tickets",
                params={"q": f'filter = "{name.replace(chr(34), "")}"', "limit": limit},
            )
        out = _search_out(page)
        if out.get("warnings"):
            raise APIErrorMessage(f"There is no saved filter called '{name}'. See list_filters.")
        return out

    @server.tool()
    async def save_filter(
        ctx: Context,
        name: str,
        query: Annotated[str, Field(description="RQL")],
        visibility: Literal["private", "project", "instance"] = "private",
        project: Annotated[str | None, Field(description="Required for visibility=project")] = None,
    ) -> dict[str, Any]:
        """Save an RQL query under a name, private by default."""
        async with api(ctx) as client:
            saved = await client.call(
                "POST",
                "/filters",
                json={"name": name, "rql": query, "visibility": visibility, "project": project},
            )
        return {"name": saved["name"], "rql": saved["rql"], "visibility": saved["visibility"]}
