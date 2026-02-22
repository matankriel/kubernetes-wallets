"""Pydantic schemas for admin endpoints (user roles + org CRUD)."""

from pydantic import BaseModel, ConfigDict

# ── User role schemas ──────────────────────────────────────────────────────────


class UpsertUserRoleRequest(BaseModel):
    username: str
    role: str
    scope_id: str | None = None


class UserRoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    role: str
    scope_id: str | None
    assigned_by: str
    assigned_at: str | None


# ── Center schemas ─────────────────────────────────────────────────────────────


class CreateCenterRequest(BaseModel):
    name: str


class UpdateCenterRequest(BaseModel):
    name: str


class CenterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str


# ── Field schemas ──────────────────────────────────────────────────────────────


class CreateFieldRequest(BaseModel):
    center_id: str
    name: str
    site: str


class UpdateFieldRequest(BaseModel):
    name: str
    site: str


class FieldResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    center_id: str
    name: str
    site: str


# ── Department schemas ─────────────────────────────────────────────────────────


class CreateDepartmentRequest(BaseModel):
    field_id: str
    name: str


class UpdateDepartmentRequest(BaseModel):
    name: str


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    field_id: str
    name: str


# ── Team schemas ───────────────────────────────────────────────────────────────


class CreateTeamRequest(BaseModel):
    department_id: str
    name: str
    ldap_group_cn: str | None = None


class UpdateTeamRequest(BaseModel):
    name: str
    ldap_group_cn: str | None = None


class TeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    department_id: str
    name: str
    ldap_group_cn: str | None
