"""Exports over REST (Folio 5.2): ask, follow, download; who may and who may not."""

import io
import zipfile

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.db.models import AuditApp, AuditEntry
from tests.conftest import Team, run_jobs
from tests.integration.folio_helpers import API, publish


@pytest.fixture
async def guide(client: AsyncClient, team: Team) -> str:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "guias", "name": "Guías"})
    body = {"space": "guias", "kind": "page", "title": "Conectar un agente"}
    page = (await client.post(f"{API}/nodes", headers=i, json=body)).json()
    await publish(client, team, page["id"], "# Paso 1\n\nPide el token.")
    return str(page["id"])


async def test_ask_follow_and_download(
    client: AsyncClient, db: AsyncSession, team: Team, guide: str
) -> None:
    i = team.instance.headers
    r = await client.post(f"{API}/exports", headers=i, json={"node": guide, "format": "markdown"})
    assert r.status_code == 202, r.text
    export = r.json()
    assert export["status"] == "queued" and export["download_url"] is None
    early = await client.get(f"{API}/exports/{export['id']}/download", headers=i)
    assert early.status_code == 422 and "queued" in early.json()["detail"]

    await run_jobs(db)
    done = (await client.get(f"{API}/exports/{export['id']}", headers=i)).json()
    assert done["status"] == "done" and done["stats"]["pages"] == 1
    file = await client.get(done["download_url"], headers=i)
    assert file.status_code == 200 and file.headers["content-type"] == "application/zip"
    assert "conectar-un-agente-markdown.zip" in file.headers["content-disposition"]
    assert (
        "Paso 1" in zipfile.ZipFile(io.BytesIO(file.content)).read("conectar-un-agente.md").decode()
    )
    listed = (await client.get(f"{API}/exports", headers=i)).json()["items"]
    assert [x["id"] for x in listed] == [export["id"]]
    entry = await db.scalar(select(AuditEntry).where(AuditEntry.action == "folio.export_create"))
    assert entry is not None and entry.app == AuditApp.folio


async def test_errors(client: AsyncClient, team: Team, guide: str) -> None:
    i = team.instance.headers
    both = {"node": guide, "space": "guias", "format": "pdf"}
    r = await client.post(f"{API}/exports", headers=i, json=both)
    assert r.status_code == 422 and "either node" in r.json()["detail"]
    r = await client.post(f"{API}/exports", headers=i, json={"space": "guias", "format": "rtf"})
    assert r.status_code == 422
    r = await client.post(f"{API}/exports", headers=i, json={"space": "nope", "format": "html"})
    assert r.status_code == 404


async def test_permissions(client: AsyncClient, team: Team, guide: str) -> None:
    i, m = team.instance.headers, team.member.headers
    r = await client.post(f"{API}/exports", headers=m, json={"space": "guias", "format": "html"})
    assert r.status_code == 403 and "export permission" in r.json()["detail"]
    mine = (
        await client.post(f"{API}/exports", headers=i, json={"space": "guias", "format": "html"})
    ).json()
    assert (await client.get(f"{API}/exports/{mine['id']}", headers=m)).status_code == 404
    r = await client.get(f"{API}/exports/{mine['id']}/download", headers=m)
    assert r.status_code == 404
    assert (await client.get(f"{API}/exports", headers=m)).json()["items"] == []
