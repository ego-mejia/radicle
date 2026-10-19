from httpx import AsyncClient

from tests.conftest import Actor, Team, make_project

API = "/api/v1"


async def test_create_project_seeds_workflows_and_admin(client: AsyncClient, admin: Actor) -> None:
    body = await make_project(client, admin)
    assert body["key"] == "PA" and body["role"] == "admin" and body["archived"] is False
    assert [m["handle"] for m in body["members"]] == ["fernando"]
    workflows = {w["type"]: w for w in body["workflows"]}
    assert [s["name"] for s in workflows["task"]["statuses"]] == [
        "To Do",
        "In Progress",
        "In Review",
        "Done",
    ]
    assert [s["name"] for s in workflows["bug"]["statuses"]] == [
        "Reported",
        "In Progress",
        "QA Verified",
        "Done",
    ]
    assert [s["name"] for s in workflows["draft"]["statuses"]] == [
        "New",
        "In Review",
        "Approved",
        "Discarded",
    ]
    close = next(t for t in workflows["task"]["transitions"] if t["name"] == "Close")
    assert close["from_status"] is None and close["allowed_resolutions"] == ["wont_do", "duplicate"]
    bug_close = next(t for t in workflows["bug"]["transitions"] if t["name"] == "Close")
    assert "cannot_reproduce" in bug_close["allowed_resolutions"]
    reopens = [t for t in workflows["draft"]["transitions"] if t["name"] == "Reopen"]
    assert {t["from_status"] for t in reopens} == {"Approved", "Discarded"}
    for w in workflows.values():
        assert sum(s["is_initial"] for s in w["statuses"]) == 1


async def test_acceptance_project_with_areas_and_milestone(
    client: AsyncClient, admin: Actor
) -> None:
    await make_project(client, admin)
    for name in ("Legal", "Marketing", "Backend", "Frontend"):
        r = await client.post(
            f"{API}/projects/PA/areas", headers=admin.headers, json={"name": name}
        )
        assert r.status_code == 201
    r = await client.post(
        f"{API}/projects/PA/milestones",
        headers=admin.headers,
        json={"name": "V1", "target_date": "2026-12-15"},
    )
    assert r.status_code == 201
    assert r.json()["counts"] == {"todo": 0, "in_progress": 0, "done": 0}
    r = await client.get(f"{API}/projects/PA", headers=admin.headers)
    detail = r.json()
    assert [a["name"] for a in detail["areas"]] == ["Legal", "Marketing", "Backend", "Frontend"]
    assert detail["milestones"][0]["name"] == "V1"
    assert detail["milestones"][0]["target_date"] == "2026-12-15"


async def test_key_validation_and_normalization(client: AsyncClient, admin: Actor) -> None:
    r = await client.post(
        f"{API}/projects", headers=admin.headers, json={"key": "web2", "name": "W"}
    )
    assert r.status_code == 201 and r.json()["key"] == "WEB2"
    for bad in ("P", "1PA", "PA-1", "ABCDEFGHIJK"):
        r = await client.post(
            f"{API}/projects", headers=admin.headers, json={"key": bad, "name": "X"}
        )
        assert r.status_code == 422, bad
        assert r.json()["errors"][0]["field"] == "key"
    r = await client.post(
        f"{API}/projects", headers=admin.headers, json={"key": "Web2", "name": "W"}
    )
    assert r.status_code == 409


async def test_key_is_immutable(client: AsyncClient, admin: Actor) -> None:
    await make_project(client, admin)
    r = await client.patch(f"{API}/projects/PA", headers=admin.headers, json={"key": "PB"})
    assert r.status_code == 422  # unknown field


async def test_patch_project(client: AsyncClient, team: Team) -> None:
    r = await client.patch(
        f"{API}/projects/PA",
        headers=team.admin.headers,
        json={"name": "Proyecto A", "description_md": "# Hola"},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Proyecto A" and r.json()["description_md"] == "# Hola"


async def test_list_projects_and_me(client: AsyncClient, team: Team) -> None:
    await make_project(client, team.instance, "PB")
    r = await client.get(f"{API}/projects", headers=team.member.headers)
    assert [(p["key"], p["role"]) for p in r.json()["items"]] == [("PA", "member")]
    r = await client.get(f"{API}/projects", headers=team.outsider.headers)
    assert r.json()["items"] == []
    r = await client.get(f"{API}/projects", headers=team.instance.headers)
    assert [p["key"] for p in r.json()["items"]] == ["PA", "PB"]
    r = await client.get(f"{API}/me", headers=team.viewer.headers)
    assert r.json()["projects"] == [{"key": "PA", "name": "ProyectoA", "role": "viewer"}]


async def test_only_instance_admins_create_projects(client: AsyncClient, team: Team) -> None:
    r = await client.post(
        f"{API}/projects", headers=team.admin.headers, json={"key": "PZ", "name": "Z"}
    )
    assert r.status_code == 403


async def test_archive_makes_project_read_only(client: AsyncClient, team: Team) -> None:
    r = await client.post(f"{API}/projects/PA/archive", headers=team.admin.headers)
    assert r.status_code == 200 and r.json()["archived"] is True
    r = await client.post(
        f"{API}/projects/PA/areas", headers=team.admin.headers, json={"name": "Legal"}
    )
    assert r.status_code == 409
    assert "archived" in r.json()["detail"]
    r = await client.get(f"{API}/projects", headers=team.member.headers)
    assert r.json()["items"] == []
    r = await client.get(
        f"{API}/projects", headers=team.member.headers, params={"include_archived": True}
    )
    assert r.json()["items"][0]["archived"] is True
    assert (
        await client.post(f"{API}/projects/PA/archive", headers=team.admin.headers)
    ).status_code == 409
    r = await client.post(f"{API}/projects/PA/unarchive", headers=team.admin.headers)
    assert r.status_code == 200 and r.json()["archived"] is False
    assert (
        await client.post(f"{API}/projects/PA/unarchive", headers=team.admin.headers)
    ).status_code == 409


async def test_unknown_project_is_404(client: AsyncClient, admin: Actor) -> None:
    r = await client.get(f"{API}/projects/NOPE", headers=admin.headers)
    assert r.status_code == 404
    assert r.json()["detail"] == "Project NOPE not found."


async def test_workflows_endpoint(client: AsyncClient, team: Team) -> None:
    r = await client.get(f"{API}/projects/PA/workflows", headers=team.viewer.headers)
    assert r.status_code == 200
    assert [w["type"] for w in r.json()] == ["task", "bug", "draft"]
