"""Databases over REST (Folio 3.6)."""

import pytest
from httpx import AsyncClient

from tests.conftest import Team
from tests.integration.folio_db_helpers import COLUMNS
from tests.integration.folio_helpers import API


@pytest.fixture
async def inv(client: AsyncClient, team: Team) -> str:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "ai-tools", "name": "AI Tools"})
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "ai-tools", "kind": "database", "title": "Inv"}
    )
    return str(r.json()["id"])


async def test_build_and_read_a_board(client: AsyncClient, team: Team, inv: str) -> None:
    i, m = team.instance.headers, team.member.headers
    got = (await client.get(f"{API}/databases/{inv}", headers=i)).json()
    assert got["can_edit"] and [c["key"] for c in got["columns"]] == ["name"]
    board = {"name": "Board", "kind": "board", "group_by": "status"}
    r = await client.patch(
        f"{API}/databases/{inv}",
        headers=i,
        json={"columns": COLUMNS, "views": [*got["views"], board]},
    )
    assert r.status_code == 200, r.text
    for name, status in (("Claude", "Adopted"), ("Devin", "Idea")):
        r = await client.post(
            f"{API}/databases/{inv}/rows",
            headers=i,
            json={"values": {"name": name, "status": status}},
        )
        assert r.status_code == 201, r.text
    rows = await client.get(f"{API}/databases/{inv}/rows", params={"view": "board"}, headers=m)
    body = rows.json()
    assert body["view"]["kind"] == "board"
    assert [x["values"]["status"] for x in body["items"]] == ["Adopted", "Idea"]
    reader = (await client.get(f"{API}/databases/{inv}", headers=m)).json()
    assert reader["can_edit"] is False


async def test_change_move_delete_and_clear(client: AsyncClient, team: Team, inv: str) -> None:
    i = team.instance.headers
    a = (
        await client.post(f"{API}/databases/{inv}/rows", headers=i, json={"values": {"name": "a"}})
    ).json()
    b = (
        await client.post(f"{API}/databases/{inv}/rows", headers=i, json={"values": {"name": "7"}})
    ).json()
    r = await client.patch(f"{API}/rows/{b['id']}", headers=i, json={"to_top": True})
    assert r.status_code == 200
    names = [
        x["values"]["name"]
        for x in (await client.get(f"{API}/databases/{inv}/rows", headers=i)).json()["items"]
    ]
    assert names == ["7", "a"]
    r = await client.patch(
        f"{API}/databases/{inv}",
        headers=i,
        json={"columns": [{"key": "name", "name": "Name", "type": "number"}]},
    )
    assert r.json()["cleared"] == 1
    assert (await client.delete(f"{API}/rows/{a['id']}", headers=i)).status_code == 204
    assert (await client.patch(f"{API}/rows/{a['id']}", headers=i, json={})).status_code == 404


async def test_errors_and_permissions(client: AsyncClient, team: Team, inv: str) -> None:
    i, m = team.instance.headers, team.member.headers
    r = await client.post(f"{API}/databases/{inv}/rows", headers=m, json={"values": {"name": "x"}})
    assert r.status_code == 403
    r = await client.post(f"{API}/databases/{inv}/rows", headers=i, json={"values": {"nope": 1}})
    assert r.status_code == 422 and "Unknown columns" in r.json()["detail"]
    r = await client.get(f"{API}/databases/{inv}/rows", params={"view": "x"}, headers=i)
    assert r.status_code == 422
    r = await client.patch(
        f"{API}/databases/{inv}", headers=i, json={"columns": [{"name": "X", "type": "money"}]}
    )
    assert r.status_code == 422
    await client.put(
        f"{API}/nodes/{inv}/restrictions",
        headers=i,
        json={"view": [{"grantee_type": "user", "grantee": team.instance.handle}]},
    )
    assert (await client.get(f"{API}/databases/{inv}", headers=m)).status_code == 404
    assert (await client.get(f"{API}/databases/{inv}/rows", headers=m)).status_code == 404
