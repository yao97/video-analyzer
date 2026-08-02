"""
SQLAlchemy ORM models for all database tables.
Replaces the in-memory dict (Bug #2) with persistent, concurrent-safe PostgreSQL storage.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class Job(Base):
    """
    Job table — replaces the in-memory `jobs = {}` dict.
    Supports persistent task state, concurrent-safe access, and job chaining.
    """

    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'transcribe' | 'analyze'
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending | processing | completed | failed | cancelled

    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Input
    video_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    video_duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Output
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_traceback: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Job chaining
    parent_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )

    # Metadata
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    transcripts: Mapped[list[Transcript]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    analysis_results: Mapped[list[AnalysisResult]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        """Serialize to dict for API responses."""
        return {
            "id": str(self.id),
            "type": self.type,
            "status": self.status,
            "progress": self.progress,
            "video_filename": self.video_filename,
            "video_duration": self.video_duration,
            "storage_key": self.storage_key,
            "result": self.result,
            "error_message": self.error_message,
            "parent_job_id": str(self.parent_job_id) if self.parent_job_id else None,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class Transcript(Base):
    """Transcription results table — stores Whisper output segments and full text."""

    __tablename__ = "transcripts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    video_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    segments: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # [{start, end, text}, ...]
    full_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationship
    job: Mapped[Job] = relationship(back_populates="transcripts")

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "job_id": str(self.job_id),
            "video_filename": self.video_filename,
            "language": self.language,
            "duration": self.duration,
            "segments": self.segments,
            "full_text": self.full_text,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AnalysisResult(Base):
    """LLM analysis results table — stores deep analysis output from LLM providers."""

    __tablename__ = "analysis_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    transcript_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transcripts.id", ondelete="SET NULL"), nullable=True
    )
    analysis_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # 'copy_analysis' | 'deep_analysis'
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationship
    job: Mapped[Job] = relationship(back_populates="analysis_results")

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "job_id": str(self.job_id),
            "transcript_id": str(self.transcript_id) if self.transcript_id else None,
            "analysis_type": self.analysis_type,
            "model_used": self.model_used,
            "result": self.result,
            "tokens_used": self.tokens_used,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ApiKey(Base):
    """
    API Keys table — server-side encrypted key management.
    Resolves Bug #5: keys are no longer passed from frontend, managed securely on server.
    """

    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    # 'siliconflow' | 'openai' | 'ollama' | 'zhipu'
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False)  # first 8 chars for ID
    key_encrypted: Mapped[bytes] = mapped_column(nullable=False)  # AES-256-GCM encrypted
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    daily_quota: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    used_today: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quota_reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def to_dict(self, include_key: bool = False) -> dict:
        data = {
            "id": str(self.id),
            "provider": self.provider,
            "key_prefix": self.key_prefix,
            "is_active": self.is_active,
            "daily_quota": self.daily_quota,
            "used_today": self.used_today,
            "quota_reset_at": self.quota_reset_at.isoformat() if self.quota_reset_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_key:
            data["key_encrypted"] = "***encrypted***"
        return data
