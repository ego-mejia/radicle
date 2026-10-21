"""Live doc tools (Folio 2.5): minutes and dailies an agent writes along with people."""

from typing import Annotated, Any

from mcp.server.mcpserver import Context, MCPServer
from pydantic import Field

from radicle.folio.mcp.read import NodeId, SpaceKey
from radicle.platform.mcp.api import api


def register(server: MCPServer) -> None:
    @server.tool()
    async def create_live_doc(
        ctx: Context,
        space: SpaceKey,
        title: str,
        content_md: Annotated[str | None, Field(description="What it starts with")] = None,
        parent: Annotated[str | None, Field(description="Parent page or folder id")] = None,
    ) -> dict[str, Any]:
        """A live doc for minutes or a daily: always editable, never published, and no
        metadata needed. People see what you write as you write it."""
        body = {"space": space, "kind": "live_doc", "title": title, "parent": parent}
        async with api(ctx) as client:
            node = await client.call("POST", "/folio/nodes", json=body)
            if content_md:
                await client.call(
                    "POST", f"/folio/nodes/{node['id']}/append", json={"content_md": content_md}
                )
        return {"id": node["id"], "title": node["title"], "space": node["space"]}

    @server.tool()
    async def append_to_live_doc(
        ctx: Context,
        id: NodeId,
        content_md: Annotated[str, Field(description="Markdown to add at the end")],
    ) -> dict[str, Any]:
        """Add a section at the end of a live doc. What others are writing at the same time
        stays as it is; returns the whole doc in Markdown."""
        async with api(ctx) as client:
            out = await client.call(
                "POST", f"/folio/nodes/{id}/append", json={"content_md": content_md}
            )
        return {"id": id, "content_md": out["content_md"]}
