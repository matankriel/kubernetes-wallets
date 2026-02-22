"""Repository for all allocation tables.

All quota reads that precede a write use .with_for_update() to prevent
race conditions on the allocation invariant check.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ConflictError, NotFoundError
from app.models.org import (
    Center,
    Department,
    DepartmentQuotaAllocation,
    Field,
    FieldServerAllocation,
    Team,
    TeamQuotaAllocation,
)
from app.models.server import Server


class AllocationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Field server allocations ───────────────────────────────────────────────

    async def get_server_allocation(self, server_id: str) -> FieldServerAllocation | None:
        result = await self.session.execute(
            select(FieldServerAllocation).where(FieldServerAllocation.server_id == server_id)
        )
        return result.scalar_one_or_none()

    async def get_server_allocation_by_id(self, allocation_id: str) -> FieldServerAllocation:
        result = await self.session.execute(
            select(FieldServerAllocation).where(FieldServerAllocation.id == allocation_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise NotFoundError(f"Server allocation '{allocation_id}' not found")
        return row

    async def create_server_allocation(
        self, server_id: str, field_id: str, allocated_by: str
    ) -> FieldServerAllocation:
        existing = await self.get_server_allocation(server_id)
        if existing is not None:
            raise ConflictError(f"Server '{server_id}' is already assigned to a field")
        allocation = FieldServerAllocation(
            server_id=server_id, field_id=field_id, allocated_by=allocated_by
        )
        self.session.add(allocation)
        await self.session.flush()
        await self.session.refresh(allocation)
        return allocation

    async def delete_server_allocation(self, allocation: FieldServerAllocation) -> None:
        await self.session.delete(allocation)
        await self.session.flush()

    async def field_has_dept_quotas(self, field_id: str) -> bool:
        result = await self.session.execute(
            select(func.count())
            .select_from(DepartmentQuotaAllocation)
            .where(
                DepartmentQuotaAllocation.field_id == field_id,
                DepartmentQuotaAllocation.cpu_used > 0,
            )
        )
        return result.scalar_one() > 0

    async def get_field_total_cpu_ram(self, field_id: str, site: str) -> tuple[int, int]:
        """Return (total_cpu, total_ram_gb) of servers assigned to a field at a site."""
        result = await self.session.execute(
            select(func.coalesce(func.sum(Server.cpu), 0), func.coalesce(func.sum(Server.ram_gb), 0))
            .join(FieldServerAllocation, FieldServerAllocation.server_id == Server.id)
            .join(Field, Field.id == FieldServerAllocation.field_id)
            .where(FieldServerAllocation.field_id == field_id, Field.site == site)
        )
        row = result.one()
        return int(row[0]), int(row[1])

    async def get_dept_quota_sum_for_field_site(self, field_id: str, site: str) -> tuple[int, int]:
        """Return (sum cpu_limit, sum ram_gb_limit) across all dept quotas for field+site."""
        result = await self.session.execute(
            select(
                func.coalesce(func.sum(DepartmentQuotaAllocation.cpu_limit), 0),
                func.coalesce(func.sum(DepartmentQuotaAllocation.ram_gb_limit), 0),
            ).where(
                DepartmentQuotaAllocation.field_id == field_id,
                DepartmentQuotaAllocation.site == site,
            )
        )
        row = result.one()
        return int(row[0]), int(row[1])

    # ── Department quota allocations ───────────────────────────────────────────

    async def get_dept_quota_for_update(
        self, dept_id: str, site: str
    ) -> DepartmentQuotaAllocation | None:
        result = await self.session.execute(
            select(DepartmentQuotaAllocation)
            .where(
                DepartmentQuotaAllocation.department_id == dept_id,
                DepartmentQuotaAllocation.site == site,
            )
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_dept_quota_by_id(self, quota_id: str) -> DepartmentQuotaAllocation:
        result = await self.session.execute(
            select(DepartmentQuotaAllocation)
            .where(DepartmentQuotaAllocation.id == quota_id)
            .with_for_update()
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise NotFoundError(f"Department quota '{quota_id}' not found")
        return row

    async def create_dept_quota(
        self, field_id: str, dept_id: str, site: str, cpu_limit: int, ram_gb_limit: int
    ) -> DepartmentQuotaAllocation:
        quota = DepartmentQuotaAllocation(
            field_id=field_id,
            department_id=dept_id,
            site=site,
            cpu_limit=cpu_limit,
            ram_gb_limit=ram_gb_limit,
        )
        self.session.add(quota)
        await self.session.flush()
        await self.session.refresh(quota)
        return quota

    async def get_team_quota_sum_for_dept_site(self, dept_id: str, site: str) -> tuple[int, int]:
        result = await self.session.execute(
            select(
                func.coalesce(func.sum(TeamQuotaAllocation.cpu_limit), 0),
                func.coalesce(func.sum(TeamQuotaAllocation.ram_gb_limit), 0),
            ).where(
                TeamQuotaAllocation.department_id == dept_id,
                TeamQuotaAllocation.site == site,
            )
        )
        row = result.one()
        return int(row[0]), int(row[1])

    # ── Team quota allocations ─────────────────────────────────────────────────

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

    async def get_team_quota_by_id(self, quota_id: str) -> TeamQuotaAllocation:
        result = await self.session.execute(
            select(TeamQuotaAllocation)
            .where(TeamQuotaAllocation.id == quota_id)
            .with_for_update()
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise NotFoundError(f"Team quota '{quota_id}' not found")
        return row

    async def create_team_quota(
        self, dept_id: str, team_id: str, site: str, cpu_limit: int, ram_gb_limit: int
    ) -> TeamQuotaAllocation:
        quota = TeamQuotaAllocation(
            department_id=dept_id,
            team_id=team_id,
            site=site,
            cpu_limit=cpu_limit,
            ram_gb_limit=ram_gb_limit,
        )
        self.session.add(quota)
        await self.session.flush()
        await self.session.refresh(quota)
        return quota

    # ── Org navigation ─────────────────────────────────────────────────────────

    async def get_field(self, field_id: str) -> Field:
        result = await self.session.execute(select(Field).where(Field.id == field_id))
        row = result.scalar_one_or_none()
        if row is None:
            raise NotFoundError(f"Field '{field_id}' not found")
        return row

    async def get_dept(self, dept_id: str) -> Department:
        result = await self.session.execute(
            select(Department).where(Department.id == dept_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise NotFoundError(f"Department '{dept_id}' not found")
        return row

    async def get_team(self, team_id: str) -> Team:
        result = await self.session.execute(select(Team).where(Team.id == team_id))
        row = result.scalar_one_or_none()
        if row is None:
            raise NotFoundError(f"Team '{team_id}' not found")
        return row

    async def get_server(self, server_id: str) -> Server:
        result = await self.session.execute(select(Server).where(Server.id == server_id))
        row = result.scalar_one_or_none()
        if row is None:
            raise NotFoundError(f"Server '{server_id}' not found")
        return row

    # ── Allocation tree ────────────────────────────────────────────────────────

    async def get_full_tree(self) -> list[Center]:
        result = await self.session.execute(select(Center))
        return list(result.scalars().all())

    async def get_fields_for_center(self, center_id: str) -> list[Field]:
        result = await self.session.execute(
            select(Field).where(Field.center_id == center_id)
        )
        return list(result.scalars().all())

    async def get_dept_quotas_for_field(
        self, field_id: str
    ) -> list[DepartmentQuotaAllocation]:
        result = await self.session.execute(
            select(DepartmentQuotaAllocation).where(
                DepartmentQuotaAllocation.field_id == field_id
            )
        )
        return list(result.scalars().all())

    async def get_team_quotas_for_dept(
        self, dept_id: str
    ) -> list[TeamQuotaAllocation]:
        result = await self.session.execute(
            select(TeamQuotaAllocation).where(TeamQuotaAllocation.department_id == dept_id)
        )
        return list(result.scalars().all())

    async def get_servers_for_field(self, field_id: str) -> list[Server]:
        result = await self.session.execute(
            select(Server)
            .join(FieldServerAllocation, FieldServerAllocation.server_id == Server.id)
            .where(FieldServerAllocation.field_id == field_id)
        )
        return list(result.scalars().all())
