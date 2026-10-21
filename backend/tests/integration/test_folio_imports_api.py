"""Imports over REST (Folio 5.3): upload, dry run, run, and who may."""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioNode
from tests.conftest import Team, run_jobs
from tests.folio_import_fixtures import zipped
from tests.integration.folio_helpers import API


async def _space(client: AsyncClient, team: Team) -> None:
    i = team.instance.headers
    r = await client.post(f"{API}/spaces", headers=i, json={"key": "eng", "name": "Ingeniería"})
    assert r.status_code == 201, r.text


def _upload(source: str = "confluence", data: bytes | None = None, name: str = "ENG.zip") -> dict:
    return {
        "files": {"file": (name, data if data is not None else zipped("confluence"))},
        "data": {"source": source, "space": "eng"},
    }


async def test_upload_dry_run_and_run(client: AsyncClient, db: AsyncSession, team: Team) -> None:
    await _space(client, team)
    i = team.instance.headers
    r = await client.post(f"{API}/imports", headers=i, **_upload())
    assert r.status_code == 201, r.text
    made = r.json()
    assert made["status"] == "uploaded" and made["space"] == "eng" and made["report"] == {}
    r = await client.post(f"{API}/imports/{made['id']}/dry-run", headers=i, json={})
    assert r.status_code == 200, r.text
    plan = r.json()["report"]
    assert plan["totals"]["pages"] == 4 and plan["authors"][0]["source"] == "Ana López"
    r = await client.post(f"{API}/imports/{made['id']}/run", headers=i)
    assert r.status_code == 202 and r.json()["status"] == "running"
    await run_jobs(db)
    r = await client.get(f"{API}/imports/{made['id']}", headers=i)
    done = r.json()
    assert done["status"] == "done" and done["stats"]["created"] == 4
    assert "run_by" not in done["stats"] and len(done["report"]["run"]) == 4
    assert [x["id"] for x in (await client.get(f"{API}/imports", headers=i)).json()["items"]] == [
        made["id"]
    ]
    titles = set(await db.scalars(select(FolioNode.title)))
    assert {"Home", "Guías", "Conectar un agente", "Decisiones"} <= titles


async def test_errors(client: AsyncClient, team: Team) -> None:
    await _space(client, team)
    i = team.instance.headers
    r = await client.post(f"{API}/imports", headers=i, **_upload(data=b"", name="a.md"))
    assert r.status_code == 422 and "empty" in r.json()["detail"]
    r = await client.post(f"{API}/imports", headers=i, **_upload(source="evernote"))
    assert r.status_code == 422
    made = (await client.post(f"{API}/imports", headers=i, **_upload())).json()
    r = await client.post(f"{API}/imports/{made['id']}/run", headers=i)
    assert r.status_code == 409 and "dry run first" in r.json()["detail"]
    r = await client.post(f"{API}/imports/{made['id']}/dry-run", headers=i, json={"x": 1})
    assert r.status_code == 422
    r = await client.post(
        f"{API}/imports/{made['id']}/dry-run", headers=i, json={"authors": {"Ana": "nope"}}
    )
    assert r.status_code == 422 and "not an id" in r.json()["detail"]
    r = await client.get(f"{API}/imports/{team.instance.handle}", headers=i)
    assert r.status_code == 422
    r = await client.get(f"{API}/imports/00000000-0000-0000-0000-000000000000", headers=i)
    assert r.status_code == 404


async def test_only_the_space_admins(client: AsyncClient, team: Team) -> None:
    await _space(client, team)
    i, m = team.instance.headers, team.member.headers
    r = await client.post(f"{API}/imports", headers=m, **_upload())
    assert r.status_code == 403 and "Only the admins of Ingeniería" in r.json()["detail"]
    made = (await client.post(f"{API}/imports", headers=i, **_upload())).json()
    assert (await client.get(f"{API}/imports/{made['id']}", headers=m)).status_code == 403
    assert (await client.get(f"{API}/imports", headers=m)).json()["items"] == []
    r = await client.post(f"{API}/imports/{made['id']}/dry-run", headers=m, json={})
    assert r.status_code == 403
    assert (await client.post(f"{API}/imports/{made['id']}/run", headers=m)).status_code == 403
    r = await client.post(f"{API}/imports", headers=team.agent.headers, **_upload())
    assert r.status_code == 403
