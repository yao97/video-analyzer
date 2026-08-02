"""
Pytest configuration and fixtures.
Provides test client, database session, and mock objects for testing.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set test environment variables
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://vca:vca_secret@localhost:5432/video_analyzer_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")  # Use DB 1 for tests
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("ENCRYPTION_KEY", "")


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP test client."""
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
def sample_video_meta():
    """Sample video metadata for tests."""
    return {
        "duration": 120.5,
        "width": 1920,
        "height": 1080,
        "fps": 30.0,
        "codec": "h264",
        "size_bytes": 50000000,
        "has_audio": True,
        "orientation": "landscape",
    }


@pytest.fixture
def sample_transcription():
    """Sample transcription data for tests."""
    return {
        "text": "大家好，今天给大家推荐一款非常好用的产品。这个产品特别值得购买。",
        "segments": [
            {"start": 0.0, "end": 5.0, "text": "大家好，今天给大家推荐一款非常好用的产品。"},
            {"start": 5.0, "end": 10.0, "text": "这个产品特别值得购买。"},
        ],
        "language": "zh",
        "keywords": {
            "highFreq": ["产品", "推荐"],
            "actions": ["推荐", "介绍"],
            "emotions": ["非常", "特别", "值得"],
            "products": ["产品"],
        },
    }
