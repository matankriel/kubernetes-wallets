"""Allocation service — all business logic for the hierarchical resource allocation.

RBAC and the allocation invariant are enforced here. Repositories only do DB access.

Invariant: cpu_used + requested <= cpu_limit at every level.
All quota reads that precede a write use SELECT FOR UPDATE (via repository).
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import Claims
from app.errors import ConflictError, ForbiddenError, QuotaExceededError
from app.repositories.allocation_repo import AllocationRepository
from app.schemas.allocation import (
    AllocationTreeResponse,
    CenterNode,
    DeptQuotaNode,
    DeptQuotaResponse,
    FieldNode,
    FieldServerAllocationResponse,
    TeamQuotaNode,
    TeamQuotaResponse,
)


class AllocationService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = AllocationRepository(session)
        self.session = session

    # ── Server → Field allocation ──────────────────────────────────────────────

    async def assign_server_to_field(
        self, claims: Claims, server_id: str, field_id: str
    ) -> FieldServerAllocationResponse:
        if claims.role != "center_admin":
            raise ForbiddenError("Only center_admin can assign servers to fields")

        await self.repo.get_server(server_id)
        await self.repo.get_field(field_id)

        async with self.session.begin():
            allocation = await self.repo.create_server_allocation(
                server_id=server_id, field_id=field_id, allocated_by=claims.sub
            )

        return FieldServerAllocationResponse.model_validate(allocation)

    async def remove_server_from_field(
        self, claims: Claims, allocation_id: str
    ) -> None:
        if claims.role != "center_admin":
            raise ForbiddenError("Only center_admin can remove server allocations")

        async with self.session.begin():
            allocation = await self.repo.get_server_allocation_by_id(allocation_id)
            if await self.repo.field_has_dept_quotas(allocation.field_id):
                raise ConflictError(
                    "Cannot remove server: field still has active department quota allocations"
                )
            await self.repo.delete_server_allocation(allocation)

    async def swap_server_between_fields(
        self, claims: Claims, server_id: str, from_field_id: str, to_field_id: str
    ) -> FieldServerAllocationResponse:
        if claims.role != "center_admin":
            raise ForbiddenError("Only center_admin can swap server allocations")

        await self.repo.get_field(from_field_id)
        await self.repo.get_field(to_field_id)

        async with self.session.begin():
            existing = await self.repo.get_server_allocation(server_id)
            if existing is None or existing.field_id != from_field_id:
                raise ConflictError(
                    f"Server '{server_id}' is not currently assigned to field '{from_field_id}'"
                )
            await self.repo.delete_server_allocation(existing)
            new_allocation = await self.repo.create_server_allocation(
                server_id=server_id, field_id=to_field_id, allocated_by=claims.sub
            )

        return FieldServerAllocationResponse.model_validate(new_allocation)

    # ── Field → Department quota ───────────────────────────────────────────────

    async def create_dept_quota(
        self,
        claims: Claims,
        field_id: str,
        dept_id: str,
        site: str,
        cpu_limit: int,
        ram_gb_limit: int,
    ) -> DeptQuotaResponse:
        if claims.role != "field_admin" or claims.scope_id != field_id:
            raise ForbiddenError("Only field_admin scoped to this field can set department quotas")

        async with self.session.begin():
            existing = await self.repo.get_dept_quota_for_update(dept_id, site)
            if existing is not None:
                raise ConflictError(
                    f"Department quota for dept '{dept_id}' at site '{site}' already exists"
                )

            field_cpu, field_ram = await self.repo.get_field_total_cpu_ram(field_id, site)
            used_cpu, used_ram = await self.repo.get_dept_quota_sum_for_field_site(field_id, site)

            if used_cpu + cpu_limit > field_cpu:
                raise QuotaExceededError(
                    f"Field '{field_id}' at site '{site}' has insufficient CPU. "
                    f"Available: {field_cpu - used_cpu}, requested: {cpu_limit}"
                )
            if used_ram + ram_gb_limit > field_ram:
                raise QuotaExceededError(
                    f"Field '{field_id}' at site '{site}' has insufficient RAM. "
                    f"Available: {field_ram - used_ram} GB, requested: {ram_gb_limit} GB"
                )

            quota = await self.repo.create_dept_quota(
                field_id=field_id,
                dept_id=dept_id,
                site=site,
                cpu_limit=cpu_limit,
                ram_gb_limit=ram_gb_limit,
            )

        return DeptQuotaResponse.model_validate(quota)

    async def update_dept_quota(
        self, claims: Claims, quota_id: str, cpu_limit: int, ram_gb_limit: int
    ) -> DeptQuotaResponse:
        async with self.session.begin():
            quota = await self.repo.get_dept_quota_by_id(quota_id)

            if claims.role != "field_admin" or claims.scope_id != quota.field_id:
                raise ForbiddenError("Only field_admin scoped to this field can update department quotas")

            if cpu_limit < quota.cpu_used:
                raise QuotaExceededError(
                    f"Cannot reduce cpu_limit to {cpu_limit}: {quota.cpu_used} CPU already in use"
                )
            if ram_gb_limit < quota.ram_gb_used:
                raise QuotaExceededError(
                    f"Cannot reduce ram_gb_limit to {ram_gb_limit}: {quota.ram_gb_used} GB already in use"
                )

            field_cpu, field_ram = await self.repo.get_field_total_cpu_ram(quota.field_id, quota.site)
            used_cpu, used_ram = await self.repo.get_dept_quota_sum_for_field_site(
                quota.field_id, quota.site
            )
            delta_cpu = cpu_limit - quota.cpu_limit
            delta_ram = ram_gb_limit - quota.ram_gb_limit

            if used_cpu + delta_cpu > field_cpu:
                raise QuotaExceededError(
                    f"Field does not have enough CPU to cover increased limit. "
                    f"Field total: {field_cpu}, currently allocated: {used_cpu}, requested increase: {delta_cpu}"
                )
            if used_ram + delta_ram > field_ram:
                raise QuotaExceededError(
                    "Field does not have enough RAM to cover increased limit."
                )

            quota.cpu_limit = cpu_limit
            quota.ram_gb_limit = ram_gb_limit

        return DeptQuotaResponse.model_validate(quota)

    # ── Department → Team quota ────────────────────────────────────────────────

    async def create_team_quota(
        self,
        claims: Claims,
        dept_id: str,
        team_id: str,
        site: str,
        cpu_limit: int,
        ram_gb_limit: int,
    ) -> TeamQuotaResponse:
        if claims.role != "dept_admin" or claims.scope_id != dept_id:
            raise ForbiddenError("Only dept_admin scoped to this department can set team quotas")

        async with self.session.begin():
            existing = await self.repo.get_team_quota_for_update(team_id, site)
            if existing is not None:
                raise ConflictError(
                    f"Team quota for team '{team_id}' at site '{site}' already exists"
                )

            dept_quota = await self.repo.get_dept_quota_for_update(dept_id, site)
            if dept_quota is None:
                raise QuotaExceededError(
                    f"No department quota found for dept '{dept_id}' at site '{site}'"
                )

            used_cpu, used_ram = await self.repo.get_team_quota_sum_for_dept_site(dept_id, site)

            if used_cpu + cpu_limit > dept_quota.cpu_limit:
                raise QuotaExceededError(
                    f"Department '{dept_id}' at site '{site}' has insufficient CPU. "
                    f"Available: {dept_quota.cpu_limit - used_cpu}, requested: {cpu_limit}"
                )
            if used_ram + ram_gb_limit > dept_quota.ram_gb_limit:
                raise QuotaExceededError(
                    f"Department '{dept_id}' at site '{site}' has insufficient RAM. "
                    f"Available: {dept_quota.ram_gb_limit - used_ram} GB, requested: {ram_gb_limit} GB"
                )

            quota = await self.repo.create_team_quota(
                dept_id=dept_id,
                team_id=team_id,
                site=site,
                cpu_limit=cpu_limit,
                ram_gb_limit=ram_gb_limit,
            )

        return TeamQuotaResponse.model_validate(quota)

    async def update_team_quota(
        self, claims: Claims, quota_id: str, cpu_limit: int, ram_gb_limit: int
    ) -> TeamQuotaResponse:
        async with self.session.begin():
            quota = await self.repo.get_team_quota_by_id(quota_id)

            if claims.role != "dept_admin" or claims.scope_id != quota.department_id:
                raise ForbiddenError(
                    "Only dept_admin scoped to this department can update team quotas"
                )

            if cpu_limit < quota.cpu_used:
                raise QuotaExceededError(
                    f"Cannot reduce cpu_limit to {cpu_limit}: {quota.cpu_used} CPU already in use"
                )
            if ram_gb_limit < quota.ram_gb_used:
                raise QuotaExceededError(
                    f"Cannot reduce ram_gb_limit to {ram_gb_limit}: {quota.ram_gb_used} GB already in use"
                )

            dept_quota = await self.repo.get_dept_quota_for_update(quota.department_id, quota.site)
            if dept_quota is not None:
                used_cpu, used_ram = await self.repo.get_team_quota_sum_for_dept_site(
                    quota.department_id, quota.site
                )
                delta_cpu = cpu_limit - quota.cpu_limit
                delta_ram = ram_gb_limit - quota.ram_gb_limit
                if used_cpu + delta_cpu > dept_quota.cpu_limit:
                    raise QuotaExceededError("Department does not have enough CPU headroom.")
                if used_ram + delta_ram > dept_quota.ram_gb_limit:
                    raise QuotaExceededError("Department does not have enough RAM headroom.")

            quota.cpu_limit = cpu_limit
            quota.ram_gb_limit = ram_gb_limit

        return TeamQuotaResponse.model_validate(quota)

    # ── Allocation tree ────────────────────────────────────────────────────────

    async def get_allocation_tree(self, claims: Claims) -> AllocationTreeResponse:
        centers = await self.repo.get_full_tree()
        result: list[CenterNode] = []

        for center in centers:
            fields_result = await self.session.execute(
                __import__("sqlalchemy", fromlist=["select"]).select(
                    __import__("app.models.org", fromlist=["Field"]).Field
                ).where(
                    __import__("app.models.org", fromlist=["Field"]).Field.center_id == center.id
                )
            )
            fields = list(fields_result.scalars().all())

            field_nodes: list[FieldNode] = []
            for field in fields:
                if claims.role == "field_admin" and claims.scope_id != field.id:
                    continue

                servers = await self.repo.get_servers_for_field(field.id)
                total_cpu = sum(s.cpu or 0 for s in servers)
                total_ram = sum(s.ram_gb or 0 for s in servers)

                dept_quotas = await self.repo.get_dept_quotas_for_field(field.id)

                dept_nodes: list[DeptQuotaNode] = []
                for dq in dept_quotas:
                    dept = await self.repo.get_dept(dq.department_id)

                    if claims.role == "dept_admin" and claims.scope_id != dq.department_id:
                        continue

                    team_quotas = await self.repo.get_team_quotas_for_dept(dq.department_id)
                    team_nodes: list[TeamQuotaNode] = []
                    for tq in team_quotas:
                        team = await self.repo.get_team(tq.team_id)
                        if claims.role == "team_lead" and claims.scope_id != tq.team_id:
                            continue
                        team_nodes.append(
                            TeamQuotaNode(
                                team_id=tq.team_id,
                                team_name=team.name,
                                site=tq.site,
                                cpu_limit=tq.cpu_limit,
                                ram_gb_limit=tq.ram_gb_limit,
                                cpu_used=tq.cpu_used,
                                ram_gb_used=tq.ram_gb_used,
                            )
                        )

                    dept_nodes.append(
                        DeptQuotaNode(
                            dept_id=dq.department_id,
                            dept_name=dept.name,
                            site=dq.site,
                            cpu_limit=dq.cpu_limit,
                            ram_gb_limit=dq.ram_gb_limit,
                            cpu_used=dq.cpu_used,
                            ram_gb_used=dq.ram_gb_used,
                            teams=team_nodes,
                        )
                    )

                field_nodes.append(
                    FieldNode(
                        field_id=field.id,
                        field_name=field.name,
                        site=field.site,
                        total_cpu=total_cpu,
                        total_ram_gb=total_ram,
                        departments=dept_nodes,
                    )
                )

            if field_nodes or claims.role == "center_admin":
                result.append(
                    CenterNode(
                        center_id=center.id, center_name=center.name, fields=field_nodes
                    )
                )

        return AllocationTreeResponse(centers=result)
