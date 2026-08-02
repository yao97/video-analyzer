"""
Job manager service — handles task state transitions and persistence.
Replaces the in-memory dict (Bug #2) with PostgreSQL-backed job state.
"""
from __future__ import annotations

import traceback
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, JobAlreadyRunningError
from app.core.logging import get_logger
from app.db.models import Job, Transcript, AnalysisResult

log = get_logger("job_manager")


async def create_job(
    db: AsyncSession,
    job_type: str,
    video_filename: str | None = None,
    video_duration: float | None = None,
    storage_key: str | None = None,
    created_by: str | None = None,
    parent_job_id: str | None = None,
) -> Job:
    """Create a new job record in the database."""
    job = Job(
        type=job_type,
        status="pending",
        video_filename=video_filename,
        video_duration=video_duration,
        storage_key=storage_key,
        created_by=created_by,
        parent_job_id=uuid.UUID(parent_job_id) if parent_job_id else None,
    )
    db.add(job)
    await db.flush()
    log.info("job_created", job_id=str(job.id), type=job_type)
    return job


async def get_job(db: AsyncSession, job_id: str) -> Job:
    """Get a job by ID. Raises NotFoundError if not found."""
    job = await db.get(Job, uuid.UUID(job_id))
    if not job:
        raise NotFoundError("Job", job_id)
    return job


async def update_job_status(
    db: AsyncSession,
    job_id: str,
    status: str,
    progress: float | None = None,
    result: dict | None = None,
    error_message: str | None = None,
    error_traceback: str | None = None,
) -> Job:
    """Update job status, progress, and optional result/error."""
    job = await get_job(db, job_id)

    job.status = status
    if progress is not None:
        job.progress = progress
    if result is not None:
        job.result = result
    if error_message is not None:
        job.error_message = error_message
    if error_traceback is not None:
        job.error_traceback = error_traceback

    # Set timestamps based on status
    now = datetime.now(timezone.utc)
    if status == "processing" and job.started_at is None:
        job.started_at = now
    elif status in ("completed", "failed", "cancelled"):
        job.completed_at = now

    await db.flush()
    log.info(
        "job_status_updated",
        job_id=job_id,
        status=status,
        progress=job.progress,
    )
    return job


async def cancel_job(db: AsyncSession, job_id: str) -> Job:
    """Cancel a job. Only pending or processing jobs can be cancelled."""
    job = await get_job(db, job_id)
    if job.status in ("completed", "failed", "cancelled"):
        raise JobAlreadyRunningError(f"Job {job_id} is already {job.status} and cannot be cancelled")
    job.status = "cancelled"
    job.completed_at = datetime.now(timezone.utc)
    await db.flush()
    log.info("job_cancelled", job_id=job_id)
    return job


async def delete_job(db: AsyncSession, job_id: str) -> None:
    """Delete a job and all associated records."""
    job = await get_job(db, job_id)
    await db.delete(job)
    await db.flush()
    log.info("job_deleted", job_id=job_id)


async def list_jobs(
    db: AsyncSession,
    status: str | None = None,
    job_type: str | None = None,
    created_by: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Job], int]:
    """
    List jobs with optional filters.

    Returns:
        Tuple of (job list, total count).
    """
    query = select(Job)

    if status:
        query = query.where(Job.status == status)
    if job_type:
        query = query.where(Job.type == job_type)
    if created_by:
        query = query.where(Job.created_by == created_by)

    query = query.order_by(Job.created_at.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    jobs = list(result.scalars().all())

    # Get total count
    count_query = select(func.count(Job.id))
    if status:
        count_query = count_query.where(Job.status == status)
    if job_type:
        count_query = count_query.where(Job.type == job_type)
    if created_by:
        count_query = count_query.where(Job.created_by == created_by)

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return jobs, total


async def save_transcript(
    db: AsyncSession,
    job_id: str,
    segments: list[dict],
    full_text: str,
    language: str | None = None,
    duration: float | None = None,
    video_filename: str | None = None,
) -> Transcript:
    """Save transcription results to the database."""
    transcript = Transcript(
        job_id=uuid.UUID(job_id),
        video_filename=video_filename,
        language=language,
        duration=duration,
        segments=segments,
        full_text=full_text,
    )
    db.add(transcript)
    await db.flush()
    log.info("transcript_saved", job_id=job_id, transcript_id=str(transcript.id))
    return transcript


async def get_transcript(db: AsyncSession, job_id: str) -> Transcript | None:
    """Get the transcript for a job."""
    result = await db.execute(
        select(Transcript).where(Transcript.job_id == uuid.UUID(job_id))
    )
    return result.scalar_one_or_none()


async def save_analysis_result(
    db: AsyncSession,
    job_id: str,
    analysis_type: str,
    result: dict,
    model_used: str | None = None,
    tokens_used: int | None = None,
    transcript_id: str | None = None,
) -> AnalysisResult:
    """Save LLM analysis results to the database."""
    analysis = AnalysisResult(
        job_id=uuid.UUID(job_id),
        transcript_id=uuid.UUID(transcript_id) if transcript_id else None,
        analysis_type=analysis_type,
        model_used=model_used,
        result=result,
        tokens_used=tokens_used,
    )
    db.add(analysis)
    await db.flush()
    log.info("analysis_result_saved", job_id=job_id, analysis_id=str(analysis.id))
    return analysis


async def get_analysis_result(db: AsyncSession, job_id: str) -> AnalysisResult | None:
    """Get the analysis result for a job."""
    result = await db.execute(
        select(AnalysisResult).where(AnalysisResult.job_id == uuid.UUID(job_id))
    )
    return result.scalar_one_or_none()
