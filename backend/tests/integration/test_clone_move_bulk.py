import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import Team, make_project, new_ticket, run_jobs
from tests.mcp.conftest import McpFor, payload
from tests.mcp.conftest import mcp_for as mcp_for  # the fixture

API = "/api/v1"


async def get(client: AsyncClient, team: Team, key: str) -> dict:
    r = await client.get(f"{API}/tickets/{key}", headers=team.instance.headers)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture
async def two(client: AsyncClient, board: Team) -> Team:
    """PA plus PB with areas Backend and Ops, where luis and the agent are members."""
    await make_project(client, board.instance, "PB")
    for area in ("Backend", "Ops"):
        await client.post(
            f"{API}/projects/PB/areas", headers=board.instance.headers, json={"name": area}
        )
    for handle in ("luis", "agent-backend", "ana"):
        await client.put(
            f"{API}/projects/PB/members/{handle}",
            headers=board.instance.headers,
            json={"role": "member"},
        )
    return board


async def test_clone_options(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.member, title="Padre")
    await new_ticket(
        client,
        board.member,
        title="Original",
        description_md="Contexto\n\n- [x] Hecho @luis\n- [ ] Pendiente",
        tags=["pagos"],
        assignee="luis",
        collaborators=["ana"],
        parent="PA-1",
        priority="high",
    )
    await client.post(
        f"{API}/tickets/PA-2/attachments",
        headers=board.member.headers,
        files={"file": ("log.txt", b"stack trace")},
    )
    await new_ticket(client, board.member, title="Hijo", parent="PA-2")

    r = await client.post(f"{API}/tickets/PA-2/clone", headers=board.agent.headers, json={})
    assert r.status_code == 201, r.text
    bare = r.json()
    assert bare["key"] == "PA-4" and bare["title"] == "Original"
    assert bare["description_md"] == "- [ ] Hecho @luis\n- [ ] Pendiente"
    assert bare["tags"] == [] and bare["collaborators"] == [] and bare["attachments"] == []
    assert bare["assignee"] is None and bare["reporter"]["handle"] == "agent-backend"
    assert bare["status"]["name"] == "To Do" and bare["priority"] == "high"
    assert bare["parent"]["key"] == "PA-1"
    assert bare["links"][0]["type"] == "clones" and bare["links"][0]["ticket"]["key"] == "PA-2"
    history = (await client.get(f"{API}/tickets/PA-4/history", headers=board.member.headers)).json()
    assert {"cloned_from", "created"} <= {e["event_type"] for e in history["items"]}

    r = await client.post(
        f"{API}/tickets/PA-2/clone",
        headers=board.member.headers,
        json={
            "include": [
                "description",
                "checklist_state",
                "tags",
                "collaborators",
                "attachments",
                "children",
            ]
        },
    )
    full = r.json()
    assert full["description_md"].startswith("Contexto") and "- [x] Hecho" in full["description_md"]
    assert full["tags"] == ["pagos"]
    assert [c["handle"] for c in full["collaborators"]] == ["ana"]
    assert [a["filename"] for a in full["attachments"]] == ["log.txt"]
    content = await client.get(full["attachments"][0]["url"])
    assert content.content == b"stack trace"
    assert full["children_count"] == 1
    children = (
        await client.get(f"{API}/tickets/{full['key']}/children", headers=board.member.headers)
    ).json()
    assert children["items"][0]["title"] == "Hijo"

    r = await client.post(
        f"{API}/tickets/PA-2/clone", headers=board.member.headers, json={"include": ["nope"]}
    )
    assert r.status_code == 422
    r = await client.post(f"{API}/tickets/PA-2/clone", headers=board.viewer.headers, json={})
    assert r.status_code == 403


