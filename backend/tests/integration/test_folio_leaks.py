"""A restricted Folio page never leaks (Folio 1.4): every GET route of Folio is listed here
and asked by someone outside the restriction; none may mention the page. A new GET route
fails `test_every_folio_get_route_is_covered` until it is added."""

import pytest
from httpx import AsyncClient

from radicle.main import create_app
from tests.conftest import Team
from tests.integration.folio_helpers import API, publish

SECRET = "Plan secreto de legal"


@pytest.fixture
async def secret(client: AsyncClient, team: Team) -> dict:
    i = team.instance.headers
    await client.post("/api/v1/groups", headers=i, json={"name": "equipo-legal"})
    await client.put("/api/v1/groups/equipo-legal/members/vera", headers=i)
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    page = (
        await client.post(
            f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": SECRET}
        )
    ).json()
    child = (
        await client.post(
            f"{API}/nodes",
            headers=i,
            json={"space": "docs", "kind": "page", "title": "Hija secreta", "parent": page["id"]},
        )
    ).json()
    await publish(client, team, page["id"], md="Confidencial")
    await publish(client, team, child["id"], md="Confidencial")
    asset = await client.post(
        f"{API}/nodes/{page['id']}/assets",
        headers=i,
        files={"file": ("plan.pdf", b"%PDF-1.4\n%secret\n")},
    )
    r = await client.put(
        f"{API}/nodes/{page['id']}/restrictions",
        headers=i,
        json={"view": [{"grantee_type": "group", "grantee": "equipo-legal"}]},
    )
    assert r.status_code == 200, r.text
    return {"page": page["id"], "child": child["id"], "asset": asset.json()["id"]}


def _urls(s: dict) -> dict[str, list[str]]:
    p, c = s["page"], s["child"]
    return {
        "/api/v1/folio/spaces": [f"{API}/spaces"],
        "/api/v1/folio/me/personal-space": [f"{API}/me/personal-space"],
        "/api/v1/folio/spaces/{key}": [f"{API}/spaces/docs"],
        "/api/v1/folio/spaces/{key}/tree": [f"{API}/spaces/docs/tree"],
        "/api/v1/folio/spaces/{key}/posts": [f"{API}/spaces/docs/posts"],
        "/api/v1/folio/spaces/{key}/grants": [f"{API}/spaces/docs/grants"],
        "/api/v1/folio/nodes/{node_id}": [f"{API}/nodes/{p}", f"{API}/nodes/{c}"],
        "/api/v1/folio/nodes/{node_id}/draft": [f"{API}/nodes/{p}/draft"],
        "/api/v1/folio/nodes/{node_id}/versions": [f"{API}/nodes/{p}/versions"],
        "/api/v1/folio/nodes/{node_id}/snapshots": [f"{API}/nodes/{p}/snapshots"],
        "/api/v1/folio/nodes/{node_id}/snapshots/{snapshot_id}": [
            f"{API}/nodes/{p}/snapshots/00000000-0000-0000-0000-000000000000"
        ],
        "/api/v1/folio/nodes/{node_id}/versions/{number}": [f"{API}/nodes/{c}/versions/1"],
        "/api/v1/folio/nodes/{node_id}/diff": [f"{API}/nodes/{p}/diff?from=1&to=1"],
        "/api/v1/folio/nodes/{node_id}/restrictions": [f"{API}/nodes/{p}/restrictions"],
        "/api/v1/folio/submissions": [f"{API}/submissions"],
        "/api/v1/folio/spaces/{key}/archived": [f"{API}/spaces/docs/archived"],
        "/api/v1/folio/watch/{target_type}/{target_id}": [f"{API}/watch/node/{p}"],
        "/api/v1/folio/reactions/{target_type}/{target_id}": [f"{API}/reactions/node/{p}"],
        "/api/v1/folio/me/recents": [f"{API}/me/recents"],
        "/api/v1/folio/me/tasks": [f"{API}/me/tasks", f"{API}/me/tasks?status=all"],
        "/api/v1/folio/me/feed": [f"{API}/me/feed"],
        "/api/v1/folio/me/favorites": [f"{API}/me/favorites"],
        "/api/v1/folio/templates": [f"{API}/templates"],
        "/api/v1/folio/nodes/{node_id}/comments": [f"{API}/nodes/{p}/comments"],
        "/api/v1/folio/nodes": [
            f"{API}/nodes",
            f"{API}/nodes?q=title ~ secreto",
            f"{API}/nodes?q=text ~ Confidencial",
            f"{API}/nodes?q=space = docs ORDER BY title",
        ],
        "/api/v1/folio/home": [f"{API}/home"],
        "/api/v1/folio/page-list": [
            f"{API}/page-list?label=mcp",
            f"{API}/page-list?label=agentes&space=docs",
        ],
        "/api/v1/folio/search": [
            f"{API}/search?q=secreto",
            f"{API}/search?q=Confidencial&mode=text",
            f"{API}/search?q=legal&space=docs",
        ],
        "/api/v1/folio/submissions/{submission_id}": [f"{API}/submissions/{p}"],
    }


# Folio GET routes without page content.
EXEMPT = {
    "/api/v1/folio/health",
    "/api/v1/folio/me",
    "/api/v1/folio/admin/grants",
    "/api/v1/folio/metadata-schema",
    "/api/v1/folio/admin/{catalog}",
    "/api/v1/folio/assets/{asset_id}",  # covered below: ids of hidden pages' assets
    # Templates hold no page; a hidden space's templates: test_folio_templates_api.py.
    "/api/v1/folio/templates/{template_id}",
    "/api/v1/folio/link-preview",  # outside pages, not Folio content
    # Folio admins only (they see every page); test_folio_home_layouts.py checks the 403.
    "/api/v1/folio/admin/home/draft",
    "/api/v1/folio/admin/home/history",
    # Names and handles of people who read Folio, for @mentions; no page data.
    "/api/v1/folio/people",
}


def test_every_folio_get_route_is_covered() -> None:
    routes = {
        path
        for path, ops in create_app().openapi()["paths"].items()
        if "get" in ops and path.startswith("/api/v1/folio")
    }
    covered = set(_urls({"page": "x", "child": "y"}))
    missing = routes - covered - EXEMPT
    assert not missing, f"Cover these Folio GET routes in the leak test: {sorted(missing)}"


async def test_nothing_leaks_through_get_routes(
    client: AsyncClient, team: Team, secret: dict
) -> None:
    for urls in _urls(secret).values():
        for url in urls:
            r = await client.get(url, headers=team.member.headers)
            assert SECRET not in r.text and "Hija secreta" not in r.text, url
            if r.is_success:  # a 404 may repeat the id the caller already sent
                assert secret["page"] not in r.text and secret["child"] not in r.text, url
    r = await client.get(f"{API}/assets/{secret['asset']}", headers=team.member.headers)
    assert r.status_code == 404


async def test_members_of_the_restriction_and_admins_see_it(
    client: AsyncClient, team: Team, secret: dict
) -> None:
    for headers in (team.viewer.headers, team.instance.headers):  # vera is in equipo-legal
        tree = (await client.get(f"{API}/spaces/docs/tree", headers=headers)).json()
        assert [n["title"] for n in tree] == [SECRET]
        assert tree[0]["children"][0]["title"] == "Hija secreta"
    r = await client.get(f"{API}/nodes/{secret['child']}", headers=team.member.headers)
    assert r.status_code == 404
