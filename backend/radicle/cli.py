"""`radicle` command line: `radicle worker` runs background jobs."""

import argparse
import asyncio
import logging

from radicle.core.config import get_settings


def _worker(concurrency: int) -> None:
    from radicle.worker.app import build_app

    app = build_app()

    async def run() -> None:
        async with app.open_async():
            await app.run_worker_async(concurrency=concurrency, wait=True)

    asyncio.run(run())


def _backfill(command: str, start: str | None) -> None:
    from datetime import date

    from radicle.db.session import dispose_engine, get_sessionmaker
    from radicle.services import periods

    async def run() -> None:
        async with get_sessionmaker()() as db:
            if command == "backfill-periods":
                count = await periods.backfill(db)
                print(f"{count} status periods rebuilt")
            else:
                count = await periods.backfill_snapshots(db, date.fromisoformat(start or ""))
                print(f"{count} daily rows written")
            await db.commit()
        await dispose_engine()

    asyncio.run(run())


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="radicle")
    commands = parser.add_subparsers(dest="command", required=True)
    worker = commands.add_parser("worker", help="Run background jobs")
    worker.add_argument("--concurrency", type=int, default=4)
    commands.add_parser("backfill-periods", help="Rebuild status periods from ticket history")
    snapshots = commands.add_parser(
        "backfill-snapshots", help="Recompute daily status counts from a date until today"
    )
    snapshots.add_argument("--from", dest="start", required=True, help="YYYY-MM-DD")
    args = parser.parse_args(argv)
    logging.basicConfig(level=get_settings().log_level.upper())
    if args.command == "worker":
        _worker(args.concurrency)
    else:
        _backfill(args.command, getattr(args, "start", None))


if __name__ == "__main__":  # pragma: no cover
    main()
