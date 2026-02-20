"""Pydantic request/response schemas for the projects API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator


class CreateProjectRequest(BaseModel):
    name: str
    site: str
    sla_type: str
    performance_tier: str

    @field_validator("sla_type")
    @classmethod
    def validate_sla_type(cls, v: str) -> str:
        allowed = {"bronze", "silver", "gold"}
        if v not in allowed:
            msg = f"sla_type must be one of {allowed}"
            raise ValueError(msg)
        return v

    @field_validator("performance_tier")
    @classmethod
    def validate_performance_tier(cls, v: str) -> str:
        allowed = {"regular", "high_performance"}
        if v not in allowed:
            msg = f"performance_tier must be one of {allowed}"
            raise ValueError(msg)
        return v


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    team_id: str
    site: str | None
    sla_type: str | None
    performance_tier: str | None
    namespace_name: str | None
    status: str
    quota_cpu: int | None
    quota_ram_gb: int | None
