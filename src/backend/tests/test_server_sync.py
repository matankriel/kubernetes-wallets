"""Tests for STORY-004: server sync logic and inventory endpoints.

Uses AsyncMock to mock the external HTTP call and an in-memory DB session
for repository tests. No real DB or external API required for unit tests.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.jwt import build_claims, create_token
from app.main import app
from app.sync.server_sync import _classify_tier, sync_servers

# ---------------------------------------------------------------------------
# Performance tier classification
# ---------------------------------------------------------------------------


class TestClassifyTier:
    def test_high_performance_at_threshold(self):
        assert _classify_tier(64) == "high_performance"

    def test_high_performance_above_threshold(self):
        assert _classify_tier(128) == "high_performance"

    def test_regular_below_threshold(self):
        assert _classify_tier(32) == "regular"

    def test_regular_when_cpu_is_none(self):
        assert _classify_tier(None) == "regular"


# ---------------------------------------------------------------------------
# sync_servers function
# ---------------------------------------------------------------------------


def _make_http_response(data, status_code=200):
    mock = MagicMock()
    mock.json.return_value = data
    mock.raise_for_status = MagicMock()
    mock.status_code = status_code
    return mock


class TestSyncServers:
    async def test_new_server_is_inserted(self):
        raw = [{"name": "srv-001", "cpu": 32, "ram_gb": 128, "site": "berlin",
                "vendor": "Dell", "deployment_cluster": "c1",
                "serial_number": "SN001", "product": "R750"}]

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_make_http_response(raw))

        mock_repo = AsyncMock()
        mock_repo.upsert_from_external = AsyncMock(return_value={"inserted": 1, "updated": 0})
        mock_repo.mark_offline = AsyncMock(return_value=0)

        with patch("app.sync.server_sync.ServerRepository", return_value=mock_repo):
            result = await sync_servers(AsyncMock(), mock_client)

        assert result["synced"] == 1
        assert result["updated"] == 0
        assert result["marked_offline"] == 0

    async def test_existing_server_is_updated(self):
        raw = [{"name": "srv-001", "cpu": 32, "site": "berlin"}]
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_make_http_response(raw))

        mock_repo = AsyncMock()
        mock_repo.upsert_from_external = AsyncMock(return_value={"inserted": 0, "updated": 1})
        mock_repo.mark_offline = AsyncMock(return_value=0)

        with patch("app.sync.server_sync.ServerRepository", return_value=mock_repo):
            result = await sync_servers(AsyncMock(), mock_client)

        assert result["updated"] == 1

    async def test_server_missing_from_api_is_marked_offline(self):
        raw = []  # No servers returned — all existing should go offline
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_make_http_response(raw))

        mock_repo = AsyncMock()
        mock_repo.upsert_from_external = AsyncMock(return_value={"inserted": 0, "updated": 0})
        mock_repo.mark_offline = AsyncMock(return_value=3)

        with patch("app.sync.server_sync.ServerRepository", return_value=mock_repo):
            result = await sync_servers(AsyncMock(), mock_client)

        assert result["marked_offline"] == 3
        mock_repo.mark_offline.assert_called_once_with([])  # empty keep-list

    async def test_malformed_server_is_skipped_not_raised(self):
        raw = [
            {"name": "srv-ok", "cpu": 16},
            {"no_name_key": "bad"},  # malformed
        ]
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_make_http_response(raw))

        mock_repo = AsyncMock()
        mock_repo.upsert_from_external = AsyncMock(return_value={"inserted": 1, "updated": 0})
        mock_repo.mark_offline = AsyncMock(return_value=0)

        with patch("app.sync.server_sync.ServerRepository", return_value=mock_repo):
            await sync_servers(AsyncMock(), mock_client)

        # Only the valid server was upserted
        call_args = mock_repo.upsert_from_external.call_args[0][0]
        assert len(call_args) == 1
        assert call_args[0]["name"] == "srv-ok"

    async def test_http_failure_returns_zeros(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("network error"))

        result = await sync_servers(AsyncMock(), mock_client)
        assert result == {"synced": 0, "updated": 0, "marked_offline": 0}

    async def test_performance_tier_classified_correctly(self):
        raw = [
            {"name": "hp-srv", "cpu": 128},
            {"name": "reg-srv", "cpu": 16},
        ]
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_make_http_response(raw))

        captured = []
        mock_repo = AsyncMock()

        async def capture_upsert(data):
            captured.extend(data)
            return {"inserted": 2, "updated": 0}

        mock_repo.upsert_from_external = capture_upsert
        mock_repo.mark_offline = AsyncMock(return_value=0)

        with patch("app.sync.server_sync.ServerRepository", return_value=mock_repo):
            await sync_servers(AsyncMock(), mock_client)

        hp = next(d for d in captured if d["name"] == "hp-srv")
        reg = next(d for d in captured if d["name"] == "reg-srv")
        assert hp["performance_tier"] == "high_performance"
        assert reg["performance_tier"] == "regular"


# ---------------------------------------------------------------------------
# Server inventory API endpoints
# ---------------------------------------------------------------------------


def _center_admin_token() -> str:
    return create_token(build_claims("admin", "center_admin", None))


@pytest.fixture
async def api_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestServerEndpoints:
    async def test_list_servers_requires_auth(self, api_client):
        response = await api_client.get("/api/v1/servers")
        assert response.status_code == 401

    async def test_list_servers_returns_paginated_response(self, api_client):
        mock_repo = AsyncMock()
        mock_repo.list_servers = AsyncMock(return_value=([], 0))

        with patch("app.routers.servers.ServerRepository", return_value=mock_repo):
            response = await api_client.get(
                "/api/v1/servers",
                headers={"Authorization": f"Bearer {_center_admin_token()}"},
            )

        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert "pagination" in body
        assert body["pagination"]["page"] == 1

    async def test_get_server_not_found_returns_404(self, api_client):
        mock_repo = AsyncMock()
        from app.errors import NotFoundError
        mock_repo.get_by_id = AsyncMock(side_effect=NotFoundError("not found"))

        with patch("app.routers.servers.ServerRepository", return_value=mock_repo):
            response = await api_client.get(
                "/api/v1/servers/bad-uuid",
                headers={"Authorization": f"Bearer {_center_admin_token()}"},
            )

        assert response.status_code == 404

    async def test_sync_trigger_forbidden_for_non_center_admin(self, api_client):
        token = create_token(build_claims("bob", "field_admin", "field-1"))
        response = await api_client.post(
            "/api/v1/admin/sync/servers",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    async def test_sync_trigger_succeeds_for_center_admin(self, api_client):
        with patch(
            "app.routers.servers.sync_servers",
            AsyncMock(return_value={"synced": 5, "updated": 2, "marked_offline": 1}),
        ), patch("app.routers.servers.AsyncSessionLocal"), \
           patch("app.routers.servers.httpx.AsyncClient"):
            response = await api_client.post(
                "/api/v1/admin/sync/servers",
                headers={"Authorization": f"Bearer {_center_admin_token()}"},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["synced"] == 5
        assert body["updated"] == 2
        assert body["marked_offline"] == 1
