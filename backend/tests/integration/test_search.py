import pytest
from httpx import AsyncClient

from tests.conftest import Team, make_project, new_ticket

API = "/api/v1"


async def keys(client: AsyncClient, actor, q: str, **params: object) -> list[str]:  # type: ignore[no-untyped-def]
    r = await client.get(f"{API}/tickets", headers=actor.headers, params={"q": q, **params})
    assert r.status_code == 200, r.text
    return [t["key"] for t in r.json()["items"]]


async def move(client: AsyncClient, team: Team, key: str, to: str, **extra: object) -> None:
    r = await client.post(
        f"{API}/tickets/{key}/transitions",
        headers=team.member.headers,
        json={"to_status": to, **extra},
    )
    assert r.status_code == 200, r.text


@pytest.fixture
async def data(client: AsyncClient, board: Team) -> Team:
    m = board.member
    # PA-1 bug high V1 (reported by luis)
    await new_ticket(
        client, m, type="bug", title="Login falla", area="Frontend", priority="high", milestone="V1"
    )
    # PA-2 bug highest V1 #backlog
    await new_ticket(
        client,
        m,
        type="bug",
        title="Checkout roto",
        area="Backend",
        priority="highest",
        milestone="V1",
        tags=["backlog"],
    )
    # PA-3 task assigned to agent, In Progress, about pagos
    await new_ticket(
        client,
        m,
        type="task",
        title="API de pagos",
        area="Backend",
        assignee="agent-backend",
        description_md="Integrar cobro con tarjeta y pagos.",
        milestone="V1",
        priority="medium",
    )
    # PA-4 legal task #backlog, parent of PA-5
    await new_ticket(client, m, type="task", title="Términos", area="Legal", tags=["backlog"])
    # PA-5 child of PA-4, done
    await new_ticket(client, m, type="task", title="Revisar contrato", area="Legal", parent="PA-4")
    # PA-6 draft reported by ana (admin)
    await new_ticket(
        client,
        board.admin,
        type="draft",
        classification="idea",
        title="Idea de onboarding",
        area=None,
    )
    await move(client, board, "PA-3", "In Progress")
    await move(client, board, "PA-5", "Done", resolution="wont_do")
    r = await client.post(
        f"{API}/tickets/PA-4/links", headers=m.headers, json={"type": "blocks", "target": "PA-3"}
    )
    assert r.status_code == 201
    return board


async def test_spec_examples(client: AsyncClient, data: Team) -> None:
    m, agent = data.member, data.agent
    assert await keys(
        client,
        m,
        'project = PA AND type = bug AND priority >= high AND milestone = "V1" AND tag != backlog',
    ) == ["PA-1"]
    assert await keys(
        client,
        agent,
        "assignee = currentUser() AND category != done ORDER BY priority DESC, due ASC",
    ) == ["PA-3"]
    assert await keys(client, m, "#backlog AND area = Legal") == ["PA-4"]
    assert await keys(client, m, 'text ~ "pagos" AND updated >= -7d') == ["PA-3"]
    assert await keys(client, m, 'blocked = true AND milestone = "V1"') == ["PA-3"]
    assert await keys(client, m, "parent = PA-4 AND category = done") == ["PA-5"]
    assert await keys(
        client, m, "(type = bug OR type = draft) AND reporter = ana AND NOT #backlog"
    ) == ["PA-6"]


async def test_more_fields(client: AsyncClient, data: Team) -> None:
    m = data.member
    assert await keys(client, m, "type = bug ORDER BY key") == ["PA-1", "PA-2"]
    assert await keys(client, m, "assignee != agent-backend ORDER BY key") == [
        "PA-1",
        "PA-2",
        "PA-4",
        "PA-5",
        "PA-6",
    ]
    assert (await keys(client, m, "assignee IS EMPTY ORDER BY key DESC"))[:2] == ["PA-6", "PA-5"]
    assert await keys(client, m, 'status = "in progress"') == ["PA-3"]
    assert await keys(client, m, "resolution = wont_do") == ["PA-5"]
    assert await keys(client, m, "resolution IS EMPTY AND area = Legal") == ["PA-4"]
    assert await keys(client, m, "area IS EMPTY") == ["PA-6"]
    assert await keys(client, m, "key IN (PA-1, PA-4) ORDER BY key") == ["PA-1", "PA-4"]
    assert await keys(client, m, "title ~ login") == ["PA-1"]
    assert await keys(client, m, "linked = PA-3") == ["PA-4"]
    assert await keys(client, m, "blocked = false AND type = task ORDER BY key") == ["PA-4", "PA-5"]
    assert (await keys(client, m, "ORDER BY priority DESC, key"))[:2] == ["PA-2", "PA-1"]
    assert await keys(client, m, "resolved >= -1h") == ["PA-5"]
    assert await keys(client, m, "created > 2000-01-01 AND project = pa", limit=2) != []
    assert await keys(client, m, "category = in_progress OR category = done ORDER BY key") == [
        "PA-3",
        "PA-5",
    ]


