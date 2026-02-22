"""Tests for STORY-003: LDAP auth + JWT middleware.

Uses MockLDAPClient to avoid a real LDAP server.
Covers: successful login, wrong password (401), no group (403),
        expired token (401), valid token decoding, get_current_user.
"""

import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import get_current_user
from app.auth.jwt import Claims, build_claims, create_token, verify_token
from app.auth.ldap_client import LDAPClient
from app.database import get_db
from app.errors import UnauthorizedError
from app.main import app
from app.models.org import UserRole
from app.routers.auth import get_ldap_client

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


class MockLDAPClient(LDAPClient):
    def __init__(self, groups: list[str], should_fail: bool = False) -> None:
        self._groups = groups
        self._should_fail = should_fail

    async def authenticate(self, username: str, password: str) -> list[str]:
        if self._should_fail:
            raise UnauthorizedError("Invalid credentials")
        return self._groups


def _mock_db_session(db_role_row: UserRole | None = None):
    """Return an async generator that yields a mock session.

    The mock session's execute() returns a result whose scalar_one_or_none()
    returns db_role_row (None = no DB override; a UserRole = DB override wins).
    """
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=db_role_row)
    session = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)

    async def _get_db():
        yield session

    return _get_db


def make_client(ldap: LDAPClient, db_role_row: UserRole | None = None) -> AsyncClient:
    app.dependency_overrides[get_ldap_client] = lambda: ldap
    app.dependency_overrides[get_db] = _mock_db_session(db_role_row)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Login endpoint
# ---------------------------------------------------------------------------


class TestLogin:
    async def test_successful_login_returns_token(self):
        ldap = MockLDAPClient(groups=["infrahub-center-admins"])
        async with make_client(ldap) as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"username": "alice", "password": "secret"},
            )

        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert body["expires_in"] == 900

    async def test_wrong_password_returns_401(self):
        ldap = MockLDAPClient(groups=[], should_fail=True)
        async with make_client(ldap) as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"username": "alice", "password": "wrong"},
            )

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "UNAUTHORIZED"

    async def test_no_infrahub_group_returns_403(self):
        ldap = MockLDAPClient(groups=["some-other-group", "another-group"])
        async with make_client(ldap) as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"username": "alice", "password": "secret"},
            )

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "FORBIDDEN"

    async def test_field_admin_login_returns_correct_role(self):
        field_id = "field-uuid-123"
        ldap = MockLDAPClient(groups=[f"infrahub-field-admins-{field_id}"])
        async with make_client(ldap) as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"username": "bob", "password": "secret"},
            )

        assert response.status_code == 200
        claims = verify_token(response.json()["access_token"])
        assert claims.role == "field_admin"
        assert claims.scope_id == field_id

    async def test_team_lead_login_returns_correct_role(self):
        team_id = "team-uuid-456"
        ldap = MockLDAPClient(groups=[f"infrahub-team-leads-{team_id}"])
        async with make_client(ldap) as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"username": "carol", "password": "secret"},
            )

        assert response.status_code == 200
        claims = verify_token(response.json()["access_token"])
        assert claims.role == "team_lead"
        assert claims.scope_id == team_id

    async def test_center_admin_has_null_scope_id(self):
        ldap = MockLDAPClient(groups=["infrahub-center-admins"])
        async with make_client(ldap) as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "secret"},
            )

        claims = verify_token(response.json()["access_token"])
        assert claims.role == "center_admin"
        assert claims.scope_id is None

    async def test_platform_admin_login_via_ldap_group(self):
        ldap = MockLDAPClient(groups=["infrahub-platform-admins"])
        async with make_client(ldap) as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"username": "superadmin", "password": "secret"},
            )

        assert response.status_code == 200
        claims = verify_token(response.json()["access_token"])
        assert claims.role == "platform_admin"
        assert claims.scope_id is None

    async def test_platform_admin_wins_over_center_admin_ldap_group(self):
        """When both platform-admins and center-admins groups are present, platform_admin wins."""
        ldap = MockLDAPClient(groups=["infrahub-platform-admins", "infrahub-center-admins"])
        async with make_client(ldap) as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"username": "superadmin", "password": "secret"},
            )

        claims = verify_token(response.json()["access_token"])
        assert claims.role == "platform_admin"

    async def test_db_role_override_wins_over_ldap_groups(self):
        """DB role override takes precedence over LDAP group membership."""
        db_row = MagicMock(spec=UserRole)
        db_row.role = "field_admin"
        db_row.scope_id = "field-xyz"

        # User has center-admins in LDAP but DB says field_admin — DB should win.
        ldap = MockLDAPClient(groups=["infrahub-center-admins"])
        async with make_client(ldap, db_role_row=db_row) as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"username": "carol", "password": "secret"},
            )

        assert response.status_code == 200
        claims = verify_token(response.json()["access_token"])
        assert claims.role == "field_admin"
        assert claims.scope_id == "field-xyz"


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------


class TestJWT:
    def test_create_and_verify_token_roundtrip(self):
        claims = build_claims(sub="alice", role="center_admin", scope_id=None)
        token = create_token(claims)
        decoded = verify_token(token)
        assert decoded.sub == "alice"
        assert decoded.role == "center_admin"
        assert decoded.scope_id is None

    def test_verify_expired_token_raises_unauthorized(self):
        expired_claims = Claims(
            sub="alice", role="center_admin", scope_id=None,
            exp=int(time.time()) - 1,
        )
        token = create_token(expired_claims)
        with pytest.raises(UnauthorizedError, match="expired"):
            verify_token(token)

    def test_verify_garbage_token_raises_unauthorized(self):
        with pytest.raises(UnauthorizedError):
            verify_token("not.a.valid.jwt")

    def test_token_expiry_is_15_minutes(self):
        before = int(time.time())
        claims = build_claims(sub="x", role="center_admin", scope_id=None)
        after = int(time.time())
        assert before + 900 <= claims.exp <= after + 900


# ---------------------------------------------------------------------------
# get_current_user dependency
# ---------------------------------------------------------------------------


class TestGetCurrentUser:
    async def test_missing_token_raises_unauthorized(self):
        with pytest.raises(UnauthorizedError):
            await get_current_user(credentials=None)

    async def test_valid_token_returns_claims(self):
        from fastapi.security import HTTPAuthorizationCredentials

        claims = build_claims(sub="alice", role="center_admin", scope_id=None)
        token = create_token(claims)
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        result = await get_current_user(credentials=creds)
        assert result.sub == "alice"
        assert result.role == "center_admin"
