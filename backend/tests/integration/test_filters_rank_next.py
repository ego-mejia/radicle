import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import Team, new_ticket, run_jobs
from tests.mcp.conftest import McpFor, error_text, payload
from tests.mcp.conftest import mcp_for as mcp_for  # the fixture

API = "/api/v1"


async def keys(client: AsyncClient, actor, q: str) -> list[str]:  # type: ignore[no-untyped-def]
    r = await client.get(f"{API}/tickets", headers=actor.headers, params={"q": q})
    assert r.status_code == 200, r.text
    return [t["key"] for t in r.json()["items"]]


async def test_saved_filters_and_rql(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.member, type="bug", milestone="V1", title="Bug V1")
    await new_ticket(client, board.member, type="bug", title="Bug suelto")
    await new_ticket(client, board.member, milestone="V1", title="Task V1")
    r = await client.post(
        f"{API}/filters",
        headers=board.member.headers,
        json={
            "name": "Bugs abiertos de V1",
            "rql": "type = bug AND milestone = V1 AND category != done",
            "visibility": "project",
            "project": "PA",
        },
    )
    assert r.status_code == 201, r.text
    shared = r.json()
    assert shared["project"] == "PA" and shared["mine"] is True
    assert await keys(client, board.viewer, 'filter = "Bugs abiertos de V1"') == ["PA-1"]
    assert await keys(client, board.viewer, 'filter = "bugs abiertos de v1" OR key = PA-3') == [
        "PA-3",
        "PA-1",
    ]
    r = await client.get(
        f"{API}/tickets", headers=board.viewer.headers, params={"q": 'filter = "Nope"'}
    )
    assert (
        r.json()["total"] == 0
        and "Filter 'Nope' does not exist" in r.json()["warnings"][0]["message"]
    )

    # Filters inside filters, and a loop.
    await client.post(
        f"{API}/filters",
        headers=board.member.headers,
        json={"name": "V1 o bugs", "rql": 'filter = "Bugs abiertos de V1" OR key = PA-2'},
    )
    assert await keys(client, board.member, 'filter = "V1 o bugs"') == ["PA-2", "PA-1"]
    me = await client.post(
        f"{API}/filters", headers=board.member.headers, json={"name": "Bucle", "rql": "key = PA-1"}
    )
    await client.patch(
        f"{API}/filters/{me.json()['id']}",
        headers=board.member.headers,
        json={"rql": 'filter = "Bucle"'},
    )
    r = await client.get(
        f"{API}/tickets", headers=board.member.headers, params={"q": 'filter = "Bucle"'}
    )
    assert r.status_code == 422 and "refers to itself" in r.json()["detail"]

    # Visibility: private filters stay private; outsiders do not see project filters.
    r = await client.get(f"{API}/filters", headers=board.viewer.headers)
    assert [f["name"] for f in r.json()["items"]] == ["Bugs abiertos de V1"]
    r = await client.get(f"{API}/filters", headers=board.outsider.headers)
    assert r.json()["items"] == []
    r = await client.patch(
        f"{API}/filters/{shared['id']}", headers=board.viewer.headers, json={"name": "Mío"}
    )
    assert r.status_code == 403
    r = await client.delete(f"{API}/filters/{shared['id']}", headers=board.outsider.headers)
    assert r.status_code == 404

    cases = [
        ({"name": "x", "rql": "type = = bug"}, 422),
        ({"name": "Bugs abiertos de V1", "rql": "type = bug"}, 409),
        ({"name": "y", "rql": "type = bug", "visibility": "instance"}, 403),
        ({"name": "z", "rql": "type = bug", "visibility": "project"}, 422),
        ({"name": " ", "rql": "type = bug"}, 422),
    ]
    for body, status in cases:
        r = await client.post(f"{API}/filters", headers=board.member.headers, json=body)
        assert r.status_code == status, (body, r.text)
    r = await client.post(
        f"{API}/filters",
        headers=board.instance.headers,
        json={"name": "Todo", "rql": "category != done", "visibility": "instance"},
    )
    assert r.status_code == 201
    r = await client.get(f"{API}/filters", headers=board.outsider.headers)
    assert [f["name"] for f in r.json()["items"]] == ["Todo"]
    r = await client.delete(f"{API}/filters/{shared['id']}", headers=board.member.headers)
    assert r.status_code == 204


