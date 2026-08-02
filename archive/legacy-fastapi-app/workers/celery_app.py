"""
Celery application configuration.
Uses Redis as broker and result backend. Configures task serialization, retries, and scheduling.
"""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "video_analyzer",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.tasks.transcribe_task",
        "app.workers.tasks.analyze_task",
        "app.workers.tasks.cleanup_task",
    ],
)

# Configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task execution
    task_acks_late=True,  # Acknowledge after completion (crash safety)
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,  # Don't prefetch (fair scheduling)

    # Result expiry
    result_expires=3600,  # Results expire after 1 hour

    # Task time limits
    task_time_limit=600,  # 10 min hard limit
    task_soft_time_limit=540,  # 9 min soft limit

    # Retry settings
    task_default_retry_delay=30,
    task_default_max_retries=3,

    # Beat schedule (periodic tasks)
    beat_schedule={
        "cleanup-old-files": {
            "task": "app.workers.tasks.cleanup_task.cleanup_old_files",
            "schedule": crontab(minute=0, hour="*"),  # Every hour
        },
    },
)

# Configure structlog for Celery
from app.core.logging import configure_logging
configure_logging(debug=settings.debug)
