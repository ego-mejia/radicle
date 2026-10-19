from httpx import AsyncClient

from tests.conftest import Team, new_ticket, patch_ticket
from tests.mcp.conftest import McpFor, payload
from tests.mcp.conftest import mcp_for as mcp_for  # the fixture

API = "/api/v1"


async def ticket(client: AsyncClient, team: Team, key: str = "PA-1") -> dict:
    return (await client.get(f"{API}/tickets/{key}", headers=team.member.headers)).json()


async def test_votes_and_backlog_by_votes(client: AsyncClient, board: Team) -> None:
    for title in ("Poco", "Mucho", "Nada"):
        await new_ticket(client, board.member, title=title, tags=["backlog"])
    for actor in (board.member, board.admin, board.viewer):
        r = await client.put(f"{API}/tickets/PA-2/vote", headers=actor.headers)
        assert r.status_code == (403 if actor is board.viewer else 200)
    r = await client.put(f"{API}/tickets/PA-2/vote", headers=board.member.headers)
    assert r.json() == {"vote_count": 2, "voted_by_me": True}  # twice changes nothing
    await client.put(f"{API}/tickets/PA-1/vote", headers=board.member.headers)
    r = await client.put(f"{API}/tickets/PA-1/vote", headers=board.agent.headers)
    assert r.status_code == 403 and "agents" in r.json()["detail"].lower()

    r = await client.get(
        f"{API}/tickets",
        headers=board.member.headers,
        params={"q": "#backlog ORDER BY votes DESC, key ASC"},
    )
    assert [t["key"] for t in r.json()["items"]] == ["PA-2", "PA-1", "PA-3"]
    assert r.json()["items"][0]["vote_count"] == 2
    r = await client.get(f"{API}/tickets", headers=board.member.headers, params={"q": "votes >= 2"})
    assert [t["key"] for t in r.json()["items"]] == ["PA-2"]

    t = await ticket(client, board, "PA-2")
    assert t["vote_count"] == 2 and t["voted_by_me"] is True
    r = await client.get(f"{API}/tickets/PA-2/voters", headers=board.viewer.headers)
    assert [u["handle"] for u in r.json()["items"]] == ["luis", "ana"]
    r = await client.delete(f"{API}/tickets/PA-2/vote", headers=board.member.headers)
    assert r.json() == {"vote_count": 1, "voted_by_me": False}
    r = await client.delete(f"{API}/tickets/PA-2/vote", headers=board.member.headers)
    assert r.json()["vote_count"] == 1
    history = (await client.get(f"{API}/tickets/PA-2/history", headers=board.member.headers)).json()
    assert [e["event_type"] for e in history["items"]][:3] == [
        "vote_removed",
        "vote_added",
        "vote_added",
    ]
    assert t["version"] == 1  # votes are not edits


async def test_original_estimate_and_remaining(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.member)
    t = await ticket(client, board)
    assert t["original_estimate_hours"] is None and t["remaining_hours"] is None
    await patch_ticket(client, board.member, "PA-1", estimate_hours=8)
    await patch_ticket(client, board.member, "PA-1", estimate_hours=10)
    t = await ticket(client, board)
    assert (t["original_estimate_hours"], t["estimate_hours"], t["remaining_hours"]) == (8, 10, 10)

    r = await client.post(
        f"{API}/tickets/PA-1/worklogs", headers=board.member.headers, json={"minutes": 150}
    )
    assert r.status_code == 201
    t = await ticket(client, board)
    assert (t["spent_hours"], t["remaining_hours"], t["remaining_mode"]) == (2.5, 7.5, "auto")

    r = await patch_ticket(client, board.member, "PA-1", remaining_hours=3)
    t = r.json()
    assert (t["remaining_hours"], t["remaining_mode"]) == (3, "manual")
    await client.post(
        f"{API}/tickets/PA-1/worklogs", headers=board.member.headers, json={"minutes": 60}
    )
    assert (await ticket(client, board))["remaining_hours"] == 3  # manual stays
    r = await patch_ticket(client, board.member, "PA-1", remaining_mode="auto")
    assert (r.json()["remaining_hours"], r.json()["remaining_mode"]) == (6.5, "auto")
    await client.post(
        f"{API}/tickets/PA-1/worklogs", headers=board.member.headers, json={"minutes": 1440}
    )
    assert (await ticket(client, board))["remaining_hours"] == 0
    created = await new_ticket(client, board.member, estimate_hours=4)
    assert created["original_estimate_hours"] == 4 and created["remaining_hours"] == 4


