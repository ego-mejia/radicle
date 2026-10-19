from httpx import AsyncClient

from tests.conftest import Team, make_project, new_ticket

API = "/api/v1"


async def widget_data(client: AsyncClient, actor, widget_id: str):  # type: ignore[no-untyped-def]
    return await client.get(f"{API}/widgets/{widget_id}/data", headers=actor.headers)


async def add_widget(client: AsyncClient, actor, dashboard: dict, **body: object):  # type: ignore[no-untyped-def]
    return await client.post(
        f"{API}/dashboards/{dashboard['id']}/widgets", headers=actor.headers, json=body
    )


async def test_every_project_gets_a_summary(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.member, type="bug", title="Falla", assignee="luis")
    r = await client.get(f"{API}/projects/PA/dashboard", headers=board.viewer.headers)
    assert r.status_code == 200, r.text
    summary = r.json()
    assert summary["name"] == "Summary" and summary["is_project_default"] is True
    assert summary["can_edit"] is False and summary["refresh_seconds"] == 300
    kinds = [w["widget_type"] for w in summary["widgets"]]
    assert kinds[:3] == ["count", "count", "created_vs_resolved"]
    for w in summary["widgets"]:
        r = await widget_data(client, board.viewer, w["id"])
        assert r.status_code == 200, (w["widget_type"], r.text)
    open_count = next(w for w in summary["widgets"] if w["title"] == "Open tickets")
    assert (await widget_data(client, board.viewer, open_count["id"])).json()["data"]["count"] == 1

    # Its project's admins edit it; members do not, and nobody deletes it.
    admin_view = (
        await client.get(f"{API}/projects/PA/dashboard", headers=board.admin.headers)
    ).json()
    assert admin_view["can_edit"] is True
    r = await add_widget(
        client, board.member, summary, widget_type="markdown", title="Notas", config={"text": "x"}
    )
    assert r.status_code == 403
    r = await add_widget(
        client,
        board.admin,
        summary,
        widget_type="markdown",
        title="Notas",
        config={"text": "**hola**"},
    )
    assert r.status_code == 201, r.text
    assert (await widget_data(client, board.member, r.json()["id"])).json()["data"][
        "text"
    ] == "**hola**"
    r = await client.delete(f"{API}/dashboards/{summary['id']}", headers=board.admin.headers)
    assert r.status_code == 409


async def test_acceptance_v1_go_to_market(client: AsyncClient, board: Team) -> None:
    """Progress, open bugs by area and blocked tickets, shared with the project; a member
    sees it with their own permissions."""
    await make_project(client, board.instance, "PB")
    r = await client.post(
        f"{API}/projects/PB/areas", headers=board.instance.headers, json={"name": "Ops"}
    )
    assert r.status_code == 201, r.text
    for key, area in (("PA", "Backend"), ("PA", "Frontend"), ("PB", "Ops")):
        body = {"type": "bug", "title": f"Bug {key}", "milestone": "V1" if key == "PA" else None}
        r = await client.post(
            f"{API}/projects/{key}/tickets",
            headers=board.instance.headers,
            json={**body, "area": area},
        )
        assert r.status_code == 201, r.text
    r = await client.post(
        f"{API}/tickets/PA-1/links",
        headers=board.member.headers,
        json={"type": "blocks", "target": "PA-2"},
    )
    assert r.status_code == 201, r.text

    r = await client.post(
        f"{API}/dashboards",
        headers=board.instance.headers,
        json={"name": "V1 Go to market", "visibility": "private"},
    )
    assert r.status_code == 201, r.text
    dash = r.json()
    progress = await add_widget(
        client,
        board.instance,
        dash,
        widget_type="milestone_progress",
        title="V1",
        config={"project": "PA", "milestone": "V1"},
        layout={"x": 0, "y": 0, "w": 4, "h": 4},
    )
    bugs = await add_widget(
        client,
        board.instance,
        dash,
        widget_type="distribution",
        title="Bugs por área",
        config={"rql": "type = bug AND category != done", "field": "area", "chart": "pie"},
    )
    blocked = await add_widget(
        client, board.instance, dash, widget_type="blocked_tickets", title="Bloqueados", config={}
    )
    assert {r.status_code for r in (progress, bugs, blocked)} == {201}
    assert bugs.json()["layout"] == {"x": 0, "y": 4, "w": 6, "h": 4}

    # Private: the member cannot see it yet.
    r = await client.get(f"{API}/dashboards/{dash['id']}", headers=board.member.headers)
    assert r.status_code == 404
    r = await client.patch(
        f"{API}/dashboards/{dash['id']}",
        headers=board.instance.headers,
        json={"visibility": "project", "project": "PA"},
    )
    assert r.status_code == 200, r.text
    listed = (await client.get(f"{API}/dashboards", headers=board.member.headers)).json()["items"]
    assert "V1 Go to market" in [d["name"] for d in listed]

    # The instance admin sees PB's bug; the member only PA's.
    admin_rows = (await widget_data(client, board.instance, bugs.json()["id"])).json()["data"][
        "rows"
    ]
    member_rows = (await widget_data(client, board.member, bugs.json()["id"])).json()["data"][
        "rows"
    ]
    assert sum(r["count"] for r in admin_rows) == 3
    assert {r["value"]: r["count"] for r in member_rows} == {"Backend": 1, "Frontend": 1}
    data = (await widget_data(client, board.member, blocked.json()["id"])).json()
    assert [(t["key"], t["blocked_by"]) for t in data["tickets"]] == [("PA-2", ["PA-1"])]
    summary = (await widget_data(client, board.member, progress.json()["id"])).json()["data"][
        "summary"
    ]
    assert summary["tickets"] == 2 and summary["state"] == "no_forecast"

    # Only the owner edits it.
    r = await client.patch(
        f"{API}/dashboards/{dash['id']}", headers=board.member.headers, json={"name": "Mío"}
    )
    assert r.status_code == 403 and "owner" in r.json()["detail"]
    assert (await widget_data(client, board.outsider, bugs.json()["id"])).status_code == 404


