"""
Job management routes — list, get, cancel, delete jobs.
All job state is persisted in PostgreSQL (Bug #2 fix).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.deps import get_db
from app.core.limiter import limiter
from app.services import job_manager, storage
from app.api.v1.schemas.job import (
    JobResponse,
    JobListResponse,
    JobCancelResponse,
    JobDeleteResponse,
)

router = APIRouter(prefix="/api/v1", tags=["jobs"])
settings = get_settings()


@router.get("/jobs", response_model=JobListResponse)
@limiter.limit(settings.rate_limit_jobs)
async def list_jobs(
    request: Request,
    status: str | None = Query(None, description="Filter by status"),
    job_type: str | None = Query(None, description="Filter by job type"),
    created_by: str | None = Query(None, description="Filter by creator"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
) -> JobListResponse:
    """List jobs with optional filters and pagination."""
    jobs, total = await job_manager.list_jobs(
        db,
        status=status,
        job_type=job_type,
        created_by=created_by,
        limit=limit,
        offset=offset,
    )

    return JobListResponse(
        data=[JobResponse(**job.to_dict()) for job in jobs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
@limiter.limit("60/minute")
async def get_job(
    request: Request,
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """Get details of a specific job."""
    job = await job_manager.get_job(db, job_id)
    return JobResponse(**job.to_dict())


@router.post("/jobs/{job_id}/cancel", response_model=JobCancelResponse)
@limiter.limit("10/minute")
async def cancel_job(
    request: Request,
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> JobCancelResponse:
    """Cancel a pending or processing job."""
    job = await job_manager.cancel_job(db, job_id)
    await db.commit()

    return JobCancelResponse(
        job_id=job_id,
        status=job.status,
        message=f"Job {job_id} has been cancelled",
    )


@router.delete("/jobs/{job_id}", response_model=JobDeleteResponse)
@limiter.limit("5/minute")
async def delete_job(
    request: Request,
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> JobDeleteResponse:
    """Delete a job and all associated records."""
    # Get the job to find the storage key
    job = await job_manager.get_job(db, job_id)
    storage_key = job.storage_key

    # Delete from database (cascades to transcripts and analysis_results)
    await job_manager.delete_job(db, job_id)
    await db.commit()

    # Delete the file from MinIO if it exists
    if storage_key:
        storage_service = storage.StorageService()
        storage_service.delete_file(storage_key)

    return JobDeleteResponse(
        job_id=job_id,
        deleted=True,
        message=f"Job {job_id} and associated files have been deleted",
    )