async def test_clone_to_another_project_needs_area_mapping(client: AsyncClient, two: Team) -> None:
    await new_ticket(client, two.member, area="Legal", title="Contrato")
    r = await client.post(
        f"{API}/tickets/PA-1/clone", headers=two.member.headers, json={"target_project": "PB"}
    )
    assert r.status_code == 422
    assert "Area 'Legal' of PA-1 does not exist in PB" in r.json()["detail"]
    r = await client.post(
        f"{API}/tickets/PA-1/clone",
        headers=two.member.headers,
        json={"target_project": "PB", "area_mapping": {"Legal": "Ops"}},
    )
    assert r.status_code == 201 and r.json()["key"] == "PB-1" and r.json()["area"] == "Ops"


async def test_acceptance_move_keeps_old_key(
    client: AsyncClient, db: AsyncSession, two: Team
) -> None:
    for i in range(14):
        await client.post(
            f"{API}/projects/PB/tickets",
            headers=two.member.headers,
            json={"type": "draft", "title": f"b{i}"},
        )
    for i in range(6):
        await new_ticket(client, two.member, title=f"a{i}")
    await client.post(f"{API}/projects/PB/detach", headers=two.instance.headers)
    await client.post(f"{API}/projects/PA/detach", headers=two.instance.headers)
    await client.post(
        f"{API}/projects/PA/fields",
        headers=two.instance.headers,
        json={"key": "solo_pa", "name": "Solo PA", "field_type": "text"},
    )
    await client.post(
        f"{API}/projects/PB/fields",
        headers=two.instance.headers,
        json={"key": "notes", "name": "Notes", "field_type": "text"},
    )
    await client.post(
        f"{API}/projects/PA/fields",
        headers=two.instance.headers,
        json={"key": "notes", "name": "Notes", "field_type": "text"},
    )
    seven = await new_ticket(
        client,
        two.member,
        title="Mover",
        assignee="luis",
        custom_fields={"notes": "se queda", "solo_pa": "se va"},
    )
    assert seven["key"] == "PA-7"
    await new_ticket(client, two.member, title="Hijo de 7", parent="PA-7")
    await client.post(
        f"{API}/tickets/PA-7/comments", headers=two.member.headers, json={"body_md": "hola"}
    )
    await client.post(
        f"{API}/tickets/PA-7/worklogs", headers=two.member.headers, json={"minutes": 30}
    )
    await client.post(
        f"{API}/tickets/PA-7/transitions",
        headers=two.member.headers,
        json={"to_status": "In Progress"},
    )
    await client.post(
        f"{API}/tickets/PA-1/links",
        headers=two.member.headers,
        json={"type": "blocks", "target": "PA-7"},
    )

    r = await client.post(
        f"{API}/tickets/PA-7/move", headers=two.member.headers, json={"target_project": "PB"}
    )
    assert r.status_code == 403  # admin in the source is required
    r = await client.post(
        f"{API}/tickets/PA-7/move", headers=two.admin.headers, json={"target_project": "PB"}
    )
    assert r.status_code == 200, r.text  # ana: admin in PA, member in PB
    moved = r.json()
    assert moved["key"] == "PB-15" and moved["moved_from"] == "PA-7"
    assert moved["status"]["name"] == "In Progress" and moved["area"] == "Backend"
    assert moved["custom_fields"] == {"notes": "se queda"}
    assert moved["assignee"]["handle"] == "luis" and moved["comments_count"] == 1
    assert moved["spent_hours"] == 0.5 and moved["blocked"] is True

    old = await get(client, two, "PA-7")
    assert old["key"] == "PB-15" and old["moved_from"] == "PA-7"
    child = await get(client, two, "PA-8")
    assert child["key"] == "PB-16" and child["parent"]["key"] == "PB-15"
    r = await client.get(f"{API}/tickets/PA-7/history", headers=two.member.headers)
    moved_event = r.json()["items"][0]
    assert moved_event["event_type"] == "moved"
    assert moved_event["old_value"]["key"] == "PA-7"
    assert moved_event["new_value"]["dropped_custom_fields"] == ["solo_pa"]
    r = await client.patch(
        f"{API}/tickets/PA-7",
        headers={**two.member.headers, "If-Match": str(old["version"])},
        json={"title": "Por alias"},
    )
    assert r.status_code == 200 and r.json()["key"] == "PB-15"
    assert (await get(client, two, "PA-1"))["links"][0]["ticket"]["key"] == "PB-15"


