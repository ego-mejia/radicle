"""get_page_analytics and get_search_gaps (Folio 5.9). Acceptance: an agent sees what people
search without finding, to propose what to document."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import Team, run_jobs
from tests.integration.folio_helpers import API, publish
from tests.mcp.conftest import error_text, folio_mcp, payload


async def _page(client: AsyncClient, db: AsyncSession, team: Team) -> str:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": "Deploy"}
    )
    await publish(client, team, r.json()["id"], md="# Deploy\n\nCon Docker.")
    await run_jobs(db)
    return str(r.json()["id"])


async def _make_admin(client: AsyncClient, team: Team) -> None:
    r = await client.post(
        f"{API}/admin/grants",
        headers=team.instance.headers,
        json={"grantee_type": "user", "grantee": team.agent.handle, "role": "admin"},
    )
    assert r.status_code == 201, r.text


async def test_acceptance_an_agent_sees_what_people_do_not_find(
    client: AsyncClient, db: AsyncSession, team: Team
) -> None:
    page = await _page(client, db, team)
    m = team.member.headers
    await client.post(f"{API}/analytics/views", headers=m, json={"node_id": page})
    for q in ("vpn", "VPN", "onboarding"):
        await client.get(f"{API}/search", headers=m, params={"q": q})
    await _make_admin(client, team)
    async with folio_mcp(client, team.agent) as folio:
        gaps = payload(await folio.call_tool("get_search_gaps", {"days": 7}))
        stats = payload(await folio.call_tool("get_page_analytics", {"id": page}))
    assert [(g["query"], g["times"]) for g in gaps["no_results"]] == [("vpn", 2), ("onboarding", 1)]
    assert gaps["unanswered"] == []
    assert stats["views"] == 1 and stats["unique_readers"] == 1


async def test_a_reader_agent_is_told_who_may_see_them(
    client: AsyncClient, db: AsyncSession, team: Team
) -> None:
    page = await _page(client, db, team)
    async with folio_mcp(client, team.agent) as folio:
        text = error_text(await folio.call_tool("get_page_analytics", {"id": page}))
        assert "owner" in text
        assert error_text(await folio.call_tool("get_search_gaps", {}))
