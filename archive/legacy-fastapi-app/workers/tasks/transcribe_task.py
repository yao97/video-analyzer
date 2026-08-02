"""
Whisper transcription async task.
Runs in a Celery worker process, separate from the FastAPI HTTP server.
Resolves Bug #1 (synchronous blocking) by offloading to async queue.
"""
from __future__ import annotations

import asyncio
import os
import tempfile
import traceback
from pathlib import Path
from typing import Any

from app.workers.celery_app import celery_app
from app.workers.progress import publish_progress, publish_completion, publish_error
from app.core.logging import get_logger
from app.db.session import async_session_factory
from app.services import job_manager, transcription, audio_extract, storage
from app.config import get_settings

log = get_logger("transcribe_task")


@celery_app.task(
    name="app.workers.tasks.transcribe_task.transcribe_video",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def transcribe_video(self, job_id: str, model: str = "tiny", language: str | None = None) -> dict:
    """
    Transcribe a video: download from MinIO -> extract audio -> Whisper transcribe -> save results.

    Args:
        job_id: Job ID in the database.
        model: Whisper model name (tiny, base, small, medium).
        language: Optional language hint.

    Returns:
        Dict with transcription results.
    """
    log.info("transcribe_task_started", job_id=job_id, model=model, language=language)

    try:
        # Run async code in sync Celery context
        return asyncio.run(_transcribe_async(job_id, model, language))

    except Exception as exc:
        log.error("transcribe_task_failed", job_id=job_id, error=str(exc), traceback=traceback.format_exc())

        # Update job status to failed
        asyncio.run(_mark_job_failed(job_id, str(exc)))

        # Publish error to WebSocket subscribers
        publish_error(job_id, str(exc))

        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))


async def _transcribe_async(job_id: str, model: str, language: str | None) -> dict:
    """Async implementation of the transcription workflow."""

    async with async_session_factory() as db:
        # 1. Get job and update status
        job = await job_manager.get_job(db, job_id)
        await job_manager.update_job_status(db, job_id, "processing", progress=0.0)
        await db.commit()
        publish_progress(job_id, 0.0, "Starting transcription")

        # 2. Download video from MinIO
        publish_progress(job_id, 0.1, "Downloading video from storage")
        storage_service = storage.StorageService()
        video_data = storage_service.download_file(job.storage_key)

        # Save to temp file
        temp_dir = Path(tempfile.gettempdir()) / "video_analyzer"
        temp_dir.mkdir(parents=True, exist_ok=True)
        video_path = temp_dir / f"{job_id}_{job.video_filename or 'video.mp4'}"

        with open(video_path, "wb") as f:
            f.write(video_data)

        log.info("video_downloaded", job_id=job_id, path=str(video_path), size=len(video_data))

        # 3. Extract audio with ffmpeg (Bug #4 fix: no shell=True)
        publish_progress(job_id, 0.2, "Extracting audio")
        wav_path = audio_extract.extract_audio(
            video_path,
            duration=job.video_duration,
            output_dir=temp_dir,
        )

        # 4. Load Whisper and transcribe
        publish_progress(job_id, 0.3, "Loading Whisper model")

        # Update model if specified
        settings = get_settings()
        if model and model != settings.whisper_model:
            # Override the model for this task
            import app.services.transcription as trans_svc
            trans_svc._whisper_model = None  # Force reload
            trans_svc._whisper_model_name = ""
            # Temporarily override settings
            import app.config
            app.config.get_settings.cache_clear()
            os.environ["WHISPER_MODEL"] = model

        publish_progress(job_id, 0.4, "Transcribing audio")

        # Progress callback for Whisper
        def progress_cb(progress: float, message: str) -> None:
            # Map 0.4-0.9 range for transcription progress
            mapped = 0.4 + progress * 0.5
            publish_progress(job_id, mapped, message)

        result = transcription.transcribe_audio(
            wav_path,
            language=language,
            progress_callback=progress_cb,
        )

        publish_progress(job_id, 0.9, "Saving transcription results")

        # 5. Save transcript to database
        await job_manager.save_transcript(
            db,
            job_id=job_id,
            segments=result["segments"],
            full_text=result["text"],
            language=result["language"],
            duration=job.video_duration,
            video_filename=job.video_filename,
        )

        # 6. Update job status
        await job_manager.update_job_status(
            db,
            job_id,
            "completed",
            progress=1.0,
            result={
                "transcript": result,
                "language": result["language"],
                "segment_count": len(result["segments"]),
            },
        )
        await db.commit()

        # 7. Cleanup temp files (Bug #10 fix)
        try:
            os.remove(video_path)
            os.remove(wav_path)
            log.info("temp_files_cleaned", job_id=job_id)
        except OSError as e:
            log.warning("temp_cleanup_failed", job_id=job_id, error=str(e))

        # 8. Publish completion
        publish_completion(job_id, result)

        log.info("transcribe_task_completed", job_id=job_id, language=result["language"])
        return result


async def _mark_job_failed(job_id: str, error: str) -> None:
    """Mark a job as failed in the database."""
    try:
        async with async_session_factory() as db:
            await job_manager.update_job_status(
                db, job_id, "failed", error_message=error,
                error_traceback=traceback.format_exc(),
            )
            await db.commit()
    except Exception as e:
        log.error("failed_to_mark_job_failed", job_id=job_id, error=str(e))
