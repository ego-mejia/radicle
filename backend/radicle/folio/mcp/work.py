"""Folio's tools for an agent's day (Folio 2.4): its tasks, what it follows, its feed and
its notifications."""

from typing import Annotated, Any, Literal

from mcp.server.mcpserver import Context, MCPServer
from pydantic import Field

from radicle.platform.mcp.api import api


def register(server: MCPServer) -> None:
    @server.tool()
    async def list_my_tasks(
        ctx: Context, status: Literal["open", "done", "all"] = "open"
    ) -> list[dict[str, Any]]:
        """Action items assigned to you in documents you can see, by due date: each with
        its id (for set_task_done), text, due date, bucket (overdue, today, upcoming,
        no_date) and the page it lives in."""
        async with api(ctx) as client:
            found = await client.call("GET", "/folio/me/tasks", params={"status": status})
        return [
            {
                "id": t["id"],
                "text": t["text"],
                "done": t["done"],
                "due": t["due"],
                "bucket": t["bucket"],
                "page": {"id": t["node"]["id"], "title": t["node"]["title"]},
            }
            for t in found["items"]
        ]

    @server.tool()
    async def set_task_done(
        ctx: Context,
        id: Annotated[str, Field(description="Task id from list_my_tasks")],
        done: bool = True,
    ) -> dict[str, Any]:
        """Check a task off (or back on). The document changes too, live for anyone
        editing it."""
        async with api(ctx) as client:
            t = await client.call("PATCH", f"/folio/action-items/{id}", json={"done": done})
        return {"id": t["id"], "text": t["text"], "done": t["done"]}

    @server.tool()
    async def watch(
        ctx: Context,
        target_type: Literal["node", "space"],
        id: Annotated[str, Field(description="A page id, or a space key or id")],
        follow: bool = True,
    ) -> dict[str, Any]:
        """Follow a page or a space (or stop with follow=false): you then hear about its
        publications and comments in list_notifications and get_feed."""
        async with api(ctx) as client:
            target = id
            if target_type == "space" and len(id) != 36:
                target = (await client.call("GET", f"/folio/spaces/{id}"))["id"]
            method = "PUT" if follow else "DELETE"
            await client.call(method, f"/folio/watch/{target_type}/{target}")
        return {"target_type": target_type, "id": target, "following": follow}

    @server.tool()
    async def get_feed(
        ctx: Context, limit: Annotated[int, Field(ge=1, le=50)] = 20
    ) -> list[dict[str, Any]]:
        """What's new for you: publications of the pages and spaces you follow, then the
        week's most read in your spaces (`reason` says which)."""
        async with api(ctx) as client:
            found = await client.call("GET", "/folio/me/feed", params={"limit": limit})
        keep = ("id", "title", "description", "space", "author", "published_at", "reason")
        return [{k: item[k] for k in keep} for item in found["items"]]

    @server.tool()
    async def list_notifications(
        ctx: Context, unread_only: bool = True, mark_read: bool = False
    ) -> dict[str, Any]:
        """Your notifications (mentions, assigned tasks, shares, comments), newest first.
        With mark_read=true the ones returned are marked read."""
        async with api(ctx) as client:
            page = await client.call(
                "GET", "/me/notifications", params={"unread_only": unread_only, "limit": 50}
            )
            items = page["items"]
            if mark_read and items:
                await client.call(
                    "POST", "/me/notifications/read", json={"ids": [n["id"] for n in items]}
                )
        keep = ("id", "app", "type", "title", "body", "link", "read", "created_at")
        return {"unread": page["unread"], "items": [{k: n[k] for k in keep} for n in items]}
