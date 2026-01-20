"""
Test basic API endpoints.
"""

import pytest


@pytest.mark.asyncio
async def test_health_check(async_client):
    """Health check endpoint returns 200"""
    response = await async_client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "environment" in data


@pytest.mark.asyncio
async def test_root_endpoint(async_client):
    """Root endpoint returns API info"""
    response = await async_client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "RMS API"
    assert "docs_url" in data
    assert "openapi_url" in data
