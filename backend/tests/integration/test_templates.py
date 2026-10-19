import copy
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.db.models import Project, Template
from radicle.services import template_sync
from radicle.services.template_config import parse
from radicle.services.templates import system_user
from tests.conftest import Team, new_ticket, run_jobs

API = "/api/v1"
DEFAULT_ID = "00000000-0000-0000-0000-000000000002"


async def project(client: AsyncClient, team: Team, key: str) -> dict:
    r = await client.get(f"{API}/projects/{key}", headers=team.instance.headers)
    assert r.status_code == 200, r.text
    return r.json()


def statuses(p: dict, ticket_type: str = "task") -> list[str]:
    workflow = next(w for w in p["workflows"] if w["type"] == ticket_type)
    return [s["name"] for s in workflow["statuses"]]


async def create_from(
    client: AsyncClient, team: Team, key: str, template_id: str, mode: str = "linked"
) -> dict:
    r = await client.post(
        f"{API}/projects",
        headers=team.instance.headers,
        json={
            "key": key,
            "name": f"Proyecto {key}",
            "template_id": template_id,
            "template_mode": mode,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


async def patch_config(
    client: AsyncClient, team: Team, template_id: str, config: dict, **extra: object
):
    return await client.patch(
        f"{API}/templates/{template_id}",
        headers=team.instance.headers,
        json={"config": config, **extra},
    )


@pytest.fixture
async def producto(client: AsyncClient, board: Team) -> dict:
    """PA (4 areas, a custom field) saved as "Producto digital"; PB linked, PC detached."""
    r = await client.post(f"{API}/projects/PA/detach", headers=board.instance.headers)
    assert r.status_code == 200
    r = await client.post(
        f"{API}/projects/PA/fields",
        headers=board.instance.headers,
        json={
            "key": "environment",
            "name": "Environment",
            "field_type": "select",
            "options": [{"value": "prod"}, {"value": "dev"}],
            "applies_to_types": ["bug"],
        },
    )
    assert r.status_code == 201
    r = await client.post(
        f"{API}/projects/PA/save-as-template",
        headers=board.admin.headers,
        json={"name": "Producto digital", "description_md": "Web y apps"},
    )
    assert r.status_code == 201, r.text
    template = r.json()
    await create_from(client, board, "PB", template["id"])
    await create_from(client, board, "PC", template["id"])
    r = await client.post(f"{API}/projects/PC/detach", headers=board.instance.headers)
    assert r.status_code == 200 and r.json()["template"]["mode"] == "detached"
    return template


async def test_acceptance_template_propagates_to_linked_projects_only(
    client: AsyncClient, db: AsyncSession, board: Team, producto: dict
) -> None:
    pb = await project(client, board, "PB")
    assert [a["name"] for a in pb["areas"]] == ["Legal", "Marketing", "Backend", "Frontend"]
    assert [f["key"] for f in pb["custom_fields"]] == ["environment"]
    assert pb["template"] == {
        "id": producto["id"],
        "name": "Producto digital",
        "mode": "linked",
        "version": 1,
        "applied_version": 1,
    }
    assert pb["milestones"] == [] and len(pb["members"]) == 1

    config = copy.deepcopy(producto["config"])
    task = config["workflows"]["task"]
    task["statuses"].insert(2, {"ref": "blocked", "name": "Blocked", "category": "in_progress"})
    task["transitions"].append(
        {"ref": "block", "name": "Block", "from": "in_progress", "to": "blocked"}
    )
    r = await patch_config(client, board, producto["id"], config)
    assert r.status_code == 200, r.text
    assert r.json()["version"] == 2
    assert "In task, no transition reaches" not in " ".join(r.json()["warnings"])

    r = await client.get(
        f"{API}/templates/{producto['id']}/sync-runs", headers=board.instance.headers
    )
    assert [(run["project"], run["status"]) for run in r.json()["items"]] == [("PB", "pending")]
    assert await run_jobs(db) == ["template_sync"]

    pb = await project(client, board, "PB")
    assert statuses(pb) == ["To Do", "In Progress", "Blocked", "In Review", "Done"]
    assert pb["template"]["applied_version"] == 2
    assert statuses(await project(client, board, "PC")) == [
        "To Do",
        "In Progress",
        "In Review",
        "Done",
    ]
    assert statuses(await project(client, board, "PA")) == [
        "To Do",
        "In Progress",
        "In Review",
        "Done",
    ]
    r = await client.get(
        f"{API}/templates/{producto['id']}/sync-runs", headers=board.instance.headers
    )
    assert r.json()["items"][0]["status"] == "succeeded"

    r = await client.get(f"{API}/templates", headers=board.member.headers)
    linked = next(t for t in r.json()["items"] if t["name"] == "Producto digital")[
        "linked_projects"
    ]
    assert linked == [{"key": "PB", "name": "Proyecto PB", "template_version": 2, "in_sync": True}]


async def test_removing_a_status_needs_a_mapping_and_moves_tickets(
    client: AsyncClient, db: AsyncSession, board: Team, producto: dict
) -> None:
    r = await client.put(
        f"{API}/projects/PB/members/luis", headers=board.instance.headers, json={"role": "member"}
    )
    assert r.status_code == 200
    r = await client.post(
        f"{API}/projects/PB/areas", headers=board.instance.headers, json={"name": "Extra"}
    )
    r = await client.post(
        f"{API}/projects/PB/tickets",
        headers=board.member.headers,
        json={"type": "task", "title": "En revisión", "area": "Backend"},
    )
    key = r.json()["key"]
    for status in ("In Progress", "In Review"):
        r = await client.post(
            f"{API}/tickets/{key}/transitions",
            headers=board.member.headers,
            json={"to_status": status},
        )
        assert r.status_code == 200, r.text

    config = copy.deepcopy(producto["config"])
    task = config["workflows"]["task"]
    task["statuses"] = [s for s in task["statuses"] if s["ref"] != "in_review"]
    task["transitions"] = [
        t for t in task["transitions"] if "in_review" not in (t["from"], t["to"])
    ]
    task["transitions"].append(
        {"ref": "finish", "name": "Finish", "from": "in_progress", "to": "done"}
    )
    r = await patch_config(client, board, producto["id"], config)
    assert r.status_code == 422
    body = r.json()
    assert body["type"].endswith("status_mapping_required")
    assert "'In Review' (task) has tickets: 1 in PB" in body["detail"]

    r = await patch_config(
        client, board, producto["id"], config, status_mappings={"in_review": "nope"}
    )
    assert r.status_code == 422 and "not a status of the new workflow" in r.json()["detail"]

    r = await patch_config(
        client,
        board,
        producto["id"],
        config,
        status_mappings={"task": {"in_review": "in_progress"}},
    )
    assert r.status_code == 200, r.text
    await run_jobs(db)

    ticket = (await client.get(f"{API}/tickets/{key}", headers=board.member.headers)).json()
    assert ticket["status"]["name"] == "In Progress"
    events = (await client.get(f"{API}/tickets/{key}/history", headers=board.member.headers)).json()
    remap = events["items"][0]
    assert remap["event_type"] == "status_remapped"
    assert remap["actor"] == {"handle": "system", "display_name": "Radicle", "kind": "system"}
    assert remap["old_value"]["status"] == "In Review"
    pb = await project(client, board, "PB")
    assert statuses(pb) == ["To Do", "In Progress", "Done"]
    assert "Extra" in [a["name"] for a in pb["areas"]]  # project extras survive


async def test_rename_reorder_and_fields_by_ref(
    client: AsyncClient, db: AsyncSession, board: Team, producto: dict
) -> None:
    r = await client.post(
        f"{API}/projects/PB/tickets",
        headers=board.instance.headers,
        json={"type": "task", "title": "x", "area": "Backend"},
    )
    key = r.json()["key"]
    config = copy.deepcopy(producto["config"])
    task = config["workflows"]["task"]
    task["statuses"][0]["name"] = "Backlog"
    task["statuses"][1], task["statuses"][2] = task["statuses"][2], task["statuses"][1]
    task["transitions"][0]["name"] = "Begin"
    config["custom_fields"] = [
        {
            "ref": "severity",
            "key": "severity",
            "name": "Severity",
            "field_type": "select",
            "options": [{"value": "s1"}, {"value": "s2"}],
            "applies_to_types": ["bug"],
            "applies_to_areas": ["Backend"],
        }
    ]
    config["areas"].append({"name": "Legal Ops", "color": "#123456"})
    config["tags"] = ["backlog", "urgent"]
    config["settings"]["blocked_policy"] = "enforce"
    r = await patch_config(client, board, producto["id"], config)
    assert r.status_code == 200, r.text
    await run_jobs(db)

    pb = await project(client, board, "PB")
    assert statuses(pb) == ["Backlog", "In Review", "In Progress", "Done"]
    task_wf = next(w for w in pb["workflows"] if w["type"] == "task")
    assert task_wf["transitions"][0]["name"] == "Begin"
    assert task_wf["statuses"][0]["ref"] == "to_do"
    ticket = (await client.get(f"{API}/tickets/{key}", headers=board.instance.headers)).json()
    assert ticket["status"]["name"] == "Backlog"
    assert [f["key"] for f in pb["custom_fields"]] == ["severity"]
    assert pb["custom_fields"][0]["applies_to_areas"] == ["Backend"]
    r = await client.get(
        f"{API}/projects/PB/fields",
        headers=board.instance.headers,
        params={"include_archived": True},
    )
    archived = {f["key"]: f["archived"] for f in r.json()["items"]}
    assert archived == {"environment": True, "severity": False}
    assert "Legal Ops" in [a["name"] for a in pb["areas"]]
    assert pb["suggested_tags"] == ["backlog", "urgent"]
    assert pb["blocked_policy"] == "enforce"

    # Running the same sync again changes nothing and duplicates nothing.
    r = await patch_config(client, board, producto["id"], config)
    assert r.json()["version"] == 2  # identical config: no new version
    pb_row = await db.scalar(select(Project).where(Project.key == "PB"))
    template = await db.get(Template, uuid.UUID(producto["id"]))
    assert pb_row is not None and template is not None
    report = await template_sync.apply_config(
        db, pb_row, parse(template.config), actor=await system_user(db)
    )
    assert report.added == [] and report.removed == [] and report.remapped_tickets == 0
    assert statuses(await project(client, board, "PB")) == [
        "Backlog",
        "In Review",
        "In Progress",
        "Done",
    ]


async def test_failed_sync_does_not_stop_others_and_can_be_retried(
    client: AsyncClient,
    db: AsyncSession,
    board: Team,
    producto: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await create_from(client, board, "PD", producto["id"])
    original = template_sync.apply_config

    async def flaky(db_, project_, *args, **kwargs):  # type: ignore[no-untyped-def]
        if project_.key == "PB":
            raise ValueError("disk full")
        return await original(db_, project_, *args, **kwargs)

    monkeypatch.setattr("radicle.services.templates.apply_config", flaky)
    config = copy.deepcopy(producto["config"])
    config["areas"].append({"name": "Soporte"})
    r = await patch_config(client, board, producto["id"], config)
    assert r.status_code == 200
    await run_jobs(db)
    runs = (
        await client.get(
            f"{API}/templates/{producto['id']}/sync-runs", headers=board.instance.headers
        )
    ).json()["items"]
    by_project = {r["project"]: r for r in runs}
    assert by_project["PB"]["status"] == "failed" and by_project["PB"]["error"] == "disk full"
    assert by_project["PD"]["status"] == "succeeded"
    assert "Soporte" in [a["name"] for a in (await project(client, board, "PD"))["areas"]]
    assert "Soporte" not in [a["name"] for a in (await project(client, board, "PB"))["areas"]]

    monkeypatch.setattr("radicle.services.templates.apply_config", original)
    run_id = by_project["PB"]["id"]
    r = await client.post(
        f"{API}/templates/{producto['id']}/sync-runs/{by_project['PD']['id']}/retry",
        headers=board.instance.headers,
    )
    assert r.status_code == 409
    r = await client.post(
        f"{API}/templates/{producto['id']}/sync-runs/{run_id}/retry", headers=board.instance.headers
    )
    assert r.status_code == 200 and r.json()["status"] == "pending"
    await run_jobs(db)
    assert "Soporte" in [a["name"] for a in (await project(client, board, "PB"))["areas"]]
    r = await client.post(
        f"{API}/templates/{producto['id']}/sync-runs/{uuid.uuid4()}/retry",
        headers=board.instance.headers,
    )
    assert r.status_code == 404


async def test_linked_projects_cannot_edit_configuration(
    client: AsyncClient, board: Team, producto: dict
) -> None:
    field = {"key": "notes", "name": "Notes", "field_type": "text"}
    r = await client.post(f"{API}/projects/PB/fields", headers=board.instance.headers, json=field)
    assert r.status_code == 409
    assert "linked to the template 'Producto digital'" in r.json()["detail"]
    assert r.json()["template"] == "Producto digital"
    r = await client.put(
        f"{API}/projects/PB/settings",
        headers=board.instance.headers,
        json={"blocked_policy": "enforce"},
    )
    assert r.status_code == 409
    pb = await project(client, board, "PB")
    workflow = {"statuses": [{"ref": "a", "name": "A", "category": "done", "is_initial": True}]}
    r = await client.put(
        f"{API}/projects/PB/workflows/task",
        headers=board.instance.headers,
        json={"workflow": workflow},
    )
    assert r.status_code == 409
    assert pb["template"]["mode"] == "linked"

    r = await client.post(f"{API}/projects/PC/fields", headers=board.instance.headers, json=field)
    assert r.status_code == 201
    r = await client.put(
        f"{API}/projects/PC/settings",
        headers=board.instance.headers,
        json={"blocked_policy": "enforce"},
    )
    assert r.status_code == 200 and r.json()["blocked_policy"] == "enforce"
    r = await client.post(f"{API}/projects/PC/detach", headers=board.instance.headers)
    assert r.status_code == 409


async def test_independent_project_workflow_editor(client: AsyncClient, board: Team) -> None:
    await create_from(client, board, "PE", DEFAULT_ID, mode="detached")
    r = await client.post(
        f"{API}/projects/PE/tickets",
        headers=board.instance.headers,
        json={"type": "bug", "title": "x", "area": None} | {"area": None},
    )
    assert r.status_code == 422  # no areas yet
    r = await client.post(
        f"{API}/projects/PE/areas", headers=board.instance.headers, json={"name": "Web"}
    )
    r = await client.post(
        f"{API}/projects/PE/tickets",
        headers=board.instance.headers,
        json={"type": "bug", "title": "x", "area": "Web"},
    )
    key = r.json()["key"]
    workflow = {
        "statuses": [
            {"ref": "triage", "name": "Triage", "category": "todo", "is_initial": True},
            {"ref": "fixing", "name": "Fixing", "category": "in_progress"},
            {"ref": "done", "name": "Done", "category": "done"},
            {"ref": "limbo", "name": "Limbo", "category": "todo"},
        ],
        "transitions": [
            {"ref": "fix", "name": "Fix", "from": "triage", "to": "fixing"},
            {
                "ref": "close",
                "name": "Close",
                "from": None,
                "to": "done",
                "allowed_resolutions": ["done"],
            },
        ],
    }
    url = f"{API}/projects/PE/workflows/bug"
    r = await client.put(url, headers=board.instance.headers, json={"workflow": workflow})
    assert r.status_code == 422 and "'Reported' (1 tickets, ref reported)" in r.json()["detail"]
    r = await client.put(
        url,
        headers=board.instance.headers,
        json={"workflow": workflow, "status_mappings": {"reported": "triage"}},
    )
    assert r.status_code == 200, r.text
    assert r.json()["warnings"] == ["No transition reaches: Limbo."]
    ticket = (await client.get(f"{API}/tickets/{key}", headers=board.instance.headers)).json()
    assert ticket["status"]["name"] == "Triage"
    events = (
        await client.get(f"{API}/tickets/{key}/history", headers=board.instance.headers)
    ).json()
    assert events["items"][0]["actor"]["handle"] == "fernando"
    r = await client.post(
        f"{API}/tickets/{key}/transitions",
        headers=board.instance.headers,
        json={"to_status": "Done"},
    )
    assert r.status_code == 200 and r.json()["resolution"] == "done"

    r = await client.put(
        url,
        headers=board.member.headers,
        json={"workflow": workflow},
    )
    assert r.status_code == 404  # luis is not in PE


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda w: w["statuses"][1].update(is_initial=True),
            "exactly one initial status (it has 2)",
        ),
        (
            lambda w: [s.update(category="todo") for s in w["statuses"]],
            "at least one status in the done",
        ),
        (lambda w: w["transitions"][0].update(to="nowhere"), "points to unknown status 'nowhere'"),
        (lambda w: w["statuses"][1].update(name="TO DO"), "Repeated status name"),
        (lambda w: w["statuses"][1].update(ref="Bad Ref"), "Invalid ref 'Bad Ref'"),
        (
            lambda w: w["transitions"][0].update(**{"from": "to_do", "to": "to_do"}),
            "starts and ends",
        ),
        (lambda w: w.update(statuses=[]), "at least one status"),
    ],
)
async def test_config_validation(
    client: AsyncClient,
    board: Team,
    mutate,
    message: str,  # type: ignore[no-untyped-def]
) -> None:
    template = (
        await client.get(f"{API}/templates/{DEFAULT_ID}", headers=board.member.headers)
    ).json()
    config = copy.deepcopy(template["config"])
    mutate(config["workflows"]["task"])
    r = await client.post(
        f"{API}/templates", headers=board.instance.headers, json={"name": "Roto", "config": config}
    )
    assert r.status_code == 422, r.text
    assert message in r.json()["detail"], r.json()["detail"]


