"""Archiving (Folio 2.6). Acceptance: archiving takes a page out of the tree, search and
the RAG index; restoring brings it back."""

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioChunk
from tests.conftest import Team, run_jobs
from tests.integration.folio_helpers import API, publish


@pytest.fixture
async def pages(client: AsyncClient, db: AsyncSession, team: Team) -> dict:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    made = {}
    for title, parent in (("Guía de deploy", None), ("Rollback", "Guía de deploy")):
        body = {"space": "docs", "kind": "page", "title": title, "parent": made.get(parent)}
        made[title] = (await client.post(f"{API}/nodes", headers=i, json=body)).json()["id"]
        await publish(client, team, made[title], md=f"# {title}\n\nDespliegue con Docker.")
    await run_jobs(db)
    return {"guide": made["Guía de deploy"], "child": made["Rollback"]}


async def _tree(client: AsyncClient, team: Team) -> list[str]:
    r = await client.get(f"{API}/spaces/docs/tree", headers=team.member.headers)
    out: list[str] = []

    def walk(items: list[dict]) -> None:
        for item in items:
            out.append(item["id"])
            walk(item["children"])

    walk(r.json())
    return out


async def _search(client: AsyncClient, team: Team) -> list[str]:
    params = {"q": "despliegue docker", "mode": "text"}
    r = await client.get(f"{API}/search", params=params, headers=team.member.headers)
    return [h["node_id"] for h in r.json()["items"]]


async def _chunks(db: AsyncSession) -> int:
    return int(await db.scalar(select(func.count()).select_from(FolioChunk)) or 0)


async def test_acceptance_archive_and_restore(
    client: AsyncClient, db: AsyncSession, team: Team, pages: dict
) -> None:
    i = team.instance.headers
    assert set(await _search(client, team)) == {pages["guide"], pages["child"]}
    indexed = await _chunks(db)
    r = await client.post(f"{API}/nodes/{pages['guide']}/archive", headers=i)
    assert r.status_code == 200 and r.json()["archived_at"], r.text
    await run_jobs(db)
    assert await _tree(client, team) == [] and await _search(client, team) == []
    assert await _chunks(db) == 0
    rql = (await client.get(f"{API}/nodes", params={"q": "space = docs"}, headers=i)).json()
    assert rql["items"] == []
    rql = await client.get(f"{API}/nodes", params={"q": "archived = true"}, headers=i)
    assert {d["id"] for d in rql.json()["items"]} == {pages["guide"], pages["child"]}
    archived = (await client.get(f"{API}/spaces/docs/archived", headers=i)).json()["items"]
    assert [a["id"] for a in archived] == [pages["guide"]]  # only the root
    assert archived[0]["archived_by"] == team.instance.handle
    page = await client.get(f"{API}/nodes/{pages['child']}", headers=team.member.headers)
    assert page.status_code == 200  # direct links keep working

    r = await client.post(f"{API}/nodes/{pages['guide']}/unarchive", headers=i)
    assert r.status_code == 200 and r.json()["archived_at"] is None
    await run_jobs(db)
    assert await _tree(client, team) == [pages["guide"], pages["child"]]
    assert set(await _search(client, team)) == {pages["guide"], pages["child"]}
    assert await _chunks(db) == indexed > 0


async def test_restoring_keeps_what_was_archived_on_its_own(
    client: AsyncClient, db: AsyncSession, team: Team, pages: dict
) -> None:
    i = team.instance.headers
    await client.post(f"{API}/nodes/{pages['child']}/archive", headers=i)
    await client.post(f"{API}/nodes/{pages['guide']}/archive", headers=i)
    archived = (await client.get(f"{API}/spaces/docs/archived", headers=i)).json()["items"]
    assert [a["id"] for a in archived] == [pages["guide"], pages["child"]]
    await client.post(f"{API}/nodes/{pages['guide']}/unarchive", headers=i)
    assert await _tree(client, team) == [pages["guide"]]


async def test_errors_and_permissions(client: AsyncClient, team: Team, pages: dict) -> None:
    i, m = team.instance.headers, team.member.headers
    r = await client.post(f"{API}/nodes/{pages['guide']}/archive", headers=m)
    assert r.status_code == 403 and "delete" in r.json()["detail"]
    assert (
        await client.post(f"{API}/nodes/{pages['guide']}/unarchive", headers=i)
    ).status_code == 409
    await client.post(f"{API}/nodes/{pages['guide']}/archive", headers=i)
    assert (
        await client.post(f"{API}/nodes/{pages['guide']}/archive", headers=i)
    ).status_code == 409
    r = await client.post(f"{API}/nodes/{pages['child']}/unarchive", headers=i)
    assert r.status_code == 409 and "Guía de deploy" in r.json()["detail"]
    r = await client.get(f"{API}/spaces/nada/archived", headers=i)
    assert r.status_code == 404
