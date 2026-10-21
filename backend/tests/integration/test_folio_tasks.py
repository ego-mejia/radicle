"""Action items and Mis tareas (Folio 2.4). Acceptance: I assign an action item, the
person checks it off from Mis tareas and it's checked in the document."""

from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioDraft
from radicle.folio.services import actions, quality
from radicle.platform.db.models import Notification, User
from tests.conftest import Team, run_jobs
from tests.integration.folio_helpers import API, publish


def _md(team: Team, due_late: str, due_soon: str, who: str | None = None) -> str:
    who = who or team.member.handle
    return (
        "# Minuta\n\n"
        f"::task[Mandar el contrato]{{id=ai-1 assignee={who} due={due_late}}}\n\n"
        f"::task[Revisar el deploy]{{id=ai-2 assignee={team.member.handle} due={due_soon}}}\n\n"
        "::task[Sin dueño]{id=ai-3}\n"
    )


async def _notices(db: AsyncSession, handle: str) -> list[str]:
    user = await db.scalar(select(User).where(User.handle == handle))
    assert user is not None
    rows = await db.scalars(select(Notification.title).where(Notification.user_id == user.id))
    return list(rows)


@pytest.fixture
async def page(client: AsyncClient, team: Team) -> str:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": "Minuta"}
    )
    await publish(client, team, r.json()["id"])  # readers see it
    return str(r.json()["id"])


def test_extract_keeps_order_and_the_first_of_a_repeated_id() -> None:
    def item(key: str, text: str) -> dict:
        return {
            "type": "actionItem",
            "attrs": {"id": key},
            "content": [{"type": "text", "text": text}],
        }

    doc = {
        "type": "doc",
        "content": [
            item("a", "uno"),
            {"type": "panel", "content": [item("b", "dos")]},
            item("a", "x"),
        ],
    }
    assert [(i.key, i.text) for i in actions.extract(doc)] == [("a", "uno"), ("b", "dos")]


async def test_acceptance_assign_and_check_off_from_my_tasks(
    client: AsyncClient, db: AsyncSession, team: Team, page: str
) -> None:
    i, m = team.instance.headers, team.member.headers
    today = quality.today()
    late, soon = today - timedelta(days=2), today + timedelta(days=3)
    r = await client.put(
        f"{API}/nodes/{page}/draft", headers=i, json={"content_md": _md(team, str(late), str(soon))}
    )
    assert r.status_code == 200, r.text
    await run_jobs(db)
    notices = [t for t in await _notices(db, team.member.handle) if "assigned you" in t]
    assert len(notices) == 2
    assert all(t.startswith("Fernando assigned you") for t in notices)

    tasks = (await client.get(f"{API}/me/tasks", headers=m)).json()["items"]
    assert [(t["text"], t["bucket"]) for t in tasks] == [
        ("Mandar el contrato", "overdue"),
        ("Revisar el deploy", "upcoming"),
    ]
    assert tasks[0]["url"].startswith("/folio/p/") and tasks[0]["node"]["title"] == "Minuta"

    # The member only reads the page, but it's their task: they check it off.
    r = await client.patch(f"{API}/action-items/{tasks[0]['id']}", headers=m, json={"done": True})
    assert r.status_code == 200, r.text
    assert r.json()["done"] is True
    draft = await db.get(FolioDraft, tasks[0]["node"]["id"])
    assert draft is not None
    done = [n for n in draft.content_json["content"] if n["type"] == "actionItem"]
    assert [n["attrs"].get("done", False) for n in done] == [True, False, False]
    left = (await client.get(f"{API}/me/tasks", headers=m)).json()["items"]
    assert [t["text"] for t in left] == ["Revisar el deploy"]
    finished = (await client.get(f"{API}/me/tasks", params={"status": "done"}, headers=m)).json()
    assert [t["text"] for t in finished["items"]] == ["Mandar el contrato"]


async def test_reassigning_tells_the_new_person(
    client: AsyncClient, db: AsyncSession, team: Team, page: str
) -> None:
    i = team.instance.headers
    today = str(quality.today())
    await client.put(
        f"{API}/nodes/{page}/draft", headers=i, json={"content_md": _md(team, today, today)}
    )
    await run_jobs(db)
    md = _md(team, today, today, who=team.viewer.handle)
    await client.put(f"{API}/nodes/{page}/draft", headers=i, json={"content_md": md})
    await run_jobs(db)
    assert len([t for t in await _notices(db, team.viewer.handle) if "assigned you" in t]) == 1
    tasks = (await client.get(f"{API}/me/tasks", headers=team.member.headers)).json()["items"]
    assert [t["text"] for t in tasks] == ["Revisar el deploy"]
    viewer = (await client.get(f"{API}/me/tasks", headers=team.viewer.headers)).json()["items"]
    assert [(t["text"], t["bucket"]) for t in viewer] == [("Mandar el contrato", "today")]
    # Deleting an item from the document removes it.
    await client.put(f"{API}/nodes/{page}/draft", headers=i, json={"content_md": "Nada"})
    assert (await client.get(f"{API}/me/tasks", headers=team.viewer.headers)).json()["items"] == []


async def test_no_notice_for_a_task_you_assign_yourself(
    client: AsyncClient, db: AsyncSession, team: Team, page: str
) -> None:
    i, me = team.instance.headers, team.instance.handle
    md = f"::task[Escribir las notas]{{id=ai-1 assignee={me}}}\n"
    r = await client.put(f"{API}/nodes/{page}/draft", headers=i, json={"content_md": md})
    assert r.status_code == 200, r.text
    await run_jobs(db)
    assert [t for t in await _notices(db, me) if "assigned you" in t] == []


async def test_permissions(client: AsyncClient, db: AsyncSession, team: Team, page: str) -> None:
    i = team.instance.headers
    today = str(quality.today())
    await client.put(
        f"{API}/nodes/{page}/draft", headers=i, json={"content_md": _md(team, today, today)}
    )
    tasks = (await client.get(f"{API}/me/tasks", headers=team.member.headers)).json()["items"]
    r = await client.patch(
        f"{API}/action-items/{tasks[0]['id']}", headers=team.viewer.headers, json={"done": True}
    )
    assert r.status_code == 403 and "assigned" in r.json()["detail"]
    r = await client.patch(
        f"{API}/action-items/00000000-0000-0000-0000-000000000000", headers=i, json={"done": True}
    )
    assert r.status_code == 404
    await client.put(
        f"{API}/nodes/{page}/restrictions",
        headers=i,
        json={"view": [{"grantee_type": "user", "grantee": team.instance.handle}]},
    )
    assert (await client.get(f"{API}/me/tasks", headers=team.member.headers)).json()["items"] == []
    r = await client.patch(
        f"{API}/action-items/{tasks[0]['id']}", headers=team.member.headers, json={"done": True}
    )
    assert r.status_code == 404