async def test_move_mappings_and_errors(client: AsyncClient, two: Team) -> None:
    await new_ticket(client, two.member, area="Legal", milestone="V1")
    await client.post(
        f"{API}/tickets/PA-1/transitions",
        headers=two.member.headers,
        json={"to_status": "In Progress"},
    )
    url = f"{API}/tickets/PA-1/move"
    r = await client.post(url, headers=two.instance.headers, json={"target_project": "PB"})
    assert r.status_code == 422 and r.json()["type"].endswith("area_mapping_required")
    r = await client.post(url, headers=two.instance.headers, json={"target_project": "PA"})
    assert r.status_code == 422 and "already in PA" in r.json()["detail"]
    r = await client.post(
        url,
        headers=two.instance.headers,
        json={"target_project": "PB", "area_mapping": {"Legal": "Ops"}, "milestone": "Nope"},
    )
    assert r.status_code == 422 and "Milestone 'Nope'" in r.json()["detail"]
    r = await client.post(
        url,
        headers=two.instance.headers,
        json={
            "target_project": "PB",
            "area_mapping": {"Legal": "Ops"},
            "status_mapping": {"In Progress": "In Review"},
        },
    )
    body = r.json()
    assert body["area"] == "Ops" and body["status"]["name"] == "In Review"
    assert body["milestone"] is None  # PB has no V1


async def test_bulk_dry_run_and_partial_errors(client: AsyncClient, board: Team) -> None:
    for i in range(4):
        await new_ticket(client, board.member, title=f"t{i}", tags=["backlog"])
    await new_ticket(client, board.member, title="sin tag")
    body = {
        "query": "project = PA AND #backlog",
        "operations": [
            {"op": "set_field", "field": "milestone", "value": "V1"},
            {"op": "remove_tag", "tag": "backlog"},
            {"op": "transition", "to_status": "In Progress"},
        ],
        "dry_run": True,
    }
    r = await client.post(f"{API}/tickets/bulk", headers=board.member.headers, json=body)
    assert r.status_code == 200, r.text
    preview = r.json()
    assert (preview["total"], preview["succeeded"], preview["failed"]) == (4, 4, 0)
    assert (await get(client, board, "PA-1"))["tags"] == ["backlog"]  # nothing changed

    await client.post(
        f"{API}/tickets/PA-2/transitions",
        headers=board.member.headers,
        json={"to_status": "In Progress"},
    )
    r = await client.post(
        f"{API}/tickets/bulk", headers=board.member.headers, json={**body, "dry_run": False}
    )
    result = r.json()
    assert (result["succeeded"], result["failed"]) == (3, 1)
    failure = next(x for x in result["results"] if not x["ok"])
    assert failure["key"] == "PA-2" and "not allowed from 'In Progress'" in failure["error"]
    assert (await get(client, board, "PA-1"))["milestone"] == "V1"
    pa2 = await get(client, board, "PA-2")
    assert pa2["tags"] == ["backlog"] and pa2["milestone"] is None  # its own savepoint

    r = await client.post(
        f"{API}/tickets/bulk",
        headers=board.member.headers,
        json={"keys": ["PA-1", "PA-99"], "operations": [{"op": "assign", "handle": "luis"}]},
    )
    assert [x["ok"] for x in r.json()["results"]] == [True, False]
    r = await client.post(
        f"{API}/tickets/bulk",
        headers=board.member.headers,
        json={"keys": ["PA-1"], "operations": [{"op": "explode"}]},
    )
    assert r.status_code == 422
    r = await client.post(
        f"{API}/tickets/bulk",
        headers=board.member.headers,
        json={"keys": ["PA-1"], "query": "x", "operations": [{"op": "assign", "handle": None}]},
    )
    assert r.status_code == 422
    r = await client.post(
        f"{API}/tickets/bulk",
        headers=board.viewer.headers,
        json={"keys": ["PA-1"], "operations": [{"op": "add_tag", "tag": "x"}]},
    )
    assert r.json()["results"][0]["ok"] is False


