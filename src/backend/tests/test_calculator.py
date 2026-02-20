"""Tests for STORY-008: CPU tier calculator service and endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.jwt import build_claims, create_token
from app.errors import ValidationError
from app.main import app
from app.services.calculator_service import convert_cpu, get_conversion_info

# ---------------------------------------------------------------------------
# Calculator service unit tests
# ---------------------------------------------------------------------------


class TestConvertCpu:
    def test_hp_to_regular_ratio_2(self):
        result = convert_cpu(8, "high_performance", "regular")
        assert result["output_cpu"] == 16.0  # 8 * 2.0

    def test_regular_to_hp_ratio_2(self):
        result = convert_cpu(8, "regular", "high_performance")
        assert result["output_cpu"] == 4.0  # 8 / 2.0

    def test_regular_to_hp_rounds_up_to_nearest_half(self):
        # 3 regular / 2.0 = 1.5 → already a half
        result = convert_cpu(3, "regular", "high_performance")
        assert result["output_cpu"] == 1.5

    def test_regular_to_hp_odd_number(self):
        # 5 regular / 2.0 = 2.5 → nearest 0.5 = 2.5
        result = convert_cpu(5, "regular", "high_performance")
        assert result["output_cpu"] == 2.5

    def test_cpu_count_zero_raises_validation_error(self):
        with pytest.raises(ValidationError, match="greater than 0"):
            convert_cpu(0, "regular", "high_performance")

    def test_negative_cpu_count_raises_validation_error(self):
        with pytest.raises(ValidationError):
            convert_cpu(-1, "regular", "high_performance")

    def test_same_tier_raises_validation_error(self):
        with pytest.raises(ValidationError, match="different"):
            convert_cpu(8, "regular", "regular")

    def test_result_includes_ratio_used(self):
        result = convert_cpu(4, "high_performance", "regular")
        assert "ratio_used" in result
        assert result["ratio_used"] == 2.0

    def test_result_includes_all_fields(self):
        result = convert_cpu(4, "high_performance", "regular")
        assert result["input_cpu"] == 4
        assert result["from_tier"] == "high_performance"
        assert result["to_tier"] == "regular"


class TestGetConversionInfo:
    def test_returns_ratio_and_description(self):
        info = get_conversion_info()
        assert "ratio" in info
        assert "description" in info
        assert info["ratio"] == 2.0
        assert "high_performance" in info["description"]


# ---------------------------------------------------------------------------
# Calculator API endpoint tests
# ---------------------------------------------------------------------------


@pytest.fixture
async def api_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


def _center_admin_token() -> str:
    return create_token(build_claims("admin", "center_admin", None))


class TestCalculatorEndpoints:
    async def test_cpu_conversion_info_no_auth_required(self, api_client):
        response = await api_client.get("/api/v1/calculator/cpu-conversion")
        assert response.status_code == 200
        body = response.json()
        assert "ratio" in body
        assert "description" in body

    async def test_convert_hp_to_regular(self, api_client):
        response = await api_client.post(
            "/api/v1/calculator/convert",
            json={"cpu_count": 8, "from_tier": "high_performance", "to_tier": "regular"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["output_cpu"] == 16.0
        assert body["from_tier"] == "high_performance"
        assert body["to_tier"] == "regular"

    async def test_convert_regular_to_hp(self, api_client):
        response = await api_client.post(
            "/api/v1/calculator/convert",
            json={"cpu_count": 8, "from_tier": "regular", "to_tier": "high_performance"},
        )
        assert response.status_code == 200
        assert response.json()["output_cpu"] == 4.0

    async def test_same_tier_returns_422(self, api_client):
        response = await api_client.post(
            "/api/v1/calculator/convert",
            json={"cpu_count": 8, "from_tier": "regular", "to_tier": "regular"},
        )
        assert response.status_code == 422

    async def test_zero_cpu_count_returns_422(self, api_client):
        response = await api_client.post(
            "/api/v1/calculator/convert",
            json={"cpu_count": 0, "from_tier": "regular", "to_tier": "high_performance"},
        )
        assert response.status_code == 422

    async def test_invalid_tier_returns_422(self, api_client):
        response = await api_client.post(
            "/api/v1/calculator/convert",
            json={"cpu_count": 4, "from_tier": "turbo", "to_tier": "regular"},
        )
        assert response.status_code == 422
