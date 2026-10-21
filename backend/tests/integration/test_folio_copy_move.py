"""Copying and moving between spaces (Folio 2.6)."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioChunk
from tests.conftest import Team, run_jobs
from tests.integration.folio_helpers import API, publish


@pytest.fixture
async def tree(client: AsyncClient, db: AsyncSession, team: Team) -> dict:
    i = team.instance.headers
    for key in ("docs", "ops"):
        await client.post(f"{API}/spaces", headers=i, json={"key": key, "name": key.title()})
    made: dict[str, str] = {}
    for title, parent in (
        ("Guía", None),
        ("Paso 1", "Guía"),
        ("Paso 2", "Guía"),
        ("Viejo", "Guía"),
    ):
        body = {"space": "docs", "kind": "page", "title": title, "parent": made.get(parent)}
        made[title] = (await client.post(f"{API}/nodes", headers=i, json=body)).json()["id"]
        await publish(client, team, made[title], md=f"# {title}\n\nTexto de {title}.")
    await client.post(f"{API}/nodes/{made['Viejo']}/archive", headers=i)
    await run_jobs(db)
    return made


async def _titles(client: AsyncClient, team: Team, space: str) -> list[tuple[str, list[str]]]:
    r = await client.get(f"{API}/spaces/{space}/tree", headers=team.instance.headers)
    return [(n["title"], [c["title"] for c in n["children"]]) for n in r.json()]


async def test_copy_with_children(client: AsyncClient, team: Team, tree: dict) -> None:
    i = team.instance.headers
    body = {"space": "ops", "include_children": True}
    r = await client.post(f"{API}/nodes/{tree['Guía']}/copy", headers=i, json=body)
    assert r.status_code == 201, r.text
    copy = r.json()
    assert copy["id"] != tree["Guía"] and copy["version"] is None and copy["status"] == "draft"
    assert await _titles(client, team, "ops") == [("Guía", ["Paso 1", "Paso 2"])]  # no archived
    draft = (await client.get(f"{API}/nodes/{copy['id']}/draft", headers=i)).json()
    assert "Texto de Guía" in draft["content_md"] and draft["metadata"]["doc_type"] == "how-to"
    assert await _titles(client, team, "docs") == [("Guía", ["Paso 1", "Paso 2"])]  # untouched


async def test_copy_alone_in_the_same_space(client: AsyncClient, team: Team, tree: dict) -> None:
    r = await client.post(
        f"{API}/nodes/{tree['Paso 1']}/copy", headers=team.instance.headers, json={}
    )
    assert r.status_code == 201 and r.json()["space"] == "docs" and r.json()["parent_id"] is None
    assert ("Paso 1", []) in await _titles(client, team, "docs")


async def test_move_to_another_space_keeps_id_and_reindexes(
    client: AsyncClient, db: AsyncSession, team: Team, tree: dict
) -> None:
    i = team.instance.headers
    r = await client.post(f"{API}/nodes/{tree['Guía']}/move", headers=i, json={"space": "ops"})
    assert r.status_code == 200, r.text
    assert r.json()["id"] == tree["Guía"] and r.json()["space"] == "ops"
    assert await _titles(client, team, "docs") == []
    assert await _titles(client, team, "ops") == [("Guía", ["Paso 1", "Paso 2"])]
    child = (await client.get(f"{API}/nodes/{tree['Paso 1']}", headers=i)).json()
    assert child["space"] == "ops"
    await run_jobs(db)
    spaces = set(await db.scalars(select(FolioChunk.metadata_["space"].astext)))
    assert spaces == {"ops"}


async def test_errors_and_permissions(client: AsyncClient, team: Team, tree: dict) -> None:
    i, m = team.instance.headers, team.member.headers
    r = await client.post(f"{API}/nodes/{tree['Guía']}/move", headers=m, json={"space": "ops"})
    assert r.status_code == 403
    r = await client.post(f"{API}/nodes/{tree['Guía']}/copy", headers=m, json={"space": "ops"})
    assert r.status_code == 403 and "creator role" in r.json()["detail"]
    r = await client.post(f"{API}/nodes/{tree['Guía']}/move", headers=i, json={"space": "nada"})
    assert r.status_code == 404
    post = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "blog_post", "title": "Post"}
    )
    url = f"{API}/nodes/{post.json()['id']}/copy"
    r = await client.post(url, headers=i, json={"include_children": True})
    assert r.status_code == 422