async def test_worklogs_permissions_and_history(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.member)
    r = await client.post(
        f"{API}/tickets/PA-1/worklogs",
        headers=board.member.headers,
        json={"minutes": 90, "description": "Pruebas", "started_at": "2026-10-18T09:00:00Z"},
    )
    log = r.json()
    assert log["user"]["handle"] == "luis" and log["started_at"] == "2026-10-18T09:00:00Z"
    for minutes in (0, 1441):
        r = await client.post(
            f"{API}/tickets/PA-1/worklogs", headers=board.member.headers, json={"minutes": minutes}
        )
        assert r.status_code == 422
    r = await client.post(
        f"{API}/tickets/PA-1/worklogs", headers=board.viewer.headers, json={"minutes": 10}
    )
    assert r.status_code == 403

    r = await client.patch(
        f"{API}/worklogs/{log['id']}", headers=board.agent.headers, json={"minutes": 10}
    )
    assert r.status_code == 403 and "your own worklogs" in r.json()["detail"]
    r = await client.patch(
        f"{API}/worklogs/{log['id']}",
        headers=board.member.headers,
        json={"minutes": 30, "description": None},
    )
    assert r.json()["minutes"] == 30 and r.json()["description"] is None
    assert (await ticket(client, board))["spent_hours"] == 0.5
    r = await client.patch(
        f"{API}/worklogs/{log['id']}", headers=board.admin.headers, json={"description": "Fix"}
    )
    assert r.status_code == 200
    r = await client.get(f"{API}/tickets/PA-1/worklogs", headers=board.viewer.headers)
    assert [w["description"] for w in r.json()["items"]] == ["Fix"]
    r = await client.delete(f"{API}/worklogs/{log['id']}", headers=board.member.headers)
    assert r.status_code == 204
    assert (await ticket(client, board))["spent_hours"] == 0
    r = await client.delete(f"{API}/worklogs/{log['id']}", headers=board.member.headers)
    assert r.status_code == 404
    events = (await client.get(f"{API}/tickets/PA-1/history", headers=board.member.headers)).json()
    kinds = [e["event_type"] for e in events["items"]]
    assert kinds[:4] == ["worklog_deleted", "worklog_updated", "worklog_updated", "worklog_added"]

    r = await client.get(f"{API}/tickets", headers=board.member.headers, params={"q": "spent > 0"})
    assert r.json()["total"] == 0


async def test_rql_time_fields(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.member, estimate_hours=8)
    await new_ticket(client, board.member, estimate_hours=2)
    await client.post(
        f"{API}/tickets/PA-2/worklogs", headers=board.member.headers, json={"minutes": 300}
    )
    await client.post(
        f"{API}/tickets/PA-1/worklogs", headers=board.member.headers, json={"minutes": 90}
    )

    async def keys(q: str) -> list[str]:
        r = await client.get(f"{API}/tickets", headers=board.member.headers, params={"q": q})
        assert r.status_code == 200, r.text
        return [t["key"] for t in r.json()["items"]]

    assert await keys("spent > 4") == ["PA-2"]
    assert await keys("spent >= 1.5 ORDER BY spent ASC") == ["PA-1", "PA-2"]
    assert await keys("remaining = 0") == ["PA-2"]
    assert await keys("original_estimate > 4") == ["PA-1"]
    assert await keys("remaining > 6 ORDER BY remaining DESC") == ["PA-1"]


async def test_transition_logs_time(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.member)
    r = await client.post(
        f"{API}/tickets/PA-1/transitions",
        headers=board.member.headers,
        json={"to_status": "In Progress", "log_minutes": 45},
    )
    assert r.status_code == 200 and r.json()["spent_hours"] == 0.75
    logs = (await client.get(f"{API}/tickets/PA-1/worklogs", headers=board.member.headers)).json()
    assert logs["items"][0]["description"] == "Moving to In Progress"


async def test_acceptance_agent_logs_two_hours(
    client: AsyncClient, board: Team, mcp_for: McpFor
) -> None:
    await new_ticket(client, board.member, assignee="agent-backend", estimate_hours=5)
    async with mcp_for(board.agent) as mcp:
        result = payload(
            await mcp.call_tool(
                "log_work", {"key": "PA-1", "minutes": 120, "description": "Webhook de pagos"}
            )
        )
        assert result["spent_hours"] == 2 and result["remaining_hours"] == 3
        logs = payload(await mcp.call_tool("list_worklogs", {"key": "PA-1"}))
        assert logs["items"][0]["user"] == "agent-backend"
        moved = payload(
            await mcp.call_tool(
                "transition_ticket", {"key": "PA-1", "to_status": "In Progress", "log_minutes": 30}
            )
        )
        assert moved["status"] == "In Progress"
        detail = payload(await mcp.call_tool("get_ticket", {"key": "PA-1", "comments": 0}))
        assert detail["spent_hours"] == 2.5 and detail["vote_count"] == 0
