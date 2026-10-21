import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

# Importing the modules registers their tables on the shared metadata.
import radicle.folio.db.analytics
import radicle.folio.db.calendars
import radicle.folio.db.chat
import radicle.folio.db.collab
import radicle.folio.db.databases
import radicle.folio.db.docket_links
import radicle.folio.db.glossary
import radicle.folio.db.models
import radicle.folio.db.templates
import radicle.folio.db.whiteboards  # noqa: F401  (ruff flags only the last of these)
from radicle.docket.db.models import Base
from radicle.platform.config import get_settings

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _include_object(obj: object, name: str | None, type_: str, *_: object) -> bool:
    """Procrastinate owns its tables, and Folio creates one HNSW index per embedding
    dimension at run time (ADR 0037); autogenerate must not try to drop them."""
    return not (name or "").startswith(("procrastinate", "ix_folio_chunks_embedding_"))


def _url() -> str:
    return config.get_main_option("sqlalchemy.url") or get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        include_object=_include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def _run(connection: Connection) -> None:
    context.configure(
        connection=connection, target_metadata=target_metadata, include_object=_include_object
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(_url())
    async with engine.connect() as connection:
        await connection.run_sync(_run)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
