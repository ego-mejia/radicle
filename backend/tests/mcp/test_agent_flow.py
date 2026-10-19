"""The stage 1 acceptance flow, as an agent connected over MCP."""

from httpx import AsyncClient

from tests.conftest import Team, new_ticket
from tests.mcp.conftest import McpFor, payload


async def test_agent_flow_end_to_end(client: AsyncClient, board: Team, mcp_for: McpFor) -> None:
    for i in range(3):
        await new_ticket(client, board.member, title=f"T{i + 1}")
    await new_ticket(
        client,
        board.member,
        title="API de pagos",
        assignee="agent-backend",
        description_md="Integrar cobro.\n\n- [ ] Definir endpoints\n- [ ] Webhook @luis",
    )
    await new_ticket(client, board.member, title="Checkout")

    async with mcp_for(board.agent) as mcp:
        me = payload(await mcp.call_tool("whoami"))
        assert me["handle"] == "agent-backend" and me["kind"] == "agent"
        assert me["projects"] == [{"key": "PA", "name": "ProyectoA", "role": "member"}]

        mine = payload(await mcp.call_tool("my_tickets"))
        assert [t["key"] for t in mine["items"]] == ["PA-4"]

        ticket = payload(await mcp.call_tool("get_ticket", {"key": "PA-4"}))
        assert [i["text"] for i in ticket["checklist"]] == ["Definir endpoints", "Webhook"]

        moved = payload(
            await mcp.call_tool("transition_ticket", {"key": "PA-4", "to_status": "In Progress"})
        )
        assert moved["status"] == "In Progress"

        checked = payload(
            await mcp.call_tool("set_checklist_item", {"key": "PA-4", "index": 0, "checked": True})
        )
        assert checked["checklist"][0]["checked"] is True

        comment = payload(
            await mcp.call_tool(
                "add_comment", {"key": "PA-4", "body": "Endpoints definidos. Sigue el webhook."}
            )
        )
        assert comment["author"] == "agent-backend"

        links = payload(
            await mcp.call_tool(
                "link_tickets", {"source": "PA-4", "type": "blocks", "target": "PA-5"}
            )
        )
        assert links == [{"id": links[0]["id"], "label": "blocks", "key": "PA-5"}]

        found = payload(await mcp.call_tool("search_tickets", {"query": "blocked = true"}))
        assert [t["key"] for t in found["items"]] == ["PA-5"]

    # Everything shows up in the API and the history as done by the agent.
    r = await client.get("/api/v1/tickets/PA-4/history", headers=board.member.headers)
    agent_events = [e for e in r.json()["items"] if e["actor"]["handle"] == "agent-backend"]
    assert [e["event_type"] for e in agent_events] == [
        "link_added",
        "comment_added",
        "checklist_item_toggled",
        "status_changed",
    ]
    assert all(e["actor"]["kind"] == "agent" for e in agent_events)
    r = await client.get("/api/v1/tickets/PA-5/history", headers=board.member.headers)
    assert r.json()["items"][0]["actor"]["handle"] == "agent-backend"
    pa4 = (await client.get("/api/v1/tickets/PA-4", headers=board.member.headers)).json()
    assert pa4["status"]["name"] == "In Progress" and pa4["checklist"][0]["checked"] is True
    assert pa4["comments_count"] == 1
