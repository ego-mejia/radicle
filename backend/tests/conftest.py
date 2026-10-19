import os
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from argon2 import PasswordHasher
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from radicle.api.ratelimit import login_limiter
from radicle.core import security
from radicle.core.config import get_settings
from radicle.db.session import get_db

BACKEND_DIR = Path(__file__).resolve().parent.parent
ADMIN_PASSWORD = "admin-password-1"

# Cheap hashing keeps fixtures that create many users fast. Production uses argon2 defaults.
security._hasher = PasswordHasher(time_cost=1, memory_cost=1024, parallelism=1)


def run_alembic(url: str, *args: str) -> None:
    env = {**os.environ, "RADICLE_DATABASE_URL": url}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(f"alembic {' '.join(args)} failed:\n{result.stderr[-3000:]}")


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


@dataclass
class Team:
    """Project PA with one actor per role, plus an outsider. All use bearer tokens
    except `instance`, the instance admin, who uses the shared client's session."""

    instance: Actor
    admin: Actor
    member: Actor
    viewer: Actor
    agent: Actor
    outsider: Actor

    def by_role(self, role: str) -> Actor:
        return getattr(self, role)


async def make_project(client: AsyncClient, admin: Actor, key: str = "PA") -> dict:
    r = await client.post(
        "/api/v1/projects", headers=admin.headers, json={"key": key, "name": "ProyectoA"}
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
async def team(client: AsyncClient, admin: Actor) -> Team:
    await make_project(client, admin)
    actors = {
        "admin": await bearer_for_new_human(client, admin, "ana"),
        "member": await bearer_for_new_human(client, admin, "luis"),
        "viewer": await bearer_for_new_human(client, admin, "vera"),
        "outsider": await bearer_for_new_human(client, admin, "olga"),
        "agent": await new_agent(client, admin, "agent-backend"),
    }
    roles = {"admin": "admin", "member": "member", "viewer": "viewer", "agent": "member"}
    for name, role in roles.items():
        r = await client.put(
            f"/api/v1/projects/PA/members/{actors[name].handle}",
            headers=admin.headers,
            json={"role": role},
        )
        assert r.status_code == 200, r.text
    return Team(instance=admin, **actors)


AREAS = ("Legal", "Marketing", "Backend", "Frontend")


@pytest.fixture
async def board(client: AsyncClient, team: Team) -> Team:
    """`team` plus the acceptance setup: four areas and milestone V1."""
    for name in AREAS:
        r = await client.post(
            "/api/v1/projects/PA/areas", headers=team.instance.headers, json={"name": name}
        )
        assert r.status_code == 201, r.text
    r = await client.post(
        "/api/v1/projects/PA/milestones",
        headers=team.instance.headers,
        json={"name": "V1", "target_date": "2026-12-15"},
    )
    assert r.status_code == 201, r.text
    return team


async def new_ticket(client: AsyncClient, actor: Actor, **fields: object) -> dict:
    body = {"type": "task", "title": "Ticket", "area": "Backend", **fields}
    r = await client.post("/api/v1/projects/PA/tickets", headers=actor.headers, json=body)
    assert r.status_code == 201, r.text
    return r.json()


async def patch_ticket(client: AsyncClient, actor: Actor, key: str, **fields: object):
    current = (await client.get(f"/api/v1/tickets/{key}", headers=actor.headers)).json()
    return await client.patch(
        f"/api/v1/tickets/{key}",
        headers={**actor.headers, "If-Match": str(current["version"])},
        json=fields,
    )
