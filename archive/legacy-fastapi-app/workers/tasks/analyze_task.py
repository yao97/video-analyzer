"""
LLM analysis async task.
Calls external LLM API to generate deep content analysis.
Resolves Bug #5 (API Key server-side) and Bug #11 (timeout/retry support).
"""
from __future__ import annotations

import asyncio
import traceback
from typing import Any

from app.workers.celery_app import celery_app
from app.workers.progress import publish_progress, publish_completion, publish_error
from app.core.logging import get_logger
from app.db.session import async_session_factory
from app.services import job_manager, llm_analyze

log = get_logger("analyze_task")


@celery_app.task(
    name="app.workers.tasks.analyze_task.analyze_content",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def analyze_content(
    self,
    job_id: str,
    transcription_data: dict[str, Any],
    analysis_data: dict[str, Any],
    video_meta: dict[str, Any],
    model: str | None = None,
    provider: str | None = None,
) -> dict[str, Any]:
    """
    Run LLM deep analysis on transcription + video analysis data.

    Args:
        job_id: Job ID in the database.
        transcription_data: Transcription text, segments, keywords.
        analysis_data: Video frame analysis results.
        video_meta: Video metadata (width, height, fps).
        model: LLM model name.
        provider: LLM provider (siliconflow/ollama/zhipu).

    Returns:
        Dict with analysis report and metadata.
    """
    log.info(
        "analyze_task_started",
        job_id=job_id,
        model=model,
        provider=provider,
    )

    try:
        return asyncio.run(
            _analyze_async(job_id, transcription_data, analysis_data, video_meta, model, provider)
        )

    except Exception as exc:
        log.error("analyze_task_failed", job_id=job_id, error=str(exc), traceback=traceback.format_exc())

        asyncio.run(_mark_job_failed(job_id, str(exc)))
        publish_error(job_id, str(exc))

        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


async def _analyze_async(
    job_id: str,
    transcription_data: dict,
    analysis_data: dict,
    video_meta: dict,
    model: str | None,
    provider: str | None,
) -> dict:
    """Async implementation of the LLM analysis workflow."""

    async with async_session_factory() as db:
        # 1. Update job status
        await job_manager.update_job_status(db, job_id, "processing", progress=0.0)
        await db.commit()
        publish_progress(job_id, 0.1, "Starting LLM analysis")

        # 2. Call LLM API
        publish_progress(job_id, 0.2, "Calling LLM API (this may take a while)")

        result = await llm_analyze.analyze_content(
            transcription=transcription_data,
            analysis=analysis_data,
            video_meta=video_meta,
            model=model,
            provider=provider,
        )

        publish_progress(job_id, 0.8, "LLM analysis complete, saving results")

        # 3. Save analysis result to database
        await job_manager.save_analysis_result(
            db,
            job_id=job_id,
            analysis_type="deep_analysis",
            result={"report": result["report"]},
            model_used=result["model_used"],
            tokens_used=result["tokens_used"],
        )

        # 4. Update job status
        await job_manager.update_job_status(
            db,
            job_id,
            "completed",
            progress=1.0,
            result={
                "report": result["report"],
                "model_used": result["model_used"],
                "tokens_used": result["tokens_used"],
            },
        )
        await db.commit()

        # 5. Publish completion
        publish_completion(job_id, result)

        log.info(
            "analyze_task_completed",
            job_id=job_id,
            model=result["model_used"],
            tokens=result["tokens_used"],
        )
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
