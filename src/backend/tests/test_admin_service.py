"""Tests for STORY-009: AdminService — user role management and org CRUD.

All tests mock the repositories; no real DB required.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.auth.jwt import Claims
from app.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models.org import Center, Department, Field, Team, UserRole
from app.services.admin_service import AdminService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _claims(role: str, scope_id: str | None = None, sub: str = "admin") -> Claims:
    return Claims(sub=sub, role=role, scope_id=scope_id, exp=9999999999)


def _make_user_role(
    username: str = "alice",
    role: str = "field_admin",
    scope_id: str | None = "field-1",
    assigned_by: str = "admin",
) -> UserRole:
    obj = MagicMock(spec=UserRole)
    obj.id = "ur-1"
    obj.username = username
    obj.role = role
    obj.scope_id = scope_id
    obj.assigned_by = assigned_by
    obj.assigned_at = None
    return obj


def _make_center(id: str = "c-1", name: str = "HQ East") -> Center:
    obj = MagicMock(spec=Center)
    obj.id = id
    obj.name = name
    return obj


def _make_field(
    id: str = "f-1", center_id: str = "c-1", name: str = "Berlin", site: str = "berlin"
) -> Field:
    obj = MagicMock(spec=Field)
    obj.id = id
    obj.center_id = center_id
    obj.name = name
    obj.site = site
    return obj


def _make_dept(id: str = "d-1", field_id: str = "f-1", name: str = "Engineering") -> Department:
    obj = MagicMock(spec=Department)
    obj.id = id
    obj.field_id = field_id
    obj.name = name
    return obj


def _make_team(
    id: str = "t-1",
    department_id: str = "d-1",
    name: str = "Platform",
    ldap_group_cn: str | None = None,
) -> Team:
    obj = MagicMock(spec=Team)
    obj.id = id
    obj.department_id = department_id
    obj.name = name
    obj.ldap_group_cn = ldap_group_cn
    return obj


def _make_service() -> tuple[AdminService, MagicMock, MagicMock]:
    """Return (service, mock_repo, mock_user_role_repo)."""
    session = MagicMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=None)
    ctx.__aexit__ = AsyncMock(return_value=False)
    session.begin = MagicMock(return_value=ctx)

    svc = AdminService(session)
    mock_repo = AsyncMock()
    mock_ur_repo = AsyncMock()
    svc.repo = mock_repo
    svc.user_role_repo = mock_ur_repo
    return svc, mock_repo, mock_ur_repo


# ---------------------------------------------------------------------------
# User role management
# ---------------------------------------------------------------------------


class TestUpsertUserRole:
    async def test_non_super_admin_is_forbidden(self):
        svc, _, _ = _make_service()
        with pytest.raises(ForbiddenError):
            await svc.upsert_user_role(_claims("field_admin", "f-1"), "bob", "field_admin", "f-1")

    async def test_center_admin_can_upsert(self):
        svc, _, ur_repo = _make_service()
        ur_repo.upsert_user_role = AsyncMock(return_value=_make_user_role())

        result = await svc.upsert_user_role(_claims("center_admin"), "alice", "field_admin", "f-1")

        assert result.username == "alice"
        ur_repo.upsert_user_role.assert_awaited_once()

    async def test_platform_admin_can_upsert(self):
        svc, _, ur_repo = _make_service()
        ur_repo.upsert_user_role = AsyncMock(return_value=_make_user_role())

        result = await svc.upsert_user_role(
            _claims("platform_admin"), "alice", "field_admin", "f-1"
        )

        assert result.role == "field_admin"

    async def test_invalid_role_raises_validation_error(self):
        svc, _, _ = _make_service()
        with pytest.raises(ValidationError):
            await svc.upsert_user_role(_claims("center_admin"), "alice", "center_admin", None)

    async def test_unknown_role_raises_validation_error(self):
        svc, _, _ = _make_service()
        with pytest.raises(ValidationError):
            await svc.upsert_user_role(_claims("center_admin"), "alice", "super_user", None)


class TestDeleteUserRole:
    async def test_cannot_revoke_own_role(self):
        svc, _, _ = _make_service()
        with pytest.raises(ForbiddenError, match="own role"):
            await svc.delete_user_role(_claims("center_admin", sub="alice"), username="alice")

    async def test_not_found_raises_not_found(self):
        svc, _, ur_repo = _make_service()
        ur_repo.get_by_username = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await svc.delete_user_role(_claims("center_admin", sub="admin"), username="bob")

    async def test_happy_path_deletes_role(self):
        svc, _, ur_repo = _make_service()
        row = _make_user_role(username="bob")
        ur_repo.get_by_username = AsyncMock(return_value=row)
        ur_repo.delete = AsyncMock()

        await svc.delete_user_role(_claims("center_admin", sub="admin"), username="bob")

        ur_repo.delete.assert_awaited_once_with(row)

    async def test_non_super_admin_is_forbidden(self):
        svc, _, _ = _make_service()
        with pytest.raises(ForbiddenError):
            await svc.delete_user_role(_claims("dept_admin", "d-1"), username="bob")


# ---------------------------------------------------------------------------
# Org CRUD
# ---------------------------------------------------------------------------


class TestCreateCenter:
    async def test_non_super_admin_is_forbidden(self):
        svc, _, _ = _make_service()
        with pytest.raises(ForbiddenError):
            await svc.create_center(_claims("team_lead", "t-1"), "NewCenter")

    async def test_happy_path_returns_center_response(self):
        svc, repo, _ = _make_service()
        repo.create_center = AsyncMock(return_value=_make_center(name="NewCenter"))

        result = await svc.create_center(_claims("platform_admin"), "NewCenter")

        assert result.name == "NewCenter"


class TestDeleteCenter:
    async def test_delete_center_with_fields_raises_conflict(self):
        svc, repo, _ = _make_service()
        repo.get_center = AsyncMock(return_value=_make_center())
        repo.center_has_fields = AsyncMock(return_value=True)

        with pytest.raises(ConflictError, match="fields still exist"):
            await svc.delete_center(_claims("center_admin"), "c-1")

    async def test_delete_center_without_fields_succeeds(self):
        svc, repo, _ = _make_service()
        center = _make_center()
        repo.get_center = AsyncMock(return_value=center)
        repo.center_has_fields = AsyncMock(return_value=False)
        repo.delete_center = AsyncMock()

        await svc.delete_center(_claims("center_admin"), "c-1")

        repo.delete_center.assert_awaited_once_with(center)


class TestDeleteField:
    async def test_delete_field_with_departments_raises_conflict(self):
        svc, repo, _ = _make_service()
        repo.get_field = AsyncMock(return_value=_make_field())
        repo.field_has_departments = AsyncMock(return_value=True)

        with pytest.raises(ConflictError, match="departments still exist"):
            await svc.delete_field(_claims("center_admin"), "f-1")


class TestDeleteDepartment:
    async def test_delete_dept_with_teams_raises_conflict(self):
        svc, repo, _ = _make_service()
        repo.get_dept = AsyncMock(return_value=_make_dept())
        repo.department_has_teams = AsyncMock(return_value=True)

        with pytest.raises(ConflictError, match="teams still exist"):
            await svc.delete_department(_claims("center_admin"), "d-1")


class TestDeleteTeam:
    async def test_delete_team_with_projects_raises_conflict(self):
        svc, repo, _ = _make_service()
        repo.get_team = AsyncMock(return_value=_make_team())
        repo.team_has_projects = AsyncMock(return_value=True)

        with pytest.raises(ConflictError, match="active projects"):
            await svc.delete_team(_claims("center_admin"), "t-1")

    async def test_delete_team_without_projects_succeeds(self):
        svc, repo, _ = _make_service()
        team = _make_team()
        repo.get_team = AsyncMock(return_value=team)
        repo.team_has_projects = AsyncMock(return_value=False)
        repo.delete_team = AsyncMock()

        await svc.delete_team(_claims("center_admin"), "t-1")

        repo.delete_team.assert_awaited_once_with(team)


class TestCreateField:
    async def test_raises_not_found_if_center_missing(self):
        svc, repo, _ = _make_service()
        repo.get_center = AsyncMock(side_effect=NotFoundError("Center not found"))

        with pytest.raises(NotFoundError):
            await svc.create_field(_claims("platform_admin"), "c-999", "Berlin", "berlin")
