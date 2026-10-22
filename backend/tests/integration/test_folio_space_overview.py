"""A space at a glance (RAD-57): counts, sections and who takes part, and the sections an
admin may hide or reorder."""

import pytest
from httpx import AsyncClient

from tests.conftest import Team
from tests.integration.folio_helpers import API, METADATA


async def _page(client: AsyncClient, team: Team, title: str, doc_type: str, **extra: object) -> str:
    i = team.instance.headers
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "eng", "kind": "page", "title": title, **extra}
    )
    assert r.status_code == 201, r.text
    nid = r.json()["id"]
    body = {"content_md": "Hola", "metadata": METADATA | {"doc_type": doc_type}}
    assert (await client.put(f"{API}/nodes/{nid}/draft", headers=i, json=body)).status_code == 200
    assert (await client.post(f"{API}/nodes/{nid}/publish", headers=i, json={})).status_code == 201
    return nid


@pytest.fixture
async def space(client: AsyncClient, team: Team) -> str:
    i = team.instance.headers
    r = await client.post(f"{API}/spaces", headers=i, json={"key": "eng", "name": "Ingeniería"})
    assert r.status_code == 201, r.text
    folder = (
        await client.post(
            f"{API}/nodes", headers=i, json={"space": "eng", "kind": "folder", "title": "Specs"}
        )
    ).json()["id"]
    await _page(client, team, "Etapa 5", "build-spec", parent=folder)
    await _page(client, team, "Etapa 4", "build-spec", parent=folder)
    await _page(client, team, "pgvector", "decision-log")
    await _page(client, team, "Despliegue", "how-to")
    await client.post(f"{API}/nodes", headers=i, json={"space": "eng", "title": "Borrador"})
    grants = (await client.get(f"{API}/spaces/eng/grants", headers=i)).json()["grants"]
    grants += [
        {"grantee_type": "user", "grantee": team.admin.handle, "permissions": ["admin"]},
        {"grantee_type": "user", "grantee": team.member.handle, "permissions": ["view", "create"]},
    ]
    r = await client.put(f"{API}/spaces/eng/grants", headers=i, json={"grants": grants})
    assert r.status_code == 200, r.text
    return "eng"


async def test_the_overview_counts_and_lists_people(
    client: AsyncClient, team: Team, space: str
) -> None:
    r = await client.get(f"{API}/spaces/{space}/overview", headers=team.member.headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["pages"] == 4 and body["folders"] == 1  # the unpublished draft is not theirs
    counts = {s["key"]: s["count"] for s in body["sections"]}
    assert counts == {"specs": 2, "decisions": 1, "guides": 1, "docs": 0}
    assert [s["key"] for s in body["sections"]] == ["specs", "decisions", "guides", "docs"]
    roles = [(p["handle"], p["role"]) for p in body["participants"]]
    assert {h for h, role in roles[:2]} == {team.instance.handle, team.admin.handle}
    assert all(role == "admin" for _, role in roles[:2])
    assert (team.member.handle, "editor") in roles
    assert body["everyone_role"] == "reader"


async def test_an_admin_hides_and_reorders_sections(
    client: AsyncClient, team: Team, space: str
) -> None:
    body = {"sections": [{"key": "guides"}, {"key": "docs", "visible": False}]}
    r = await client.put(f"{API}/spaces/{space}/sections", headers=team.admin.headers, json=body)
    assert r.status_code == 200, r.text
    assert [(s["key"], s["visible"]) for s in r.json()] == [
        ("guides", True),
        ("docs", False),
        ("specs", True),
        ("decisions", True),
    ]
    r = await client.get(f"{API}/spaces/{space}/overview", headers=team.viewer.headers)
    assert [s["key"] for s in r.json()["sections"]][:2] == ["guides", "docs"]


async def test_errors(client: AsyncClient, team: Team, space: str) -> None:
    i = team.instance.headers
    bad = {"sections": [{"key": "specs"}, {"key": "specs"}]}
    r = await client.put(f"{API}/spaces/{space}/sections", headers=i, json=bad)
    assert r.status_code == 422 and "once" in r.json()["detail"]
    r = await client.put(
        f"{API}/spaces/{space}/sections", headers=i, json={"sections": [{"key": "x"}]}
    )
    assert r.status_code == 422
    assert (await client.get(f"{API}/spaces/nope/overview", headers=i)).status_code == 404


async def test_only_admins_change_sections_and_counts_respect_restrictions(
    client: AsyncClient, team: Team, space: str
) -> None:
    r = await client.put(
        f"{API}/spaces/{space}/sections",
        headers=team.member.headers,
        json={"sections": [{"key": "docs"}]},
    )
    assert r.status_code == 403
    secret = await _page(client, team, "Plan secreto", "build-spec")
    view = {"view": [{"grantee_type": "user", "grantee": team.instance.handle}]}
    r = await client.put(
        f"{API}/nodes/{secret}/restrictions", headers=team.instance.headers, json=view
    )
    assert r.status_code == 200, r.text
    mine = (
        await client.get(f"{API}/spaces/{space}/overview", headers=team.instance.headers)
    ).json()
    theirs = (
        await client.get(f"{API}/spaces/{space}/overview", headers=team.member.headers)
    ).json()
    assert mine["sections"][0]["count"] == 3 and theirs["sections"][0]["count"] == 2
    assert theirs["pages"] == mine["pages"] - 1
