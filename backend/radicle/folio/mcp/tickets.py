"""Folio's Docket tools (Folio 4.1): link a doc or one of its sections to tickets, unlink
them, and find the docs of a ticket. Tickets are read with your own Docket access."""

from typing import Annotated, Any

from mcp.server.mcpserver import Context, MCPServer
from pydantic import Field

from radicle.folio.mcp.read import NodeId
from radicle.platform.mcp.api import api

Key = Annotated[str, Field(description="A Docket ticket key, e.g. PA-4")]


def _link(link: dict[str, Any]) -> dict[str, Any]:
    ticket = link["ticket"]
    return {
        "link_id": link["id"],
        "kind": link["kind"],
        "section": link["anchor"],
        "ticket": None
        if ticket is None
        else {k: ticket[k] for k in ("key", "title", "status", "assignee", "url")},
        "restricted": link["restricted"],
    }


def register(server: MCPServer) -> None:
    @server.tool()
    async def link_ticket(
        ctx: Context,
        id: NodeId,
        key: Key,
        section: Annotated[
            str | None,
            Field(description="A heading anchor of the page, e.g. conecta-un-agente"),
        ] = None,
    ) -> dict[str, Any]:
        """Link the page, or one of its sections, to a Docket ticket. Needs edit on the
        page; linking the same ticket twice does nothing."""
        body: dict[str, Any] = {"key": key, "anchor": section}
        async with api(ctx) as client:
            link = await client.call("POST", f"/folio/nodes/{id}/ticket-links", json=body)
        return _link(link)

    @server.tool()
    async def unlink_ticket(ctx: Context, id: NodeId, key: Key) -> dict[str, Any]:
        """Remove the page's links to this ticket. A mention comes back the next time the
        page is published while it still names the key."""
        async with api(ctx) as client:
            links = await client.call("GET", f"/folio/nodes/{id}/ticket-links")
            wanted = key.strip().upper()
            removed = 0
            for link in links["items"]:
                if link["ticket"] and link["ticket"]["key"] == wanted:
                    await client.call("DELETE", f"/folio/nodes/{id}/ticket-links/{link['id']}")
                    removed += 1
        return {"removed": removed}

    @server.tool()
    async def get_docs_for_ticket(ctx: Context, key: Key) -> list[dict[str, Any]]:
        """The docs linked to a ticket that you may see, with the section when there is
        one: docs that mention it, that created it, or that were linked by hand."""
        async with api(ctx) as client:
            found = await client.call("GET", "/folio/links", params={"ticket": key})
        return [
            {
                "id": d["node"]["id"],
                "title": d["node"]["title"],
                "space": d["space"],
                "kind": d["kind"],
                "section": d["anchor"],
                "url": d["url"],
            }
            for d in found["items"]
        ]
