from httpx import AsyncClient

from tests.conftest import Team, new_ticket, patch_ticket

API = "/api/v1"


async def test_acceptance_three_types_with_all_fields(client: AsyncClient, board: Team) -> None:
    m = board.member
    full = {
        "description_md": "Integrar cobro.\n\n- [x] Definir endpoints @luis\n"
        "- [ ] Webhook @agent-backend\n- [ ] Revisar @nadie",
        "milestone": "v1",
        "priority": "high",
        "assignee": "agent-backend",
        "collaborators": ["luis", "@ana"],
        "due_date": "2026-11-15",
        "estimate_hours": 8,
        "tags": ["#Pagos", "backlog"],
    }
    task = await new_ticket(client, m, type="task", title="API de pagos", area="backend", **full)
    bug = await new_ticket(client, m, type="bug", title="Falla login", area="Frontend", **full)
    draft = await new_ticket(client, m, type="draft", title="Idea", area=None)
    assert [task["key"], bug["key"], draft["key"]] == ["PA-1", "PA-2", "PA-3"]

    assert task["status"] == {"name": "To Do", "category": "todo"}
    assert bug["status"]["name"] == "Reported" and draft["status"]["name"] == "New"
    assert draft["area"] is None
    assert task["area"] == "Backend" and task["milestone"] == "V1"
    assert task["priority"] == "high" and task["due_date"] == "2026-11-15"
    assert task["estimate_hours"] == 8.0 and task["tags"] == ["pagos", "backlog"]
    assert task["assignee"] == {
        "handle": "agent-backend",
        "display_name": "agent-backend",
        "kind": "agent",
    }
    assert [c["handle"] for c in task["collaborators"]] == ["luis", "ana"]
    assert task["reporter"]["handle"] == "luis"
    assert task["version"] == 1 and task["resolution"] is None
    assert task["checklist"] == [
        {
            "index": 0,
            "text": "Definir endpoints",
            "checked": True,
            "assignee": "luis",
            "assignee_unknown": False,
        },
        {
            "index": 1,
            "text": "Webhook",
            "checked": False,
            "assignee": "agent-backend",
            "assignee_unknown": False,
        },
        {
            "index": 2,
            "text": "Revisar",
            "checked": False,
            "assignee": "nadie",
            "assignee_unknown": True,
        },
    ]
    assert task["created_at"].endswith("Z")
    r = await client.get(f"{API}/projects/PA/milestones/V1", headers=m.headers)
    assert r.json()["counts"] == {"todo": 2, "in_progress": 0, "done": 0}
    r = await client.get(f"{API}/projects", headers=m.headers)
    assert r.json()["items"][0]["open_tickets"] == 3


async def test_create_validation_errors(client: AsyncClient, board: Team) -> None:
    h = board.member.headers
    cases = [
        ({"type": "task", "title": "x"}, "area", "Area is required"),
        ({"type": "task", "title": "x", "area": "Nope"}, "area", "Valid areas: Legal"),
        ({"type": "draft", "title": "x", "milestone": "V9"}, "milestone", "Open milestones: V1"),
        ({"type": "draft", "title": "x", "assignee": "vera"}, "assignee", "only active members"),
        ({"type": "draft", "title": "x", "assignee": "ghost"}, "assignee", "does not exist"),
        ({"type": "draft", "title": "x", "parent": "PA-99"}, "parent", "must be a ticket in PA"),
        ({"type": "draft", "title": "a\nb"}, "title", "line breaks"),
        ({"type": "draft", "title": "x", "tags": ["no spaces"]}, "tags", "Invalid tag"),
        ({"type": "draft", "title": "x", "estimate_hours": 10000}, "estimate_hours", "between"),
    ]
    for body, field, message in cases:
        r = await client.post(f"{API}/projects/PA/tickets", headers=h, json=body)
        assert r.status_code == 422, body
        assert r.json()["errors"][0]["field"] == field, body
        assert message in r.json()["detail"], r.json()["detail"]
    r = await client.post(
        f"{API}/projects/PA/tickets", headers=h, json={"type": "epic", "title": "x"}
    )
    assert r.status_code == 422


async def test_closed_milestone_and_archived_area_rejected(
    client: AsyncClient, board: Team
) -> None:
    i = board.instance.headers
    await client.patch(f"{API}/projects/PA/milestones/V1", headers=i, json={"status": "closed"})
    await client.delete(f"{API}/projects/PA/areas/Legal", headers=i)
    r = await client.post(
        f"{API}/projects/PA/tickets",
        headers=board.member.headers,
        json={"type": "task", "title": "x", "area": "Legal"},
    )
    assert "is archived" in r.json()["detail"]
    r = await client.post(
        f"{API}/projects/PA/tickets",
        headers=board.member.headers,
        json={"type": "draft", "title": "x", "milestone": "V1"},
    )
    assert "is closed" in r.json()["detail"]


