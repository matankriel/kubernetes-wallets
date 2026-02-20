"""Allocation API endpoints.

GET    /api/v1/allocations/tree                         — scoped allocation tree
POST   /api/v1/allocations/servers                      — assign server to field (center_admin)
DELETE /api/v1/allocations/servers/{id}                 — remove server allocation (center_admin)
POST   /api/v1/allocations/servers/swap                 — swap server between fields (center_admin)
POST   /api/v1/allocations/department-quota             — create dept quota (field_admin)
PUT    /api/v1/allocations/department-quota/{id}        — update dept quota (field_admin)
POST   /api/v1/allocations/team-quota                   — create team quota (dept_admin)
PUT    /api/v1/allocations/team-quota/{id}              — update team quota (dept_admin)
"""

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import get_current_user
from app.auth.jwt import Claims
from app.database import get_db
from app.schemas.allocation import (
    AllocationTreeResponse,
    AssignServerRequest,
    CreateDeptQuotaRequest,
    CreateTeamQuotaRequest,
    DeptQuotaResponse,
    FieldServerAllocationResponse,
    SwapServerRequest,
    TeamQuotaResponse,
    UpdateDeptQuotaRequest,
    UpdateTeamQuotaRequest,
)
from app.services.allocation_service import AllocationService

router = APIRouter(prefix="/api/v1/allocations", tags=["allocations"])


def _service(session=Depends(get_db)) -> AllocationService:
    return AllocationService(session)


# ── Allocation tree ────────────────────────────────────────────────────────────

@router.get("/tree", response_model=AllocationTreeResponse)
async def get_allocation_tree(
    claims: Claims = Depends(get_current_user),
    svc: AllocationService = Depends(_service),
) -> AllocationTreeResponse:
    return await svc.get_allocation_tree(claims)


# ── Server → Field allocation ──────────────────────────────────────────────────

@router.post(
    "/servers",
    response_model=FieldServerAllocationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_server_to_field(
    body: AssignServerRequest,
    claims: Claims = Depends(get_current_user),
    svc: AllocationService = Depends(_service),
) -> FieldServerAllocationResponse:
    return await svc.assign_server_to_field(claims, body.server_id, body.field_id)


@router.delete("/servers/{allocation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_server_from_field(
    allocation_id: str,
    claims: Claims = Depends(get_current_user),
    svc: AllocationService = Depends(_service),
) -> None:
    await svc.remove_server_from_field(claims, allocation_id)


@router.post(
    "/servers/swap",
    response_model=FieldServerAllocationResponse,
)
async def swap_server_between_fields(
    body: SwapServerRequest,
    claims: Claims = Depends(get_current_user),
    svc: AllocationService = Depends(_service),
) -> FieldServerAllocationResponse:
    return await svc.swap_server_between_fields(
        claims, body.server_id, body.from_field_id, body.to_field_id
    )


# ── Field → Department quota ───────────────────────────────────────────────────

@router.post(
    "/department-quota",
    response_model=DeptQuotaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_dept_quota(
    body: CreateDeptQuotaRequest,
    claims: Claims = Depends(get_current_user),
    svc: AllocationService = Depends(_service),
) -> DeptQuotaResponse:
    return await svc.create_dept_quota(
        claims,
        field_id=body.field_id,
        dept_id=body.dept_id,
        site=body.site,
        cpu_limit=body.cpu_limit,
        ram_gb_limit=body.ram_gb_limit,
    )


@router.put("/department-quota/{quota_id}", response_model=DeptQuotaResponse)
async def update_dept_quota(
    quota_id: str,
    body: UpdateDeptQuotaRequest,
    claims: Claims = Depends(get_current_user),
    svc: AllocationService = Depends(_service),
) -> DeptQuotaResponse:
    return await svc.update_dept_quota(
        claims,
        quota_id=quota_id,
        cpu_limit=body.cpu_limit,
        ram_gb_limit=body.ram_gb_limit,
    )


# ── Department → Team quota ────────────────────────────────────────────────────

@router.post(
    "/team-quota",
    response_model=TeamQuotaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_team_quota(
    body: CreateTeamQuotaRequest,
    claims: Claims = Depends(get_current_user),
    svc: AllocationService = Depends(_service),
) -> TeamQuotaResponse:
    return await svc.create_team_quota(
        claims,
        dept_id=body.dept_id,
        team_id=body.team_id,
        site=body.site,
        cpu_limit=body.cpu_limit,
        ram_gb_limit=body.ram_gb_limit,
    )


@router.put("/team-quota/{quota_id}", response_model=TeamQuotaResponse)
async def update_team_quota(
    quota_id: str,
    body: UpdateTeamQuotaRequest,
    claims: Claims = Depends(get_current_user),
    svc: AllocationService = Depends(_service),
) -> TeamQuotaResponse:
    return await svc.update_team_quota(
        claims,
        quota_id=quota_id,
        cpu_limit=body.cpu_limit,
        ram_gb_limit=body.ram_gb_limit,
    )
