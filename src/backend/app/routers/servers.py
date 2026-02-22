"""Server inventory and sync endpoints.

GET  /api/v1/servers           — paginated list (filtered by site, tier, status)
GET  /api/v1/servers/{id}      — single server
POST /api/v1/admin/sync/servers — manual sync trigger (center_admin only)
"""

import httpx
from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import get_current_user
from app.auth.jwt import Claims
from app.auth.roles import is_super_admin
from app.config import settings
from app.database import AsyncSessionLocal, get_db
from app.errors import ForbiddenError
from app.repositories.server_repo import ServerRepository
from app.schemas.server import PaginationMeta, ServerListResponse, ServerResponse, SyncResult
from app.sync.server_sync import sync_servers

router = APIRouter(prefix="/api/v1", tags=["servers"])

_DEFAULT_PAGE_SIZE = 50
_MAX_PAGE_SIZE = 200


@router.get("/servers", response_model=ServerListResponse)
async def list_servers(
    site: str | None = Query(default=None),
    performance_tier: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=_DEFAULT_PAGE_SIZE, ge=1, le=_MAX_PAGE_SIZE),
    session=Depends(get_db),
    claims: Claims = Depends(get_current_user),
) -> ServerListResponse:
    repo = ServerRepository(session)
    servers, total = await repo.list_servers(
        site=site,
        performance_tier=performance_tier,
        status=status,
        page=page,
        page_size=page_size,
    )
    return ServerListResponse(
        data=[ServerResponse.model_validate(s) for s in servers],
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total=total,
            has_next_page=(page * page_size) < total,
        ),
    )


@router.get("/servers/{server_id}", response_model=ServerResponse)
async def get_server(
    server_id: str,
    session=Depends(get_db),
    claims: Claims = Depends(get_current_user),
) -> ServerResponse:
    repo = ServerRepository(session)
    server = await repo.get_by_id(server_id)
    return ServerResponse.model_validate(server)


@router.post("/admin/sync/servers", response_model=SyncResult)
async def trigger_sync(
    claims: Claims = Depends(get_current_user),
) -> SyncResult:
    if not is_super_admin(claims):
        raise ForbiddenError("Only center_admin or platform_admin can trigger server sync")

    async with AsyncSessionLocal() as session:
        async with httpx.AsyncClient(timeout=settings.EXTERNAL_API_TIMEOUT_SECONDS) as client:
            result = await sync_servers(session, client)

    return SyncResult(**result)