async def test_acceptance_bulk_120_runs_as_job(
    client: AsyncClient, db: AsyncSession, board: Team
) -> None:
    for i in range(120):
        await client.post(
            f"{API}/projects/PA/tickets",
            headers=board.member.headers,
            json={"type": "draft", "title": f"Idea {i}", "tags": ["backlog"]},
        )
    body = {
        "query": "#backlog",
        "operations": [
            {"op": "remove_tag", "tag": "backlog"},
            {"op": "set_field", "field": "milestone", "value": "V1"},
        ],
    }
    r = await client.post(
        f"{API}/tickets/bulk", headers=board.member.headers, json={**body, "dry_run": True}
    )
    assert r.json()["total"] == 120 and r.json()["succeeded"] == 120
    r = await client.post(f"{API}/tickets/bulk", headers=board.member.headers, json=body)
    assert r.status_code == 202
    job = r.json()["job"]
    assert job["total"] == 120 and job["status"] == "pending"
    assert await run_jobs(db) == ["bulk_update"]
    r = await client.get(f"{API}/jobs/{job['id']}", headers=board.member.headers)
    done = r.json()
    assert done["status"] == "succeeded" and done["progress"] == 120
    assert done["result"]["succeeded"] == 120 and len(done["result"]["results"]) == 120
    r = await client.get(f"{API}/tickets", headers=board.member.headers, params={"q": "#backlog"})
    assert r.json()["total"] == 0
    r = await client.get(
        f"{API}/tickets", headers=board.member.headers, params={"q": "milestone = V1"}
    )
    assert r.json()["total"] == 120


async def test_bulk_over_500_is_refused(client: AsyncClient, board: Team) -> None:
    keys = [f"PA-{i}" for i in range(1, 502)]
    r = await client.post(
        f"{API}/tickets/bulk",
        headers=board.member.headers,
        json={"keys": keys, "operations": [{"op": "add_tag", "tag": "x"}]},
    )
    assert r.status_code == 422 and "at most 500" in r.json()["detail"]


async def test_mcp_clone_move_bulk(client: AsyncClient, two: Team, mcp_for: McpFor) -> None:
    await client.put(
        f"{API}/projects/PA/members/agent-backend",
        headers=two.instance.headers,
        json={"role": "admin"},
    )
    await new_ticket(client, two.member, title="Uno", tags=["backlog"])
    async with mcp_for(two.agent) as mcp:
        clone = payload(await mcp.call_tool("clone_ticket", {"key": "PA-1", "include": ["tags"]}))
        assert clone["key"] == "PA-2" and clone["tags"] == ["backlog"]
        preview = payload(
            await mcp.call_tool(
                "bulk_update",
                {"keys": ["PA-1", "PA-2"], "operations": [{"op": "remove_tag", "tag": "backlog"}]},
            )
        )
        assert preview == {"dry_run": True, "total": 2, "succeeded": 2, "failed": []}
        assert (await get(client, two, "PA-1"))["tags"] == ["backlog"]
        applied = payload(
            await mcp.call_tool(
                "bulk_update",
                {
                    "keys": ["PA-1", "PA-2"],
                    "operations": [{"op": "remove_tag", "tag": "backlog"}],
                    "dry_run": False,
                },
            )
        )
        assert applied["succeeded"] == 2
        moved = payload(await mcp.call_tool("move_ticket", {"key": "PA-1", "target_project": "PB"}))
        assert moved["key"] == "PB-1" and moved["moved_from"] == "PA-1"
        again = payload(await mcp.call_tool("get_ticket", {"key": "PA-1", "comments": 0}))
        assert again["key"] == "PB-1"
