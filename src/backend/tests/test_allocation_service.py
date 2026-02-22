"""Tests for STORY-005: Hierarchical allocation API.

Covers:
- Server → Field assignment (center_admin gate, conflict, cascade block)
- Server removal (gate, cascade block)
- Server swap (atomic, gate, conflict)
- Department quota CRUD (field_admin gate, invariant, delta)
- Team quota CRUD (dept_admin gate, invariant, delta)
- Allocation tree (role-scoped visibility)
All tests mock the repository; no real DB required.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.auth.jwt import Claims
from app.errors import ConflictError, ForbiddenError, QuotaExceededError
from app.models.org import (
    DepartmentQuotaAllocation,
    FieldServerAllocation,
    TeamQuotaAllocation,
)
from app.services.allocation_service import AllocationService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _claims(role: str, scope_id: str | None = None) -> Claims:
    return Claims(sub="user", role=role, scope_id=scope_id, exp=9999999999)


def _make_server_alloc(server_id="srv-1", field_id="field-1") -> FieldServerAllocation:
    obj = MagicMock(spec=FieldServerAllocation)
    obj.id = "alloc-1"
    obj.server_id = server_id
    obj.field_id = field_id
    obj.allocated_by = "admin"
    return obj


def _make_dept_quota(
    id="dq-1",
    field_id="field-1",
    department_id="dept-1",
    site="berlin",
    cpu_limit=100,
    ram_gb_limit=200,
    cpu_used=10,
    ram_gb_used=20,
) -> DepartmentQuotaAllocation:
    obj = MagicMock(spec=DepartmentQuotaAllocation)
    obj.id = id
    obj.field_id = field_id
    obj.department_id = department_id
    obj.site = site
    obj.cpu_limit = cpu_limit
    obj.ram_gb_limit = ram_gb_limit
    obj.cpu_used = cpu_used
    obj.ram_gb_used = ram_gb_used
    return obj


def _make_team_quota(
    id="tq-1",
    department_id="dept-1",
    team_id="team-1",
    site="berlin",
    cpu_limit=40,
    ram_gb_limit=80,
    cpu_used=5,
    ram_gb_used=10,
) -> TeamQuotaAllocation:
    obj = MagicMock(spec=TeamQuotaAllocation)
    obj.id = id
    obj.department_id = department_id
    obj.team_id = team_id
    obj.site = site
    obj.cpu_limit = cpu_limit
    obj.ram_gb_limit = ram_gb_limit
    obj.cpu_used = cpu_used
    obj.ram_gb_used = ram_gb_used
    return obj


def _make_service() -> tuple[AllocationService, MagicMock]:
    """Return (service, mock_repo). Session.begin() returns a no-op async ctx."""
    session = MagicMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=None)
    ctx.__aexit__ = AsyncMock(return_value=False)
    session.begin = MagicMock(return_value=ctx)

    svc = AllocationService(session)
    mock_repo = AsyncMock()
    svc.repo = mock_repo
    return svc, mock_repo


# ---------------------------------------------------------------------------
# Server → Field assignment
# ---------------------------------------------------------------------------


class TestAssignServerToField:
    async def test_non_center_admin_is_forbidden(self):
        svc, _ = _make_service()
        with pytest.raises(ForbiddenError):
            await svc.assign_server_to_field(
                _claims("field_admin", "field-1"), "srv-1", "field-1"
            )

    async def test_platform_admin_can_assign_server(self):
        svc, repo = _make_service()
        alloc = _make_server_alloc()
        repo.get_server = AsyncMock()
        repo.get_field = AsyncMock()
        repo.create_server_allocation = AsyncMock(return_value=alloc)

        result = await svc.assign_server_to_field(
            _claims("platform_admin"), "srv-1", "field-1"
        )

        assert result.server_id == "srv-1"

    async def test_happy_path_returns_response(self):
        svc, repo = _make_service()
        alloc = _make_server_alloc()
        repo.get_server = AsyncMock()
        repo.get_field = AsyncMock()
        repo.create_server_allocation = AsyncMock(return_value=alloc)

        result = await svc.assign_server_to_field(
            _claims("center_admin"), "srv-1", "field-1"
        )

        assert result.server_id == "srv-1"
        assert result.field_id == "field-1"

    async def test_already_assigned_raises_conflict(self):
        svc, repo = _make_service()
        repo.get_server = AsyncMock()
        repo.get_field = AsyncMock()
        repo.create_server_allocation = AsyncMock(
            side_effect=ConflictError("already assigned")
        )

        with pytest.raises(ConflictError):
            await svc.assign_server_to_field(
                _claims("center_admin"), "srv-1", "field-1"
            )


# ---------------------------------------------------------------------------
# Server removal
# ---------------------------------------------------------------------------


class TestRemoveServerFromField:
    async def test_non_center_admin_is_forbidden(self):
        svc, _ = _make_service()
        with pytest.raises(ForbiddenError):
            await svc.remove_server_from_field(_claims("field_admin", "f-1"), "alloc-1")

    async def test_removal_blocked_when_dept_quotas_exist(self):
        svc, repo = _make_service()
        alloc = _make_server_alloc()
        repo.get_server_allocation_by_id = AsyncMock(return_value=alloc)
        repo.field_has_dept_quotas = AsyncMock(return_value=True)

        with pytest.raises(ConflictError, match="active department quota"):
            await svc.remove_server_from_field(_claims("center_admin"), "alloc-1")

    async def test_removal_succeeds_when_no_dept_quotas(self):
        svc, repo = _make_service()
        alloc = _make_server_alloc()
        repo.get_server_allocation_by_id = AsyncMock(return_value=alloc)
        repo.field_has_dept_quotas = AsyncMock(return_value=False)
        repo.delete_server_allocation = AsyncMock()

        await svc.remove_server_from_field(_claims("center_admin"), "alloc-1")

        repo.delete_server_allocation.assert_awaited_once_with(alloc)


# ---------------------------------------------------------------------------
# Server swap
# ---------------------------------------------------------------------------


class TestSwapServerBetweenFields:
    async def test_non_center_admin_is_forbidden(self):
        svc, _ = _make_service()
        with pytest.raises(ForbiddenError):
            await svc.swap_server_between_fields(
                _claims("field_admin", "f-1"), "srv-1", "field-1", "field-2"
            )

    async def test_swap_when_server_not_in_from_field_raises_conflict(self):
        svc, repo = _make_service()
        repo.get_field = AsyncMock()
        existing = _make_server_alloc(field_id="field-OTHER")
        repo.get_server_allocation = AsyncMock(return_value=existing)

        with pytest.raises(ConflictError, match="not currently assigned"):
            await svc.swap_server_between_fields(
                _claims("center_admin"), "srv-1", "field-1", "field-2"
            )

    async def test_swap_when_server_not_assigned_raises_conflict(self):
        svc, repo = _make_service()
        repo.get_field = AsyncMock()
        repo.get_server_allocation = AsyncMock(return_value=None)

        with pytest.raises(ConflictError):
            await svc.swap_server_between_fields(
                _claims("center_admin"), "srv-1", "field-1", "field-2"
            )

    async def test_happy_path_returns_new_allocation(self):
        svc, repo = _make_service()
        repo.get_field = AsyncMock()
        existing = _make_server_alloc(field_id="field-1")
        new_alloc = _make_server_alloc(field_id="field-2")
        repo.get_server_allocation = AsyncMock(return_value=existing)
        repo.delete_server_allocation = AsyncMock()
        repo.create_server_allocation = AsyncMock(return_value=new_alloc)

        result = await svc.swap_server_between_fields(
            _claims("center_admin"), "srv-1", "field-1", "field-2"
        )

        assert result.field_id == "field-2"
        repo.delete_server_allocation.assert_awaited_once_with(existing)


# ---------------------------------------------------------------------------
# Department quota creation
# ---------------------------------------------------------------------------


class TestCreateDeptQuota:
    async def test_wrong_role_is_forbidden(self):
        svc, _ = _make_service()
        with pytest.raises(ForbiddenError):
            await svc.create_dept_quota(
                _claims("dept_admin", "dept-1"),
                field_id="field-1",
                dept_id="dept-1",
                site="berlin",
                cpu_limit=10,
                ram_gb_limit=20,
            )

    async def test_wrong_scope_id_is_forbidden(self):
        svc, _ = _make_service()
        with pytest.raises(ForbiddenError):
            await svc.create_dept_quota(
                _claims("field_admin", "field-OTHER"),
                field_id="field-1",
                dept_id="dept-1",
                site="berlin",
                cpu_limit=10,
                ram_gb_limit=20,
            )

    async def test_duplicate_raises_conflict(self):
        svc, repo = _make_service()
        repo.get_dept_quota_for_update = AsyncMock(return_value=_make_dept_quota())

        with pytest.raises(ConflictError, match="already exists"):
            await svc.create_dept_quota(
                _claims("field_admin", "field-1"),
                field_id="field-1",
                dept_id="dept-1",
                site="berlin",
                cpu_limit=10,
                ram_gb_limit=20,
            )

    async def test_exceeding_cpu_raises_quota_exceeded(self):
        svc, repo = _make_service()
        repo.get_dept_quota_for_update = AsyncMock(return_value=None)
        repo.get_field_total_cpu_ram = AsyncMock(return_value=(50, 100))
        repo.get_dept_quota_sum_for_field_site = AsyncMock(return_value=(40, 0))

        with pytest.raises(QuotaExceededError, match="insufficient CPU"):
            await svc.create_dept_quota(
                _claims("field_admin", "field-1"),
                field_id="field-1",
                dept_id="dept-1",
                site="berlin",
                cpu_limit=20,  # 40 + 20 = 60 > 50
                ram_gb_limit=10,
            )

    async def test_exceeding_ram_raises_quota_exceeded(self):
        svc, repo = _make_service()
        repo.get_dept_quota_for_update = AsyncMock(return_value=None)
        repo.get_field_total_cpu_ram = AsyncMock(return_value=(100, 50))
        repo.get_dept_quota_sum_for_field_site = AsyncMock(return_value=(0, 40))

        with pytest.raises(QuotaExceededError, match="insufficient RAM"):
            await svc.create_dept_quota(
                _claims("field_admin", "field-1"),
                field_id="field-1",
                dept_id="dept-1",
                site="berlin",
                cpu_limit=10,
                ram_gb_limit=20,  # 40 + 20 = 60 > 50
            )

    async def test_happy_path_returns_quota(self):
        svc, repo = _make_service()
        dq = _make_dept_quota(cpu_limit=10, ram_gb_limit=20)
        repo.get_dept_quota_for_update = AsyncMock(return_value=None)
        repo.get_field_total_cpu_ram = AsyncMock(return_value=(100, 200))
        repo.get_dept_quota_sum_for_field_site = AsyncMock(return_value=(0, 0))
        repo.create_dept_quota = AsyncMock(return_value=dq)

        result = await svc.create_dept_quota(
            _claims("field_admin", "field-1"),
            field_id="field-1",
            dept_id="dept-1",
            site="berlin",
            cpu_limit=10,
            ram_gb_limit=20,
        )

        assert result.cpu_limit == 10
        assert result.ram_gb_limit == 20

    async def test_platform_admin_can_create_dept_quota_for_any_field(self):
        svc, repo = _make_service()
        dq = _make_dept_quota(cpu_limit=10, ram_gb_limit=20)
        repo.get_dept_quota_for_update = AsyncMock(return_value=None)
        repo.get_field_total_cpu_ram = AsyncMock(return_value=(100, 200))
        repo.get_dept_quota_sum_for_field_site = AsyncMock(return_value=(0, 0))
        repo.create_dept_quota = AsyncMock(return_value=dq)

        # platform_admin has no scope_id but can still create quotas for any field
        result = await svc.create_dept_quota(
            _claims("platform_admin"),
            field_id="field-any",
            dept_id="dept-1",
            site="berlin",
            cpu_limit=10,
            ram_gb_limit=20,
        )

        assert result.cpu_limit == 10


# ---------------------------------------------------------------------------
# Department quota update
# ---------------------------------------------------------------------------


class TestUpdateDeptQuota:
    async def test_wrong_role_is_forbidden(self):
        svc, repo = _make_service()
        dq = _make_dept_quota(field_id="field-1")
        repo.get_dept_quota_by_id = AsyncMock(return_value=dq)

        with pytest.raises(ForbiddenError):
            await svc.update_dept_quota(
                _claims("dept_admin", "dept-1"),
                quota_id="dq-1",
                cpu_limit=50,
                ram_gb_limit=100,
            )

    async def test_reducing_below_used_raises_quota_exceeded(self):
        svc, repo = _make_service()
        dq = _make_dept_quota(field_id="field-1", cpu_used=30, ram_gb_used=60)
        repo.get_dept_quota_by_id = AsyncMock(return_value=dq)
        repo.get_field_total_cpu_ram = AsyncMock(return_value=(100, 200))
        repo.get_dept_quota_sum_for_field_site = AsyncMock(return_value=(30, 60))

        with pytest.raises(QuotaExceededError, match="already in use"):
            await svc.update_dept_quota(
                _claims("field_admin", "field-1"),
                quota_id="dq-1",
                cpu_limit=20,  # < cpu_used=30
                ram_gb_limit=100,
            )

    async def test_increasing_beyond_field_raises_quota_exceeded(self):
        svc, repo = _make_service()
        # Field total: 100 CPU. Currently allocated (sum): 80.
        # Existing quota has cpu_limit=50. We try to raise to 80 → delta=+30.
        # 80 + 30 = 110 > 100 → fail.
        dq = _make_dept_quota(field_id="field-1", cpu_limit=50, cpu_used=5, ram_gb_used=0)
        repo.get_dept_quota_by_id = AsyncMock(return_value=dq)
        repo.get_field_total_cpu_ram = AsyncMock(return_value=(100, 200))
        repo.get_dept_quota_sum_for_field_site = AsyncMock(return_value=(80, 0))

        with pytest.raises(QuotaExceededError, match="enough CPU"):
            await svc.update_dept_quota(
                _claims("field_admin", "field-1"),
                quota_id="dq-1",
                cpu_limit=80,  # delta = +30; 80 + 30 = 110 > 100
                ram_gb_limit=200,
            )

    async def test_happy_path_updates_limits(self):
        svc, repo = _make_service()
        dq = _make_dept_quota(field_id="field-1", cpu_limit=50, ram_gb_limit=100,
                               cpu_used=5, ram_gb_used=10)
        repo.get_dept_quota_by_id = AsyncMock(return_value=dq)
        repo.get_field_total_cpu_ram = AsyncMock(return_value=(200, 400))
        repo.get_dept_quota_sum_for_field_site = AsyncMock(return_value=(50, 100))

        result = await svc.update_dept_quota(
            _claims("field_admin", "field-1"),
            quota_id="dq-1",
            cpu_limit=60,
            ram_gb_limit=120,
        )

        assert result.cpu_limit == 60
        assert result.ram_gb_limit == 120


# ---------------------------------------------------------------------------
# Team quota creation
# ---------------------------------------------------------------------------


class TestCreateTeamQuota:
    async def test_wrong_role_is_forbidden(self):
        svc, _ = _make_service()
        with pytest.raises(ForbiddenError):
            await svc.create_team_quota(
                _claims("field_admin", "field-1"),
                dept_id="dept-1",
                team_id="team-1",
                site="berlin",
                cpu_limit=10,
                ram_gb_limit=20,
            )

    async def test_wrong_dept_scope_is_forbidden(self):
        svc, _ = _make_service()
        with pytest.raises(ForbiddenError):
            await svc.create_team_quota(
                _claims("dept_admin", "dept-OTHER"),
                dept_id="dept-1",
                team_id="team-1",
                site="berlin",
                cpu_limit=10,
                ram_gb_limit=20,
            )

    async def test_duplicate_raises_conflict(self):
        svc, repo = _make_service()
        repo.get_team_quota_for_update = AsyncMock(return_value=_make_team_quota())

        with pytest.raises(ConflictError, match="already exists"):
            await svc.create_team_quota(
                _claims("dept_admin", "dept-1"),
                dept_id="dept-1",
                team_id="team-1",
                site="berlin",
                cpu_limit=10,
                ram_gb_limit=20,
            )

    async def test_no_dept_quota_raises_quota_exceeded(self):
        svc, repo = _make_service()
        repo.get_team_quota_for_update = AsyncMock(return_value=None)
        repo.get_dept_quota_for_update = AsyncMock(return_value=None)

        with pytest.raises(QuotaExceededError, match="No department quota"):
            await svc.create_team_quota(
                _claims("dept_admin", "dept-1"),
                dept_id="dept-1",
                team_id="team-1",
                site="berlin",
                cpu_limit=10,
                ram_gb_limit=20,
            )

    async def test_exceeding_dept_cpu_raises_quota_exceeded(self):
        svc, repo = _make_service()
        repo.get_team_quota_for_update = AsyncMock(return_value=None)
        dept_quota = _make_dept_quota(cpu_limit=50, ram_gb_limit=100)
        repo.get_dept_quota_for_update = AsyncMock(return_value=dept_quota)
        repo.get_team_quota_sum_for_dept_site = AsyncMock(return_value=(40, 0))

        with pytest.raises(QuotaExceededError, match="insufficient CPU"):
            await svc.create_team_quota(
                _claims("dept_admin", "dept-1"),
                dept_id="dept-1",
                team_id="team-1",
                site="berlin",
                cpu_limit=20,  # 40 + 20 = 60 > 50
                ram_gb_limit=10,
            )

    async def test_happy_path_returns_quota(self):
        svc, repo = _make_service()
        tq = _make_team_quota(cpu_limit=10, ram_gb_limit=20)
        repo.get_team_quota_for_update = AsyncMock(return_value=None)
        dept_quota = _make_dept_quota(cpu_limit=100, ram_gb_limit=200)
        repo.get_dept_quota_for_update = AsyncMock(return_value=dept_quota)
        repo.get_team_quota_sum_for_dept_site = AsyncMock(return_value=(0, 0))
        repo.create_team_quota = AsyncMock(return_value=tq)

        result = await svc.create_team_quota(
            _claims("dept_admin", "dept-1"),
            dept_id="dept-1",
            team_id="team-1",
            site="berlin",
            cpu_limit=10,
            ram_gb_limit=20,
        )

        assert result.cpu_limit == 10


# ---------------------------------------------------------------------------
# Team quota update
# ---------------------------------------------------------------------------


class TestUpdateTeamQuota:
    async def test_wrong_role_is_forbidden(self):
        svc, repo = _make_service()
        tq = _make_team_quota(department_id="dept-1")
        repo.get_team_quota_by_id = AsyncMock(return_value=tq)

        with pytest.raises(ForbiddenError):
            await svc.update_team_quota(
                _claims("field_admin", "field-1"),
                quota_id="tq-1",
                cpu_limit=20,
                ram_gb_limit=40,
            )

    async def test_reducing_below_used_raises_quota_exceeded(self):
        svc, repo = _make_service()
        tq = _make_team_quota(department_id="dept-1", cpu_limit=40, cpu_used=30, ram_gb_used=0)
        repo.get_team_quota_by_id = AsyncMock(return_value=tq)
        dept_quota = _make_dept_quota(cpu_limit=100, ram_gb_limit=200)
        repo.get_dept_quota_for_update = AsyncMock(return_value=dept_quota)
        repo.get_team_quota_sum_for_dept_site = AsyncMock(return_value=(40, 0))

        with pytest.raises(QuotaExceededError, match="already in use"):
            await svc.update_team_quota(
                _claims("dept_admin", "dept-1"),
                quota_id="tq-1",
                cpu_limit=20,  # < cpu_used=30
                ram_gb_limit=80,
            )

    async def test_happy_path_updates_limits(self):
        svc, repo = _make_service()
        tq = _make_team_quota(department_id="dept-1", cpu_limit=40, ram_gb_limit=80,
                               cpu_used=5, ram_gb_used=10)
        repo.get_team_quota_by_id = AsyncMock(return_value=tq)
        dept_quota = _make_dept_quota(cpu_limit=200, ram_gb_limit=400)
        repo.get_dept_quota_for_update = AsyncMock(return_value=dept_quota)
        repo.get_team_quota_sum_for_dept_site = AsyncMock(return_value=(40, 80))

        result = await svc.update_team_quota(
            _claims("dept_admin", "dept-1"),
            quota_id="tq-1",
            cpu_limit=50,
            ram_gb_limit=100,
        )

        assert result.cpu_limit == 50
        assert result.ram_gb_limit == 100


# ---------------------------------------------------------------------------
# Allocation tree — layer-violation regression (fields must come from repo)
# ---------------------------------------------------------------------------


def _make_center(id: str = "c1", name: str = "HQ"):
    obj = MagicMock()
    obj.id = id
    obj.name = name
    return obj


def _make_field(id: str, name: str = "Berlin", site: str = "berlin"):
    obj = MagicMock()
    obj.id = id
    obj.name = name
    obj.site = site
    return obj


class TestGetAllocationTreeFieldsAreFromRepo:
    """Verify the layer fix: get_allocation_tree fetches fields via repo.get_fields_for_center,
    not via raw session.execute."""

    async def test_repo_get_fields_for_center_is_called(self):
        svc, repo = _make_service()
        repo.get_full_tree = AsyncMock(return_value=[_make_center(id="c1", name="HQ")])
        repo.get_fields_for_center = AsyncMock(return_value=[_make_field(id="f1")])
        repo.get_servers_for_field = AsyncMock(return_value=[])
        repo.get_dept_quotas_for_field = AsyncMock(return_value=[])

        result = await svc.get_allocation_tree(_claims("center_admin"))

        repo.get_fields_for_center.assert_awaited_once_with("c1")
        assert len(result.centers) == 1
        assert len(result.centers[0].fields) == 1
        assert result.centers[0].fields[0].field_id == "f1"

    async def test_center_appears_with_empty_fields_for_center_admin(self):
        """center_admin sees centers even when they have no fields."""
        svc, repo = _make_service()
        repo.get_full_tree = AsyncMock(return_value=[_make_center(id="c1", name="HQ")])
        repo.get_fields_for_center = AsyncMock(return_value=[])
        repo.get_servers_for_field = AsyncMock(return_value=[])
        repo.get_dept_quotas_for_field = AsyncMock(return_value=[])

        result = await svc.get_allocation_tree(_claims("center_admin"))

        assert len(result.centers) == 1
        assert len(result.centers[0].fields) == 0


class TestGetAllocationTreeScopedVisibility:
    """Verify field_admin only sees the field matching their scope_id after the repo refactor."""

    async def test_field_admin_sees_only_own_field(self):
        svc, repo = _make_service()
        repo.get_full_tree = AsyncMock(return_value=[_make_center(id="c1")])
        repo.get_fields_for_center = AsyncMock(
            return_value=[_make_field(id="f1"), _make_field(id="f2")]
        )
        repo.get_servers_for_field = AsyncMock(return_value=[])
        repo.get_dept_quotas_for_field = AsyncMock(return_value=[])

        result = await svc.get_allocation_tree(_claims("field_admin", scope_id="f1"))

        assert len(result.centers[0].fields) == 1
        assert result.centers[0].fields[0].field_id == "f1"

    async def test_field_admin_with_wrong_scope_sees_no_fields(self):
        """field_admin whose scope_id matches no field gets an empty fields list."""
        svc, repo = _make_service()
        repo.get_full_tree = AsyncMock(return_value=[_make_center(id="c1")])
        repo.get_fields_for_center = AsyncMock(
            return_value=[_make_field(id="f1"), _make_field(id="f2")]
        )
        repo.get_servers_for_field = AsyncMock(return_value=[])
        repo.get_dept_quotas_for_field = AsyncMock(return_value=[])

        result = await svc.get_allocation_tree(_claims("field_admin", scope_id="f-other"))

        assert len(result.centers) == 0

    async def test_platform_admin_sees_all_fields(self):
        """platform_admin with no scope_id sees every field in every center."""
        svc, repo = _make_service()
        repo.get_full_tree = AsyncMock(return_value=[_make_center(id="c1")])
        repo.get_fields_for_center = AsyncMock(
            return_value=[_make_field(id="f1"), _make_field(id="f2")]
        )
        repo.get_servers_for_field = AsyncMock(return_value=[])
        repo.get_dept_quotas_for_field = AsyncMock(return_value=[])

        result = await svc.get_allocation_tree(_claims("platform_admin"))

        assert len(result.centers) == 1
        assert len(result.centers[0].fields) == 2

    async def test_platform_admin_center_appears_with_empty_fields(self):
        """platform_admin sees centers even when they have no fields (same as center_admin)."""
        svc, repo = _make_service()
        repo.get_full_tree = AsyncMock(return_value=[_make_center(id="c1")])
        repo.get_fields_for_center = AsyncMock(return_value=[])
        repo.get_servers_for_field = AsyncMock(return_value=[])
        repo.get_dept_quotas_for_field = AsyncMock(return_value=[])

        result = await svc.get_allocation_tree(_claims("platform_admin"))

        assert len(result.centers) == 1
        assert len(result.centers[0].fields) == 0
