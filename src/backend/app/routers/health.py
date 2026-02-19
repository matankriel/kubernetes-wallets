"""Health check endpoints for InfraHub.

Both endpoints are unauthenticated and mounted at root (no /api/v1 prefix).
Used by Kubernetes liveness and readiness probes.
"""

import importlib.metadata

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe: returns 200 if the application process is running."""
    version = importlib.metadata.version("infrahub")
    return {"status": "ok", "version": version}


@router.get("/health/ready")
async def health_ready(  # type: ignore[return]
    session: AsyncSession = Depends(get_db),
):
    """Readiness probe: returns 200 if the DB is reachable, 503 otherwise."""
    try:
        await session.execute(text("SELECT 1"))
        return JSONResponse(status_code=200, content={"status": "ok"})
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=503,
