"""
Tests for health check endpoints.
"""
import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    """Test the /health liveness endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_root_endpoint(client):
    """Test the root endpoint returns API info."""
    response = await client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert "service" in data
    assert "version" in data
    assert "docs" in data
