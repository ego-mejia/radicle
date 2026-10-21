from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.docket.db.models import ApiToken
from tests.conftest import Actor, new_agent


async def test_personal_token_lifecycle(client: AsyncClient, admin: Actor) -> None:
    r = await client.post(
        "/api/v1/me/tokens", headers=admin.headers, json={"name": "claude-code laptop"}
    )
    assert r.status_code == 201
    created = r.json()
    token = created["token"]
    assert token.startswith("rdc_") and created["prefix"] == token[:8]

    r = await client.get("/api/v1/me/tokens", headers=admin.headers)
    listed = r.json()["items"]
    assert [t["name"] for t in listed] == ["claude-code laptop"]
    assert "token" not in listed[0]

    r = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    r = await client.get("/api/v1/me/tokens", headers=admin.headers)
    assert r.json()["items"][0]["last_used_at"] is not None

    r = await client.delete(f"/api/v1/me/tokens/{created['id']}", headers=admin.headers)
    assert r.status_code == 204
    client.cookies.clear()
    r = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
    assert "revoked" in r.json()["detail"]


async def test_revoke_twice_and_unknown(client: AsyncClient, admin: Actor) -> None:
    r = await client.post("/api/v1/me/tokens", headers=admin.headers, json={"name": "x"})
    token_id = r.json()["id"]
    await client.delete(f"/api/v1/me/tokens/{token_id}", headers=admin.headers)
    r = await client.delete(f"/api/v1/me/tokens/{token_id}", headers=admin.headers)
    assert r.status_code == 409
    r = await client.delete(
        "/api/v1/me/tokens/00000000-0000-0000-0000-000000000000", headers=admin.headers
    )
    assert r.status_code == 404


async def test_expired_token(client: AsyncClient, admin: Actor, db: AsyncSession) -> None:
    r = await client.post("/api/v1/me/tokens", headers=admin.headers, json={"name": "short"})
    token = r.json()["token"]
    await db.execute(update(ApiToken).values(expires_at=datetime.now(UTC) - timedelta(seconds=1)))
    client.cookies.clear()
    r = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
    assert "expired" in r.json()["detail"]


async def test_token_expiry_must_be_future(client: AsyncClient, admin: Actor) -> None:
    r = await client.post(
        "/api/v1/me/tokens",
        headers=admin.headers,
        json={"name": "x", "expires_at": "2000-01-01T00:00:00Z"},
    )
    assert r.status_code == 422


async def test_malformed_and_unknown_bearer(client: AsyncClient) -> None:
    for header in ("Bearer nope", "Basic abc", "Bearer ", f"Bearer rdc_{'a' * 40}"):
        r = await client.get("/api/v1/me", headers={"Authorization": header})
        assert r.status_code == 401, header


async def test_agent_cannot_manage_personal_tokens(client: AsyncClient, admin: Actor) -> None:
    agent = await new_agent(client, admin, "agent-backend")
    client.cookies.clear()
    r = await client.get("/api/v1/me/tokens", headers=agent.headers)
    assert r.status_code == 403
    r = await client.patch("/api/v1/me", headers=agent.headers, json={"display_name": "x"})
    assert r.status_code == 403
