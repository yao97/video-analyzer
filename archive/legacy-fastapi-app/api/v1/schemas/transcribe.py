"""Pydantic models for transcription endpoints."""
from __future__ import annotations

from pydantic import BaseModel, Field


class TranscribeRequest(BaseModel):
    """Request model for starting a transcription job."""

    job_id: str = Field(..., description="Job ID from upload")
    model: str = Field("tiny", pattern="^(tiny|base|small|medium)$", description="Whisper model")
    language: str | None = Field(None, max_length=10, description="Language hint (e.g., 'zh', 'en')")


class TranscribeResponse(BaseModel):
    """Response model for transcription start."""

    job_id: str
    status: str = Field(..., description="Current job status")
    websocket_url: str = Field(..., description="WebSocket URL for progress updates")


class TranscriptSegment(BaseModel):
    """A single transcript segment."""

    start: float
    end: float
    text: str


class TranscriptResult(BaseModel):
    """Full transcription result."""

    job_id: str
    language: str | None = None
    duration: float | None = None
    full_text: str = ""
    segments: list[TranscriptSegment] = []
    keywords: dict = Field(default_factory=dict)
