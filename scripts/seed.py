"""Seed a project with realistic tickets for demos and benchmarks.

Usage: cd backend && uv run python ../scripts/seed.py --tickets 10000 [--project PERF]
Uses RADICLE_DATABASE_URL. Demo users get the password from --password.
"""

import argparse
import asyncio
import sys

from radicle.platform.db.session import dispose_engine, get_sessionmaker
from radicle.seed import seed


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tickets", type=int, default=10_000)
    parser.add_argument("--project", default="PERF")
    parser.add_argument("--password", default="radicle-demo")
    args = parser.parse_args()
    async with get_sessionmaker()() as db:
        result = await seed(
            db, tickets=args.tickets, project_key=args.project, password=args.password
        )
        await db.commit()
    await dispose_engine()
    sys.stdout.write(
        f"Seeded {result.tickets} tickets in {result.project_key}. "
        f"Sign in as {result.admin_email} / {result.admin_password}\n"
    )


if __name__ == "__main__":
    asyncio.run(main())
