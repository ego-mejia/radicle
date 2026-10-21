"""Docs linked to Docket milestones and areas through their metadata (Folio 4.4).
Acceptance: the V1 milestone in Docket lists its docs."""

from httpx import AsyncClient

from tests.conftest import Team
from tests.integration.folio_helpers import API, METADATA

DOCKET = {"docket_project": "pa", "docket_milestones": ["v1"], "docket_areas": ["Backend"]}


async def _page(client: AsyncClient, team: Team, title: str, metadata: dict) -> str:
    i = team.instance.headers
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "eng", "kind": "page", "title": title}
    )
    nid = r.json()["id"]
    r = await client.put(
        f"{API}/nodes/{nid}/draft", headers=i, json={"content_md": "Hola", "metadata": metadata}
    )
    assert r.status_code == 200, r.text
    r = await client.post(f"{API}/nodes/{nid}/publish", headers=i, json={})
    assert r.is_success, r.text
    return str(nid)


async def test_acceptance_the_milestone_lists_its_docs(client: AsyncClient, board: Team) -> None:
    i, m = board.instance.headers, board.member.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "eng", "name": "Ingeniería"})
    guide = await _page(client, board, "Guía V1", METADATA | DOCKET)
    secret = await _page(client, board, "Plan secreto", METADATA | DOCKET)
    await _page(client, board, "Otra", METADATA)
    body = {"view": [{"grantee_type": "user", "grantee": board.instance.handle}]}
    await client.put(f"{API}/nodes/{secret}/restrictions", headers=i, json=body)

    r = await client.get(f"{API}/nodes/{guide}/draft", headers=i)
    assert r.json()["metadata"]["docket_project"] == "pa"  # as typed; published as PA
    r = await client.get(f"{API}/links", params={"milestone": "PA:V1"}, headers=i)
    assert r.status_code == 200, r.text
    assert sorted(d["node"]["title"] for d in r.json()["items"]) == ["Guía V1", "Plan secreto"]
    first = r.json()["items"][0]
    assert first["kind"] is None and first["description"] == METADATA["description"]
    r = await client.get(f"{API}/links", params={"milestone": "pa:v1"}, headers=m)
    assert [d["node"]["id"] for d in r.json()["items"]] == [guide]
    r = await client.get(f"{API}/links", params={"area": "PA:backend"}, headers=m)
    assert [d["node"]["title"] for d in r.json()["items"]] == ["Guía V1"]


async def test_errors(client: AsyncClient, board: Team) -> None:
    i = board.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "eng", "name": "Ingeniería"})
    for params, status in (
        ({"milestone": "PA:V9"}, 404),
        ({"area": "ZZ:Backend"}, 404),
        ({"milestone": "V1"}, 422),
        ({}, 422),
        ({"ticket": "PA-1", "milestone": "PA:V1"}, 422),
    ):
        r = await client.get(f"{API}/links", params=params, headers=i)
        assert r.status_code == status, (params, r.text)
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "eng", "kind": "page", "title": "Mala"}
    )
    nid = r.json()["id"]
    for bad, field in (
        ({"docket_milestones": ["V1"]}, "docket_milestones"),
        ({"docket_project": "p a"}, "docket_project"),
        ({"docket_project": "PA", "docket_areas": "Backend"}, "docket_areas"),
    ):
        await client.put(
            f"{API}/nodes/{nid}/draft",
            headers=i,
            json={"content_md": "x", "metadata": METADATA | bad},
        )
        r = await client.post(f"{API}/nodes/{nid}/publish", headers=i, json={})
        assert r.status_code == 422, r.text
        assert field in {e["field"] for e in r.json()["errors"]}
