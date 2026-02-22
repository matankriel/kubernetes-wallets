"""Admin router — user role management and org hierarchy CRUD.

All endpoints require center_admin or platform_admin.

GET    /api/v1/admin/user-roles
POST   /api/v1/admin/user-roles
DELETE /api/v1/admin/user-roles/{username}

POST   /api/v1/admin/org/centers
PATCH  /api/v1/admin/org/centers/{center_id}
DELETE /api/v1/admin/org/centers/{center_id}

POST   /api/v1/admin/org/fields
PATCH  /api/v1/admin/org/fields/{field_id}
DELETE /api/v1/admin/org/fields/{field_id}

POST   /api/v1/admin/org/departments
PATCH  /api/v1/admin/org/departments/{dept_id}
DELETE /api/v1/admin/org/departments/{dept_id}

POST   /api/v1/admin/org/teams
PATCH  /api/v1/admin/org/teams/{team_id}
DELETE /api/v1/admin/org/teams/{team_id}
"""

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import get_current_user
from app.auth.jwt import Claims
from app.database import get_db
from app.schemas.admin import (
    CenterResponse,
    CreateCenterRequest,
    CreateDepartmentRequest,
    CreateFieldRequest,
    CreateTeamRequest,
    DepartmentResponse,
    FieldResponse,
    TeamResponse,
    UpdateCenterRequest,
    UpdateDepartmentRequest,
    UpdateFieldRequest,
    UpdateTeamRequest,
    UpsertUserRoleRequest,
    UserRoleResponse,
)
from app.services.admin_service import AdminService

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _service(session=Depends(get_db)) -> AdminService:
    return AdminService(session)


# ── User role endpoints ────────────────────────────────────────────────────────


@router.get("/user-roles", response_model=list[UserRoleResponse])
async def list_user_roles(
    claims: Claims = Depends(get_current_user),
    svc: AdminService = Depends(_service),
) -> list[UserRoleResponse]:
    return await svc.list_user_roles(claims)


@router.post(
    "/user-roles",
    response_model=UserRoleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upsert_user_role(
    body: UpsertUserRoleRequest,
    claims: Claims = Depends(get_current_user),
    svc: AdminService = Depends(_service),
) -> UserRoleResponse:
    return await svc.upsert_user_role(
        claims, username=body.username, role=body.role, scope_id=body.scope_id
    )


@router.delete("/user-roles/{username}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_role(
    username: str,
    claims: Claims = Depends(get_current_user),
    svc: AdminService = Depends(_service),
) -> None:
    await svc.delete_user_role(claims, username=username)


# ── Center endpoints ───────────────────────────────────────────────────────────


@router.post(
    "/org/centers",
    response_model=CenterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_center(
    body: CreateCenterRequest,
    claims: Claims = Depends(get_current_user),
    svc: AdminService = Depends(_service),
) -> CenterResponse:
    return await svc.create_center(claims, name=body.name)


@router.patch("/org/centers/{center_id}", response_model=CenterResponse)
async def update_center(
    center_id: str,
    body: UpdateCenterRequest,
    claims: Claims = Depends(get_current_user),
    svc: AdminService = Depends(_service),
) -> CenterResponse:
    return await svc.update_center(claims, center_id=center_id, name=body.name)


@router.delete("/org/centers/{center_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_center(
    center_id: str,
    claims: Claims = Depends(get_current_user),
    svc: AdminService = Depends(_service),
) -> None:
    await svc.delete_center(claims, center_id=center_id)


# ── Field endpoints ────────────────────────────────────────────────────────────


@router.post(
    "/org/fields",
    response_model=FieldResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_field(
    body: CreateFieldRequest,
    claims: Claims = Depends(get_current_user),
    svc: AdminService = Depends(_service),
) -> FieldResponse:
    return await svc.create_field(
        claims, center_id=body.center_id, name=body.name, site=body.site
    )


@router.patch("/org/fields/{field_id}", response_model=FieldResponse)
async def update_field(
    field_id: str,
    body: UpdateFieldRequest,
    claims: Claims = Depends(get_current_user),
    svc: AdminService = Depends(_service),
) -> FieldResponse:
    return await svc.update_field(claims, field_id=field_id, name=body.name, site=body.site)


@router.delete("/org/fields/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_field(
    field_id: str,
    claims: Claims = Depends(get_current_user),
    svc: AdminService = Depends(_service),
) -> None:
    await svc.delete_field(claims, field_id=field_id)


# ── Department endpoints ───────────────────────────────────────────────────────


@router.post(
    "/org/departments",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_department(
    body: CreateDepartmentRequest,
    claims: Claims = Depends(get_current_user),
    svc: AdminService = Depends(_service),
) -> DepartmentResponse:
    return await svc.create_department(claims, field_id=body.field_id, name=body.name)


@router.patch("/org/departments/{dept_id}", response_model=DepartmentResponse)
async def update_department(
    dept_id: str,
    body: UpdateDepartmentRequest,
    claims: Claims = Depends(get_current_user),
    svc: AdminService = Depends(_service),
) -> DepartmentResponse:
    return await svc.update_department(claims, dept_id=dept_id, name=body.name)


@router.delete("/org/departments/{dept_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    dept_id: str,
    claims: Claims = Depends(get_current_user),
    svc: AdminService = Depends(_service),
) -> None:
    await svc.delete_department(claims, dept_id=dept_id)


# ── Team endpoints ─────────────────────────────────────────────────────────────


@router.post(
    "/org/teams",
    response_model=TeamResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_team(
    body: CreateTeamRequest,
    claims: Claims = Depends(get_current_user),
    svc: AdminService = Depends(_service),
) -> TeamResponse:
    return await svc.create_team(
        claims,
        department_id=body.department_id,
        name=body.name,
        ldap_group_cn=body.ldap_group_cn,
    )


@router.patch("/org/teams/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: str,
    body: UpdateTeamRequest,
    claims: Claims = Depends(get_current_user),
    svc: AdminService = Depends(_service),
) -> TeamResponse:
    return await svc.update_team(
        claims, team_id=team_id, name=body.name, ldap_group_cn=body.ldap_group_cn
    )


@router.delete("/org/teams/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: str,
    claims: Claims = Depends(get_current_user),
    svc: AdminService = Depends(_service),
) -> None:
    await svc.delete_team(claims, team_id=team_id)
