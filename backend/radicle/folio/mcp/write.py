"""Folio's write tools (Folio 1.7): write a page in Markdown and send it for approval.
An agent's publish never goes live by itself: a Folio admin approves it first."""

from typing import Annotated, Any, Literal

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from radicle.folio.mcp.read import NodeId, SpaceKey
from radicle.platform.mcp.api import APIError, RadicleAPI, api

Markdown = Annotated[str, Field(description="The page in Markdown; # headings become its sections")]
Metadata = Annotated[
    dict[str, Any],
    Field(
        description="description, doc_type, labels, owner (@handle), audiences, language; "
        "get_metadata_schema lists the valid values"
    ),
]


def _explained(exc: APIError) -> ToolError:
    """The problem with each field that failed, so the agent can fix them all at once."""
    fields = [f"{e.get('field')}: {e.get('message')}" for e in exc.problem.get("errors", [])]
    return ToolError(f"{exc} {'; '.join(fields)}".strip() if fields else str(exc))


async def _write(client: RadicleAPI, node_id: str, body: dict[str, Any]) -> dict[str, Any]:
    try:
        draft = await client.call("PUT", f"/folio/nodes/{node_id}/draft", json=body)
    except APIError as exc:
        raise _explained(exc) from exc
    return {"metadata": draft["metadata"], "saved": draft["saved"]}


def register(server: MCPServer) -> None:
    @server.tool()
    async def create_page(
        ctx: Context,
        space: SpaceKey,
        title: str,
        content_md: Markdown,
        metadata: Metadata,
        kind: Literal["page", "blog_post"] = "page",
        parent: Annotated[str | None, Field(description="Parent page or folder id")] = None,
    ) -> dict[str, Any]:
        """Create a page or blog post with its draft. Search first (search_docs) so you do
        not duplicate a doc, and read get_metadata_schema. Nothing is published until you
        call submit_for_publication."""
        body = {"space": space, "kind": kind, "title": title, "parent": parent}
        async with api(ctx) as client:
            node = await client.call("POST", "/folio/nodes", json=body)
            try:
                draft = await _write(
                    client, node["id"], {"content_md": content_md, "metadata": metadata}
                )
            except ToolError as exc:
                raise ToolError(
                    f"The page was created (id {node['id']}) but its draft was not saved: "
                    f"{exc} Fix it with update_draft."
                ) from exc
        return {"id": node["id"], "title": node["title"], "space": node["space"]} | draft

    @server.tool()
    async def update_draft(
        ctx: Context,
        id: NodeId,
        content_md: Markdown | None = None,
        metadata: Metadata | None = None,
    ) -> dict[str, Any]:
        """Replace the draft's content and/or its metadata (whole, not merged). The
        published version does not change until the draft is approved."""
        if content_md is None and metadata is None:
            raise ToolError("Send content_md, metadata or both.")
        body = {"content_md": content_md, "metadata": metadata}
        async with api(ctx) as client:
            draft = await _write(client, id, {k: v for k, v in body.items() if v is not None})
        return {"id": id} | draft

    @server.tool()
    async def submit_for_publication(
        ctx: Context,
        id: NodeId,
        change_note: Annotated[str, Field(description="What changed, for reviewers")],
    ) -> dict[str, Any]:
        """Send the draft to be published. For agents it waits for a Folio admin's approval
        (status pending; check list_my_submissions). People with permission publish right
        away. Missing metadata is listed field by field."""
        async with api(ctx) as client:
            try:
                out = await client.call(
                    "POST", f"/folio/nodes/{id}/publish", json={"change_note": change_note}
                )
            except APIError as exc:
                raise _explained(exc) from exc
        if "status" in out:  # a submission
            return {"status": out["status"], "submission_id": out["id"], "node_id": id}
        return {"status": "published", "version": out["number"], "node_id": id}

    @server.tool()
    async def list_my_submissions(
        ctx: Context,
        status: Literal["pending", "approved", "rejected", "superseded"] | None = None,
    ) -> list[dict[str, Any]]:
        """What you sent for approval: its status, the version it became and, when it was
        rejected, the reviewer's comment to act on."""
        async with api(ctx) as client:
            found = await client.call("GET", "/folio/submissions", params={"status": status})
        keep = ("id", "node_id", "title", "status", "change_note", "review_comment", "version")
        return [{k: s[k] for k in keep} for s in found["items"]]