async def test_missing_workflow_and_bad_screen(client: AsyncClient, board: Team) -> None:
    template = (
        await client.get(f"{API}/templates/{DEFAULT_ID}", headers=board.member.headers)
    ).json()
    config = copy.deepcopy(template["config"])
    del config["workflows"]["draft"]
    r = await client.post(
        f"{API}/templates", headers=board.instance.headers, json={"name": "X", "config": config}
    )
    assert r.status_code == 422 and "missing for: draft" in r.json()["detail"]
    config = copy.deepcopy(template["config"])
    config["screens"] = [
        {"type": "bug", "operation": "transition", "transition": "nope", "fields": []}
    ]
    r = await client.post(
        f"{API}/templates", headers=board.instance.headers, json={"name": "X", "config": config}
    )
    assert r.status_code == 422 and "unknown transition 'nope'" in r.json()["detail"]


async def test_template_lifecycle_and_permissions(client: AsyncClient, board: Team) -> None:
    r = await client.post(f"{API}/templates", headers=board.admin.headers, json={"name": "Nope"})
    assert r.status_code == 403
    r = await client.post(
        f"{API}/templates", headers=board.instance.headers, json={"name": "Vacío"}
    )
    assert r.status_code == 201
    template = r.json()
    assert template["version"] == 1 and template["is_default"] is False
    assert set(template["config"]["workflows"]) == {"task", "bug", "draft"}

    r = await client.patch(
        f"{API}/templates/{template['id']}",
        headers=board.instance.headers,
        json={"name": "Producto", "description_md": "Para apps"},
    )
    assert r.json()["name"] == "Producto" and r.json()["version"] == 1
    r = await client.get(
        f"{API}/templates/{template['id']}/sync-runs", headers=board.member.headers
    )
    assert r.status_code == 403

    r = await client.post(
        f"{API}/templates/{template['id']}/archive", headers=board.instance.headers
    )
    assert r.json()["archived"] is True
    r = await client.get(f"{API}/templates", headers=board.member.headers)
    assert "Producto" not in [t["name"] for t in r.json()["items"]]
    r = await client.patch(
        f"{API}/templates/{template['id']}", headers=board.instance.headers, json={"name": "X"}
    )
    assert r.status_code == 409
    r = await client.post(
        f"{API}/projects",
        headers=board.instance.headers,
        json={"key": "PZ", "name": "Z", "template_id": template["id"]},
    )
    assert r.status_code == 422 and "archived" in r.json()["detail"]
    r = await client.post(
        f"{API}/templates/{template['id']}/unarchive", headers=board.instance.headers
    )
    assert r.json()["archived"] is False

    r = await client.post(f"{API}/templates/{DEFAULT_ID}/archive", headers=board.instance.headers)
    assert r.status_code == 409
    r = await client.get(f"{API}/templates/{uuid.uuid4()}", headers=board.member.headers)
    assert r.status_code == 404
    r = await client.post(
        f"{API}/projects/PA/save-as-template", headers=board.member.headers, json={"name": "X"}
    )
    assert r.status_code == 403


async def test_new_projects_follow_radicle_default(client: AsyncClient, board: Team) -> None:
    pa = await project(client, board, "PA")
    assert pa["template"]["name"] == "Radicle default" and pa["template"]["mode"] == "linked"
    task = next(w for w in pa["workflows"] if w["type"] == "task")
    assert [s["ref"] for s in task["statuses"]] == ["to_do", "in_progress", "in_review", "done"]
    close = next(t for t in task["transitions"] if t["name"] == "Close")
    assert (close["ref"], close["from_ref"], close["to_ref"]) == ("close", None, "done")
    draft = next(w for w in pa["workflows"] if w["type"] == "draft")
    assert [t["ref"] for t in draft["transitions"]][-2:] == ["reopen", "reopen_discarded"]
    await new_ticket(client, board.member)
