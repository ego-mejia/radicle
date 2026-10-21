"""Ticket numbers under real concurrency: separate sessions that commit, on their own DB."""

import asyncio

from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.community.postgres import PostgresContainer

from radicle.platform.api.ratelimit import login_limiter
from radicle.platform.config import get_settings
from radicle.platform.db import session as db_session
from tests.conftest import run_alembic


async def test_50_parallel_creations_get_numbers_1_to_50(
    postgres: PostgresContainer, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    admin_url = postgres.get_connection_url()
    engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    async with engine.connect() as conn:
        await conn.execute(text("DROP DATABASE IF EXISTS concurrency_check"))
        await conn.execute(text("CREATE DATABASE concurrency_check"))
    await engine.dispose()
    url = admin_url.rsplit("/", 1)[0] + "/concurrency_check"
    await asyncio.to_thread(run_alembic, url, "upgrade", "head")

    monkeypatch.setenv("RADICLE_DATABASE_URL", url)
    get_settings.cache_clear()
    await db_session.dispose_engine()
    login_limiter.reset()
    from radicle.main import create_app

    app = create_app()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            setup = await c.post(
                "/api/v1/setup",
                json={
                    "handle": "root",
                    "display_name": "Root",
                    "email": "r@example.com",
                    "password": "password-123",
                },
            )
            assert setup.status_code == 201, setup.text
            h = {"X-CSRF-Token": c.cookies["radicle_csrf"]}
            token = (await c.post("/api/v1/me/tokens", headers=h, json={"name": "t"})).json()
            bearer = {"Authorization": f"Bearer {token['token']}"}
            await c.post("/api/v1/projects", headers=h, json={"key": "PA", "name": "A"})
            c.cookies.clear()

            async def create(i: int) -> int:
                r = await c.post(
                    "/api/v1/projects/PA/tickets",
                    headers=bearer,
                    json={"type": "draft", "classification": "idea", "title": f"t{i}"},
                )
                assert r.status_code == 201, r.text
                return int(r.json()["key"].split("-")[1])

            numbers = await asyncio.gather(*(create(i) for i in range(50)))
            assert sorted(numbers) == list(range(1, 51))
            ranks = await c.get("/api/v1/tickets/PA-50", headers=bearer)
            assert ranks.status_code == 200
    finally:
        await db_session.dispose_engine()
        get_settings.cache_clear()


async def fresh_app(postgres: PostgresContainer, monkeypatch, name: str):  # type: ignore[no-untyped-def]
    """An app on its own freshly migrated database, with sessions that really commit."""
    admin_url = postgres.get_connection_url()
    engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    async with engine.connect() as conn:
        await conn.execute(text(f"DROP DATABASE IF EXISTS {name}"))
        await conn.execute(text(f"CREATE DATABASE {name}"))
    await engine.dispose()
    url = admin_url.rsplit("/", 1)[0] + f"/{name}"
    await asyncio.to_thread(run_alembic, url, "upgrade", "head")
    monkeypatch.setenv("RADICLE_DATABASE_URL", url)
    get_settings.cache_clear()
    await db_session.dispose_engine()
    login_limiter.reset()
    from radicle.main import create_app

    return create_app()


async def test_parallel_votes_keep_vote_count_exact(
    postgres: PostgresContainer, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    app = await fresh_app(postgres, monkeypatch, "votes_check")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            await c.post(
                "/api/v1/setup",
                json={
                    "handle": "root",
                    "display_name": "Root",
                    "email": "r@example.com",
                    "password": "password-123",
                },
            )
            h = {"X-CSRF-Token": c.cookies["radicle_csrf"]}
            await c.post("/api/v1/projects", headers=h, json={"key": "PA", "name": "A"})
            await c.post(
                "/api/v1/projects/PA/tickets",
                headers=h,
                json={"type": "draft", "classification": "idea", "title": "Idea"},
            )
            bearers = []
            for i in range(8):
                handle = f"user{i}"
                await c.post(
                    "/api/v1/users",
                    headers=h,
                    json={
                        "handle": handle,
                        "display_name": handle,
                        "email": f"{handle}@example.com",
                        "password": "password-123",
                    },
                )
                await c.put(
                    f"/api/v1/projects/PA/members/{handle}", headers=h, json={"role": "member"}
                )
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as u:
                    await u.post(
                        "/api/v1/auth/login",
                        json={"email": f"{handle}@example.com", "password": "password-123"},
                    )
                    token = await u.post(
                        "/api/v1/me/tokens",
                        headers={"X-CSRF-Token": u.cookies["radicle_csrf"]},
                        json={"name": "t"},
                    )
                bearers.append({"Authorization": f"Bearer {token.json()['token']}"})
            c.cookies.clear()

            async def vote(headers: dict[str, str]) -> int:
                r = await c.put("/api/v1/tickets/PA-1/vote", headers=headers)
                assert r.status_code == 200, r.text
                return int(r.status_code)

            # Every user votes three times at once: only one vote each counts.
            await asyncio.gather(*(vote(b) for b in bearers for _ in range(3)))
            ticket = (await c.get("/api/v1/tickets/PA-1", headers=bearers[0])).json()
            assert ticket["vote_count"] == 8
            voters = (await c.get("/api/v1/tickets/PA-1/voters", headers=bearers[0])).json()
            assert len(voters["items"]) == 8
    finally:
        await db_session.dispose_engine()
        get_settings.cache_clear()


async def test_ten_agents_claim_different_tickets(postgres: PostgresContainer, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    app = await fresh_app(postgres, monkeypatch, "claims_check")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            await c.post(
                "/api/v1/setup",
                json={
                    "handle": "root",
                    "display_name": "Root",
                    "email": "r@example.com",
                    "password": "password-123",
                },
            )
            h = {"X-CSRF-Token": c.cookies["radicle_csrf"]}
            await c.post("/api/v1/projects", headers=h, json={"key": "PA", "name": "A"})
            await c.post("/api/v1/projects/PA/areas", headers=h, json={"name": "Backend"})
            for i in range(12):
                await c.post(
                    "/api/v1/projects/PA/tickets",
                    headers=h,
                    json={"type": "task", "title": f"t{i}", "area": "Backend"},
                )
            agents = []
            for i in range(10):
                r = await c.post(
                    "/api/v1/agents",
                    headers=h,
                    json={"handle": f"bot{i}", "display_name": f"Bot {i}"},
                )
                await c.put(
                    f"/api/v1/projects/PA/members/bot{i}", headers=h, json={"role": "member"}
                )
                agents.append({"Authorization": f"Bearer {r.json()['token']['token']}"})
            c.cookies.clear()

            async def claim(headers: dict[str, str]) -> str:
                r = await c.post("/api/v1/tickets/next", headers=headers, json={"claim": True})
                assert r.status_code == 200, r.text
                return str(r.json()["ticket"]["key"])

            claimed = await asyncio.gather(*(claim(a) for a in agents))
            assert len(set(claimed)) == 10
            assert sorted(claimed, key=lambda k: int(k.split("-")[1])) == [
                f"PA-{i}" for i in range(1, 11)
            ]
    finally:
        await db_session.dispose_engine()
        get_settings.cache_clear()
