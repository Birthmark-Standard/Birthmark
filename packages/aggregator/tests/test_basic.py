"""Basic tests for aggregation server."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test root endpoint returns service info."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Birthmark Protocol Aggregation Server"
    assert data["version"] == "1.0.0"
    assert data["phase"] == "Phase 1 (Mock Backend)"


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_invalid_submission_type(client: AsyncClient):
    """Test submission with invalid type returns error."""
    response = await client.post(
        "/api/v1/submit",
        json={
            "submission_type": "invalid",
            "image_hash": "a" * 64,
        },
    )
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_verify_nonexistent_image(client: AsyncClient):
    """Test verifying non-existent image returns not_found."""
    response = await client.get("/api/v1/verify", params={"image_hash": "a" * 64})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_found"
    assert data["image_hash"] == "a" * 64
