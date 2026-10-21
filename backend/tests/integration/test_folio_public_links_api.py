"""Public links over REST (Folio 5.1). Acceptance: a public link opens without an account
and, once revoked, answers 404."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.db.models import AuditApp, AuditEntry
from tests.conftest import Team
from tests.integration.folio_helpers import API, publish


@pytest.fixture
async def guide(client: AsyncClient, team: Team) -> str:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "guias", "name": "Guías"})
    body = {"space": "guias", "kind": "page", "title": "Conectar un agente"}
    page = (await client.post(f"{API}/nodes", headers=i, json=body)).json()
    await publish(client, team, page["id"], "# Paso 1\n\nPide el token a @luis.")
    return str(page["id"])


async def test_acceptance_a_link_opens_without_an_account_and_dies_when_revoked(
    client: AsyncClient, db: AsyncSession, team: Team, guide: str
) -> None:
    i = team.instance.headers
    r = await client.post(f"{API}/public-links", headers=i, json={"node": guide})
    assert r.status_code == 201, r.text
    link = r.json()
    token = link["url"].rsplit("/", 1)[1]
    assert link["noindex"] and link["url"].endswith(f"/pub/{token}")

    session = dict(client.cookies)
    client.cookies.clear()  # no session and no token: a stranger
    assert (await client.get(f"{API}/spaces")).status_code == 401
    r = await client.get(f"{API}/pub/{token}")
    assert r.status_code == 200, r.text
    assert r.headers["x-robots-tag"] == "noindex, nofollow"
    body = r.json()
    assert body["page"]["title"] == "Conectar un agente"
    assert "owner" not in body["page"]["metadata"] and team.instance.handle not in r.text
    assert "luis" not in r.text
    html = await client.get(f"/pub/{token}")
    assert html.status_code == 200 and html.headers["x-robots-tag"] == "noindex, nofollow"
    client.cookies.update(session)

    listed = (await client.get(f"{API}/public-links", headers=i, params={"node": guide})).json()
    assert [x["id"] for x in listed["items"]] == [link["id"]]
    assert listed["items"][0]["view_count"] == 1

    assert (await client.delete(f"{API}/public-links/{link['id']}", headers=i)).status_code == 204
    assert (await client.get(f"{API}/pub/{token}")).status_code == 404
    assert (await client.get(f"/pub/{token}")).status_code == 404
    actions = list(
        await db.scalars(
            select(AuditEntry.action).where(
                AuditEntry.app == AuditApp.folio, AuditEntry.action.like("folio.public_link_%")
            )
        )
    )
    assert sorted(actions) == ["folio.public_link_create", "folio.public_link_revoke"]


async def test_a_space_link_never_shows_restricted_pages_or_their_files(
    client: AsyncClient, team: Team, guide: str
) -> None:
    i = team.instance.headers
    body = {"space": "guias", "kind": "page", "title": "Salarios"}
    secret = (await client.post(f"{API}/nodes", headers=i, json=body)).json()["id"]
    await publish(client, team, secret, "Confidencial")
    asset = await client.post(
        f"{API}/nodes/{secret}/assets", headers=i, files={"file": ("plan.pdf", b"%PDF-1.4\n")}
    )
    open_asset = await client.post(
        f"{API}/nodes/{guide}/assets", headers=i, files={"file": ("guia.pdf", b"%PDF-1.4\n")}
    )
    view = {"view": [{"grantee_type": "user", "grantee": team.instance.handle}]}
    assert (
        await client.put(f"{API}/nodes/{secret}/restrictions", headers=i, json=view)
    ).status_code == 200
    r = await client.post(
        f"{API}/public-links", headers=i, json={"space": "guias", "noindex": False}
    )
    token = r.json()["url"].rsplit("/", 1)[1]

    index = await client.get(f"{API}/pub/{token}")
    assert "x-robots-tag" not in index.headers
    assert [n["title"] for n in index.json()["nodes"]] == ["Conectar un agente"]
    assert index.json()["page"] is None and "Salarios" not in index.text
    assert (await client.get(f"{API}/pub/{token}/pages/{guide}")).status_code == 200
    assert (await client.get(f"{API}/pub/{token}/pages/{secret}")).status_code == 404
    r = await client.get(f"{API}/pub/{token}/assets/{asset.json()['id']}")
    assert r.status_code == 404
    r = await client.get(f"{API}/pub/{token}/assets/{open_asset.json()['id']}")
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    listed = await client.get(f"{API}/public-links", headers=i, params={"space": "guias"})
    assert len(listed.json()["items"]) == 1


async def test_errors(client: AsyncClient, team: Team, guide: str) -> None:
    i = team.instance.headers
    r = await client.post(f"{API}/public-links", headers=i, json={"node": guide, "space": "guias"})
    assert r.status_code == 422 and "either node" in r.json()["detail"]
    body = {"space": "guias", "kind": "page", "title": "Borrador"}
    draft = (await client.post(f"{API}/nodes", headers=i, json=body)).json()["id"]
    r = await client.post(f"{API}/public-links", headers=i, json={"node": draft})
    assert r.status_code == 422 and "Publish" in r.json()["detail"]
    assert (await client.get(f"{API}/pub/nope")).status_code == 404
    r = await client.delete(f"{API}/public-links/00000000-0000-0000-0000-000000000000", headers=i)
    assert r.status_code == 404


async def test_only_space_admins_manage_links(client: AsyncClient, team: Team, guide: str) -> None:
    i, m = team.instance.headers, team.member.headers
    grants = {"grants": [{"grantee_type": "everyone", "permissions": ["view", "create"]}]}
    grants["grants"].append(
        {"grantee_type": "user", "grantee": team.instance.handle, "permissions": ["admin"]}
    )
    assert (
        await client.put(f"{API}/spaces/guias/grants", headers=i, json=grants)
    ).status_code == 200
    r = await client.post(f"{API}/public-links", headers=m, json={"node": guide})
    assert r.status_code == 403
    assert (
        await client.get(f"{API}/public-links", headers=m, params={"space": "guias"})
    ).status_code == 403
    link = (await client.post(f"{API}/public-links", headers=i, json={"node": guide})).json()
    assert (await client.delete(f"{API}/public-links/{link['id']}", headers=m)).status_code == 403
