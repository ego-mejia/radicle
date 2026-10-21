"""Attachment tools."""

import base64
import binascii
from typing import Annotated, Any, Literal

from mcp.server.mcpserver import Context, MCPServer
from pydantic import Field

from radicle.docket.mcp.api import api
from radicle.docket.mcp.tools.common import APIErrorMessage, Key

MCP_UPLOAD_LIMIT = 10 * 1024 * 1024
READ_LIMIT = 200 * 1024
TEXT_TYPES = ("text/", "application/json")


def attachment_brief(a: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": a["id"],
        "filename": a["filename"],
        "mime_type": a["mime_type"],
        "size_bytes": a["size_bytes"],
        "is_image": a["is_image"],
        "width": a["width"],
        "height": a["height"],
        "uploader": a["uploader"]["handle"],
        "url": a["url"],
        "markdown": a["markdown"],
    }


def register(server: MCPServer) -> None:
    @server.tool()
    async def upload_attachment(
        ctx: Context,
        key: Key,
        filename: str,
        content_base64: Annotated[str, Field(description="File content in base64, max 10 MB")],
        resize: Annotated[
            Literal["original", "large", "medium", "small"] | None,
            Field(description="Images only; default large (2048 px)"),
        ] = None,
        comment_id: str | None = None,
    ) -> dict[str, Any]:
        """Attach a file to a ticket. The result has `markdown` to reference it in a
        description or comment."""
        try:
            content = base64.b64decode(content_base64, validate=True)
        except (binascii.Error, ValueError):
            raise APIErrorMessage("content_base64 is not valid base64.") from None
        if len(content) > MCP_UPLOAD_LIMIT:
            raise APIErrorMessage(
                f"The file is {len(content) / 1024 / 1024:.1f} MB; through MCP the limit is 10 MB."
            )
        async with api(ctx) as client:
            attachment = await client.call(
                "POST",
                f"/tickets/{key}/attachments",
                files={"file": (filename, content)},
                data={"resize": resize, "comment_id": comment_id},
            )
        return attachment_brief(attachment)

    @server.tool()
    async def list_attachments(ctx: Context, key: Key) -> list[dict[str, Any]]:
        """Files attached to a ticket: name, type, size and a download URL."""
        async with api(ctx) as client:
            page = await client.call("GET", f"/tickets/{key}/attachments")
        return [attachment_brief(a) for a in page["items"]]

    @server.tool()
    async def read_attachment(
        ctx: Context, id: Annotated[str, Field(description="Attachment id from list_attachments")]
    ) -> dict[str, Any]:
        """Content of a text attachment (md, txt, json, csv, logs), up to 200 KB."""
        async with api(ctx) as client:
            response = await client.raw(f"/attachments/{id}/content")
        mime = response.headers.get("content-type", "").split(";")[0]
        if not mime.startswith(TEXT_TYPES):
            raise APIErrorMessage(
                f"This attachment is {mime}, not text. Open its URL from list_attachments."
            )
        body = response.content
        truncated = len(body) > READ_LIMIT
        return {
            "id": id,
            "mime_type": mime,
            "truncated": truncated,
            "content": body[:READ_LIMIT].decode("utf-8", errors="replace"),
        }
