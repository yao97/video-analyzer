"""Pydantic models for job management endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class JobResponse(BaseModel):
    """Response model for a single job."""

    id: str
    type: str
    status: str
    progress: float
    video_filename: str | None = None
    video_duration: float | None = None
    storage_key: str | None = None
    result: dict[str, Any] | None = None
    error_message: str | None = None
    parent_job_id: str | None = None
    created_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class JobListResponse(BaseModel):
    """Response model for job list."""

    data: list[JobResponse]
    total: int
    limit: int
    offset: int


class JobCancelResponse(BaseModel):
    """Response model for job cancellation."""

    job_id: str
    status: str
    message: str


class JobDeleteResponse(BaseModel):
    """Response model for job deletion."""

    job_id: str
    deleted: bool
    message: str
