"""InfraHub FastAPI application factory.

Entry point: uvicorn app.main:app
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import AsyncSessionLocal, async_engine
from app.errors import InfraHubError
from app.middleware import RequestIDMiddleware, get_request_id
from app.routers import allocations, auth, calculator, health, projects, servers
from app.sync.server_sync import sync_servers


async def _scheduled_sync(http_client: httpx.AsyncClient) -> None:
    async with AsyncSessionLocal() as session:
        await sync_servers(session, http_client)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    http_client = httpx.AsyncClient(timeout=settings.EXTERNAL_API_TIMEOUT_SECONDS)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _scheduled_sync,
        "interval",
        minutes=settings.SYNC_INTERVAL_MINUTES,
        args=[http_client],
    )
    scheduler.start()

    yield

    scheduler.shutdown(wait=False)
    await http_client.aclose()
    await async_engine.dispose()


app = FastAPI(title="InfraHub", lifespan=lifespan)

app.add_middleware(RequestIDMiddleware)


@app.exception_handler(InfraHubError)
async def infrahub_error_handler(request: Request, exc: InfraHubError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "request_id": get_request_id(),
            }
        },
        headers={"X-Request-ID": get_request_id()},
    )


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(servers.router)
app.include_router(allocations.router)
app.include_router(projects.router)
app.include_router(calculator.router)
