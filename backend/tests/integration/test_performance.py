"""Spec performance budget with 10,000 seeded tickets, on a dedicated database.

RQL search p95 < 300 ms and loading a 500-ticket board < 1 s, measured through the API.
"""

import asyncio
import statistics
import time

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.community.postgres import PostgresContainer

from radicle.core.config import get_settings
from radicle.db import session as db_session
from tests.conftest import run_alembic

QUERIES = [
    "project = PERF AND type = bug AND priority >= high AND milestone = V1 AND tag != backlog",
    "assignee = currentUser() AND category != done ORDER BY priority DESC, due ASC",
    "#backlog AND area = Legal",
    'text ~ "pagos" AND updated >= -30d',
    "blocked = true AND milestone = V1",
    "category = done ORDER BY updated DESC",
    "title ~ login OR title ~ checkout",
    "",
]


@pytest.mark.slow
async def test_search_p95_and_board_with_10k_tickets(
    postgres: PostgresContainer, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    admin_url = postgres.get_connection_url()
    engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    async with engine.connect() as conn:
        await conn.execute(text("DROP DATABASE IF EXISTS perf_check"))
        await conn.execute(text("CREATE DATABASE perf_check"))
    await engine.dispose()
    url = admin_url.rsplit("/", 1)[0] + "/perf_check"
    await asyncio.to_thread(run_alembic, url, "upgrade", "head")
    monkeypatch.setenv("RADICLE_DATABASE_URL", url)
    get_settings.cache_clear()
    await db_session.dispose_engine()

    from radicle.main import create_app
    from radicle.seed import seed

    async with db_session.get_sessionmaker()() as db:
        await seed(db, tickets=10_000)
        await db.commit()
        # The seed writes one to three periods per ticket; two more each make the year
        # scan about 50,000 periods.
        for back, length in ((40, 20), (20, 10)):
            await db.execute(
                text(
                    "INSERT INTO ticket_status_periods "
                    "(id, ticket_id, status_id, category, entered_at, exited_at) "
                    "SELECT gen_random_uuid(), id, status_id, 'in_progress', "
                    "created_at - make_interval(days => :back), "
                    "created_at - make_interval(days => :until) FROM tickets"
                ),
                {"back": back, "until": back - length},
            )
        await db.commit()
        await db.execute(text("ANALYZE"))
        await db.commit()
    try:
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.post(
                "/api/v1/auth/login", json={"email": "luis@example.com", "password": "radicle-demo"}
            )
            assert r.status_code == 200
            h = {"X-CSRF-Token": c.cookies["radicle_csrf"]}
            token = (await c.post("/api/v1/me/tokens", headers=h, json={"name": "p"})).json()
            bearer = {"Authorization": f"Bearer {token['token']}"}

            timings = []
            for _ in range(5):
                for q in QUERIES:
                    start = time.perf_counter()
                    r = await c.get("/api/v1/tickets", headers=bearer, params={"q": q})
                    timings.append(time.perf_counter() - start)
                    assert r.status_code == 200, r.text
            p95 = statistics.quantiles(timings, n=20)[18]
            assert p95 < 0.3, f"RQL p95 {p95 * 1000:.0f} ms"

            start = time.perf_counter()
            loaded, cursor = 0, None
            while loaded < 500:
                params = {"q": "project = PERF AND category != done ORDER BY rank", "limit": 200}
                if cursor:
                    params["cursor"] = cursor
                r = await c.get("/api/v1/tickets", headers=bearer, params=params)
                loaded += len(r.json()["items"])
                cursor = r.json()["next_cursor"]
            board = time.perf_counter() - start
            assert board < 1.0, f"board of {loaded} tickets took {board * 1000:.0f} ms"

            boards = (await c.get("/api/v1/projects/PERF/boards", headers=bearer)).json()
            board_id = boards["items"][0]["id"]
            start = time.perf_counter()
            r = await c.get(
                f"/api/v1/boards/{board_id}/data", headers=bearer, params={"swimlane": "area"}
            )
            configured = time.perf_counter() - start
            assert r.status_code == 200 and r.json()["lanes"]
            assert configured < 1.0, f"configurable board took {configured * 1000:.0f} ms"
            start = time.perf_counter()
            r = await c.get(
                "/api/v1/reports/cfd",
                headers=bearer,
                params={"project": "PERF", "from": "2025-10-20", "to": "2026-10-19"},
            )
            cfd = time.perf_counter() - start
            assert r.status_code == 200 and len(r.json()["rows"]) == 365, r.text
            assert sum(r.json()["rows"][-1][k] for k in r.json()["columns"][1:]) > 0
            assert cfd < 1.0, f"CFD of a year took {cfd * 1000:.0f} ms"
            print(
                f"\nCFD 365 days {cfd * 1000:.0f} ms; "
                f"RQL p95 {p95 * 1000:.0f} ms; board {loaded} tickets {board * 1000:.0f} ms; "
                f"configurable board with lanes {configured * 1000:.0f} ms"
            )
    finally:
        await db_session.dispose_engine()
        get_settings.cache_clear()
