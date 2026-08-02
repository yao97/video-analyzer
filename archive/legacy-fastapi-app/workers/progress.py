"""
Redis pub/sub progress publishing.
Workers publish progress updates to Redis, WebSocket consumers subscribe and forward to browsers.
Replaces the 2-second HTTP polling pattern with real-time push.
"""
from __future__ import annotations

import json
from typing import Any

import redis

from app.config import get_settings
from app.core.logging import get_logger

log = get_logger("progress")


def _get_redis() -> redis.Redis:
    """Get a synchronous Redis connection (for Celery workers)."""
    return redis.from_url(get_settings().redis_url, decode_responses=True)


def publish_progress(job_id: str, progress: float, message: str = "", **extra: Any) -> None:
    """
    Publish a progress update for a job to Redis pub/sub.

    Args:
        job_id: Job identifier.
        progress: Progress value (0.0 to 1.0).
        message: Human-readable status message.
        **extra: Additional metadata to include.
    """
    channel = f"job:{job_id}"
    payload = json.dumps({
        "job_id": job_id,
        "progress": progress,
        "message": message,
        "status": extra.get("status", "processing"),
        **{k: v for k, v in extra.items() if k != "status"},
    }, ensure_ascii=False)

    try:
        r = _get_redis()
        r.publish(channel, payload)
        r.close()
        log.debug("progress_published", job_id=job_id, progress=progress, message=message)
    except Exception as e:
        log.warning("progress_publish_failed", job_id=job_id, error=str(e))


def publish_completion(job_id: str, result: dict | None = None) -> None:
    """Publish a job completion event."""
    publish_progress(
        job_id, 1.0, "Task completed", status="completed", result=result or {}
    )


def publish_error(job_id: str, error: str) -> None:
    """Publish a job error event."""
    publish_progress(
        job_id, 0.0, error, status="failed", error=error
    )
