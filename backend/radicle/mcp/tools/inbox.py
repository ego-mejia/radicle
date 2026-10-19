"""Inbox tools: list, score, approve, discard and mark duplicates of drafts."""

from typing import Annotated, Any, Literal

from mcp.server.mcpserver import Context, MCPServer
from pydantic import Field

from radicle.mcp.api import api
from radicle.mcp.tools.common import Key, Priority

Score = Annotated[int, Field(ge=1, le=5)]
Classification = Literal["idea", "experiment", "complaint", "suggestion"]


def _item(t: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": t["key"],
        "title": t["title"],
        "classification": t["classification"],
        "origin": t["origin"],
        "votes": t["vote_count"],
        "impact": t["impact"],
        "effort": t["effort"],
        "status": t["status"]["name"],
        "created_at": t.get("created_at"),
    }


def register(server: MCPServer) -> None:
    @server.tool()
    async def list_inbox(
        ctx: Context,
        project: Annotated[str, Field(description="Project key, e.g. PA")],
        tab: Literal["new", "in_review", "approved", "discarded"] = "new",
        classification: Classification | None = None,
        sort: Literal["votes", "age", "score"] = "votes",
    ) -> dict[str, Any]:
        """Inbox drafts with votes, impact and effort. Score = impact * 2 - effort."""
        params: dict[str, Any] = {"tab": tab, "sort": sort}
        if classification:
            params["classification"] = classification
        async with api(ctx) as client:
            out = await client.call("GET", f"/projects/{project}/inbox", params=params)
        return {"counts": out["counts"], "items": [_item(t) for t in out["items"]]}

    @server.tool()
    async def score_inbox_item(
        ctx: Context,
        key: Key,
        impact: Score,
        effort: Score,
        classification: Classification | None = None,
    ) -> dict[str, Any]:
        """Set impact and effort (1 to 5) and optionally the classification of a draft."""
        body: dict[str, Any] = {"impact": impact, "effort": effort}
        if classification:
            body["classification"] = classification
        async with api(ctx) as client:
            current = await client.call("GET", f"/tickets/{key}")
            body["expected_version"] = current["version"]
            ticket = await client.call("PATCH", f"/tickets/{key}", json=body)
        return {
            "key": ticket["key"],
            "impact": ticket["impact"],
            "effort": ticket["effort"],
            "classification": ticket["classification"],
        }

    @server.tool()
    async def approve_inbox_item(
        ctx: Context,
        key: Key,
        type: Literal["task", "bug"],
        area: str,
        milestone: str | None = None,
        priority: Priority | None = None,
        assignee: Annotated[str | None, Field(description="Handle")] = None,
    ) -> dict[str, Any]:
        """Approve a draft and turn it into a task or bug in the same ticket; it keeps its
        origin, classification, votes and comments."""
        body = {
            "type": type,
            "area": area,
            "milestone": milestone,
            "priority": priority,
            "assignee": assignee,
        }
        async with api(ctx) as client:
            ticket = await client.call(
                "POST",
                f"/tickets/{key}/inbox/approve",
                json={k: v for k, v in body.items() if v is not None},
            )
        return {
            "key": ticket["key"],
            "type": ticket["type"],
            "status": ticket["status"]["name"],
            "area": ticket["area"],
            "origin": ticket["origin"],
            "classification": ticket["classification"],
        }

    @server.tool()
    async def discard_inbox_item(
        ctx: Context,
        key: Key,
        public_comment: Annotated[
            str | None, Field(description="Shown to whoever sent it, on their tracking page")
        ] = None,
    ) -> dict[str, Any]:
        """Discard a draft (won't do)."""
        async with api(ctx) as client:
            ticket = await client.call(
                "POST", f"/tickets/{key}/inbox/discard", json={"public_comment": public_comment}
            )
        return {"key": ticket["key"], "status": ticket["status"]["name"]}

    @server.tool()
    async def mark_inbox_duplicate(
        ctx: Context, key: Key, original: Annotated[str, Field(description="Original key")]
    ) -> dict[str, Any]:
        """Mark a draft as a duplicate: it links to the original, closes, and its voters
        are added to the original's (no repeats)."""
        async with api(ctx) as client:
            ticket = await client.call(
                "POST", f"/tickets/{key}/inbox/duplicate", json={"original": original}
            )
            original_ticket = await client.call("GET", f"/tickets/{original}")
        return {
            "key": ticket["key"],
            "status": ticket["status"]["name"],
            "original": original_ticket["key"],
            "original_votes": original_ticket["vote_count"],
        }
