"""
File upload route — handles video file uploads to MinIO.
Resolves Bug #9 (hardcoded paths) by using MinIO object storage.
Resolves Bug #4 (file type validation) by checking MIME types.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import FileTooLargeError, UnsupportedMediaTypeError
from app.core.deps import get_db
from app.core.limiter import limiter
from app.services import job_manager, storage
from app.utils.video import get_video_metadata
from app.api.v1.schemas.upload import UploadResponse

router = APIRouter(prefix="/api/v1", tags=["upload"])
settings = get_settings()


@router.post("/upload", response_model=UploadResponse)
@limiter.limit(settings.rate_limit_upload)
async def upload_video(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> UploadResponse:
    """
    Upload a video file for processing.

    The file is stored in MinIO and a job record is created in PostgreSQL.
    Returns the job ID that should be used for subsequent transcription/analysis calls.
    """
    # Validate file type (Bug #4 fix)
    if file.content_type not in storage.ALLOWED_VIDEO_TYPES:
        raise UnsupportedMediaTypeError(file.content_type or "unknown")

    # Validate file size
    contents = await file.read()
    file_size = len(contents)
    if file_size > settings.max_video_size_bytes:
        raise FileTooLargeError(file_size, settings.max_video_size_bytes)

    # Upload to MinIO (Bug #9 fix: no hardcoded paths)
    storage_service = storage.StorageService()
    storage_key = storage_service.upload_bytes(
        data=contents,
        filename=file.filename or "video.mp4",
        content_type=file.content_type or "video/mp4",
    )

    # Extract video metadata
    import tempfile, os
    temp_path = None
    video_duration = None
    try:
        # Save temporarily for metadata extraction
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"upload_{file.filename or 'video.mp4'}")
        with open(temp_path, "wb") as f:
            f.write(contents)
        metadata = get_video_metadata(temp_path)
        video_duration = metadata.get("duration")
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

    # Create job record in PostgreSQL (Bug #2 fix: persistent, concurrent-safe)
    job = await job_manager.create_job(
        db,
        job_type="transcribe",
        video_filename=file.filename,
        video_duration=video_duration,
        storage_key=storage_key,
        created_by=request.headers.get("X-User-ID", "anonymous"),
    )
    await db.commit()

    return UploadResponse(
        job_id=str(job.id),
        storage_key=storage_key,
        filename=file.filename or "video.mp4",
        file_size=file_size,
        video_duration=video_duration,
    )
