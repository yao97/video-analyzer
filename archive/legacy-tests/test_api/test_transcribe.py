"""
Tests for the transcription endpoint.
"""
import pytest


@pytest.mark.asyncio
async def test_transcribe_invalid_job_id(client):
    """Test that transcribing a non-existent job returns 404."""
    response = await client.post(
        "/api/v1/transcribe",
        json={
            "job_id": "00000000-0000-0000-0000-000000000000",
            "model": "tiny",
        },
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_transcribe_invalid_model(client):
    """Test that invalid model name returns 422."""
    response = await client.post(
        "/api/v1/transcribe",
        json={
            "job_id": "00000000-0000-0000-0000-000000000000",
            "model": "invalid_model",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_transcription_not_found(client):
    """Test that getting transcription for non-existent job returns 404."""
    response = await client.get(
        "/api/v1/transcribe/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404
