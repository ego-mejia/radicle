"""Templates over REST (Folio 3.1)."""

import pytest
from httpx import AsyncClient

from tests.conftest import Team
from tests.integration.folio_helpers import API


@pytest.fixture
async def space(client: AsyncClient, team: Team) -> str:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "eng", "name": "Ingeniería"})
    return "eng"


async def _spec_id(client: AsyncClient, team: Team) -> str:
    r = await client.get(f"{API}/templates", headers=team.member.headers)
    assert r.status_code == 200, r.text
    return next(t["id"] for t in r.json()["items"] if t["name"] == "Build spec")


async def test_create_a_build_spec_page(client: AsyncClient, team: Team, space: str) -> None:
    i = team.instance.headers
    body = {"template": await _spec_id(client, team), "space": space, "title": "Etapa 5"}
    r = await client.post(f"{API}/nodes/from-template", headers=i, json=body)
    assert r.status_code == 201, r.text
    draft = (await client.get(f"{API}/nodes/{r.json()['id']}/draft", headers=i)).json()
    assert "## Entregables" in draft["content_md"]
    assert draft["metadata"]["doc_type"] == "build-spec"


async def test_manage_templates(client: AsyncClient, team: Team, space: str) -> None:
    i = team.instance.headers
    body = {"name": "Daily", "space": space, "content_md": "# {{title}}\n\nNotas."}
    r = await client.post(f"{API}/templates", headers=i, json=body)
    assert r.status_code == 201, r.text
    tid = r.json()["id"]
    assert r.json()["scope"] == "space" and r.json()["space"] == "eng"
    r = await client.patch(
        f"{API}/templates/{tid}", headers=i, json={"name": "Daily v2", "content_md": "Hola"}
    )
    assert r.json()["name"] == "Daily v2"
    assert (await client.get(f"{API}/templates/{tid}", headers=i)).status_code == 200
    listed = await client.get(f"{API}/templates", params={"space": space}, headers=i)
    assert "Daily v2" in [t["name"] for t in listed.json()["items"]]
    assert (await client.delete(f"{API}/templates/{tid}", headers=i)).status_code == 204
    assert (await client.get(f"{API}/templates/{tid}", headers=i)).status_code == 404


async def test_a_space_from_a_template(client: AsyncClient, team: Team) -> None:
    i = team.instance.headers
    structure = {"pages": [{"title": "Specs", "kind": "folder"}, {"title": "Inicio"}]}
    r = await client.post(
        f"{API}/templates",
        headers=i,
        json={"kind": "space", "name": "Equipo", "structure": structure},
    )
    body = {"template": r.json()["id"], "key": "prod", "name": "Producto"}
    r = await client.post(f"{API}/spaces/from-template", headers=i, json=body)
    assert r.status_code == 201, r.text
    tree = (await client.get(f"{API}/spaces/prod/tree", headers=i)).json()
    assert [n["title"] for n in tree] == ["Specs", "Inicio"]


async def test_errors_and_permissions(client: AsyncClient, team: Team, space: str) -> None:
    m = team.member.headers
    r = await client.post(f"{API}/templates", headers=m, json={"name": "Mía", "content_md": "x"})
    assert r.status_code == 403
    r = await client.post(
        f"{API}/templates", headers=m, json={"name": "Mía", "space": space, "content_md": "x"}
    )
    assert r.status_code == 403
    body = {"template": await _spec_id(client, team), "space": space, "title": "x"}
    r = await client.post(f"{API}/nodes/from-template", headers=m, json=body)
    assert r.status_code == 403 and "creator role" in r.json()["detail"]
    r = await client.get(f"{API}/templates/00000000-0000-0000-0000-000000000000", headers=m)
    assert r.status_code == 404
    r = await client.post(
        f"{API}/spaces/from-template",
        headers=team.instance.headers,
        json={"template": body["template"], "key": "nope", "name": "Nope"},
    )
    assert r.status_code == 422 and "page template" in r.json()["detail"]


async def test_a_hidden_spaces_templates_stay_hidden(client: AsyncClient, team: Team) -> None:
    i, m = team.instance.headers, team.member.headers
    personal = (await client.get(f"{API}/me/personal-space", headers=i)).json()["key"]
    body = {"name": "Secreta", "space": personal, "content_md": "Plan secreto"}
    tid = (await client.post(f"{API}/templates", headers=i, json=body)).json()["id"]
    listed = (await client.get(f"{API}/templates", headers=m)).json()["items"]
    assert tid not in [t["id"] for t in listed]
    assert (await client.get(f"{API}/templates/{tid}", headers=m)).status_code == 404
