from httpx import AsyncClient

from tests.conftest import ADMIN_PASSWORD, Actor, login, new_agent


async def test_login_sets_httponly_session_and_csrf(client: AsyncClient, admin: Actor) -> None:
    client.cookies.clear()
    r = await client.post(
        "/api/v1/auth/login", json={"email": "ADMIN@example.com", "password": ADMIN_PASSWORD}
    )
    assert r.status_code == 200
    cookies = r.headers.get_list("set-cookie")
    session = next(c for c in cookies if c.startswith("radicle_session="))
    csrf = next(c for c in cookies if c.startswith("radicle_csrf="))
    assert "HttpOnly" in session and "SameSite=lax" in session
    assert "HttpOnly" not in csrf


async def test_login_wrong_password(client: AsyncClient, admin: Actor) -> None:
    r = await client.post(
        "/api/v1/auth/login", json={"email": "admin@example.com", "password": "nope-nope"}
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid email or password."


async def test_login_unknown_email_same_error(client: AsyncClient, admin: Actor) -> None:
    r = await client.post(
        "/api/v1/auth/login", json={"email": "ghost@example.com", "password": "nope-nope"}
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid email or password."


async def test_login_rate_limit(client: AsyncClient, admin: Actor) -> None:
    body = {"email": "admin@example.com", "password": "wrong-pass"}
    for _ in range(10):
        assert (await client.post("/api/v1/auth/login", json=body)).status_code == 401
    r = await client.post("/api/v1/auth/login", json=body)
    assert r.status_code == 429
    assert int(r.headers["retry-after"]) >= 1
    assert r.json()["retry_after"] >= 1


async def test_deactivated_user_cannot_login(client: AsyncClient, admin: Actor) -> None:
    await client.post(
        "/api/v1/users",
        headers=admin.headers,
        json={
            "handle": "ana",
            "display_name": "Ana",
            "email": "ana@example.com",
            "password": "temporary-pass",
        },
    )
    await client.patch("/api/v1/users/ana", headers=admin.headers, json={"is_active": False})
    r = await client.post(
        "/api/v1/auth/login", json={"email": "ana@example.com", "password": "temporary-pass"}
    )
    assert r.status_code == 401


async def test_me_requires_auth(client: AsyncClient) -> None:
    r = await client.get("/api/v1/me")
    assert r.status_code == 401
    assert r.headers["content-type"] == "application/problem+json"


async def test_cookie_mutation_requires_csrf(client: AsyncClient, admin: Actor) -> None:
    r = await client.post("/api/v1/me/tokens", json={"name": "laptop"})
    assert r.status_code == 403
    assert "X-CSRF-Token" in r.json()["detail"]
    r = await client.post(
        "/api/v1/me/tokens", json={"name": "laptop"}, headers={"X-CSRF-Token": "forged"}
    )
    assert r.status_code == 403
    r = await client.post("/api/v1/me/tokens", json={"name": "laptop"}, headers=admin.headers)
    assert r.status_code == 201


async def test_bearer_mutation_needs_no_csrf(client: AsyncClient, admin: Actor) -> None:
    r = await client.post("/api/v1/me/tokens", json={"name": "cli"}, headers=admin.headers)
    token = r.json()["token"]
    client.cookies.clear()
    r = await client.post(
        "/api/v1/me/tokens", json={"name": "cli-2"}, headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 201


async def test_logout_ends_session(client: AsyncClient, admin: Actor) -> None:
    r = await client.post("/api/v1/auth/logout", headers=admin.headers)
    assert r.status_code == 204
    assert (await client.get("/api/v1/me")).status_code == 401


async def test_logout_with_token_is_rejected(client: AsyncClient, admin: Actor) -> None:
    agent = await new_agent(client, admin, "agent-backend")
    client.cookies.clear()
    r = await client.post("/api/v1/auth/logout", headers=agent.headers)
    assert r.status_code == 422


async def test_expired_session_cookie(client: AsyncClient, admin: Actor) -> None:
    client.cookies.set("radicle_session", "not-a-real-session")
    r = await client.get("/api/v1/me")
    assert r.status_code == 401
    assert "expired" in r.json()["detail"]


async def test_session_survives_relogin(client: AsyncClient, admin: Actor) -> None:
    actor = await login(client, "admin@example.com", ADMIN_PASSWORD)
    r = await client.get("/api/v1/me")
    assert r.json()["handle"] == actor.handle
