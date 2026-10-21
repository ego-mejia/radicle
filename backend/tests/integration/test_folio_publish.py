"""Publishing (Folio 1.3): complete metadata or a 422 that lists what is missing, immutable
versions, labels, and a warning when someone published after the draft started."""

import pytest
from httpx import AsyncClient
from sqlalchemy import text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioDraft
from tests.conftest import Team
from tests.unit.folio_docs import EVERY_BLOCK

API = "/api/v1/folio"
METADATA = {
    "description": "Cómo conectar un agente a Radicle por MCP, paso a paso y con el token.",
    "doc_type": "how-to",
    "labels": ["mcp", "#Agentes"],
    "owner": "@fernando",
    "audiences": ["everyone"],
    "language": "es",
}


@pytest.fixture
async def page(client: AsyncClient, team: Team) -> dict:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": "Conecta"}
    )
    return r.json()


async def _draft(client: AsyncClient, team: Team, page: dict, **body: object) -> None:
    r = await client.put(
        f"{API}/nodes/{page['id']}/draft", headers=team.instance.headers, json=body
    )
    assert r.status_code == 200, r.text


async def _publish(client: AsyncClient, team: Team, page: dict, **body: object):
    return await client.post(
        f"{API}/nodes/{page['id']}/publish", headers=team.instance.headers, json=body
    )


async def test_no_description_no_publishing(client: AsyncClient, team: Team, page: dict) -> None:
    await _draft(client, team, page, content_json=EVERY_BLOCK, metadata={"doc_type": "how-to"})
    r = await _publish(client, team, page)
    assert r.status_code == 422
    fields = [e["field"] for e in r.json()["errors"]]
    assert fields == ["description", "labels", "owner", "audiences", "language"]
    assert "metadata-schema" in r.json()["detail"]

    await _draft(client, team, page, metadata=METADATA)
    r = await _publish(client, team, page, change_note="Primera versión")
    assert r.status_code == 201, r.text
    v1 = r.json()
    assert (v1["number"], v1["author"], v1["change_note"]) == (1, "fernando", "Primera versión")
    assert v1["metadata"]["labels"] == ["mcp", "agentes"] and v1["metadata"]["owner"] == "fernando"

    node = (await client.get(f"{API}/nodes/{page['id']}", headers=team.member.headers)).json()
    assert node["version"] == 1 and node["content_json"] == EVERY_BLOCK
    assert node["metadata"]["doc_type"] == "how-to" and node["published_at"]


async def test_versions_count_up_and_cannot_change(
    client: AsyncClient, db: AsyncSession, team: Team, page: dict
) -> None:
    await _draft(client, team, page, content_md="uno", metadata=METADATA | {"title": "Uno"})
    assert (await _publish(client, team, page)).json()["number"] == 1
    await _draft(client, team, page, content_md="dos")
    assert (await _publish(client, team, page)).json()["number"] == 2
    node = (await client.get(f"{API}/nodes/{page['id']}", headers=team.instance.headers)).json()
    assert node["title"] == "Uno" and node["slug"] == "uno" and node["version"] == 2
    await db.flush()
    with pytest.raises(DBAPIError, match="insert-only"):
        await db.execute(text("UPDATE folio_versions SET title = 'x'"))


async def test_someone_published_after_the_draft_started(
    client: AsyncClient, db: AsyncSession, team: Team, page: dict
) -> None:
    await _draft(client, team, page, content_md="base", metadata=METADATA)
    await _publish(client, team, page)
    # The draft started before version 1 was published (as after a restore elsewhere).
    await db.execute(
        update(FolioDraft).where(FolioDraft.node_id == page["id"]).values(base_version_id=None)
    )
    r = await _publish(client, team, page)
    assert r.status_code == 409 and r.json()["current_version"] == 1
    assert "Version 1 was published" in r.json()["detail"]
    assert (await _publish(client, team, page, confirm=True)).json()["number"] == 2


async def test_actionable_errors(client: AsyncClient, team: Team, page: dict) -> None:
    r = await _publish(client, team, page)
    assert r.status_code == 422 and "no draft" in r.json()["detail"]
    bad = METADATA | {"doc_type": "poema", "labels": ["Con Espacios"], "audiences": ["marte"]}
    bad |= {"description": "Corta.", "owner": "agent-backend", "language": "fr"}
    await _draft(client, team, page, content_md="x", metadata=bad)
    errors = {e["field"] for e in (await _publish(client, team, page)).json()["errors"]}
    assert errors == {"description", "doc_type", "labels", "owner", "audiences", "language"}
    long = "Una frase. Dos frases. Tres frases. Cuatro frases que ya son demasiadas aquí."
    await _draft(client, team, page, metadata=METADATA | {"description": long})
    r = await _publish(client, team, page)
    assert r.json()["errors"] == [{"field": "description", "message": "1 to 3 sentences"}]
    folder = await client.post(
        f"{API}/nodes",
        headers=team.instance.headers,
        json={"space": "docs", "kind": "folder", "title": "F"},
    )
    r = await client.post(
        f"{API}/nodes/{folder.json()['id']}/publish", headers=team.instance.headers, json={}
    )
    assert r.status_code == 422 and "Folders" in r.json()["detail"]


async def test_readers_and_agents_do_not_publish(
    client: AsyncClient, team: Team, page: dict
) -> None:
    await _draft(client, team, page, content_md="x", metadata=METADATA)
    r = await client.post(f"{API}/nodes/{page['id']}/publish", headers=team.member.headers, json={})
    assert r.status_code == 403
    await client.post(
        f"{API}/admin/grants",
        headers=team.instance.headers,
        json={"grantee_type": "user", "grantee": "agent-backend", "role": "creator"},
    )
    r = await client.post(f"{API}/nodes/{page['id']}/publish", headers=team.agent.headers, json={})
    assert r.status_code == 403 and "approval" in r.json()["detail"]
