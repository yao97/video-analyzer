"""
LLM analysis route — starts async LLM deep analysis jobs.
Resolves Bug #5 (API Key server-side management).
Resolves Bug #11 (timeout/retry support via Celery + httpx).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.deps import get_db
from app.core.exceptions import NotFoundError
from app.core.limiter import limiter
from app.services import job_manager, llm_analyze
from app.api.v1.schemas.analyze import (
    AnalyzeRequest,
    AnalyzeResponse,
    AnalyzeResult,
    TestApiKeyRequest,
    TestApiKeyResponse,
)
from app.workers.tasks.analyze_task import analyze_content

router = APIRouter(prefix="/api/v1", tags=["analyze"])
settings = get_settings()


@router.post("/analyze", response_model=AnalyzeResponse)
@limiter.limit(settings.rate_limit_analyze)
async def start_analysis(
    request: Request,
    req: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
) -> AnalyzeResponse:
    """
    Start an asynchronous LLM deep analysis job.

    The job is dispatched to a Celery worker that:
    1. Builds the analysis prompt from transcription + video data
    2. Calls the LLM API (SiliconFlow / Ollama / Zhipu)
    3. Saves the report to PostgreSQL

    API Key is managed server-side (Bug #5 fix).
    Timeout and retry handled by Celery + httpx (Bug #11 fix).
    """
    # Verify the source job exists
    source_job = await job_manager.get_job(db, req.job_id)

    # Create a new analysis job linked to the transcription job
    analysis_job = await job_manager.create_job(
        db,
        job_type="analyze",
        video_filename=source_job.video_filename,
        video_duration=source_job.video_duration,
        storage_key=source_job.storage_key,
        parent_job_id=req.job_id,
        created_by=request.headers.get("X-User-ID", "anonymous"),
    )
    await db.commit()

    # Dispatch to Celery
    analyze_content.delay(
        job_id=str(analysis_job.id),
        transcription_data=req.transcription,
        analysis_data=req.analysis,
        video_meta=req.video_meta,
        model=req.model,
        provider=req.provider,
    )

    # Update job status
    await job_manager.update_job_status(db, str(analysis_job.id), "processing", progress=0.0)
    await db.commit()

    ws_host = request.base_url.hostname or "localhost"
    ws_port = request.base_url.port or 8766
    ws_url = f"ws://{ws_host}:{ws_port}/api/v1/ws/jobs/{analysis_job.id}"

    return AnalyzeResponse(
        job_id=str(analysis_job.id),
        status="processing",
        websocket_url=ws_url,
    )


@router.get("/analyze/{job_id}", response_model=AnalyzeResult)
@limiter.limit("60/minute")
async def get_analysis(
    request: Request,
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> AnalyzeResult:
    """Get LLM analysis results for a job."""
    job = await job_manager.get_job(db, job_id)

    if job.status != "completed":
        return AnalyzeResult(job_id=job_id, report="", model_used=None, tokens_used=None)

    analysis = await job_manager.get_analysis_result(db, job_id)
    if not analysis:
        raise NotFoundError("AnalysisResult", job_id)

    report = ""
    if analysis.result and isinstance(analysis.result, dict):
        report = analysis.result.get("report", "")

    return AnalyzeResult(
        job_id=job_id,
        report=report,
        model_used=analysis.model_used,
        tokens_used=analysis.tokens_used,
    )


@router.post("/test-api-key", response_model=TestApiKeyResponse)
@limiter.limit("10/minute")
async def test_api_key(
    request: Request,
    req: TestApiKeyRequest,
) -> TestApiKeyResponse:
    """
    Test an API key by listing available models from the provider.
    Used by the frontend to validate keys before starting analysis.
    """
    result = await llm_analyze.test_api_key(
        provider=req.provider,
        api_key=req.api_key,
        base_url=req.base_url,
    )

    return TestApiKeyResponse(
        valid=result["valid"],
        models=result.get("models", []),
        error=result.get("error"),
    )
