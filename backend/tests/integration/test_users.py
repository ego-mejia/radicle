import pytest
from httpx import AsyncClient

from tests.conftest import Actor, bearer_for_new_human, new_agent


async def test_create_and_list_users(client: AsyncClient, admin: Actor) -> None:
    r = await client.post(
        "/api/v1/users",
        headers=admin.headers,
        json={
            "handle": "luis",
            "display_name": "Luis",
            "email": "luis@example.com",
            "password": "temporary-pass",
        },
    )
    assert r.status_code == 201
    assert r.json()["kind"] == "human" and r.json()["is_instance_admin"] is False
    r = await client.get("/api/v1/users", headers=admin.headers)
    assert [u["handle"] for u in r.json()["items"]] == ["fernando", "luis"]


async def test_list_users_pagination(client: AsyncClient, admin: Actor) -> None:
    for i in range(3):
        await new_agent(client, admin, f"bot-{i}")
    seen: list[str] = []
    cursor = None
    while True:
        params = {"limit": 2, **({"cursor": cursor} if cursor else {})}
        r = await client.get("/api/v1/users", headers=admin.headers, params=params)
        seen += [u["handle"] for u in r.json()["items"]]
        cursor = r.json()["next_cursor"]
        if cursor is None:
            break
    assert seen == ["fernando", "bot-0", "bot-1", "bot-2"]
    r = await client.get("/api/v1/users", headers=admin.headers, params={"limit": 500})
    assert r.status_code == 422


@pytest.mark.parametrize(
    ("field", "value"), [("handle", "Fernando"), ("email", "ADMIN@example.com")]
)
async def test_duplicate_handle_or_email(
    client: AsyncClient, admin: Actor, field: str, value: str
) -> None:
    body = {
        "handle": "new",
        "display_name": "New",
        "email": "new@example.com",
        "password": "temporary-pass",
        field: value,
    }
    r = await client.post("/api/v1/users", headers=admin.headers, json=body)
    assert r.status_code == 409
    assert r.json()["errors"][0]["field"] == field


async def test_create_agent_returns_token_once(client: AsyncClient, admin: Actor) -> None:
    r = await client.post(
        "/api/v1/agents",
        headers=admin.headers,
        json={"handle": "agent-backend", "display_name": "Backend agent"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["agent"]["kind"] == "agent" and body["agent"]["email"] is None
    assert body["token"]["token"].startswith("rdc_")
    assert body["mcp_url"].endswith("/mcp")

    client.cookies.clear()
    r = await client.get(
        "/api/v1/me", headers={"Authorization": f"Bearer {body['token']['token']}"}
    )
    assert r.status_code == 200
    assert r.json()["handle"] == "agent-backend" and r.json()["kind"] == "agent"


async def test_agent_token_management(client: AsyncClient, admin: Actor) -> None:
    await new_agent(client, admin, "agent-qa")
    r = await client.post(
        "/api/v1/users/agent-qa/tokens", headers=admin.headers, json={"name": "ci"}
    )
    assert r.status_code == 201
    second = r.json()
    r = await client.get("/api/v1/users/agent-qa/tokens", headers=admin.headers)
    assert sorted(t["name"] for t in r.json()["items"]) == ["ci", "default"]
    r = await client.delete(f"/api/v1/users/agent-qa/tokens/{second['id']}", headers=admin.headers)
    assert r.status_code == 204
    r = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {second['token']}"})
    assert r.status_code == 401


async def test_human_tokens_are_created_by_owner(client: AsyncClient, admin: Actor) -> None:
    r = await client.post(
        "/api/v1/users/fernando/tokens", headers=admin.headers, json={"name": "x"}
    )
    assert r.status_code == 422
    assert "/me/tokens" in r.json()["detail"]


async def test_agent_cannot_sign_in(client: AsyncClient, admin: Actor) -> None:
    await new_agent(client, admin, "agent-backend")
    r = await client.post(
        "/api/v1/auth/login", json={"email": "agent-backend@example.com", "password": "whatever-1"}
    )
    assert r.status_code == 401


async def test_patch_user(client: AsyncClient, admin: Actor) -> None:
    await bearer_for_new_human(client, admin, "ana")
    r = await client.patch(
        "/api/v1/users/ana",
        headers=admin.headers,
        json={"display_name": "Ana María", "is_instance_admin": True},
    )
    assert r.status_code == 200
    assert r.json()["display_name"] == "Ana María" and r.json()["is_instance_admin"] is True
    r = await client.get("/api/v1/users/ana", headers=admin.headers)
    assert r.json()["is_instance_admin"] is True


async def test_deactivated_user_tokens_stop_working(client: AsyncClient, admin: Actor) -> None:
    ana = await bearer_for_new_human(client, admin, "ana")
    await client.patch("/api/v1/users/ana", headers=admin.headers, json={"is_active": False})
    r = await client.get("/api/v1/me", headers=ana.headers)
    assert r.status_code == 401
    assert "deactivated" in r.json()["detail"]


async def test_cannot_remove_last_admin(client: AsyncClient, admin: Actor) -> None:
    for body in ({"is_instance_admin": False}, {"is_active": False}):
        r = await client.patch("/api/v1/users/fernando", headers=admin.headers, json=body)
        assert r.status_code == 409
        assert "last active instance admin" in r.json()["detail"]


async def test_agents_cannot_be_admins_or_get_passwords(client: AsyncClient, admin: Actor) -> None:
    await new_agent(client, admin, "bot")
    for body in (
        {"is_instance_admin": True},
        {"password": "password-123"},
        {"email": "bot@example.com"},
    ):
        r = await client.patch("/api/v1/users/bot", headers=admin.headers, json=body)
        assert r.status_code == 422, body


async def test_unknown_user_is_404(client: AsyncClient, admin: Actor) -> None:
    r = await client.patch("/api/v1/users/ghost", headers=admin.headers, json={"is_active": False})
    assert r.status_code == 404
    assert "@ghost" in r.json()["detail"]


ADMIN_ONLY = [
    ("GET", "/api/v1/users", None),
    (
        "POST",
        "/api/v1/users",
        {
            "handle": "z",
            "display_name": "Z",
            "email": "z@example.com",
            "password": "temporary-pass",
        },
    ),
    ("POST", "/api/v1/agents", {"handle": "zz", "display_name": "Z"}),
    ("GET", "/api/v1/users/fernando", None),
    ("PATCH", "/api/v1/users/fernando", {"display_name": "Hacked"}),
    ("GET", "/api/v1/users/fernando/tokens", None),
    ("POST", "/api/v1/users/fernando/tokens", {"name": "x"}),
    ("DELETE", "/api/v1/users/fernando/tokens/00000000-0000-0000-0000-000000000000", None),
]


@pytest.mark.parametrize(("method", "path", "body"), ADMIN_ONLY)
@pytest.mark.parametrize("who", ["human", "agent"])
async def test_admin_endpoints_forbid_non_admins(
    client: AsyncClient, admin: Actor, method: str, path: str, body: dict | None, who: str
) -> None:
    actor = (
        await bearer_for_new_human(client, admin, "luis")
        if who == "human"
        else await new_agent(client, admin, "agent-x")
    )
    client.cookies.clear()
    r = await client.request(method, path, headers=actor.headers, json=body)
    assert r.status_code == 403
    assert "instance admins" in r.json()["detail"]


@pytest.mark.parametrize(("method", "path", "body"), ADMIN_ONLY)
async def test_admin_endpoints_require_auth(
    client: AsyncClient, method: str, path: str, body: dict | None
) -> None:
    r = await client.request(method, path, json=body)
    assert r.status_code == 401