async def test_spanish_stemming(client: AsyncClient, data: Team) -> None:
    assert await keys(client, data.member, 'text ~ "tarjetas"') == ["PA-3"]


async def test_errors_with_position(client: AsyncClient, data: Team) -> None:
    r = await client.get(
        f"{API}/tickets", headers=data.member.headers, params={"q": "prioridad = high"}
    )
    assert r.status_code == 422
    body = r.json()
    assert body["position"] == 0
    assert body["detail"] == "Unknown field 'prioridad' at 0. Did you mean 'priority'?"
    r = await client.get(f"{API}/tickets", headers=data.member.headers, params={"q": "(type = bug"})
    assert r.status_code == 422 and r.json()["position"] == 11
    r = await client.get(f"{API}/tickets", headers=data.member.headers, params={"q": "x" * 2001})
    assert r.status_code == 422


async def test_unknown_names_warn(client: AsyncClient, data: Team) -> None:
    r = await client.get(
        f"{API}/tickets",
        headers=data.member.headers,
        params={"q": "area = Ventas OR assignee = ghost OR project = ZZ"},
    )
    body = r.json()
    assert body["items"] == [] and body["total"] == 0
    assert [w["message"] for w in body["warnings"]] == [
        "Area 'Ventas' does not exist; it matches nothing.",
        "User @ghost does not exist; it matches nothing.",
        "Project ZZ does not exist; it matches nothing.",
    ]


async def test_permission_filter_always_applies(client: AsyncClient, data: Team) -> None:
    await make_project(client, data.instance, "PB")
    r = await client.post(
        f"{API}/projects/PB/tickets",
        headers=data.instance.headers,
        json={"type": "draft", "classification": "idea", "title": "Secret"},
    )
    assert r.status_code == 201
    assert await keys(client, data.outsider, "") == []
    assert await keys(client, data.member, "project = PB") == []
    assert await keys(client, data.member, "title ~ Secret") == []
    assert await keys(client, data.instance, "project = PB") == ["PB-1"]


async def test_deleted_tickets_excluded(client: AsyncClient, data: Team) -> None:
    await client.delete(f"{API}/tickets/PA-1", headers=data.admin.headers)
    assert "PA-1" not in await keys(client, data.member, "")


async def test_pagination(client: AsyncClient, data: Team) -> None:
    seen, cursor = [], None
    while True:
        params = {"q": "ORDER BY key", "limit": 4, **({"cursor": cursor} if cursor else {})}
        r = await client.get(f"{API}/tickets", headers=data.member.headers, params=params)
        body = r.json()
        assert body["total"] == 6
        seen += [t["key"] for t in body["items"]]
        cursor = body["next_cursor"]
        if not cursor:
            break
    assert seen == [f"PA-{i}" for i in range(1, 7)]
    r = await client.get(
        f"{API}/tickets", headers=data.member.headers, params={"cursor": "garbage!"}
    )
    assert r.status_code == 422
    r = await client.get(f"{API}/tickets", headers=data.member.headers, params={"limit": 201})
    assert r.status_code == 422


async def test_summary_shape(client: AsyncClient, data: Team) -> None:
    r = await client.get(f"{API}/tickets", headers=data.member.headers, params={"q": "key = PA-3"})
    [t] = r.json()["items"]
    assert t["blocked"] is True and t["assignee"]["kind"] == "agent"
    assert t["status"] == {"name": "In Progress", "category": "in_progress"}
    assert t["area"] == "Backend" and t["milestone"] == "V1"


async def test_search_fields(client: AsyncClient, data: Team) -> None:
    r = await client.get(f"{API}/search/fields", headers=data.viewer.headers)
    body = r.json()
    names = [f["name"] for f in body["fields"]]
    assert "priority" in names and "blocked" in names and body["values"] is None
    priority = next(f for f in body["fields"] if f["name"] == "priority")
    assert priority["operators"] == ["=", "!=", ">", ">=", "<", "<="]
    r = await client.get(
        f"{API}/search/fields", headers=data.viewer.headers, params={"project": "PA"}
    )
    values = r.json()["values"]
    assert values["areas"] == ["Legal", "Marketing", "Backend", "Frontend"]
    assert values["milestones"] == ["V1"]
    assert "To Do" in values["statuses"] and "Reported" in values["statuses"]
    assert values["tags"] == ["backlog"]
    assert "agent-backend" in values["handles"]
    r = await client.get(
        f"{API}/search/fields", headers=data.outsider.headers, params={"project": "PA"}
    )
    assert r.status_code == 404
