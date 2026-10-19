from httpx import AsyncClient

from tests.conftest import Team

API = "/api/v1/projects/PA"


async def test_area_crud(client: AsyncClient, team: Team) -> None:
    h = team.admin.headers
    r = await client.post(f"{API}/areas", headers=h, json={"name": " Legal ", "color": "#4d7c0f"})
    assert r.status_code == 201
    assert r.json() == {"name": "Legal", "color": "#4D7C0F", "position": 0, "archived": False}
    r = await client.post(f"{API}/areas", headers=h, json={"name": "legal"})
    assert r.status_code == 409
    r = await client.patch(f"{API}/areas/LEGAL", headers=h, json={"name": "Legal y Compliance"})
    assert r.status_code == 200 and r.json()["name"] == "Legal y Compliance"
    r = await client.patch(f"{API}/areas/Legal y Compliance", headers=h, json={"color": None})
    assert r.json()["color"] is None
    r = await client.post(f"{API}/areas", headers=h, json={"name": "X", "color": "red"})
    assert r.status_code == 422


async def test_area_archive_and_restore(client: AsyncClient, team: Team) -> None:
    h = team.admin.headers
    await client.post(f"{API}/areas", headers=h, json={"name": "Legal"})
    await client.post(f"{API}/areas", headers=h, json={"name": "Backend"})
    assert (await client.delete(f"{API}/areas/Legal", headers=h)).status_code == 204
    assert (await client.delete(f"{API}/areas/Legal", headers=h)).status_code == 409
    r = await client.get(f"{API}/areas", headers=h)
    assert [a["name"] for a in r.json()["items"]] == ["Backend"]
    r = await client.get(f"{API}/areas", headers=h, params={"include_archived": True})
    assert len(r.json()["items"]) == 2
    r = await client.patch(f"{API}/areas/Legal", headers=h, json={"archived": False})
    assert r.json()["archived"] is False


async def test_area_not_found(client: AsyncClient, team: Team) -> None:
    r = await client.patch(f"{API}/areas/Nope", headers=team.admin.headers, json={"name": "X"})
    assert r.status_code == 404
    assert r.json()["detail"] == "Area 'Nope' not found in PA."


async def test_milestone_crud_close_reopen(client: AsyncClient, team: Team) -> None:
    h = team.admin.headers
    r = await client.post(
        f"{API}/milestones",
        headers=h,
        json={"name": "V1", "target_date": "2026-12-15", "description_md": "x"},
    )
    assert r.status_code == 201 and r.json()["status"] == "open"
    await client.post(
        f"{API}/milestones", headers=h, json={"name": "V0", "target_date": "2026-11-01"}
    )
    await client.post(f"{API}/milestones", headers=h, json={"name": "Someday"})
    r = await client.get(f"{API}/milestones", headers=team.viewer.headers)
    assert [m["name"] for m in r.json()["items"]] == ["V0", "V1", "Someday"]

    r = await client.patch(f"{API}/milestones/v1", headers=h, json={"status": "closed"})
    assert r.json()["status"] == "closed" and r.json()["closed_at"] is not None
    r = await client.get(f"{API}/milestones", headers=h, params={"status": "open"})
    assert [m["name"] for m in r.json()["items"]] == ["V0", "Someday"]
    r = await client.patch(
        f"{API}/milestones/V1",
        headers=h,
        json={"status": "open", "target_date": None, "name": "V1.0"},
    )
    body = r.json()
    assert body["status"] == "open" and body["closed_at"] is None
    assert body["target_date"] is None and body["name"] == "V1.0"
    r = await client.get(f"{API}/milestones/V1.0", headers=team.viewer.headers)
    assert r.status_code == 200


async def test_milestone_errors(client: AsyncClient, team: Team) -> None:
    h = team.admin.headers
    await client.post(f"{API}/milestones", headers=h, json={"name": "V1"})
    r = await client.post(f"{API}/milestones", headers=h, json={"name": "v1"})
    assert r.status_code == 409
    r = await client.post(
        f"{API}/milestones", headers=h, json={"name": "V2", "target_date": "nope"}
    )
    assert r.status_code == 422
    r = await client.get(f"{API}/milestones/V9", headers=h)
    assert r.status_code == 404
    r = await client.post(f"{API}/milestones", headers=h, json={"name": "x" * 81})
    assert r.status_code == 422
