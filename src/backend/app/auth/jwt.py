"""JWT issuance and verification for InfraHub.

Uses python-jose with HS256. Tokens expire in 15 minutes (900 seconds).
Claims is a plain dataclass — no ORM, no database dependency.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from jose import ExpiredSignatureError, JWTError, jwt

from app.config import settings
from app.errors import UnauthorizedError

_ALGORITHM = "HS256"
_EXPIRY_SECONDS = 900  # 15 minutes


@dataclass
class Claims:
    sub: str
    role: str
    scope_id: str | None
    exp: int


def create_token(claims: Claims) -> str:
    payload = {
        "sub": claims.sub,
        "role": claims.role,
        "scope_id": claims.scope_id,
        "exp": claims.exp,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=_ALGORITHM)


def build_claims(sub: str, role: str, scope_id: str | None) -> Claims:
    exp = int(datetime.now(UTC).timestamp()) + _EXPIRY_SECONDS
    return Claims(sub=sub, role=role, scope_id=scope_id, exp=exp)


def verify_token(token: str) -> Claims:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[_ALGORITHM])
    except ExpiredSignatureError as exc:
        raise UnauthorizedError("Token has expired") from exc
    except JWTError as exc:
        raise UnauthorizedError("Invalid token") from exc

    return Claims(
        sub=payload["sub"],
        role=payload["role"],
        scope_id=payload.get("scope_id"),
        exp=payload["exp"],
    )
