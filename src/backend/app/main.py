"""InfraHub FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.errors import InfraHubError
from app.middleware import RequestIDMiddleware, request_id_var
from app.routers import health


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    """Application lifespan manager.

    Startup: The DB engine is created at module import time in database.py.
    Shutdown: Dispose the connection pool to release DB connections cleanly.
    """
    from app.database import async_engine  # noqa: PLC0415

    yield

    await async_engine.dispose()


app = FastAPI(
    title="InfraHub",
    description=(
        "Centralized, air-gapped, on-prem platform for managing Kubernetes "
        "namespaces and bare-metal servers across a large enterprise."
    ),
    lifespan=lifespan,
)

# Middleware
app.add_middleware(RequestIDMiddleware)


# Exception Handlers
@app.exception_handler(InfraHubError)
async def infrahub_exception_handler(request: Request, exc: InfraHubError) -> JSONResponse:
    """Convert any InfraHubError subclass to the standard API error response format.

    Response shape:
        {"error": {"code": "...", "message": "...", "request_id": "..."}}
    """
    req_id = request_id_var.get("")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
