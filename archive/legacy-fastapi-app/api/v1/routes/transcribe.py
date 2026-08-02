"""
Transcription route — starts async Whisper transcription jobs.
Resolves Bug #1 (synchronous blocking) by dispatching to Celery.
Resolves Bug #13 (CPU-only) via configurable WHISPER_DEVICE.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.deps import get_db
from app.core.exceptions import ConflictError, NotFoundError
from app.core.limiter import limiter
from app.services import job_manager
from app.api.v1.schemas.transcribe import (
    TranscribeRequest,
    TranscribeResponse,
    TranscriptResult,
    TranscriptSegment,
)
from app.workers.tasks.transcribe_task import transcribe_video

router = APIRouter(prefix="/api/v1", tags=["transcribe"])
settings = get_settings()


@router.post("/transcribe", response_model=TranscribeResponse)
@limiter.limit(settings.rate_limit_transcribe)
async def start_transcription(
    request: Request,
    req: TranscribeRequest,
    db: AsyncSession = Depends(get_db),
) -> TranscribeResponse:
    """
    Start an asynchronous transcription job.

    The job is dispatched to a Celery worker that:
    1. Downloads the video from MinIO
    2. Extracts audio with ffmpeg
    3. Runs Whisper transcription
    4. Saves results to PostgreSQL

    Progress updates are pushed via WebSocket.
    """
    job = await job_manager.get_job(db, req.job_id)

    if job.status in ("processing", "pending"):
        if job.status == "processing":
            raise ConflictError(f"Job {req.job_id} is already running")

    # Dispatch to Celery (Bug #1 fix: async, non-blocking)
    transcribe_video.delay(req.job_id, req.model, req.language)

    # Update job status
    await job_manager.update_job_status(db, req.job_id, "processing", progress=0.0)
    await db.commit()

    ws_host = request.base_url.hostname or "localhost"
    ws_port = request.base_url.port or 8766
    ws_url = f"ws://{ws_host}:{ws_port}/api/v1/ws/jobs/{req.job_id}"

    return TranscribeResponse(
        job_id=req.job_id,
        status="processing",
        websocket_url=ws_url,
    )


@router.get("/transcribe/{job_id}", response_model=TranscriptResult)
@limiter.limit("60/minute")
async def get_transcription(
    request: Request,
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> TranscriptResult:
    """Get transcription results for a job."""
    job = await job_manager.get_job(db, job_id)

    if job.status != "completed":
        return TranscriptResult(
            job_id=job_id,
            language=None,
            duration=job.video_duration,
            full_text="",
            segments=[],
            keywords={},
        )

    transcript = await job_manager.get_transcript(db, job_id)
    if not transcript:
        raise NotFoundError("Transcript", job_id)

    segments = [
        TranscriptSegment(start=s["start"], end=s["end"], text=s["text"])
        for s in (transcript.segments or [])
    ]

    keywords = {}
    if job.result and isinstance(job.result, dict):
        keywords = job.result.get("transcript", {}).get("keywords", {})

    return TranscriptResult(
        job_id=job_id,
        language=transcript.language,
        duration=transcript.duration,
        full_text=transcript.full_text or "",
        segments=segments,
        keywords=keywords,
    )
