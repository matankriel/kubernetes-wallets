"""Project service — business logic for project (namespace) provisioning.

SLA → resource quota mapping:
  bronze/regular  → 2 CPU / 4 GB RAM
  bronze/hp       → 4 CPU / 8 GB RAM
  silver/regular  → 4 CPU / 16 GB RAM
  silver/hp       → 8 CPU / 32 GB RAM
  gold/regular    → 8 CPU / 32 GB RAM
  gold/hp         → 16 CPU / 64 GB RAM

The allocation invariant is checked before creating the project:
  team.cpu_used + required_cpu <= team.cpu_limit
"""

import asyncio
import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import Claims
from app.errors import ForbiddenError, NotFoundError, QuotaExceededError
from app.helm.provisioner import (
    HelmProvisioner,
    make_namespace_name,
    poll_argocd_until_synced,
)
from app.repositories.project_repo import ProjectRepository
from app.schemas.project import ProjectResponse

log = logging.getLogger(__name__)

# SLA type → performance_tier → (cpu, ram_gb)
_SLA_QUOTA: dict[str, dict[str, tuple[int, int]]] = {
    "bronze": {"regular": (2, 4), "high_performance": (4, 8)},
    "silver": {"regular": (4, 16), "high_performance": (8, 32)},
    "gold": {"regular": (8, 32), "high_performance": (16, 64)},
}


def _get_quota(sla_type: str, performance_tier: str) -> tuple[int, int]:
    return _SLA_QUOTA[sla_type][performance_tier]


class ProjectService:
    def __init__(
        self,
        session: AsyncSession,
        provisioner: HelmProvisioner,
        http_client: httpx.AsyncClient,
        session_factory,
    ) -> None:
        self.repo = ProjectRepository(session)
        self.session = session
        self._provisioner = provisioner
        self._http_client = http_client
        self._session_factory = session_factory

    async def create_project(
        self,
        claims: Claims,
        name: str,
        site: str,
        sla_type: str,
        performance_tier: str,
    ) -> ProjectResponse:
        if claims.role != "team_lead":
            raise ForbiddenError("Only team_lead can create projects")

        team_id = claims.scope_id
        required_cpu, required_ram = _get_quota(sla_type, performance_tier)
        namespace_name = make_namespace_name(team_id, name)

        async with self.session.begin():
            quota = await self.repo.get_team_quota_for_update(team_id, site)
            if quota is None:
                raise QuotaExceededError(
                    f"No team quota found for team '{team_id}' at site '{site}'"
                )

            if quota.cpu_used + required_cpu > quota.cpu_limit:
                raise QuotaExceededError(
                    f"Team quota exceeded: need {required_cpu} CPU, "
                    f"available {quota.cpu_limit - quota.cpu_used}"
                )
            if quota.ram_gb_used + required_ram > quota.ram_gb_limit:
                raise QuotaExceededError(
                    f"Team quota exceeded: need {required_ram} GB RAM, "
                    f"available {quota.ram_gb_limit - quota.ram_gb_used}"
                )

            project = await self.repo.create_project(
                team_id=team_id,
                name=name,
                site=site,
                sla_type=sla_type,
                performance_tier=performance_tier,
                namespace_name=namespace_name,
                quota_cpu=required_cpu,
                quota_ram_gb=required_ram,
            )

            quota.cpu_used += required_cpu
            quota.ram_gb_used += required_ram

        # Provision asynchronously — do not block the HTTP response
        asyncio.create_task(self._provision_and_poll(project.id))

        return ProjectResponse.model_validate(project)

    async def _provision_and_poll(self, project_id: str) -> None:
        try:
            async with self._session_factory() as session:
                repo = ProjectRepository(session)
                project = await repo.get_by_id(project_id)
            await self._provisioner.provision(project)
        except Exception:
            log.exception("Provisioning failed for project %s", project_id)
            await self._rollback_quota_and_fail(project_id)
            return

        asyncio.create_task(
            poll_argocd_until_synced(
                self._http_client, project_id, self._session_factory
            )
        )

    async def _rollback_quota_and_fail(self, project_id: str) -> None:
        from sqlalchemy import select

        from app.models.org import TeamQuotaAllocation

        try:
            async with self._session_factory() as session:
                async with session.begin():
                    repo = ProjectRepository(session)
                    project = await repo.get_by_id_for_update(project_id)
                    if project.quota_cpu and project.quota_ram_gb:
                        result = await session.execute(
                            select(TeamQuotaAllocation)
                            .where(
                                TeamQuotaAllocation.team_id == project.team_id,
                                TeamQuotaAllocation.site == project.site,
                            )
                            .with_for_update()
                        )
                        quota = result.scalar_one_or_none()
                        if quota:
                            quota.cpu_used = max(0, quota.cpu_used - project.quota_cpu)
                            quota.ram_gb_used = max(
                                0, quota.ram_gb_used - project.quota_ram_gb
                            )
                    project.status = "failed"
        except Exception:
            log.exception("Failed to rollback quota for project %s", project_id)

    async def get_project(self, claims: Claims, project_id: str) -> ProjectResponse:
        project = await self.repo.get_by_id(project_id)
        self._assert_can_view(claims, project)
        return ProjectResponse.model_validate(project)

    async def list_projects(self, claims: Claims) -> list[ProjectResponse]:
        if claims.role == "team_lead":
            projects = await self.repo.list_projects(team_id=claims.scope_id)
        else:
            projects = await self.repo.list_projects()
        return [ProjectResponse.model_validate(p) for p in projects]

    async def delete_project(self, claims: Claims, project_id: str) -> None:
        if claims.role != "team_lead":
            raise ForbiddenError("Only team_lead can delete projects")

        async with self.session.begin():
            project = await self.repo.get_by_id_for_update(project_id)
            if project.team_id != claims.scope_id:
                raise ForbiddenError("Project belongs to a different team")

            from sqlalchemy import select

            from app.models.org import TeamQuotaAllocation

            if project.quota_cpu and project.site:
                result = await self.session.execute(
                    select(TeamQuotaAllocation)
                    .where(
                        TeamQuotaAllocation.team_id == project.team_id,
                        TeamQuotaAllocation.site == project.site,
                    )
                    .with_for_update()
                )
                quota = result.scalar_one_or_none()
                if quota:
                    quota.cpu_used = max(0, quota.cpu_used - (project.quota_cpu or 0))
                    quota.ram_gb_used = max(
                        0, quota.ram_gb_used - (project.quota_ram_gb or 0)
                    )

            project.status = "deleting"

        asyncio.create_task(self._deprovision(project_id))

    async def _deprovision(self, project_id: str) -> None:
        try:
            async with self._session_factory() as session:
                repo = ProjectRepository(session)
                project = await repo.get_by_id(project_id)
            await self._provisioner.deprovision(project)
        except Exception:
            log.exception("Deprovisioning failed for project %s", project_id)

    @staticmethod
    def _assert_can_view(claims: Claims, project) -> None:
        if claims.role == "team_lead" and project.team_id != claims.scope_id:
            raise NotFoundError(f"Project '{project.id}' not found")
