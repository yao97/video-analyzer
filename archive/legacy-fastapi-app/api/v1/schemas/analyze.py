"""Pydantic models for LLM analysis endpoints."""
from __future__ import annotations

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    """Request model for starting an LLM analysis job."""

    job_id: str = Field(..., description="Job ID from transcription")
    model: str | None = Field(None, description="LLM model name")
    provider: str | None = Field(
        None, pattern="^(siliconflow|ollama|zhipu)$", description="LLM provider"
    )
    transcription: dict = Field(..., description="Transcription data")
    analysis: dict = Field(default_factory=dict, description="Video analysis data")
    video_meta: dict = Field(default_factory=dict, description="Video metadata")


class AnalyzeResponse(BaseModel):
    """Response model for analysis start."""

    job_id: str
    status: str
    websocket_url: str


class AnalyzeResult(BaseModel):
    """Full analysis result."""

    job_id: str
    report: str = Field("", description="Markdown analysis report")
    model_used: str | None = None
    tokens_used: int | None = None


class TestApiKeyRequest(BaseModel):
    """Request model for testing an API key."""

    provider: str = Field(..., pattern="^(siliconflow|ollama|zhipu)$")
    api_key: str = Field("", description="API key to test (empty for ollama)")
    base_url: str | None = Field(None, description="Custom base URL")


class TestApiKeyResponse(BaseModel):
    """Response model for API key test."""

    valid: bool
    models: list[str] = []
    error: str | None = None