async def test_get_ticket_not_found(client: AsyncClient, board: Team) -> None:
    for key in ("PA-1", "PB-1", "nonsense"):
        r = await client.get(f"{API}/tickets/{key}", headers=board.member.headers)
        assert r.status_code == 404
    await new_ticket(client, board.member)
    r = await client.get(f"{API}/tickets/pa-1", headers=board.member.headers)
    assert r.status_code == 200 and r.json()["key"] == "PA-1"


async def test_patch_fields_and_history(client: AsyncClient, board: Team) -> None:
    t = await new_ticket(client, board.member, title="Old", description_md="hola")
    r = await patch_ticket(
        client,
        board.member,
        t["key"],
        title="New",
        description_md="hola @ana",
        priority="highest",
        area="Legal",
        milestone="V1",
        assignee="luis",
        due_date="2026-12-01",
        estimate_hours=3.5,
        tags=["a", "b"],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["version"] == 2 and body["title"] == "New" and body["area"] == "Legal"
    r = await client.get(f"{API}/tickets/PA-1/history", headers=board.viewer.headers)
    events = r.json()["items"]
    assert events[-1]["event_type"] == "created"
    changes = {e["field"]: (e["old_value"], e["new_value"]) for e in events[:-1]}
    assert changes == {
        "title": ("Old", "New"),
        "description_md": ("hola", "hola @ana"),
        "priority": ("medium", "highest"),
        "area": ("Backend", "Legal"),
        "milestone": (None, "V1"),
        "assignee": (None, "luis"),
        "due_date": (None, "2026-12-01"),
        "estimate_hours": (None, 3.5),
        "remaining_hours": (None, 3.5),
        "tags": ([], ["a", "b"]),
    }
    assert all(e["actor"]["handle"] == "luis" for e in events)
    assert all(e["event_type"] == "field_changed" for e in events[:-1])

    r = await patch_ticket(
        client,
        board.member,
        "PA-1",
        milestone=None,
        assignee=None,
        due_date=None,
        estimate_hours=None,
        tags=[],
    )
    body = r.json()
    assert body["milestone"] is None and body["assignee"] is None and body["tags"] == []


async def test_patch_noop_keeps_version(client: AsyncClient, board: Team) -> None:
    t = await new_ticket(client, board.member, title="Same")
    r = await patch_ticket(client, board.member, t["key"], title="Same")
    assert r.json()["version"] == 1


async def test_patch_rules(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.member)
    for fields, msg in (
        ({"title": None}, "cannot be cleared"),
        ({"area": None}, "Area is required"),
        ({"priority": None}, "cannot be cleared"),
    ):
        r = await patch_ticket(client, board.member, "PA-1", **fields)
        assert r.status_code == 422 and msg in r.json()["detail"], fields
    r = await patch_ticket(client, board.member, "PA-1", status="Done")
    assert r.status_code == 422


async def test_version_required_and_conflict(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.member)
    h = board.member.headers
    r = await client.patch(f"{API}/tickets/PA-1", headers=h, json={"title": "x"})
    assert r.status_code == 422 and r.json()["errors"][0]["field"] == "expected_version"
    r = await client.patch(
        f"{API}/tickets/PA-1", headers={**h, "If-Match": "abc"}, json={"title": "x"}
    )
    assert r.status_code == 422
    first = await client.patch(
        f"{API}/tickets/PA-1", headers={**h, "If-Match": '"1"'}, json={"title": "First"}
    )
    assert first.status_code == 200
    second = await client.patch(
        f"{API}/tickets/PA-1", headers=h, json={"title": "Second", "expected_version": 1}
    )
    assert second.status_code == 409
    body = second.json()
    assert body["current_version"] == 2
    assert body["current"]["title"] == "First" and body["current"]["version"] == 2
    assert "Someone else changed PA-1" in body["detail"]


async def test_parent_and_children(client: AsyncClient, board: Team) -> None:
    m = board.member
    await new_ticket(client, m, title="Epic")
    await new_ticket(client, m, title="Child", parent="PA-1")
    await new_ticket(client, m, title="Grandchild", parent="pa-2")
    r = await client.get(f"{API}/tickets/PA-2", headers=m.headers)
    assert r.json()["parent"]["key"] == "PA-1" and r.json()["children_count"] == 1
    r = await client.get(f"{API}/tickets/PA-1/children", headers=m.headers)
    assert [c["key"] for c in r.json()["items"]] == ["PA-2"]
    for parent in ("PA-3", "PA-1"):
        r = await patch_ticket(client, m, "PA-1", parent=parent)
        assert r.status_code == 422 and "cycle" in r.json()["errors"][0]["message"]
    r = await patch_ticket(client, m, "PA-3", parent="PA-1")
    assert r.status_code == 200 and r.json()["parent"]["key"] == "PA-1"


async def test_collaborators(client: AsyncClient, board: Team) -> None:
    m = board.member
    await new_ticket(client, m)
    r = await client.put(f"{API}/tickets/PA-1/collaborators/ana", headers=m.headers)
    assert [c["handle"] for c in r.json()["collaborators"]] == ["ana"]
    r = await client.put(f"{API}/tickets/PA-1/collaborators/ana", headers=m.headers)
    assert r.json()["version"] == 2  # idempotent, no new version
    r = await client.put(f"{API}/tickets/PA-1/collaborators/vera", headers=m.headers)
    assert r.status_code == 422
    r = await client.delete(f"{API}/tickets/PA-1/collaborators/ana", headers=m.headers)
    assert r.json()["collaborators"] == []
    r = await client.delete(f"{API}/tickets/PA-1/collaborators/ana", headers=m.headers)
    assert r.status_code == 422
    r = await client.get(f"{API}/tickets/PA-1/history", headers=m.headers)
    kinds = [(e["event_type"], e["old_value"], e["new_value"]) for e in r.json()["items"]]
    assert kinds[:2] == [("collaborator_removed", "ana", None), ("collaborator_added", None, "ana")]


async def test_checklist_toggle(client: AsyncClient, board: Team) -> None:
    m = board.member
    await new_ticket(
        client, m, description_md="Intro\n- [ ] uno @luis\n- [ ] dos\n```\n- [ ] x\n```"
    )
    r = await client.patch(
        f"{API}/tickets/PA-1/checklist/1", headers=m.headers, json={"checked": True}
    )
    assert r.status_code == 200
    body = r.json()
    assert [i["checked"] for i in body["checklist"]] == [False, True]
    assert body["description_md"] == "Intro\n- [ ] uno @luis\n- [x] dos\n```\n- [ ] x\n```"
    again = await client.patch(
        f"{API}/tickets/PA-1/checklist/1", headers=m.headers, json={"checked": True}
    )
    assert again.json()["version"] == body["version"]
    r = await client.patch(
        f"{API}/tickets/PA-1/checklist/2", headers=m.headers, json={"checked": True}
    )
    assert r.status_code == 404 and "0 to 1" in r.json()["detail"]
    r = await client.get(f"{API}/tickets/PA-1/history", headers=m.headers)
    event = r.json()["items"][0]
    assert event["event_type"] == "checklist_item_toggled"
    assert event["new_value"] == {"index": 1, "text": "dos", "checked": True}


async def test_soft_delete_and_restore(client: AsyncClient, board: Team) -> None:
    m, a = board.member, board.admin
    await new_ticket(client, m, title="Parent")
    await new_ticket(client, m, title="Child", parent="PA-1")
    r = await client.delete(f"{API}/tickets/PA-1", headers=m.headers)
    assert r.status_code == 403
    r = await client.delete(f"{API}/tickets/PA-1", headers=a.headers)
    assert r.status_code == 204
    assert (await client.get(f"{API}/tickets/PA-1", headers=a.headers)).status_code == 404
    child = (await client.get(f"{API}/tickets/PA-2", headers=a.headers)).json()
    assert child["parent"] is None
    r = await client.get(f"{API}/tickets/PA-2/history", headers=a.headers)
    assert r.json()["items"][0]["field"] == "parent"
    assert r.json()["items"][0]["old_value"] == "PA-1"
    r = await client.get(f"{API}/projects", headers=a.headers)
    assert r.json()["items"][0]["open_tickets"] == 1

    r = await client.post(f"{API}/tickets/PA-1/restore", headers=m.headers)
    assert r.status_code == 403
    r = await client.post(f"{API}/tickets/PA-1/restore", headers=a.headers)
    assert r.status_code == 200 and r.json()["deleted"] is False
    r = await client.post(f"{API}/tickets/PA-1/restore", headers=a.headers)
    assert r.status_code == 409
    r = await client.get(f"{API}/tickets/PA-1/history", headers=a.headers)
    assert [e["event_type"] for e in r.json()["items"]][:2] == ["restored", "deleted"]


async def test_history_pagination(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.member, title="t0")
    for i in range(1, 6):
        await patch_ticket(client, board.member, "PA-1", title=f"t{i}")
    seen, cursor = [], None
    while True:
        params = {"limit": 2, **({"cursor": cursor} if cursor else {})}
        r = await client.get(
            f"{API}/tickets/PA-1/history", headers=board.member.headers, params=params
        )
        seen += [e["new_value"] for e in r.json()["items"]]
        cursor = r.json()["next_cursor"]
        if not cursor:
            break
    assert [s if isinstance(s, str) else s["title"] for s in seen] == [
        "t5",
        "t4",
        "t3",
        "t2",
        "t1",
        "t0",
    ]
    r = await client.get(
        f"{API}/tickets/PA-1/history", headers=board.member.headers, params={"cursor": "x"}
    )
    assert r.status_code == 422


async def test_mentions_are_stored(client: AsyncClient, board: Team, db) -> None:  # type: ignore[no-untyped-def]
    from sqlalchemy import select

    from radicle.db.models import Mention, User

    await new_ticket(client, board.member, description_md="cc @ana @ghost `@luis` ana@x.com")
    handles = list(
        await db.scalars(select(User.handle).join(Mention, Mention.mentioned_user_id == User.id))
    )
    assert handles == ["ana"]
    await patch_ticket(client, board.member, "PA-1", description_md="now @luis")
    handles = list(
        await db.scalars(select(User.handle).join(Mention, Mention.mentioned_user_id == User.id))
    )
    assert handles == ["luis"]
