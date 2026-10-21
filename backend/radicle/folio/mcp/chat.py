"""Ask the docs over MCP (Folio 4.5): the docs chat for agents, answer and citations at once."""

from typing import Annotated, Any

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from radicle.platform.mcp.api import api


def register(server: MCPServer) -> None:
    @server.tool()
    async def ask_docs(
        ctx: Context,
        question: Annotated[str, Field(description="A question, e.g. how do I connect an agent?")],
        space: Annotated[str | None, Field(description="Only docs in this space")] = None,
        doc_type: Annotated[str | None, Field(description="Only docs of this type")] = None,
        audience: Annotated[str | None, Field(description="Only docs for this audience")] = None,
    ) -> dict[str, Any]:
        """An answer written only from the docs you can see, each claim cited [n] to its
        section, with links. When the docs don't cover it, the answer says so and who to ask.
        Outdated docs come with outdated=true. Needs an AI provider with a chat model."""
        async with api(ctx) as client:
            session = await client.call("POST", "/folio/chat/sessions", json={})
            body = {"content": question, "space": space, "doc_type": doc_type}
            body["audience"] = audience
            events = await client.events(f"/folio/chat/sessions/{session['id']}/messages", body)
        for name, data in events:
            if name == "error":
                raise ToolError(str(data.get("detail", "The AI provider failed.")))
            if name == "done":
                message = data["message"]
                keep = ("n", "title", "section", "url", "outdated")
                return {
                    "answer": message["content"],
                    "citations": [{k: c[k] for k in keep} for c in message["citations"]],
                }
        raise ToolError("The chat ended without an answer. Try again.")
