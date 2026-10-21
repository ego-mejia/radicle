import uuid

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.docket.db.models import Job, User
from radicle.platform.services import jobs, queue
from tests.conftest import Team, run_jobs

CALLS: list[dict] = []


@queue.handler("test_echo")
async def _echo(db: AsyncSession, **args: object) -> None:
    CALLS.append(args)
    if args.get("again"):
        await queue.enqueue(db, "test_echo", value="second")


async def queued(db: AsyncSession) -> list[tuple[str, dict]]:
    rows = await db.execute(
        text("SELECT task_name, args FROM procrastinate_jobs WHERE status = 'todo' ORDER BY id")
    )
    return [(r.task_name, r.args) for r in rows]


async def test_enqueue_is_part_of_the_transaction(db: AsyncSession) -> None:
    CALLS.clear()
    savepoint = await db.begin_nested()
    await queue.enqueue(db, "test_echo", value="lost")
    await savepoint.rollback()
    assert await queued(db) == []

    await queue.enqueue(db, "test_echo", value="first", again=True)
    assert await queued(db) == [("test_echo", {"value": "first", "again": True})]
    assert await run_jobs(db) == ["test_echo", "test_echo"]
    assert CALLS == [{"value": "first", "again": True}, {"value": "second"}]


async def test_queueing_lock_avoids_duplicates(db: AsyncSession) -> None:
    for _ in range(3):
        await queue.enqueue(db, "test_echo", queueing_lock="sync-1", value=1)
    assert len(await queued(db)) == 1


async def test_unknown_task(db: AsyncSession) -> None:
    try:
        await queue.enqueue(db, "nope")
    except KeyError as exc:
        assert "nope" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected KeyError")


async def test_get_job(client: AsyncClient, db: AsyncSession, team: Team) -> None:
    luis = await db.scalar(text("SELECT id FROM users WHERE handle = 'luis'"))
    user = await db.get(User, luis)
    assert user is not None
    job = await jobs.create_job(db, user, "bulk_update", total=3, params={"keys": ["PA-1"]})
    jobs.start(job)
    job.progress = 1
    await db.commit()  # a request that fails rolls back to the last commit
    job_id = job.id

    r = await client.get(f"/api/v1/jobs/{job_id}", headers=team.member.headers)
    assert r.status_code == 200
    assert r.json()["status"] == "running" and r.json()["progress"] == 1
    r = await client.get(f"/api/v1/jobs/{job_id}", headers=team.viewer.headers)
    assert r.status_code == 404
    r = await client.get(f"/api/v1/jobs/{job_id}", headers=team.instance.headers)
    assert r.status_code == 200
    r = await client.get(f"/api/v1/jobs/{uuid.uuid4()}", headers=team.member.headers)
    assert r.status_code == 404

    job = await db.get(Job, job_id)
    assert job is not None
    jobs.finish(job, {"ok": 3})
    await db.commit()
    r = await client.get(f"/api/v1/jobs/{job_id}", headers=team.member.headers)
    assert r.json()["status"] == "succeeded" and r.json()["progress"] == 3
    jobs.fail(job, "boom")
    assert job.error == "boom"
