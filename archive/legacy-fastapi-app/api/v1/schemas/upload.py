"""Pydantic models for upload endpoints."""
from __future__ import annotations

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """Response model for file upload."""

    job_id: str = Field(..., description="Unique job identifier")
    storage_key: str = Field(..., description="MinIO storage key for the uploaded file")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    video_duration: float | None = Field(None, description="Video duration in seconds")
