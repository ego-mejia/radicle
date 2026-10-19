from httpx import AsyncClient

from tests.conftest import Team, new_ticket, patch_ticket
from tests.mcp.conftest import McpFor, error_text, payload
from tests.mcp.conftest import mcp_for as mcp_for  # the fixture

API = "/api/v1"


async def draft(client: AsyncClient, actor, title: str, classification: str = "idea") -> dict:  # type: ignore[no-untyped-def]
    return await new_ticket(
        client, actor, type="draft", title=title, area=None, classification=classification
    )


async def inbox(client: AsyncClient, team: Team, **params: object) -> dict:
    r = await client.get(f"{API}/projects/PA/inbox", headers=team.viewer.headers, params=params)
    assert r.status_code == 200, r.text
    return r.json()


async def search(client: AsyncClient, team: Team, q: str) -> list[str]:
    r = await client.get(f"{API}/tickets", headers=team.viewer.headers, params={"q": q})
    assert r.status_code == 200, r.text
    return [t["key"] for t in r.json()["items"]]


async def test_drafts_need_a_classification_and_come_from_the_team(
    client: AsyncClient, board: Team
) -> None:
    r = await client.post(
        f"{API}/projects/PA/tickets",
        headers=board.member.headers,
        json={"type": "draft", "title": "Sin clase"},
    )
    assert r.status_code == 422 and "classification" in r.json()["detail"]
    r = await client.post(
        f"{API}/projects/PA/tickets",
        headers=board.member.headers,
        json={"type": "task", "title": "x", "area": "Backend", "classification": "idea"},
    )
    assert r.status_code == 422 and "Only drafts" in r.json()["detail"]
    t = await draft(client, board.member, "Probar pagos con QR", "experiment")
    assert (t["origin"], t["classification"], t["impact"]) == ("team", "experiment", None)
    task = await new_ticket(client, board.member, title="Normal")
    assert task["origin"] is None


async def test_score_and_tabs_and_rql(client: AsyncClient, board: Team) -> None:
    await draft(client, board.member, "Modo oscuro", "suggestion")
    await draft(client, board.member, "Lento al pagar", "complaint")
    await draft(client, board.member, "Exportar a CSV", "idea")
    for key, impact, effort in (("PA-1", 4, 2), ("PA-2", 5, 1)):
        r = await patch_ticket(client, board.member, key, impact=impact, effort=effort)
        assert r.status_code == 200, r.text
    r = await patch_ticket(client, board.member, "PA-1", impact=7)
    assert r.status_code == 422 and "1 to 5" in r.json()["detail"]
    await client.put(f"{API}/tickets/PA-3/vote", headers=board.member.headers)

    view = await inbox(client, board, sort="score")
    assert [t["key"] for t in view["items"]] == ["PA-2", "PA-1", "PA-3"]
    assert view["counts"] == {"new": 3, "in_review": 0, "approved": 0, "discarded": 0}
    assert (await inbox(client, board))["items"][0]["key"] == "PA-3"
    complaint = await inbox(client, board, classification="complaint")
    assert [t["key"] for t in complaint["items"]] == ["PA-2"]

    assert await search(client, board, "classification = complaint") == ["PA-2"]
    assert await search(client, board, "impact >= 4 ORDER BY key") == ["PA-1", "PA-2"]
    assert await search(client, board, "origin = team AND effort IS EMPTY") == ["PA-3"]
    assert await search(client, board, "converted = true") == []

    # Triage needs inbox.triage: viewers do not have it, members lose it if removed.
    r = await patch_ticket(client, board.viewer, "PA-3", impact=1, effort=1)
    assert r.status_code == 403 and "inbox.triage" in r.json()["detail"]
    await client.put(
        f"{API}/projects/PA/permissions",
        headers=board.admin.headers,
        json={"member": {"inbox.triage": False}},
    )
    r = await patch_ticket(client, board.member, "PA-3", impact=1, effort=1)
    assert r.status_code == 403


