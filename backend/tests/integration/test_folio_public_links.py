"""Public links (Folio 5.1): what a link shows, to whom, and when it stops working."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioNode, FolioSpace
from radicle.folio.services import public_links
from radicle.platform.db.models import User
from radicle.platform.errors import Forbidden, NotFound, ValidationFailed
from tests.conftest import Team
from tests.integration.folio_helpers import API, publish


async def _user(db: AsyncSession, handle: str) -> User:
    user = await db.scalar(select(User).where(User.handle == handle))
    assert user is not None
    return user


async def _page(client: AsyncClient, team: Team, title: str, parent: str | None = None) -> str:
    body = {"space": "guias", "kind": "page", "title": title, "parent": parent}
    r = await client.post(f"{API}/nodes", headers=team.instance.headers, json=body)
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


@pytest.fixture
async def space(client: AsyncClient, db: AsyncSession, team: Team) -> FolioSpace:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "guias", "name": "Guías"})
    found = await db.scalar(select(FolioSpace).where(FolioSpace.key == "guias"))
    assert found is not None
    return found


async def _node(db: AsyncSession, node_id: str) -> FolioNode:
    node = await db.get(FolioNode, uuid.UUID(node_id))
    assert node is not None
    return node


def test_tokens_are_long_and_base62() -> None:
    tokens = {public_links.new_token() for _ in range(50)}
    assert len(tokens) == 50
    assert all(len(t) == 43 and t.isalnum() for t in tokens)


async def test_a_page_link_opens_and_stops_when_revoked(
    client: AsyncClient, db: AsyncSession, team: Team, space: FolioSpace
) -> None:
    guide = await _page(client, team, "Conectar un agente")
    await publish(client, team, guide, "# Paso 1\n\nPide el token a @luis.")
    admin = await _user(db, team.instance.handle)
    link = await public_links.create_link(db, admin, await _node(db, guide))
    assert link.noindex and link.view_count == 0

    seen = await public_links.view(db, link.token)
    assert seen.page is not None and seen.page.node.title == "Conectar un agente"
    text = str(public_links.scrub(seen.page.version.content_json))
    assert "luis" not in text and "@…" in text
    await db.refresh(link)
    assert link.view_count == 1

    await public_links.revoke(db, admin, link.id)
    with pytest.raises(NotFound):
        await public_links.view(db, link.token)
    with pytest.raises(NotFound):
        await public_links.revoke(db, admin, link.id)


async def test_a_space_link_leaves_out_restricted_and_archived_branches(
    client: AsyncClient, db: AsyncSession, team: Team, space: FolioSpace
) -> None:
    i = team.instance.headers
    open_page = await _page(client, team, "Inicio")
    secret = await _page(client, team, "Salarios")
    below = await _page(client, team, "Detalle", parent=secret)
    old = await _page(client, team, "Viejo")
    draft = await _page(client, team, "Borrador")
    for node_id in (open_page, secret, below, old):
        await publish(client, team, node_id)
    view = {"view": [{"grantee_type": "user", "grantee": team.instance.handle}]}
    r = await client.put(f"{API}/nodes/{secret}/restrictions", headers=i, json=view)
    assert r.status_code == 200, r.text
    assert (await client.post(f"{API}/nodes/{old}/archive", headers=i)).status_code == 200

    admin = await _user(db, team.instance.handle)
    link = await public_links.create_link(db, admin, space)
    seen = await public_links.view(db, link.token)
    assert [n.title for n in seen.nodes] == ["Inicio"] and seen.page is None
    for hidden in (secret, below, old, draft):
        with pytest.raises(NotFound):
            await public_links.view(db, link.token, uuid.UUID(hidden))
    assert (await public_links.view(db, link.token, uuid.UUID(open_page))).page is not None

    # A restricted page can't get its own link.
    with pytest.raises(ValidationFailed, match="restricted"):
        await public_links.create_link(db, admin, await _node(db, below))
    with pytest.raises(ValidationFailed, match="Publish"):
        await public_links.create_link(db, admin, await _node(db, draft))


async def test_a_page_restricted_later_stops_its_link(
    client: AsyncClient, db: AsyncSession, team: Team, space: FolioSpace
) -> None:
    page = await _page(client, team, "Guía")
    await publish(client, team, page)
    admin = await _user(db, team.instance.handle)
    link = await public_links.create_link(db, admin, await _node(db, page))
    view = {"view": [{"grantee_type": "user", "grantee": team.instance.handle}]}
    r = await client.put(
        f"{API}/nodes/{page}/restrictions", headers=team.instance.headers, json=view
    )
    assert r.status_code == 200, r.text
    with pytest.raises(NotFound):
        await public_links.view(db, link.token)


async def test_only_space_admins_manage_links(
    client: AsyncClient, db: AsyncSession, team: Team, space: FolioSpace
) -> None:
    page = await _page(client, team, "Guía")
    await publish(client, team, page)
    reader = await _user(db, team.member.handle)
    with pytest.raises(Forbidden):
        await public_links.create_link(db, reader, space)
    admin = await _user(db, team.instance.handle)
    link = await public_links.create_link(db, admin, await _node(db, page), noindex=False)
    with pytest.raises(Forbidden):
        await public_links.revoke(db, reader, link.id)


def test_scrub_and_metadata_drop_people() -> None:
    doc = {
        "type": "doc",
        "content": [
            {"type": "actionItem", "attrs": {"id": "a1", "assignee": "luis"}, "content": []},
            {"type": "paragraph", "content": [{"type": "mention", "attrs": {"handle": "ana"}}]},
        ],
    }
    clean = public_links.scrub(doc)
    assert clean["content"][0]["attrs"]["assignee"] is None
    assert clean["content"][1]["content"] == [{"type": "text", "text": "@…"}]
    assert doc["content"][0]["attrs"]["assignee"] == "luis"  # the original is untouched
    meta = public_links.public_metadata({"owner": "@ana", "description": "D", "labels": ["x"]})
    assert meta == {"description": "D", "labels": ["x"]}
