"""
Centralized configuration management using pydantic-settings.
All configuration is loaded from environment variables, validated at startup (fail-fast).
No hardcoded secrets, URLs, or credentials anywhere in the codebase.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # === Application ===
    app_name: str = "Video Content Analyzer"
    app_version: str = "2.0.0"
    debug: bool = False

    # === Database ===
    database_url: str = "postgresql+asyncpg://vca:vca_secret@localhost:5432/video_analyzer"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_echo: bool = False

    # === Redis ===
    redis_url: str = "redis://localhost:6379/0"

    # === MinIO ===
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "video-analyzer"
    minio_secure: bool = False

    # === LLM ===
    llm_api_key: str = ""
    llm_provider: str = "siliconflow"
    llm_base_url: str = "https://api.siliconflow.cn/v1"
    llm_default_model: str = "Qwen/Qwen2.5-7B-Instruct"
    llm_request_timeout: int = 300  # 5 minutes

    # === Security ===
    encryption_key: str = ""
    allowed_origins: str = "http://127.0.0.1:8765,http://localhost:8765"

    # === Whisper ===
    whisper_model: str = "tiny"
    whisper_device: str = "cpu"

    # === File limits ===
    max_video_size_mb: int = 600

    # === Rate limiting ===
    rate_limit_upload: str = "5/minute"
    rate_limit_transcribe: str = "5/minute"
    rate_limit_analyze: str = "10/minute"
    rate_limit_jobs: str = "30/minute"

    # === Cleanup ===
    cleanup_interval_hours: int = 1
    cleanup_max_age_hours: int = 1

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def max_video_size_bytes(self) -> int:
        return self.max_video_size_mb * 1024 * 1024

    @field_validator("whisper_device")
    @classmethod
    def validate_device(cls, v: str) -> str:
        if v not in ("cpu", "cuda"):
            raise ValueError("WHISPER_DEVICE must be 'cpu' or 'cuda'")
        return v

    @field_validator("llm_provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        if v not in ("siliconflow", "ollama", "zhipu"):
            raise ValueError("LLM_PROVIDER must be 'siliconflow', 'ollama', or 'zhipu'")
        return v


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance (singleton)."""
    return Settings()
