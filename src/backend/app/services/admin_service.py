"""Admin service — user role management and org hierarchy CRUD.

All operations are restricted to super-admins (center_admin or platform_admin).
RBAC is enforced here; repositories only do DB access.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import Claims
from app.auth.roles import is_super_admin
from app.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.repositories.allocation_repo import AllocationRepository
from app.repositories.user_role_repo import UserRoleRepository
from app.schemas.admin import (
    CenterResponse,
    DepartmentResponse,
    FieldResponse,
    TeamResponse,
    UserRoleResponse,
)

_ASSIGNABLE_ROLES = frozenset({"platform_admin", "field_admin", "dept_admin", "team_lead"})


class AdminService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = AllocationRepository(session)
        self.user_role_repo = UserRoleRepository(session)
        self.session = session

    def _require_super_admin(self, claims: Claims) -> None:
        if not is_super_admin(claims):
            raise ForbiddenError("Only center_admin or platform_admin can perform this action")

    # ── User role management ───────────────────────────────────────────────────

    async def list_user_roles(self, claims: Claims) -> list[UserRoleResponse]:
        self._require_super_admin(claims)
        rows = await self.user_role_repo.list_all()
        return [UserRoleResponse.model_validate(r) for r in rows]

    async def upsert_user_role(
        self,
        claims: Claims,
        username: str,
        role: str,
        scope_id: str | None,
    ) -> UserRoleResponse:
        self._require_super_admin(claims)
        if role not in _ASSIGNABLE_ROLES:
            raise ValidationError(
                f"Invalid role '{role}'. Assignable roles: {sorted(_ASSIGNABLE_ROLES)}"
            )
        async with self.session.begin():
            row = await self.user_role_repo.upsert_user_role(
                username=username, role=role, scope_id=scope_id, assigned_by=claims.sub
            )
        return UserRoleResponse.model_validate(row)

    async def delete_user_role(self, claims: Claims, username: str) -> None:
        self._require_super_admin(claims)
        if username == claims.sub:
            raise ForbiddenError("Cannot revoke your own role")
        row = await self.user_role_repo.get_by_username(username)
        if row is None:
            raise NotFoundError(f"No role override found for user '{username}'")
        async with self.session.begin():
            await self.user_role_repo.delete(row)

    # ── Center CRUD ────────────────────────────────────────────────────────────

    async def create_center(self, claims: Claims, name: str) -> CenterResponse:
        self._require_super_admin(claims)
        async with self.session.begin():
            center = await self.repo.create_center(name=name)
        return CenterResponse.model_validate(center)

    async def update_center(self, claims: Claims, center_id: str, name: str) -> CenterResponse:
        self._require_super_admin(claims)
        async with self.session.begin():
            center = await self.repo.get_center(center_id)
            center = await self.repo.update_center(center, name=name)
        return CenterResponse.model_validate(center)

    async def delete_center(self, claims: Claims, center_id: str) -> None:
        self._require_super_admin(claims)
        async with self.session.begin():
            center = await self.repo.get_center(center_id)
            if await self.repo.center_has_fields(center_id):
                raise ConflictError("Cannot delete center: fields still exist under it")
            await self.repo.delete_center(center)

    # ── Field CRUD ─────────────────────────────────────────────────────────────

    async def create_field(
        self, claims: Claims, center_id: str, name: str, site: str
    ) -> FieldResponse:
        self._require_super_admin(claims)
        async with self.session.begin():
            await self.repo.get_center(center_id)
            field = await self.repo.create_field(center_id=center_id, name=name, site=site)
        return FieldResponse.model_validate(field)

    async def update_field(
        self, claims: Claims, field_id: str, name: str, site: str
    ) -> FieldResponse:
        self._require_super_admin(claims)
        async with self.session.begin():
            field = await self.repo.get_field(field_id)
            field = await self.repo.update_field(field, name=name, site=site)
        return FieldResponse.model_validate(field)

    async def delete_field(self, claims: Claims, field_id: str) -> None:
        self._require_super_admin(claims)
        async with self.session.begin():
            field = await self.repo.get_field(field_id)
            if await self.repo.field_has_departments(field_id):
                raise ConflictError("Cannot delete field: departments still exist under it")
            await self.repo.delete_field(field)

    # ── Department CRUD ────────────────────────────────────────────────────────

    async def create_department(
        self, claims: Claims, field_id: str, name: str
    ) -> DepartmentResponse:
        self._require_super_admin(claims)
        async with self.session.begin():
            await self.repo.get_field(field_id)
            dept = await self.repo.create_department(field_id=field_id, name=name)
        return DepartmentResponse.model_validate(dept)

    async def update_department(
        self, claims: Claims, dept_id: str, name: str
    ) -> DepartmentResponse:
        self._require_super_admin(claims)
        async with self.session.begin():
            dept = await self.repo.get_dept(dept_id)
            dept = await self.repo.update_department(dept, name=name)
        return DepartmentResponse.model_validate(dept)

    async def delete_department(self, claims: Claims, dept_id: str) -> None:
        self._require_super_admin(claims)
        async with self.session.begin():
            dept = await self.repo.get_dept(dept_id)
            if await self.repo.department_has_teams(dept_id):
                raise ConflictError("Cannot delete department: teams still exist under it")
            await self.repo.delete_department(dept)

    # ── Team CRUD ──────────────────────────────────────────────────────────────

    async def create_team(
        self,
        claims: Claims,
        department_id: str,
        name: str,
        ldap_group_cn: str | None,
    ) -> TeamResponse:
        self._require_super_admin(claims)
        async with self.session.begin():
            await self.repo.get_dept(department_id)
            team = await self.repo.create_team(
                department_id=department_id, name=name, ldap_group_cn=ldap_group_cn
            )
        return TeamResponse.model_validate(team)

    async def update_team(
        self,
        claims: Claims,
        team_id: str,
        name: str,
        ldap_group_cn: str | None,
    ) -> TeamResponse:
        self._require_super_admin(claims)
        async with self.session.begin():
            team = await self.repo.get_team(team_id)
            team = await self.repo.update_team(team, name=name, ldap_group_cn=ldap_group_cn)
        return TeamResponse.model_validate(team)

    async def delete_team(self, claims: Claims, team_id: str) -> None:
        self._require_super_admin(claims)
        async with self.session.begin():
            team = await self.repo.get_team(team_id)
            if await self.repo.team_has_projects(team_id):
                raise ConflictError("Cannot delete team: active projects still exist under it")
            await self.repo.delete_team(team)
