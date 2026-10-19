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


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="radicle")
    commands = parser.add_subparsers(dest="command", required=True)
    worker = commands.add_parser("worker", help="Run background jobs")
    worker.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args(argv)
    logging.basicConfig(level=get_settings().log_level.upper())
    if args.command == "worker":
        _worker(args.concurrency)


if __name__ == "__main__":  # pragma: no cover
    main()
