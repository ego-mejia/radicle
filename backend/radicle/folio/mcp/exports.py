"""export_page over MCP (Folio 5.2): a page in Markdown right away, or a PDF to download."""

import asyncio
from typing import Annotated, Any, Literal

from mcp.server.mcpserver import Context, MCPServer
from pydantic import Field

from radicle.platform.config import get_settings
from radicle.platform.mcp.api import api

WAIT_SECONDS = 20


def register(server: MCPServer) -> None:
    @server.tool()
    async def export_page(
        ctx: Context,
        id: Annotated[str, Field(description="The page id")],
        format: Annotated[
            Literal["markdown", "pdf"], Field(description="markdown: the text now; pdf: a file")
        ] = "markdown",
    ) -> dict[str, Any]:
        """Export a published page. Markdown comes back as text with its metadata. A PDF is
        rendered by the worker: you get its download link (send your token) once it is
        ready, or its id and status if it takes longer than a few seconds. Needs the
        space's export permission."""
        async with api(ctx) as client:
            if format == "markdown":
                node = await client.call("GET", f"/folio/nodes/{id}")
                if node["version"] is None:
                    raise ValueError("The page isn't published yet; export the published one.")
                v = await client.call("GET", f"/folio/nodes/{id}/versions/{node['version']}")
                return {
                    "title": v["title"],
                    "version": v["number"],
                    "metadata": v["metadata"],
                    "content_md": v["content_md"],
                }
            row = await client.call("POST", "/folio/exports", json={"node": id, "format": "pdf"})
            for _ in range(WAIT_SECONDS):
                if row["status"] in ("done", "failed"):
                    break
                await asyncio.sleep(1)
                row = await client.call("GET", f"/folio/exports/{row['id']}")
        base = get_settings().base_url.rstrip("/")
        out = {"export_id": row["id"], "status": row["status"], "filename": row["filename"]}
        if row["download_url"]:
            out["download_url"] = base + row["download_url"]
        if row["status"] == "failed":
            out["error"] = row["stats"].get("error")
        return out
