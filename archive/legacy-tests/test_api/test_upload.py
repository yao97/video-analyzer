"""
Tests for the upload endpoint.
"""
import pytest
from io import BytesIO


@pytest.mark.asyncio
async def test_upload_invalid_file_type(client):
    """Test that uploading a non-video file returns 415."""
    response = await client.post(
        "/api/v1/upload",
        files={"file": ("test.txt", BytesIO(b"not a video"), "text/plain")},
    )
    assert response.status_code == 415


@pytest.mark.asyncio
async def test_upload_missing_file(client):
    """Test that missing file returns 422."""
    response = await client.post("/api/v1/upload")
    assert response.status_code == 422
