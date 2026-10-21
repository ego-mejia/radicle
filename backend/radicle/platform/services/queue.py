"""Background jobs, enqueued inside the caller's transaction.

Jobs are inserted straight into Procrastinate's queue table with the same database
session, so a job only becomes visible when the change that needs it commits, and
disappears if that change rolls back. The worker (`radicle worker`) runs the handlers
registered here, each one in its own session and transaction.
"""

import json
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

QUEUE = "default"

Handler = Callable[..., Awaitable[None]]
HANDLERS: dict[str, Handler] = {}


def handler(name: str) -> Callable[[Handler], Handler]:
    """Register `async def fn(db: AsyncSession, **args)` as the job called `name`."""

    def register(fn: Handler) -> Handler:
        HANDLERS[name] = fn
        return fn

    return register


async def enqueue(
    db: AsyncSession,
    task: str,
    *,
    queueing_lock: str | None = None,
    lock: str | None = None,
    **args: Any,
) -> None:
    """Queue `task(**args)`. With `queueing_lock`, a job still waiting with the same lock
    makes this a no-op, so repeated requests do not pile up duplicates."""
    if task not in HANDLERS:
        raise KeyError(f"Unknown job {task}")
    statement = text(
        """
        INSERT INTO procrastinate_jobs (queue_name, task_name, lock, queueing_lock, args)
        VALUES (:queue, :task, :lock, :queueing_lock, CAST(:args AS jsonb))
        ON CONFLICT DO NOTHING
        """
    )
    await db.execute(
        statement,
        {
            "queue": QUEUE,
            "task": task,
            "lock": lock,
            "queueing_lock": queueing_lock,
            "args": json.dumps(args),
        },
    )
