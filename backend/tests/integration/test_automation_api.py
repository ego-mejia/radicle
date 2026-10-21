"""Automation rules over REST (Folio 5.6): instance admins manage them, start from the
examples and read each run's log; nobody else can."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import Team, run_jobs
from tests.integration.folio_helpers import API, publish

URL = "/api/v1/automation"
RULE = {
    "name": "Etiquetar",
    "trigger": {"type": "event", "event": "page.published"},
    "filter": {"space": "docs"},
    "actions": [{"type": "folio.add_label", "label": "nuevo"}],
}


async def test_manage_rules_and_read_their_runs(
    client: AsyncClient, db: AsyncSession, team: Team
) -> None:
    i = team.instance.headers
    actions = {a["name"] for a in (await client.get(f"{URL}/actions", headers=i)).json()}
    assert {"notify_channel", "notify_person", "folio.archive", "folio.add_label"} <= actions
    examples = (await client.get(f"{URL}/examples", headers=i)).json()
    assert examples[0]["trigger"] == {"type": "event", "event": "page.outdated"}
    r = await client.post(f"{URL}/rules", headers=i, json=RULE)
    assert r.status_code == 201, r.text
    rule = r.json()
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    page = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": "Guía"}
    )
    await publish(client, team, page.json()["id"])
    await run_jobs(db)
    runs = (await client.get(f"{URL}/rules/{rule['id']}/runs", headers=i)).json()
    assert runs[0]["status"] == "sent" and runs[0]["log"] == ["folio.add_label: “Guía” has #nuevo"]
    r = await client.put(f"{URL}/rules/{rule['id']}", headers=i, json=RULE | {"active": False})
    assert r.json()["active"] is False
    assert [x["name"] for x in (await client.get(f"{URL}/rules", headers=i)).json()] == [
        "Etiquetar"
    ]
    assert (await client.delete(f"{URL}/rules/{rule['id']}", headers=i)).status_code == 204
    assert (await client.get(f"{URL}/rules/{rule['id']}", headers=i)).status_code == 404


async def test_errors_say_how_to_fix(client: AsyncClient, team: Team) -> None:
    i = team.instance.headers
    bad = RULE | {"trigger": {"type": "event", "event": "page.flew"}}
    r = await client.post(f"{URL}/rules", headers=i, json=bad)
    assert r.status_code == 422 and "Pick one of these events" in r.json()["detail"]
    r = await client.post(
        f"{URL}/rules", headers=i, json=RULE | {"actions": [{"type": "folio.change_status"}]}
    )
    assert r.status_code == 422 and "needs a status" in r.json()["detail"]
    missing = "00000000-0000-0000-0000-000000000000"
    r = await client.get(f"{URL}/rules/{missing}/runs", headers=i)
    assert r.status_code == 404 and "GET /api/v1/automation/rules" in r.json()["detail"]


async def test_only_instance_admins(client: AsyncClient, team: Team) -> None:
    rule = (await client.post(f"{URL}/rules", headers=team.instance.headers, json=RULE)).json()
    for actor in (team.admin, team.member):
        h = actor.headers
        assert (await client.get(f"{URL}/rules", headers=h)).status_code == 403
        assert (await client.post(f"{URL}/rules", headers=h, json=RULE)).status_code == 403
        assert (await client.get(f"{URL}/rules/{rule['id']}/runs", headers=h)).status_code == 403
        assert (await client.get(f"{URL}/examples", headers=h)).status_code == 403
