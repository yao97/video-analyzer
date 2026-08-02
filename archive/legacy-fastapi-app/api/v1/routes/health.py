"""
Health check endpoints.
Resolves Bug #6 (no health check): provides /health (liveness) and /ready (readiness).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.deps import get_db, get_redis
from app.services.transcription import get_model_info

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health")
async def health_check() -> dict:
    """
    Liveness probe — returns immediately if the process is alive.
    Does not check dependencies (use /ready for that).
    """
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }


@router.get("/ready")
async def readiness_check(
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> dict:
    """
    Readiness probe — checks all dependency services.
    Returns 503 if any critical dependency is unavailable.
    """
    checks = {}

    # Check PostgreSQL
    try:
        result = await db.execute(text("SELECT 1"))
        checks["postgres"] = "ok" if result.scalar() == 1 else "error"
    except Exception:
        checks["postgres"] = "error"

    # Check Redis
    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"

    # Check Whisper model info
    try:
        model_info = get_model_info()
        checks["whisper_model"] = model_info["model"]
        checks["whisper_device"] = model_info["device"]
    except Exception:
        checks["whisper_model"] = "not_loaded"

    # Check MinIO
    try:
        from app.core.deps import get_minio
        minio_client = get_minio()
        if minio_client.bucket_exists(settings.minio_bucket):
            checks["minio"] = "ok"
        else:
            checks["minio"] = "bucket_not_found"
    except Exception:
        checks["minio"] = "error"

    all_ok = all(
        v == "ok" for k, v in checks.items()
        if k not in ("whisper_model", "whisper_device")
    )

    return {
        "status": "ok" if all_ok else "degraded",
        "checks": checks,
    }
