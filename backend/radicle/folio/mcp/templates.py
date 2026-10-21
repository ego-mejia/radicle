"""Folio's template tools (Folio 3.1): start docs with the right structure, a build spec
included, instead of writing every section by hand."""

from typing import Annotated, Any, Literal

from mcp.server.mcpserver import Context, MCPServer
from pydantic import Field

from radicle.folio.mcp.read import SpaceKey
from radicle.platform.mcp.api import api


def register(server: MCPServer) -> None:
    @server.tool()
    async def list_templates(
        ctx: Context,
        kind: Literal["page", "space"] = "page",
        space: SpaceKey | None = None,
    ) -> list[dict[str, Any]]:
        """Templates you can use, with their id, document type and what they're for. The
        build spec template has the sections a stage of work needs."""
        params = {"kind": kind, "space": space}
        async with api(ctx) as client:
            found = await client.call("GET", "/folio/templates", params=params)
        keep = ("id", "name", "description", "doc_type_key", "scope", "space", "builtin")
        return [{k: t[k] for k in keep} for t in found["items"]]

    @server.tool()
    async def create_from_template(
        ctx: Context,
        template: Annotated[str, Field(description="Template id, from list_templates")],
        space: SpaceKey,
        title: str,
        parent: Annotated[str | None, Field(description="Parent page or folder id")] = None,
    ) -> dict[str, Any]:
        """Create a page from a template: its draft starts with the template's sections
        (dates and your handle filled in) and metadata. Then read it with get_page, write
        it with update_draft and send it with submit_for_publication."""
        body = {"template": template, "space": space, "title": title, "parent": parent}
        async with api(ctx) as client:
            node = await client.call("POST", "/folio/nodes/from-template", json=body)
            draft = await client.call("GET", f"/folio/nodes/{node['id']}/draft")
        return {
            "id": node["id"],
            "title": node["title"],
            "space": node["space"],
            "metadata": draft["metadata"],
            "content_md": draft["content_md"],
        }
