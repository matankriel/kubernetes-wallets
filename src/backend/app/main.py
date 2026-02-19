"""InfraHub FastAPI application factory.

Entry point: uvicorn app.main:app
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.database import async_engine
from app.errors import InfraHubError
from app.middleware import RequestIDMiddleware, get_request_id
from app.routers import auth, health


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    yield
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
