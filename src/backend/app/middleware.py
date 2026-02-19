"""Request ID middleware for InfraHub.

Generates a UUID4 per request, stores it in a ContextVar so it can be
retrieved anywhere in the request lifecycle, and attaches it as a
X-Request-ID response header.
"""

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Module-level ContextVar — allows non-HTTP code (services, repos) to read
# the current request ID without needing the Request object.
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    return request_id_var.get()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Generates a UUID4 request ID, sets the ContextVar, and adds the
    X-Request-ID header to every response."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        req_id = str(uuid.uuid4())
        request_id_var.set(req_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response
