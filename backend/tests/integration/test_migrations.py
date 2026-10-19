import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.community.postgres import PostgresContainer

from tests.conftest import run_alembic


def test_upgrade_downgrade_upgrade(postgres: PostgresContainer) -> None:
    """Runs on its own database so the shared test schema is untouched."""
    admin_url = postgres.get_connection_url()

    async def recreate() -> None:
        engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
        async with engine.connect() as conn:
            await conn.execute(text("DROP DATABASE IF EXISTS migrations_check"))
            await conn.execute(text("CREATE DATABASE migrations_check"))
        await engine.dispose()

    asyncio.run(recreate())
    url = admin_url.rsplit("/", 1)[0] + "/migrations_check"
    run_alembic(url, "upgrade", "head")
    run_alembic(url, "downgrade", "base")
    run_alembic(url, "upgrade", "head")
    run_alembic(url, "check")