async def test_rank_before_after_and_rebalance(
    client: AsyncClient, db: AsyncSession, board: Team, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("radicle.services.ranking.REBALANCE_AT", 6)
    for i in range(4):
        await new_ticket(client, board.member, title=f"t{i + 1}")
    order = "project = PA ORDER BY rank ASC"
    assert await keys(client, board.member, order) == ["PA-1", "PA-2", "PA-3", "PA-4"]
    r = await client.post(
        f"{API}/tickets/PA-4/rank", headers=board.member.headers, json={"before": "PA-1"}
    )
    assert r.status_code == 200
    assert await keys(client, board.member, order) == ["PA-4", "PA-1", "PA-2", "PA-3"]
    await client.post(
        f"{API}/tickets/PA-1/rank", headers=board.member.headers, json={"after": "PA-3"}
    )
    assert await keys(client, board.member, order) == ["PA-4", "PA-2", "PA-3", "PA-1"]
    await client.post(
        f"{API}/tickets/PA-2/rank", headers=board.member.headers, json={"after": "PA-4"}
    )
    assert await keys(client, board.member, order) == ["PA-4", "PA-2", "PA-3", "PA-1"]
    history = (await client.get(f"{API}/tickets/PA-1/history", headers=board.member.headers)).json()
    assert history["items"][0]["event_type"] == "rank_changed"

    for body, message in (
        ({}, "exactly one"),
        ({"before": "PA-1", "after": "PA-2"}, "exactly one"),
        ({"before": "PA-1"}, "against itself"),
    ):
        r = await client.post(f"{API}/tickets/PA-1/rank", headers=board.member.headers, json=body)
        assert r.status_code == 422 and message in r.json()["detail"]
    r = await client.post(
        f"{API}/tickets/PA-1/rank", headers=board.viewer.headers, json={"before": "PA-2"}
    )
    assert r.status_code == 403

    # Squeezing again and again between the same two tickets triggers a rebalance.
    for _ in range(12):
        await client.post(
            f"{API}/tickets/PA-1/rank", headers=board.member.headers, json={"after": "PA-4"}
        )
        await client.post(
            f"{API}/tickets/PA-2/rank", headers=board.member.headers, json={"after": "PA-4"}
        )
    ran = await run_jobs(db)
    assert "rebalance_ranks" in ran
    ranks = (
        await client.get(f"{API}/tickets", headers=board.member.headers, params={"q": order})
    ).json()
    assert [t["key"] for t in ranks["items"]] == ["PA-4", "PA-2", "PA-1", "PA-3"]
    assert max(len(t["rank"]) for t in ranks["items"]) <= 3


async def test_next_ticket(client: AsyncClient, db: AsyncSession, board: Team) -> None:
    await new_ticket(client, board.member, title="Bloqueador", area="Legal")
    await new_ticket(client, board.member, title="Bloqueado")
    await new_ticket(client, board.member, title="De Luis", assignee="luis")
    await new_ticket(client, board.member, title="Libre", type="bug", area="Frontend")
    await client.post(
        f"{API}/tickets/PA-1/links",
        headers=board.member.headers,
        json={"type": "blocks", "target": "PA-2"},
    )
    url = f"{API}/tickets/next"
    r = await client.post(url, headers=board.agent.headers, json={})
    assert r.json()["ticket"]["key"] == "PA-1"
    r = await client.post(url, headers=board.agent.headers, json={"type": "bug"})
    assert r.json()["ticket"]["key"] == "PA-4"
    r = await client.post(url, headers=board.member.headers, json={"area": "Backend"})
    assert r.json()["ticket"]["key"] == "PA-3"  # luis's own ticket counts, PA-2 is blocked

    r = await client.post(url, headers=board.agent.headers, json={"claim": True})
    claimed = r.json()["ticket"]
    assert claimed["key"] == "PA-1"
    assert claimed["assignee"]["handle"] == "agent-backend"
    assert claimed["status"]["name"] == "In Progress"
    r = await client.post(url, headers=board.agent.headers, json={"claim": True, "area": "Backend"})
    assert r.json()["ticket"] is None  # PA-2 blocked, PA-3 is luis's
    r = await client.post(url, headers=board.viewer.headers, json={"claim": True})
    assert r.json()["ticket"] is None  # viewers cannot claim
    r = await client.post(url, headers=board.outsider.headers, json={})
    assert r.json()["ticket"] is None


async def test_preferences(client: AsyncClient, board: Team) -> None:
    r = await client.get(f"{API}/me/preferences", headers=board.member.headers)
    assert r.json() == {
        "theme": "system",
        "language": None,
        "shortcuts": True,
        "density": "comfortable",
    }
    r = await client.patch(
        f"{API}/me/preferences",
        headers=board.member.headers,
        json={"shortcuts": False, "theme": "dark", "language": "es"},
    )
    assert r.json()["shortcuts"] is False and r.json()["theme"] == "dark"
    r = await client.patch(
        f"{API}/me/preferences", headers=board.member.headers, json={"density": "tiny"}
    )
    assert r.status_code == 422
    r = await client.patch(
        f"{API}/me/preferences", headers=board.member.headers, json={"font": "x"}
    )
    assert r.status_code == 422 and "Unknown preference" in r.json()["detail"]
    r = await client.get(f"{API}/me/preferences", headers=board.agent.headers)
    assert r.status_code == 403


async def test_acceptance_agent_claims_next_ticket(
    client: AsyncClient, db: AsyncSession, board: Team, mcp_for: McpFor
) -> None:
    for title in ("Segundo", "Primero", "Tercero"):
        await new_ticket(client, board.member, title=title)
    await client.post(
        f"{API}/tickets/PA-2/rank", headers=board.member.headers, json={"before": "PA-1"}
    )
    await client.post(
        f"{API}/filters",
        headers=board.member.headers,
        json={"name": "Míos", "rql": "assignee = luis"},
    )
    async with mcp_for(board.agent) as mcp:
        peek = payload(await mcp.call_tool("next_ticket", {"project": "PA"}))
        assert peek["ticket"]["key"] == "PA-2" and peek["ticket"]["assignee"] is None
        got = payload(await mcp.call_tool("next_ticket", {"project": "PA", "claim": True}))
        assert got["ticket"]["key"] == "PA-2"
        assert got["ticket"]["assignee"] == "agent-backend"
        assert got["ticket"]["category"] == "in_progress"
        ranked = payload(await mcp.call_tool("rank_ticket", {"key": "PA-3", "before": "PA-1"}))
        assert ranked["key"] == "PA-3"
        saved = payload(
            await mcp.call_tool(
                "save_filter", {"name": "En curso", "query": "category = in_progress"}
            )
        )
        assert saved["visibility"] == "private"
        names = [f["name"] for f in payload(await mcp.call_tool("list_filters", {}))]
        assert names == ["En curso"]
        run = payload(await mcp.call_tool("run_filter", {"name": "En curso"}))
        assert [t["key"] for t in run["items"]] == ["PA-2"]
        assert "no saved filter" in error_text(await mcp.call_tool("run_filter", {"name": "Míos"}))
    r = await client.get(f"{API}/tickets/PA-2", headers=board.member.headers)
    assert r.json()["status"]["name"] == "In Progress"


async def test_claim_respects_transition_rules(
    client: AsyncClient, db: AsyncSession, board: Team
) -> None:
    await client.post(f"{API}/projects/PA/detach", headers=board.instance.headers)
    project = (await client.get(f"{API}/projects/PA", headers=board.instance.headers)).json()
    wf = next(w for w in project["workflows"] if w["type"] == "task")
    workflow = {
        "statuses": [
            {k: s[k] for k in ("ref", "name", "category", "is_initial")} for s in wf["statuses"]
        ],
        "transitions": [
            {
                "ref": t["ref"],
                "name": t["name"],
                "from": t["from_ref"],
                "to": t["to_ref"],
                "allowed_resolutions": t["allowed_resolutions"],
                "rules": [
                    {
                        "kind": "condition",
                        "rule_type": "only_user_kind",
                        "config": {"kind": "human"},
                    }
                ]
                if t["ref"] == "start"
                else [],
            }
            for t in wf["transitions"]
        ],
    }
    await client.put(
        f"{API}/projects/PA/workflows/task",
        headers=board.instance.headers,
        json={"workflow": workflow},
    )
    await new_ticket(client, board.member)
    r = await client.post(f"{API}/tickets/next", headers=board.agent.headers, json={"claim": True})
    assert r.status_code == 409 and "no transition you can run" in r.json()["detail"]
    ticket = (await client.get(f"{API}/tickets/PA-1", headers=board.member.headers)).json()
    assert ticket["assignee"] is None  # nothing kept
