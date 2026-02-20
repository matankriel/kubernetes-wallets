"""Pydantic request/response schemas for the allocation API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

# ── Request schemas ────────────────────────────────────────────────────────────

class AssignServerRequest(BaseModel):
    server_id: str
    field_id: str


class SwapServerRequest(BaseModel):
    server_id: str
    from_field_id: str
    to_field_id: str


class CreateDeptQuotaRequest(BaseModel):
    field_id: str
    dept_id: str
    site: str
    cpu_limit: int
    ram_gb_limit: int


class UpdateDeptQuotaRequest(BaseModel):
    cpu_limit: int
    ram_gb_limit: int


class CreateTeamQuotaRequest(BaseModel):
    dept_id: str
    team_id: str
    site: str
    cpu_limit: int
    ram_gb_limit: int


class UpdateTeamQuotaRequest(BaseModel):
    cpu_limit: int
    ram_gb_limit: int


# ── Response schemas ───────────────────────────────────────────────────────────

class FieldServerAllocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    server_id: str
    field_id: str
    allocated_by: str | None


class DeptQuotaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    field_id: str
    department_id: str
    site: str
    cpu_limit: int
    ram_gb_limit: int
    cpu_used: int
    ram_gb_used: int


class TeamQuotaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    department_id: str
    team_id: str
    site: str
    cpu_limit: int
    ram_gb_limit: int
    cpu_used: int
    ram_gb_used: int


# ── Tree response ──────────────────────────────────────────────────────────────

class TeamQuotaNode(BaseModel):
    team_id: str
    team_name: str
    site: str
    cpu_limit: int
    ram_gb_limit: int
    cpu_used: int
    ram_gb_used: int


class DeptQuotaNode(BaseModel):
    dept_id: str
    dept_name: str
    site: str
    cpu_limit: int
    ram_gb_limit: int
    cpu_used: int
    ram_gb_used: int
    teams: list[TeamQuotaNode] = []


class FieldNode(BaseModel):
    field_id: str
    field_name: str
    site: str
    total_cpu: int
    total_ram_gb: int
    departments: list[DeptQuotaNode] = []


class CenterNode(BaseModel):
    center_id: str
    center_name: str
    fields: list[FieldNode] = []


class AllocationTreeResponse(BaseModel):
    centers: list[CenterNode] = []
