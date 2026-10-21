"""Folio analytics over REST (5.9): views, search clicks, a page's numbers for its owner
and space admins, and the site's for Folio admins."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import Team, run_jobs
from tests.integration.folio_helpers import API, publish


@pytest.fixture
async def page(client: AsyncClient, db: AsyncSession, team: Team) -> str:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": "Deploy"}
    )
    await publish(client, team, r.json()["id"], md="# Deploy\n\nCon Docker y despliegue.")
    await run_jobs(db)
    return str(r.json()["id"])


async def test_a_view_and_a_search_show_in_the_analytics(
    client: AsyncClient, team: Team, page: str
) -> None:
    i, m = team.instance.headers, team.member.headers
    r = await client.post(f"{API}/analytics/views", headers=m, json={"node_id": page})
    assert r.status_code == 204, r.text
    found = (await client.get(f"{API}/search", headers=m, params={"q": "despliegue"})).json()
    assert found["items"] and found["search_id"]
    url = f"{API}/analytics/searches/{found['search_id']}/click"
    assert (await client.post(url, headers=m, json={"node_id": page})).status_code == 204
    await client.get(f"{API}/search", headers=m, params={"q": "kubernetes"})
    typing = {"q": "kube", "track": "false"}
    assert (await client.get(f"{API}/search", headers=m, params=typing)).json()["search_id"] is None

    r = await client.get(f"{API}/analytics/pages/{page}", headers=i, params={"days": 7})
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["views"], body["unique_readers"], len(body["daily"])) == (1, 1, 7)
    assert body["readers_visible"] is False and body["readers"] == []
    r = await client.patch(f"{API}/spaces/docs", headers=i, json={"show_readers": True})
    assert r.json()["show_readers"] is True
    r = await client.get(f"{API}/analytics/pages/{page}", headers=i)
    assert [x["handle"] for x in r.json()["readers"]] == [team.member.handle]

    site = (await client.get(f"{API}/analytics/site", headers=i)).json()
    assert site["views"] == 1 and site["searches"] == 2
    assert [g["query"] for g in site["no_results"]] == ["kubernetes"]
    assert site["top_pages"][0]["title"] == "Deploy"


async def test_errors(client: AsyncClient, team: Team, page: str) -> None:
    i, m = team.instance.headers, team.member.headers
    r = await client.get(f"{API}/analytics/pages/{page}", headers=i, params={"days": 0})
    assert r.status_code == 422
    missing = "00000000-0000-0000-0000-000000000000"
    r = await client.post(f"{API}/analytics/views", headers=m, json={"node_id": missing})
    assert r.status_code == 404
    r = await client.post(
        f"{API}/analytics/searches/{missing}/click", headers=m, json={"node_id": page}
    )
    assert r.status_code == 404 and "Search" in r.json()["detail"]


async def test_permissions(client: AsyncClient, team: Team, page: str) -> None:
    m = team.member.headers
    r = await client.get(f"{API}/analytics/pages/{page}", headers=m)
    assert r.status_code == 403 and "owner" in r.json()["detail"]
    assert (await client.get(f"{API}/analytics/site", headers=m)).status_code == 403
    r = await client.patch(f"{API}/spaces/docs", headers=m, json={"show_readers": True})
    assert r.status_code == 403
    found = (await client.get(f"{API}/search", headers=m, params={"q": "deploy"})).json()
    url = f"{API}/analytics/searches/{found['search_id']}/click"
    r = await client.post(url, headers=team.viewer.headers, json={"node_id": page})
    assert r.status_code == 404
