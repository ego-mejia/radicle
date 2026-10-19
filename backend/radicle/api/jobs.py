from typing import Any
from uuid import UUID

from fastapi import APIRouter

from radicle.api.deps import CurrentPrincipal, Db
from radicle.api.schemas.common import Output, UtcDatetime
from radicle.db.models import Job, JobStatus
from radicle.services import jobs

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobOut(Output):
    id: str
    kind: str
    status: JobStatus
    progress: int
    total: int
    result: Any
    error: str | None
    created_at: UtcDatetime
    finished_at: UtcDatetime | None


def job_out(job: Job) -> JobOut:
    return JobOut(
        id=str(job.id),
        kind=job.kind,
        status=job.status,
        progress=job.progress,
        total=job.total,
        result=job.result,
        error=job.error,
        created_at=job.created_at,
        finished_at=job.finished_at,
    )


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: UUID, principal: CurrentPrincipal, db: Db) -> JobOut:
    """Progress and result of a background job you started."""
    return job_out(await jobs.get_job(db, principal.user, job_id))
