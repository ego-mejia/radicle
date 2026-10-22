"""Folio's catalogs and the publishing schema (Folio 1.3)."""

import pytest
from httpx import AsyncClient

from tests.conftest import Team

API = "/api/v1/folio"


async def test_metadata_schema_lists_rules_and_active_entries(
    client: AsyncClient, team: Team
) -> None:
    r = await client.get(f"{API}/metadata-schema", headers=team.member.headers)
    assert r.status_code == 200
    body = r.json()
    assert [f["name"] for f in body["fields"]] == [
        "title",
        "description",
        "doc_type",
        "labels",
        "owner",
        "audiences",
        "language",
        "docket_project",
        "docket_milestones",
        "docket_areas",
        "decision_status",
        "decision_topic",
        "decision_replaces",
    ]
    assert [f["name"] for f in body["fields"] if not f["required"]] == [
        "docket_project",
        "docket_milestones",
        "docket_areas",
        "decision_status",
        "decision_topic",
        "decision_replaces",
    ]
    assert "how-to" in [d["key"] for d in body["doc_types"]]
    assert [a["key"] for a in body["audiences"]] == ["everyone"]
    assert [lang["key"] for lang in body["languages"]] == ["es", "en"]


@pytest.mark.parametrize("catalog", ["doc-types", "audiences", "languages"])
async def test_admins_add_rename_and_archive(client: AsyncClient, team: Team, catalog: str) -> None:
    i = team.instance.headers
    r = await client.post(
        f"{API}/admin/{catalog}", headers=i, json={"key": "ingenieria", "name": "Ingeniería"}
    )
    assert r.status_code == 201, r.text
    r = await client.patch(
        f"{API}/admin/{catalog}/ingenieria", headers=i, json={"name": "Eng", "archived": True}
    )
    assert r.json() == r.json() | {"name": "Eng", "archived": True}
    listed = (await client.get(f"{API}/admin/{catalog}", headers=i)).json()["items"]
    assert "ingenieria" in [e["key"] for e in listed]
    schema = (await client.get(f"{API}/metadata-schema", headers=i)).json()
    key = {"doc-types": "doc_types"}.get(catalog, catalog)
    assert "ingenieria" not in [e["key"] for e in schema[key]]
    r = await client.patch(f"{API}/admin/{catalog}/ingenieria", headers=i, json={"archived": False})
    assert r.json()["archived"] is False


async def test_actionable_errors(client: AsyncClient, team: Team) -> None:
    i = team.instance.headers
    r = await client.post(f"{API}/admin/languages", headers=i, json={"key": "Fr FR", "name": "x"})
    assert r.status_code == 422 and "lowercase" in r.json()["detail"]
    r = await client.post(f"{API}/admin/languages", headers=i, json={"key": "es", "name": "x"})
    assert r.status_code == 409
    r = await client.post(f"{API}/admin/languages", headers=i, json={"key": "fr", "name": ""})
    assert r.status_code == 422
    r = await client.patch(f"{API}/admin/languages/xx", headers=i, json={"name": "x"})
    assert r.status_code == 404
    assert (await client.get(f"{API}/admin/colors", headers=i)).status_code == 422


async def test_only_folio_admins_edit_catalogs(client: AsyncClient, team: Team) -> None:
    member = team.member.headers
    assert (await client.get(f"{API}/admin/doc-types", headers=member)).status_code == 403
    r = await client.post(f"{API}/admin/doc-types", headers=member, json={"key": "x", "name": "X"})
    assert r.status_code == 403
    r = await client.patch(f"{API}/admin/doc-types/guide", headers=member, json={"name": "X"})
    assert r.status_code == 403
