from httpx import AsyncClient

from tests.conftest import ADMIN_PASSWORD, Actor


async def test_health_and_version(client: AsyncClient) -> None:
    for path in ("/health", "/api/v1/health"):
        r = await client.get(path)
        assert r.status_code == 200
        assert r.json() == {"status": "ok", "database": "ok"}
    r = await client.get("/api/v1/version")
    assert r.json() == {"version": "0.1.0", "api_version": "v1"}


async def test_openapi_is_published(client: AsyncClient) -> None:
    r = await client.get("/api/v1/openapi.json")
    assert r.status_code == 200
    assert "/api/v1/me/tokens" in r.json()["paths"]


async def test_unknown_api_route_is_problem_json(client: AsyncClient) -> None:
    r = await client.get("/api/v1/nope")
    assert r.status_code == 404
    assert r.headers["content-type"] == "application/problem+json"
    body = r.json()
    assert {"type", "title", "status", "detail", "errors"} <= body.keys()


async def test_setup_status_before_and_after(client: AsyncClient) -> None:
    r = await client.get("/api/v1/setup/status")
    assert r.json() == {"needs_setup": True}
    r = await client.post(
        "/api/v1/setup",
        json={
            "handle": "Fernando",
            "display_name": "Fernando",
            "email": "f@example.com",
            "password": ADMIN_PASSWORD,
        },
    )
    assert r.status_code == 201
    assert r.json()["handle"] == "fernando"
    assert r.json()["is_instance_admin"] is True
    assert r.json()["created_at"].endswith("Z")
    r = await client.get("/api/v1/setup/status")
    assert r.json() == {"needs_setup": False}


async def test_setup_signs_admin_in(client: AsyncClient, admin: Actor) -> None:
    r = await client.get("/api/v1/me")
    assert r.status_code == 200
    assert r.json()["handle"] == "fernando"
    assert r.json()["projects"] == []


async def test_setup_works_only_once(client: AsyncClient, admin: Actor) -> None:
    r = await client.post(
        "/api/v1/setup",
        json={
            "handle": "other",
            "display_name": "Other",
            "email": "o@example.com",
            "password": "password-123",
        },
    )
    assert r.status_code == 409
    assert "already done" in r.json()["detail"]


async def test_setup_validation_error(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/setup",
        json={
            "handle": "-bad",
            "display_name": "X",
            "email": "x@example.com",
            "password": "pw-12345",
        },
    )
    assert r.status_code == 422
    assert r.json()["errors"][0]["field"] == "handle"
    r = await client.post("/api/v1/setup", json={"handle": "ok"})
    assert r.status_code == 422
    assert {e["field"] for e in r.json()["errors"]} >= {"email", "password", "display_name"}
