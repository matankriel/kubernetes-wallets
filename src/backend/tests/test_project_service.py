"""Tests for STORY-006: Project provisioning service.

All tests mock the repository, HelmProvisioner, and ArgoCD. No real DB or
network required.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.auth.jwt import Claims
from app.errors import ForbiddenError, QuotaExceededError
from app.helm.provisioner import make_namespace_name
from app.models.org import TeamQuotaAllocation
from app.models.project import Project
from app.services.project_service import ProjectService, _get_quota

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _claims(role: str, scope_id: str | None = None) -> Claims:
    return Claims(sub="user", role=role, scope_id=scope_id, exp=9999999999)


def _make_quota(
    team_id="team-1",
    site="berlin",
    cpu_limit=20,
    ram_gb_limit=40,
    cpu_used=0,
    ram_gb_used=0,
) -> TeamQuotaAllocation:
    obj = MagicMock(spec=TeamQuotaAllocation)
    obj.team_id = team_id
    obj.site = site
    obj.cpu_limit = cpu_limit
    obj.ram_gb_limit = ram_gb_limit
    obj.cpu_used = cpu_used
    obj.ram_gb_used = ram_gb_used
    return obj


def _make_project(
    id="proj-1",
    team_id="team-1",
    name="my-project",
    site="berlin",
    sla_type="bronze",
    performance_tier="regular",
    namespace_name="team-1-my-project",
    status="provisioning",
    quota_cpu=2,
    quota_ram_gb=4,
) -> Project:
    obj = MagicMock(spec=Project)
    obj.id = id
    obj.team_id = team_id
    obj.name = name
    obj.site = site
    obj.sla_type = sla_type
    obj.performance_tier = performance_tier
    obj.namespace_name = namespace_name
    obj.status = status
    obj.quota_cpu = quota_cpu
    obj.quota_ram_gb = quota_ram_gb
    obj.deleted_at = None
    return obj


def _make_service() -> tuple[ProjectService, MagicMock, MagicMock]:
    session = MagicMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=None)
    ctx.__aexit__ = AsyncMock(return_value=False)
    session.begin = MagicMock(return_value=ctx)

    mock_provisioner = AsyncMock()
    mock_provisioner.provision = AsyncMock()
    mock_provisioner.deprovision = AsyncMock()

    mock_http = AsyncMock()
    mock_session_factory = MagicMock()

    svc = ProjectService(
        session=session,
        provisioner=mock_provisioner,
        http_client=mock_http,
        session_factory=mock_session_factory,
    )
    mock_repo = AsyncMock()
    svc.repo = mock_repo
    return svc, mock_repo, mock_provisioner


# ---------------------------------------------------------------------------
# SLA quota mapping
# ---------------------------------------------------------------------------


class TestGetQuota:
    def test_bronze_regular(self):
        assert _get_quota("bronze", "regular") == (2, 4)

    def test_bronze_high_performance(self):
        assert _get_quota("bronze", "high_performance") == (4, 8)

    def test_silver_regular(self):
        assert _get_quota("silver", "regular") == (4, 16)

    def test_silver_high_performance(self):
        assert _get_quota("silver", "high_performance") == (8, 32)

    def test_gold_regular(self):
        assert _get_quota("gold", "regular") == (8, 32)

    def test_gold_high_performance(self):
        assert _get_quota("gold", "high_performance") == (16, 64)


# ---------------------------------------------------------------------------
# Namespace name generation
# ---------------------------------------------------------------------------


class TestMakeNamespaceName:
    def test_basic_name(self):
        result = make_namespace_name("team-1", "my-project")
        assert result == "team-1-my-project"

    def test_uppercase_is_lowercased(self):
        result = make_namespace_name("TEAM", "MyProject")
        assert result == result.lower()

    def test_special_chars_replaced_with_hyphen(self):
        result = make_namespace_name("team_1", "my project!")
        assert " " not in result
        assert "_" not in result
        assert "!" not in result

    def test_max_63_chars(self):
        long_team = "a" * 40
        long_name = "b" * 40
        result = make_namespace_name(long_team, long_name)
        assert len(result) <= 63

    def test_no_leading_or_trailing_hyphens(self):
        result = make_namespace_name("-team-", "-name-")
        assert not result.startswith("-")
        assert not result.endswith("-")


# ---------------------------------------------------------------------------
# Project creation
# ---------------------------------------------------------------------------


class TestCreateProject:
    async def test_non_team_lead_is_forbidden(self):
        svc, _, _ = _make_service()
        with pytest.raises(ForbiddenError):
            await svc.create_project(
                _claims("field_admin", "field-1"),
                name="proj",
                site="berlin",
                sla_type="bronze",
                performance_tier="regular",
            )

    async def test_no_quota_raises_quota_exceeded(self):
        svc, repo, _ = _make_service()
        repo.get_team_quota_for_update = AsyncMock(return_value=None)

        with pytest.raises(QuotaExceededError, match="No team quota"):
            await svc.create_project(
                _claims("team_lead", "team-1"),
                name="proj",
                site="berlin",
                sla_type="bronze",
                performance_tier="regular",
            )

    async def test_cpu_exceeded_raises_quota_exceeded(self):
        svc, repo, _ = _make_service()
        quota = _make_quota(cpu_limit=2, cpu_used=2)  # 2 + 2 > 2
        repo.get_team_quota_for_update = AsyncMock(return_value=quota)

        with pytest.raises(QuotaExceededError, match="CPU"):
            await svc.create_project(
                _claims("team_lead", "team-1"),
                name="proj",
                site="berlin",
                sla_type="bronze",  # needs 2 CPU
                performance_tier="regular",
            )

    async def test_ram_exceeded_raises_quota_exceeded(self):
        svc, repo, _ = _make_service()
        # CPU is fine but RAM is tight
        quota = _make_quota(cpu_limit=100, ram_gb_limit=4, cpu_used=0, ram_gb_used=4)
        repo.get_team_quota_for_update = AsyncMock(return_value=quota)

        with pytest.raises(QuotaExceededError, match="RAM"):
            await svc.create_project(
                _claims("team_lead", "team-1"),
                name="proj",
                site="berlin",
                sla_type="bronze",  # needs 4 GB
                performance_tier="regular",
            )

    async def test_happy_path_returns_response(self):
        svc, repo, _ = _make_service()
        quota = _make_quota(cpu_limit=20, ram_gb_limit=40)
        project = _make_project()
        repo.get_team_quota_for_update = AsyncMock(return_value=quota)
        repo.create_project = AsyncMock(return_value=project)

        result = await svc.create_project(
            _claims("team_lead", "team-1"),
            name="my-project",
            site="berlin",
            sla_type="bronze",
            performance_tier="regular",
        )

        assert result.id == "proj-1"
        assert result.status == "provisioning"

    async def test_happy_path_updates_quota_usage(self):
        svc, repo, _ = _make_service()
        quota = _make_quota(cpu_limit=20, ram_gb_limit=40, cpu_used=0, ram_gb_used=0)
        project = _make_project(quota_cpu=2, quota_ram_gb=4)
        repo.get_team_quota_for_update = AsyncMock(return_value=quota)
        repo.create_project = AsyncMock(return_value=project)

        await svc.create_project(
            _claims("team_lead", "team-1"),
            name="my-project",
            site="berlin",
            sla_type="bronze",
            performance_tier="regular",
        )

        # quota mock attributes are settable — verify increments applied
        assert quota.cpu_used == 2
        assert quota.ram_gb_used == 4


# ---------------------------------------------------------------------------
# Project listing
# ---------------------------------------------------------------------------


class TestListProjects:
    async def test_team_lead_only_sees_own_projects(self):
        svc, repo, _ = _make_service()
        repo.list_projects = AsyncMock(return_value=[_make_project()])

        await svc.list_projects(_claims("team_lead", "team-1"))

        repo.list_projects.assert_awaited_once_with(team_id="team-1")

    async def test_center_admin_sees_all_projects(self):
        svc, repo, _ = _make_service()
        repo.list_projects = AsyncMock(return_value=[])

        await svc.list_projects(_claims("center_admin"))

        repo.list_projects.assert_awaited_once_with()


# ---------------------------------------------------------------------------
# Project deletion
# ---------------------------------------------------------------------------


class TestDeleteProject:
    async def test_non_team_lead_is_forbidden(self):
        svc, _, _ = _make_service()
        with pytest.raises(ForbiddenError):
            await svc.delete_project(_claims("field_admin", "field-1"), "proj-1")

    async def test_wrong_team_is_forbidden(self):
        svc, repo, _ = _make_service()
        project = _make_project(team_id="team-OTHER")
        repo.get_by_id_for_update = AsyncMock(return_value=project)

        with pytest.raises(ForbiddenError, match="different team"):
            await svc.delete_project(_claims("team_lead", "team-1"), "proj-1")