async def test_acceptance_approve_and_convert(client: AsyncClient, board: Team) -> None:
    """A draft is scored, approved and stays the same ticket as a Bug with its origin."""
    await draft(client, board.member, "Checkout se congela", "complaint")
    await client.put(f"{API}/tickets/PA-1/vote", headers=board.admin.headers)
    await client.post(
        f"{API}/tickets/PA-1/comments",
        headers=board.member.headers,
        json={"body_md": "Pasa en Safari"},
    )
    await patch_ticket(client, board.member, "PA-1", impact=5, effort=2)

    # Atomic: an unknown assignee fails and nothing changes.
    r = await client.post(
        f"{API}/tickets/PA-1/inbox/approve",
        headers=board.member.headers,
        json={"type": "bug", "area": "Backend", "assignee": "nadie"},
    )
    assert r.status_code == 422, r.text
    t = (await client.get(f"{API}/tickets/PA-1", headers=board.viewer.headers)).json()
    assert (t["type"], t["status"]["name"], t["converted_at"]) == ("draft", "New", None)

    r = await client.post(
        f"{API}/tickets/PA-1/inbox/approve",
        headers=board.member.headers,
        json={
            "type": "bug",
            "area": "Backend",
            "milestone": "V1",
            "priority": "high",
            "assignee": "luis",
        },
    )
    assert r.status_code == 200, r.text
    t = r.json()
    assert (t["key"], t["type"], t["area"], t["milestone"], t["priority"]) == (
        "PA-1",
        "bug",
        "Backend",
        "V1",
        "high",
    )
    assert t["status"]["category"] == "todo" and t["converted_at"] is not None
    assert (t["origin"], t["classification"], t["vote_count"], t["comments_count"]) == (
        "team",
        "complaint",
        1,
        1,
    )
    history = (
        await client.get(f"{API}/tickets/PA-1/history", headers=board.viewer.headers)
    ).json()["items"]
    kinds = [e["event_type"] for e in history]
    assert "converted" in kinds and kinds.count("status_changed") >= 2
    assert await search(client, board, "converted = true AND origin = team") == ["PA-1"]
    assert (await inbox(client, board, tab="approved"))["counts"]["approved"] == 1
    r = await client.post(
        f"{API}/tickets/PA-1/inbox/approve",
        headers=board.member.headers,
        json={"type": "task", "area": "Backend"},
    )
    assert r.status_code == 422 and "not an inbox draft" in r.json()["detail"]


async def test_discard_and_duplicate(client: AsyncClient, board: Team) -> None:
    await draft(client, board.member, "Pago con QR")
    await draft(client, board.member, "Pagar con código QR")
    await draft(client, board.member, "Juegos en la app")
    for actor in (board.admin, board.viewer):
        await client.put(f"{API}/tickets/PA-2/vote", headers=actor.headers)
    await client.put(f"{API}/tickets/PA-1/vote", headers=board.admin.headers)

    r = await client.post(
        f"{API}/tickets/PA-2/inbox/duplicate",
        headers=board.member.headers,
        json={"original": "PA-1"},
    )
    assert r.status_code == 200, r.text
    assert (r.json()["status"]["name"], r.json()["resolution"]) == ("Discarded", "duplicate")
    original = (await client.get(f"{API}/tickets/PA-1", headers=board.viewer.headers)).json()
    assert original["vote_count"] == 2  # admin once, plus the viewer
    assert original["links"][0]["label"] == "is duplicated by"

    r = await client.post(
        f"{API}/tickets/PA-3/inbox/discard",
        headers=board.member.headers,
        json={"public_comment": "Fuera del alcance de este año."},
    )
    assert r.status_code == 200, r.text
    assert (r.json()["resolution"], r.json()["status"]["name"]) == ("wont_do", "Discarded")
    view = await inbox(client, board, tab="discarded")
    assert {t["key"] for t in view["items"]} == {"PA-2", "PA-3"}
    r = await client.post(
        f"{API}/tickets/PA-1/inbox/discard", headers=board.viewer.headers, json={}
    )
    assert r.status_code == 403


async def test_mcp_inbox_tools(client: AsyncClient, board: Team, mcp_for: McpFor) -> None:
    await draft(client, board.member, "Notificaciones push", "suggestion")
    await draft(client, board.member, "Spam", "complaint")
    async with mcp_for(board.agent) as mcp:
        listed = payload(await mcp.call_tool("list_inbox", {"project": "PA"}))
        assert [i["key"] for i in listed["items"]] == ["PA-1", "PA-2"]
        scored = payload(
            await mcp.call_tool("score_inbox_item", {"key": "PA-1", "impact": 4, "effort": 3})
        )
        assert (scored["impact"], scored["effort"]) == (4, 3)
        result = await mcp.call_tool("score_inbox_item", {"key": "PA-1", "impact": 9, "effort": 3})
        assert result.is_error
        discarded = payload(
            await mcp.call_tool("discard_inbox_item", {"key": "PA-2", "public_comment": "No"})
        )
        assert discarded["status"] == "Discarded"
        approved = payload(
            await mcp.call_tool(
                "approve_inbox_item", {"key": "PA-1", "type": "task", "area": "Backend"}
            )
        )
        assert (approved["type"], approved["classification"]) == ("task", "suggestion")
        result = await mcp.call_tool("mark_inbox_duplicate", {"key": "PA-1", "original": "PA-2"})
        assert "not an inbox draft" in error_text(result)
        created = payload(
            await mcp.call_tool(
                "create_ticket",
                {
                    "project": "PA",
                    "type": "draft",
                    "title": "Idea del agente",
                    "classification": "idea",
                },
            )
        )
        assert created["origin"] == "team"
