"""Tests for STORY-002: health endpoints.

Covers:
- GET /health returns 200 with status and version
- GET /health/ready returns 503 when DB is unavailable
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestHealthEndpoint:
    async def test_health_returns_correct_response(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert isinstance(body.get("version"), str)
        assert "x-request-id" in response.headers


class TestHealthReadyEndpoint:
    async def test_health_ready_returns_200_by_default(self, client):
        # With a real (or mock) DB that doesn't raise, we get 200
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("app.routers.health.AsyncSessionLocal", return_value=mock_session):
            response = await client.get("/health/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    async def test_health_ready_returns_503_when_db_unavailable(self, client):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(side_effect=Exception("connection refused"))
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("app.routers.health.AsyncSessionLocal", return_value=mock_session):
            response = await client.get("/health/ready")

        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "unavailable"
        assert "detail" in body
