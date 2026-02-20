"""Tests for STORY-002: InfraHubError hierarchy and global exception handler.

Verifies that each error subclass produces the correct HTTP status code
and the expected response body shape:
  {"error": {"code": "...", "message": "...", "request_id": "..."}}
"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.errors import (
    ConflictError,
    ForbiddenError,
    InfraHubError,
    NotFoundError,
    QuotaExceededError,
    UnauthorizedError,
    ValidationError,
)
from app.main import infrahub_error_handler
from app.middleware import RequestIDMiddleware


def make_test_app(*error_classes: type[InfraHubError]) -> FastAPI:
    """Build a minimal FastAPI app with one route per error class."""
    test_app = FastAPI()
    test_app.add_middleware(RequestIDMiddleware)
    test_app.add_exception_handler(InfraHubError, infrahub_error_handler)

    for cls in error_classes:
        path = f"/raise/{cls.__name__.lower()}"

        async def make_route(error_cls=cls):
            raise error_cls("test message")

        test_app.get(path)(make_route)

    return test_app


ERROR_CASES = [
    (NotFoundError, 404, "NOT_FOUND"),
    (UnauthorizedError, 401, "UNAUTHORIZED"),
    (ForbiddenError, 403, "FORBIDDEN"),
    (QuotaExceededError, 409, "QUOTA_EXCEEDED"),
    (ConflictError, 409, "CONFLICT"),
    (ValidationError, 422, "VALIDATION_ERROR"),
]


class TestErrorHierarchy:
    @pytest.mark.parametrize("error_cls,expected_status,expected_code", ERROR_CASES)
    async def test_error_status_and_code(self, error_cls, expected_status, expected_code):
        app = make_test_app(error_cls)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/raise/{error_cls.__name__.lower()}")

        assert response.status_code == expected_status
        body = response.json()
        assert "error" in body
        assert body["error"]["code"] == expected_code
        assert body["error"]["message"] == "test message"
        assert "request_id" in body["error"]

    @pytest.mark.parametrize("error_cls,expected_status,expected_code", ERROR_CASES)
    async def test_error_response_has_x_request_id_header(
        self, error_cls, expected_status, expected_code
    ):
        app = make_test_app(error_cls)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/raise/{error_cls.__name__.lower()}")

        assert "x-request-id" in response.headers

    async def test_request_id_in_body_matches_header(self):
        app = make_test_app(NotFoundError)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/raise/notfounderror")

        body = response.json()
        assert body["error"]["request_id"] == response.headers["x-request-id"]
