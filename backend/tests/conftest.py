import os
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from radicle.api.ratelimit import login_limiter
from radicle.core.config import get_settings
from radicle.db.session import get_db

BACKEND_DIR = Path(__file__).resolve().parent.parent
ADMIN_PASSWORD = "admin-password-1"


def run_alembic(url: str, *args: str) -> None:
    env = {**os.environ, "RADICLE_DATABASE_URL": url}
    subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env=env,
        check=True,
        capture_output=True,
    )


@pytest.fixture(scope="session")
def postgres() -> Iterator[PostgresContainer]:
    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as container:
        yield container


@pytest.fixture(scope="session")
def database_url(postgres: PostgresContainer) -> str:
    url = postgres.get_connection_url()
    run_alembic(url, "upgrade", "head")
    os.environ["RADICLE_DATABASE_URL"] = url
    get_settings.cache_clear()
    return url


@pytest.fixture(scope="session")
async def engine(database_url: str) -> AsyncIterator[object]:
    engine = create_async_engine(database_url)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db(engine) -> AsyncIterator[AsyncSession]:  # type: ignore[no-untyped-def]
    """A session inside an outer transaction that is rolled back after the test."""
    async with engine.connect() as conn:
        outer = await conn.begin()
        session = AsyncSession(
            bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        try:
            yield session
        finally:
            await session.close()
            await outer.rollback()


@pytest.fixture
async def client(db: AsyncSession) -> AsyncIterator[AsyncClient]:
    from radicle.main import create_app

    app = create_app()

    async def _override_db() -> AsyncIterator[AsyncSession]:
        try:
            yield db
            await db.commit()
        except BaseException:
            await db.rollback()
            raise

    app.dependency_overrides[get_db] = _override_db
    login_limiter.reset()
    transport = ASGITransport(app=app, client=("10.0.0.1", 1234))
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@dataclass
class Actor:
    """An authenticated identity: bearer headers for tokens, cookie + CSRF for sessions."""

    handle: str
    headers: dict[str, str]


async def login(client: AsyncClient, email: str, password: str) -> Actor:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return Actor(response.json()["handle"], {"X-CSRF-Token": client.cookies["radicle_csrf"]})


@pytest.fixture
async def admin(client: AsyncClient) -> Actor:
    response = await client.post(
        "/api/v1/setup",
        json={
            "handle": "fernando",
            "display_name": "Fernando",
            "email": "admin@example.com",
            "password": ADMIN_PASSWORD,
        },
    )
    assert response.status_code == 201, response.text
    return Actor("fernando", {"X-CSRF-Token": client.cookies["radicle_csrf"]})


async def bearer_for_new_human(client: AsyncClient, admin: Actor, handle: str) -> Actor:
    """Create a human and a personal token for them, without touching the admin's cookie."""
    email = f"{handle}@example.com"
    r = await client.post(
        "/api/v1/users",
        headers=admin.headers,
        json={
            "handle": handle,
            "display_name": handle.title(),
            "email": email,
            "password": "temporary-pass",
        },
    )
    assert r.status_code == 201, r.text
    # Log in on a separate cookie jar so the admin session stays in the shared client.
    async with AsyncClient(transport=client._transport, base_url="http://test") as other:
        r = await other.post(
            "/api/v1/auth/login", json={"email": email, "password": "temporary-pass"}
        )
        assert r.status_code == 200, r.text
        r = await other.post(
            "/api/v1/me/tokens",
            json={"name": "tests"},
            headers={"X-CSRF-Token": other.cookies["radicle_csrf"]},
        )
        assert r.status_code == 201, r.text
    return Actor(handle, {"Authorization": f"Bearer {r.json()['token']}"})


async def new_agent(client: AsyncClient, admin: Actor, handle: str) -> Actor:
    r = await client.post(
        "/api/v1/agents", headers=admin.headers, json={"handle": handle, "display_name": handle}
    )
    assert r.status_code == 201, r.text
    return Actor(handle, {"Authorization": f"Bearer {r.json()['token']['token']}"})
