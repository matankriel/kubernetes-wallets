"""Health check endpoints for InfraHub.

GET /health       — liveness probe (no auth, no DB)
GET /health/ready — readiness probe: runs SELECT 1 against the DB
"""

import importlib.metadata

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.database import AsyncSessionLocal

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": importlib.metadata.version("infrahub")}


@router.get("/health/ready")
async def health_ready():
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "detail": "database unavailable"},
        )
