"""Repository for project (Kubernetes namespace) records."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import NotFoundError
from app.models.org import TeamQuotaAllocation
from app.models.project import Project


class ProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_team_quota_for_update(
        self, team_id: str, site: str
    ) -> TeamQuotaAllocation | None:
        result = await self.session.execute(
            select(TeamQuotaAllocation)
            .where(
                TeamQuotaAllocation.team_id == team_id,
                TeamQuotaAllocation.site == site,
            )
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def create_project(
        self,
        team_id: str,
        name: str,
        site: str,
        sla_type: str,
        performance_tier: str,
        namespace_name: str,
        quota_cpu: int,
        quota_ram_gb: int,
    ) -> Project:
        project = Project(
            team_id=team_id,
            name=name,
            site=site,
            sla_type=sla_type,
            performance_tier=performance_tier,
            namespace_name=namespace_name,
            status="provisioning",
            quota_cpu=quota_cpu,
            quota_ram_gb=quota_ram_gb,
        )
        self.session.add(project)
        await self.session.flush()
        await self.session.refresh(project)
        return project

    async def get_by_id(self, project_id: str) -> Project:
        result = await self.session.execute(
            select(Project).where(Project.id == project_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise NotFoundError(f"Project '{project_id}' not found")
        return row

    async def get_by_id_for_update(self, project_id: str) -> Project:
        result = await self.session.execute(
            select(Project).where(Project.id == project_id).with_for_update()
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise NotFoundError(f"Project '{project_id}' not found")
        return row

    async def list_projects(self, team_id: str | None = None) -> list[Project]:
        stmt = select(Project).where(Project.deleted_at.is_(None))
        if team_id is not None:
            stmt = stmt.where(Project.team_id == team_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(self, project_id: str, status: str) -> None:
        result = await self.session.execute(
            select(Project).where(Project.id == project_id).with_for_update()
        )
        project = result.scalar_one_or_none()
        if project is not None:
            project.status = status
            await self.session.flush()
