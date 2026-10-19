"""The Procrastinate app run by `radicle worker`. One task per registered job handler."""

import importlib
import logging
from typing import Any

import procrastinate

from radicle.core.config import get_settings
from radicle.db.session import get_sessionmaker
from radicle.services import queue

log = logging.getLogger("radicle.worker")

# Modules that register job handlers with @queue.handler.
JOB_MODULES: tuple[str, ...] = (
    "radicle.services.jobs",
    "radicle.services.templates",
    "radicle.services.attachments",
    "radicle.services.bulk",
    "radicle.services.ranking",
    "radicle.services.periods",
)
# Jobs the worker defers on a schedule (cron in UTC).
PERIODIC: dict[str, str] = {"daily_snapshot": "5 * * * *"}


def conninfo(database_url: str) -> str:
    """SQLAlchemy URL to a libpq one: postgresql+asyncpg://... -> postgresql://..."""
    scheme, _, rest = database_url.partition("://")
    return f"{scheme.split('+')[0]}://{rest}"


async def run_handler(name: str, args: dict[str, Any]) -> None:
    """Run one job in its own transaction."""
    async with get_sessionmaker()() as db:
        try:
            await queue.HANDLERS[name](db, **args)
            await db.commit()
        except BaseException:
            await db.rollback()
            raise


def _task(name: str) -> Any:
    async def run(**args: Any) -> None:
        log.info("job %s %s", name, args)
        # Periodic tasks receive the schedule timestamp; handlers do not need it.
        args.pop("timestamp", None)
        await run_handler(name, args)

    run.__name__ = name
    return run


def build_app() -> procrastinate.App:
    for module in JOB_MODULES:
        importlib.import_module(module)
    app = procrastinate.App(
        connector=procrastinate.PsycopgConnector(conninfo=conninfo(get_settings().database_url))
    )
    for name in queue.HANDLERS:
        task = app.task(name=name, queue=queue.QUEUE, pass_context=False)(_task(name))
        if name in PERIODIC:
            app.periodic(cron=PERIODIC[name], periodic_id=name)(task)
    return app
