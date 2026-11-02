"""The Procrastinate app run by `gumball-factory worker`. One task per registered job handler."""

import importlib
import logging
from typing import Any

import procrastinate

from gumball_factory.platform.config import get_settings
from gumball_factory.platform.db.session import get_sessionmaker
from gumball_factory.platform.services import queue

log = logging.getLogger("gumball_factory.worker")

# Modules that register job handlers with @queue.handler.
JOB_MODULES: tuple[str, ...] = (
    "gumball_factory.platform.services.jobs",
    "gumball_factory.docket.services.templates",
    "gumball_factory.docket.services.attachments",
    "gumball_factory.docket.services.bulk",
    "gumball_factory.docket.services.ranking",
    "gumball_factory.docket.services.periods",
    "gumball_factory.platform.services.audit",
    "gumball_factory.folio.services.rag",
    "gumball_factory.folio.services.quality",
    "gumball_factory.folio.services.comment_events",
    "gumball_factory.folio.services.notices",
    "gumball_factory.folio.services.share",
    "gumball_factory.folio.services.actions",
    "gumball_factory.folio.services.views",
    "gumball_factory.folio.services.import_run",
    "gumball_factory.folio.services.exports",
    "gumball_factory.platform.services.events",
    "gumball_factory.platform.services.email",
    "gumball_factory.platform.services.webhooks",
    "gumball_factory.platform.services.chat_notices",
    "gumball_factory.platform.services.chat_commands",
    "gumball_factory.platform.services.chat_previews",
    "gumball_factory.platform.services.automation",
    "gumball_factory.folio.services.automation_actions",
    "gumball_factory.folio.services.chat_commands",
    "gumball_factory.folio.services.public_events",
)
# Jobs the worker defers on a schedule (cron in UTC).
PERIODIC: dict[str, str] = {
    "daily_snapshot": "5 * * * *",
    "audit_retention": "30 3 * * *",
    # Picks up events whose wake-up job was lost (a crash between commit and dispatch).
    "platform_dispatch_events": "* * * * *",
    # Verified pages past their date turn Outdated (Folio 2.7).
    "folio_outdate": "15 4 * * *",
    # Reads per page and day for "Most read" (Folio 2.7).
    "folio_view_counts": "25 * * * *",
    # Scheduled automation rules that are due (Folio 5.6).
    "platform_automation_schedule": "35 * * * *",
}


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
