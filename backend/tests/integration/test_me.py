from httpx import AsyncClient

from tests.conftest import ADMIN_PASSWORD, Actor


async def test_change_display_name(client: AsyncClient, admin: Actor) -> None:
    r = await client.patch("/api/v1/me", headers=admin.headers, json={"display_name": " Fer  "})
    assert r.status_code == 200
    assert r.json()["display_name"] == "Fer"


async def test_change_password(client: AsyncClient, admin: Actor) -> None:
    r = await client.patch(
        "/api/v1/me",
        headers=admin.headers,
        json={"current_password": ADMIN_PASSWORD, "new_password": "brand-new-pw"},
    )
    assert r.status_code == 200
    r = await client.post(
        "/api/v1/auth/login", json={"email": "admin@example.com", "password": "brand-new-pw"}
    )
    assert r.status_code == 200


async def test_change_password_needs_current(client: AsyncClient, admin: Actor) -> None:
    r = await client.patch("/api/v1/me", headers=admin.headers, json={"new_password": "x" * 10})
    assert r.status_code == 422
    r = await client.patch(
        "/api/v1/me",
        headers=admin.headers,
        json={"current_password": "wrong-one", "new_password": "x" * 10},
    )
    assert r.status_code == 422
    assert r.json()["errors"][0]["field"] == "current_password"


async def test_unknown_fields_are_rejected(client: AsyncClient, admin: Actor) -> None:
    r = await client.patch("/api/v1/me", headers=admin.headers, json={"is_instance_admin": False})
    assert r.status_code == 422
