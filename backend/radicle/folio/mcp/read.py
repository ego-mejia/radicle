"""Folio's read tools (Folio 1.7): find docs, read them and learn what publishing needs.
Each tool calls the REST API in process, so visibility is exactly the web app's."""

from typing import Annotated, Any, Literal

from mcp.server.mcpserver import Context, MCPServer
from pydantic import Field

from radicle.platform.mcp.api import api

NodeId = Annotated[str, Field(description="Node id (uuid), from search_docs or query_docs")]
SpaceKey = Annotated[str, Field(description="Space key, e.g. ai-tools")]


def _tree(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"id": i["id"], "kind": i["kind"], "title": i["title"], "children": _tree(i["children"])}
        for i in items
    ]


def register(server: MCPServer) -> None:
    @server.tool()
    async def list_spaces(ctx: Context) -> list[dict[str, Any]]:
        """Spaces you can see, with what you may do in each (create means you can write)."""
        async with api(ctx) as client:
            spaces = await client.call("GET", "/folio/spaces")
        keep = ("key", "name", "kind", "description", "permissions")
        return [{k: s[k] for k in keep} for s in spaces["items"]]

    @server.tool()
    async def get_space_tree(ctx: Context, space: SpaceKey) -> list[dict[str, Any]]:
        """The space's pages and folders as a tree of ids and titles. Blog posts are not in
        the tree; find them with query_docs `space = x AND kind = blog_post`."""
        async with api(ctx) as client:
            return _tree(await client.call("GET", f"/folio/spaces/{space}/tree"))

    @server.tool()
    async def search_docs(
        ctx: Context,
        query: Annotated[str, Field(description="Words or a question, e.g. how do I connect")],
        mode: Literal["hybrid", "text", "semantic"] = "hybrid",
        space: SpaceKey | None = None,
        doc_type: str | None = None,
        label: str | None = None,
        language: str | None = None,
        limit: Annotated[int, Field(ge=1, le=50)] = 10,
    ) -> list[dict[str, Any]]:
        """Search before writing: the docs you can see, best section first, with title,
        description, section and link. Hybrid mixes meaning and words; without an AI
        provider it searches the words."""
        params = {
            "q": query,
            "mode": mode,
            "space": space,
            "doc_type": doc_type,
            "label": label,
            "language": language,
            "limit": limit,
        }
        async with api(ctx) as client:
            found = await client.call("GET", "/folio/search", params=params)
        keep = ("node_id", "title", "description", "section", "url", "snippet", "space")
        return [{k: h[k] for k in keep} for h in found["items"]]

    @server.tool()
    async def query_docs(
        ctx: Context,
        rql: Annotated[
            str,
            Field(
                description="e.g. space = ai-tools AND doc_type = how-to AND published >= -30d "
                "ORDER BY published DESC; #onboarding AND language = es"
            ),
        ],
        limit: Annotated[int, Field(ge=1, le=100)] = 20,
    ) -> list[dict[str, Any]]:
        """Docs matching an RQL query. Fields: space, kind, doc_type, label (#label), owner,
        author, audience, language, title ~, text ~, parent, created, updated, published.
        Errors say the position and what would work."""
        async with api(ctx) as client:
            found = await client.call("GET", "/folio/nodes", params={"q": rql, "limit": limit})
        out = []
        for d in found["items"]:
            meta = d["metadata"] or {}
            out.append(
                {
                    "id": d["id"],
                    "kind": d["kind"],
                    "title": d["title"],
                    "space": d["space"],
                    "version": d["version"],
                    "published_at": d["published_at"],
                    "doc_type": meta.get("doc_type"),
                    "labels": meta.get("labels", []),
                }
            )
        return out

    @server.tool()
    async def get_page(
        ctx: Context,
        id: NodeId,
        version: Annotated[int | None, Field(description="Default: the published one")] = None,
    ) -> dict[str, Any]:
        """A page in Markdown with its metadata. Without a published version you get your
        draft (`draft: true`), if you can edit it."""
        async with api(ctx) as client:
            node = await client.call("GET", f"/folio/nodes/{id}")
            number = version or node["version"]
            page = {
                "id": node["id"],
                "kind": node["kind"],
                "title": node["title"],
                "space": node["space"],
                "path": [b["title"] for b in node["breadcrumbs"]],
            }
            if number is None:
                draft = await client.call("GET", f"/folio/nodes/{id}/draft")
                return page | {
                    "draft": True,
                    "metadata": draft["metadata"],
                    "content_md": draft["content_md"],
                }
            v = await client.call("GET", f"/folio/nodes/{id}/versions/{number}")
        return page | {
            "draft": False,
            "version": v["number"],
            "title": v["title"],
            "metadata": v["metadata"],
            "content_md": v["content_md"],
        }

    @server.tool()
    async def get_metadata_schema(ctx: Context) -> dict[str, Any]:
        """What publishing needs: the required fields and the valid document types,
        audiences and languages. Read it before create_page."""
        async with api(ctx) as client:
            schema = await client.call("GET", "/folio/metadata-schema")
        catalogs = {
            name: [{"key": e["key"], "name": e["name"]} for e in schema[name]]
            for name in ("doc_types", "audiences", "languages")
        }
        return {"fields": schema["fields"]} | catalogs

    @server.tool()
    async def get_versions(ctx: Context, id: NodeId) -> list[dict[str, Any]]:
        """A page's history, newest first: number, title, author, approver and note."""
        async with api(ctx) as client:
            history = await client.call("GET", f"/folio/nodes/{id}/versions")
        keep = ("number", "title", "author", "approved_by", "change_note", "created_at")
        return [{k: v[k] for k in keep} for v in history["items"]]
