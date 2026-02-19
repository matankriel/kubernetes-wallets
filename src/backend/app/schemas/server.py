"""Pydantic schemas for server domain."""

from datetime import datetime

from pydantic import BaseModel


class ServerResponse(BaseModel):
    id: str
    name: str
    vendor: str | None
    site: str | None
    deployment_cluster: str | None
    cpu: int | None
    ram_gb: int | None
    serial_number: str | None
    product: str | None
    performance_tier: str | None
    status: str
    synced_at: datetime | None

    model_config = {"from_attributes": True}


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    has_next_page: bool


class ServerListResponse(BaseModel):
    data: list[ServerResponse]
    pagination: PaginationMeta


class SyncResult(BaseModel):
    synced: int
    updated: int
    marked_offline: int