async def test_widgets_validation_and_layout(client: AsyncClient, board: Team) -> None:
    r = await client.post(f"{API}/dashboards", headers=board.member.headers, json={"name": "Mío"})
    dash = r.json()
    cases = [
        ({"widget_type": "gauge", "title": "x"}, "Unknown widget"),
        ({"widget_type": "count", "title": "x", "config": {}}, "needs rql"),
        ({"widget_type": "count", "title": "x", "config": {"rql": "type = = bug"}}, "not valid"),
        ({"widget_type": "filter_results", "title": "x", "config": {}}, "saved `filter`"),
        (
            {
                "widget_type": "markdown",
                "title": "x",
                "config": {"text": "a"},
                "layout": {"x": 10, "y": 0, "w": 6, "h": 2},
            },
            "12 columns",
        ),
        (
            {
                "widget_type": "distribution",
                "title": "x",
                "config": {"rql": "a = b", "field": "color"},
            },
            "Distribution fields",
        ),
    ]
    for body, detail in cases:
        r = await add_widget(client, board.member, dash, **body)
        assert r.status_code == 422 and detail in r.json()["detail"], (body, r.text)

    a = (
        await add_widget(client, board.member, dash, widget_type="my_tickets", title="Míos")
    ).json()
    b = (
        await add_widget(
            client,
            board.member,
            dash,
            widget_type="count",
            title="Abiertos",
            config={"rql": "category != done"},
        )
    ).json()
    r = await client.patch(
        f"{API}/dashboards/{dash['id']}",
        headers=board.member.headers,
        json={
            "layout": [
                {"id": a["id"], "x": 6, "y": 0, "w": 6, "h": 5},
                {"id": b["id"], "x": 0, "y": 0, "w": 6, "h": 5},
            ]
        },
    )
    assert [w["title"] for w in r.json()["widgets"]] == ["Abiertos", "Míos"]
    r = await client.patch(
        f"{API}/dashboards/{dash['id']}/widgets/{b['id']}",
        headers=board.member.headers,
        json={"title": "Pendientes", "config": {"rql": "category = todo"}},
    )
    assert r.json()["title"] == "Pendientes"
    r = await client.delete(
        f"{API}/dashboards/{dash['id']}/widgets/{a['id']}", headers=board.member.headers
    )
    assert r.status_code == 204
    # Sharing with the instance is for instance admins.
    r = await client.patch(
        f"{API}/dashboards/{dash['id']}",
        headers=board.member.headers,
        json={"visibility": "instance"},
    )
    assert r.status_code == 403
    r = await client.delete(f"{API}/dashboards/{dash['id']}", headers=board.member.headers)
    assert r.status_code == 204


async def test_board_widgets_and_saved_filters(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.member, title="Uno", assignee="luis")
    r = await client.post(
        f"{API}/projects/PA/boards",
        headers=board.admin.headers,
        json={"name": "Scrum", "kind": "scrum"},
    )
    scrum = r.json()
    r = await client.post(
        f"{API}/filters",
        headers=board.member.headers,
        json={"name": "Míos", "rql": "assignee = luis"},
    )
    assert r.status_code == 201, r.text
    saved = r.json()
    dash = (
        await client.post(
            f"{API}/dashboards", headers=board.member.headers, json={"name": "Equipo"}
        )
    ).json()
    widgets = {
        "results": await add_widget(
            client,
            board.member,
            dash,
            widget_type="filter_results",
            title="Filtro",
            config={"filter": saved["id"], "limit": 5},
        ),
        "burndown": await add_widget(
            client,
            board.member,
            dash,
            widget_type="sprint_burndown",
            title="Burndown",
            config={"board": scrum["id"]},
        ),
        "cfd": await add_widget(
            client,
            board.member,
            dash,
            widget_type="cumulative_flow",
            title="Flujo",
            config={"board": scrum["id"], "days": 14},
        ),
        "trend": await add_widget(
            client,
            board.member,
            dash,
            widget_type="created_vs_resolved",
            title="Tendencia",
            config={"rql": "project = PA", "days": 90},
        ),
    }
    data = {
        k: (await widget_data(client, board.member, w.json()["id"])).json()
        for k, w in widgets.items()
    }
    assert [t["key"] for t in data["results"]["tickets"]] == ["PA-1"] and data["results"][
        "total"
    ] == 1
    assert data["burndown"]["data"]["sprint"] is None
    assert len(data["cfd"]["data"]["rows"]) == 14
    assert data["trend"]["data"]["summary"]["interval"] == "week"
