import base64

from httpx import AsyncClient

from tests.conftest import Team, new_ticket
from tests.mcp.conftest import McpFor, error_text, payload


async def test_agent_uploads_lists_and_reads(
    client: AsyncClient, board: Team, mcp_for: McpFor
) -> None:
    await new_ticket(client, board.member)
    log = "2026-10-19 ERROR pago rechazado\n" * 3
    async with mcp_for(board.agent) as mcp:
        uploaded = payload(
            await mcp.call_tool(
                "upload_attachment",
                {
                    "key": "PA-1",
                    "filename": "pagos.log",
                    "content_base64": base64.b64encode(log.encode()).decode(),
                },
            )
        )
        assert uploaded["mime_type"] == "text/plain" and uploaded["uploader"] == "agent-backend"
        listed = payload(await mcp.call_tool("list_attachments", {"key": "PA-1"}))
        assert [a["filename"] for a in listed] == ["pagos.log"]
        read = payload(await mcp.call_tool("read_attachment", {"id": uploaded["id"]}))
        assert read["content"] == log and read["truncated"] is False
        ticket = payload(await mcp.call_tool("get_ticket", {"key": "PA-1", "comments": 0}))
        assert ticket["attachments"][0]["filename"] == "pagos.log"

        assert "not valid base64" in error_text(
            await mcp.call_tool(
                "upload_attachment", {"key": "PA-1", "filename": "x", "content_base64": "%%%"}
            )
        )
        binary = payload(
            await mcp.call_tool(
                "upload_attachment",
                {
                    "key": "PA-1",
                    "filename": "blob.bin",
                    "content_base64": base64.b64encode(bytes(range(256))).decode(),
                },
            )
        )
        assert "not text" in error_text(
            await mcp.call_tool("read_attachment", {"id": binary["id"]})
        )
        big = base64.b64encode(b"x" * (10 * 1024 * 1024 + 1)).decode()
        assert "limit is 10 MB" in error_text(
            await mcp.call_tool(
                "upload_attachment", {"key": "PA-1", "filename": "big", "content_base64": big}
            )
        )
