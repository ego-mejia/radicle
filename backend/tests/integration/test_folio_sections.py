"""The Specs section of a space (RAD-57)."""

from httpx import AsyncClient

from tests.conftest import Team
from tests.integration.folio_helpers import API, METADATA
from tests.integration.test_folio_build_spec import SPEC


async def _page(client: AsyncClient, team: Team, title: str, md: str, metadata: dict) -> str:
    i = team.instance.headers
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "eng", "kind": "page", "title": title}
    )
    nid = str(r.json()["id"])
    r = await client.put(
        f"{API}/nodes/{nid}/draft", headers=i, json={"content_md": md, "metadata": metadata}
    )
    assert r.status_code == 200, r.text
    r = await client.post(f"{API}/nodes/{nid}/publish", headers=i, json={})
    assert r.is_success, r.text
    return nid


SPEC_META = METADATA | {"doc_type": "build-spec"}


async def test_specs_table(client: AsyncClient, board: Team) -> None:
    i, m = board.instance.headers, board.member.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "eng", "name": "Ingeniería"})
    backend = await _page(
        client,
        board,
        "Fase 4",
        SPEC,
        SPEC_META | {"docket_project": "PA", "docket_areas": ["Backend"]},
    )
    body = {"project": "PA", "area": "Backend", "milestone": "V1"}
    r = await client.post(f"{API}/nodes/{backend}/build-spec/tickets", headers=i, json=body)
    assert r.status_code == 201, r.text
    await _page(
        client,
        board,
        "Fase 5",
        "Hola",
        SPEC_META | {"docket_project": "PA", "docket_areas": ["Frontend"]},
    )
    await _page(client, board, "Sin proyecto", "Hola", SPEC_META)
    await _page(client, board, "Una guía", "Hola", METADATA)

    url = f"{API}/spaces/eng/specs"
    r = await client.get(url, headers=m)
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["total"] == 3 and {x["node"]["title"] for x in out["items"]} == {
        "Fase 4",
        "Fase 5",
        "Sin proyecto",
    }
    assert out["projects"] == [{"value": "PA", "count": 2}] and out["features"] == []
    assert out["owners"][0]["handle"] == "fernando"

    r = await client.get(url, headers=m, params={"project": "pa", "feature": ["Backend"]})
    rows = r.json()["items"]
    assert [x["node"]["title"] for x in rows] == ["Fase 4"]
    assert rows[0]["tickets_total"] == 2 and rows[0]["status"] == "planned"
    assert {f["value"] for f in r.json()["features"]} == {"Backend", "Frontend"}

    r = await client.get(url, headers=m, params={"q": "proyecto"})
    assert [x["node"]["title"] for x in r.json()["items"]] == ["Sin proyecto"]
    r = await client.get(url, headers=m, params={"status": "planned", "limit": 1})
    assert r.json()["total"] == 3 and len(r.json()["items"]) == 1


async def test_specs_errors_and_permissions(client: AsyncClient, board: Team) -> None:
    i, m = board.instance.headers, board.member.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "eng", "name": "Ingeniería"})
    secret = await _page(client, board, "Plan secreto", "Hola", SPEC_META)
    body = {"view": [{"grantee_type": "user", "grantee": board.instance.handle}]}
    await client.put(f"{API}/nodes/{secret}/restrictions", headers=i, json=body)
    assert (await client.get(f"{API}/spaces/eng/specs", headers=m)).json()["total"] == 0
    assert (await client.get(f"{API}/spaces/eng/specs", headers=i)).json()["total"] == 1
    r = await client.get(f"{API}/spaces/eng/specs", headers=m, params={"status": "lost"})
    assert r.status_code == 422
    assert (await client.get(f"{API}/spaces/nope/specs", headers=m)).status_code == 404
