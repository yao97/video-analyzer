"""
Periodic cleanup task.
Cleans up old temporary files from MinIO storage (Bug #10 fix).
Runs on Celery beat schedule (every hour by default).
"""
from __future__ import annotations

from app.workers.celery_app import celery_app
from app.core.logging import get_logger
from app.services.storage import StorageService
from app.config import get_settings

log = get_logger("cleanup_task")


@celery_app.task(name="app.workers.tasks.cleanup_task.cleanup_old_files")
def cleanup_old_files() -> dict:
    """
    Clean up files older than the configured max age from MinIO storage.

    Returns:
        Dict with cleanup statistics.
    """
    settings = get_settings()
    max_age_hours = settings.cleanup_max_age_hours

    log.info("cleanup_task_started", max_age_hours=max_age_hours)

    try:
        storage_service = StorageService()
        deleted_count = storage_service.cleanup_old_files(max_age_hours=max_age_hours)

        log.info("cleanup_task_completed", deleted_count=deleted_count)

        return {
            "status": "completed",
            "deleted_count": deleted_count,
            "max_age_hours": max_age_hours,
        }

    except Exception as e:
        log.error("cleanup_task_failed", error=str(e))
        return {
            "status": "failed",
            "error": str(e),
        }
