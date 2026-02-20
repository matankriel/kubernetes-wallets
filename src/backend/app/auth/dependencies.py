"""FastAPI dependency for enforcing authentication on protected routes.

Usage:
    @router.get("/protected")
    async def endpoint(claims: Claims = Depends(get_current_user)):
        ...
"""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.jwt import Claims, verify_token
from app.errors import UnauthorizedError

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Claims:
    if credentials is None:
        raise UnauthorizedError("Missing Bearer token")
    return verify_token(credentials.credentials)
