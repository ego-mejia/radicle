"""Ticket numbers under real concurrency: separate sessions that commit, on their own DB."""

import asyncio

from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.community.postgres import PostgresContainer

from radicle.api.ratelimit import login_limiter
from radicle.core.config import get_settings
from radicle.db import session as db_session
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
                    json={"type": "draft", "title": f"t{i}"},
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
