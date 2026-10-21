"""Progress tracking for long operations that run in the worker."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.db.models import Job, JobStatus, User, utcnow
from radicle.platform.errors import NotFound


async def create_job(
    db: AsyncSession, user: User, kind: str, *, total: int, params: dict[str, Any]
) -> Job:
    job = Job(id=uuid.uuid4(), kind=kind, total=total, params=params, created_by=user.id)
    db.add(job)
    await db.flush()
    return job


async def get_job(db: AsyncSession, user: User, job_id: uuid.UUID) -> Job:
    """Only whoever started a job (or an instance admin) can see it."""
    job = await db.get(Job, job_id)
    if job is None or (job.created_by != user.id and not user.is_instance_admin):
        raise NotFound(f"Job {job_id} not found.", code="job_not_found")
    return job


def start(job: Job) -> None:
    job.status = JobStatus.running


def finish(job: Job, result: Any) -> None:
    job.status = JobStatus.succeeded
    job.progress = job.total
    job.result = result
    job.finished_at = utcnow()


def fail(job: Job, error: str) -> None:
    job.status = JobStatus.failed
    job.error = error
    job.finished_at = utcnow()
