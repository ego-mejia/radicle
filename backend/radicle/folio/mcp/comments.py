"""Folio's comment tools (Folio 2.3): read the discussion on a page, comment at its foot
or on a phrase, reply, and resolve threads."""

from typing import Annotated, Any

from mcp.server.mcpserver import Context, MCPServer
from pydantic import Field

from radicle.folio.mcp.read import NodeId
from radicle.platform.mcp.api import api


def _thread(t: dict[str, Any]) -> dict[str, Any]:
    return {
        "thread_id": t["id"],
        "kind": t["kind"],
        "quote": t["anchor"]["quote"] if t["anchor"] else None,
        "orphaned": t["orphaned"],
        "resolved": t["resolved_at"] is not None,
        "comments": [
            {"id": c["id"], "author": c["author"], "body": c["body_md"], "at": c["created_at"]}
            for c in t["comments"]
        ],
    }


def register(server: MCPServer) -> None:
    @server.tool()
    async def list_comments(
        ctx: Context, id: NodeId, include_resolved: bool = False
    ) -> list[dict[str, Any]]:
        """The page's comment threads with their replies; inline ones carry the text they
        quote (`orphaned` when that text was deleted)."""
        async with api(ctx) as client:
            found = await client.call(
                "GET",
                f"/folio/nodes/{id}/comments",
                params={"include_resolved": include_resolved},
            )
        return [_thread(t) for t in found["items"]]

    @server.tool()
    async def add_comment(
        ctx: Context,
        id: NodeId,
        body: Annotated[str, Field(description="Markdown; @handle notifies that person")],
        quote: Annotated[
            str | None,
            Field(description="Comment on this exact text (its first occurrence in the page)"),
        ] = None,
        thread_id: Annotated[str | None, Field(description="Reply to this thread")] = None,
    ) -> dict[str, Any]:
        """Comment at the foot of a page, inline on `quote`, or reply to `thread_id`."""
        payload: dict[str, Any] = {"body": body, "quote": quote, "thread_id": thread_id}
        async with api(ctx) as client:
            thread = await client.call(
                "POST",
                f"/folio/nodes/{id}/comments",
                json={k: v for k, v in payload.items() if v is not None},
            )
        return _thread(thread)

    @server.tool()
    async def resolve_comment(
        ctx: Context,
        thread_id: Annotated[str, Field(description="The thread, from list_comments")],
    ) -> dict[str, Any]:
        """Resolve a thread once its point is addressed; it stays in the page's history."""
        async with api(ctx) as client:
            thread = await client.call("POST", f"/folio/comments/{thread_id}/resolve")
        return _thread(thread)
