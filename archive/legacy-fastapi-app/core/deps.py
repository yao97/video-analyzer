"""
Dependency injection providers for FastAPI routes.
Provides database sessions, Redis connections, MinIO clients, and other shared resources.
"""
from __future__ import annotations

import uuid
from typing import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import Request
from minio import Minio
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """Provide a Redis connection."""
    settings = get_settings()
    redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        yield redis
    finally:
        await redis.close()


def get_minio() -> Minio:
    """Provide a MinIO client (synchronous)."""
    settings = get_settings()
    return Minio(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def get_request_id(request: Request) -> str:
    """Get or generate a request ID for tracing."""
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    return request_id


def get_settings_dep():
    """FastAPI dependency for accessing settings."""
    return get_settings()
