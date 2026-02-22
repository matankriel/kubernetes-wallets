"""Auth router: POST /api/v1/auth/login

Login priority order:
  1. LDAP bind to verify password and retrieve group CNs.
  2. DB lookup in user_roles table — if a row exists, use that role/scope_id.
  3. Else: map LDAP group CNs to role/scope_id.

LDAP group → role mapping order (first match wins):
  infrahub-platform-admins        → platform_admin, scope_id=None
  infrahub-center-admins          → center_admin, scope_id=None
  infrahub-field-admins-<id>      → field_admin,  scope_id=<id>
  infrahub-dept-admins-<id>       → dept_admin,   scope_id=<id>
  infrahub-team-leads-<id>        → team_lead,    scope_id=<id>
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import build_claims, create_token
from app.auth.ldap_client import LDAPClient, RealLDAPClient
from app.database import get_db
from app.errors import ForbiddenError, UnauthorizedError
from app.repositories.user_role_repo import UserRoleRepository

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 900


def _map_groups_to_role(group_cns: list[str]) -> tuple[str, str | None]:
    """Return (role, scope_id) from the first matching infrahub-* group CN.

    Raises ForbiddenError if no infrahub-* group is found.
    """
    for cn in group_cns:
        if cn == "infrahub-platform-admins":
            return "platform_admin", None
        if cn == "infrahub-center-admins":
            return "center_admin", None
        if cn.startswith("infrahub-field-admins-"):
            return "field_admin", cn.removeprefix("infrahub-field-admins-")
        if cn.startswith("infrahub-dept-admins-"):
            return "dept_admin", cn.removeprefix("infrahub-dept-admins-")
        if cn.startswith("infrahub-team-leads-"):
            return "team_lead", cn.removeprefix("infrahub-team-leads-")
    raise ForbiddenError("No InfraHub role assigned to this user")


def get_ldap_client() -> LDAPClient:
    return RealLDAPClient()


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    ldap: LDAPClient = Depends(get_ldap_client),
    session: AsyncSession = Depends(get_db),
) -> LoginResponse:
    try:
        group_cns = await ldap.authenticate(body.username, body.password)
    except UnauthorizedError:
        raise UnauthorizedError("Invalid credentials")

    # DB role override takes precedence over LDAP group mapping.
    db_role_row = await UserRoleRepository(session).get_by_username(body.username)
    if db_role_row is not None:
        role, scope_id = db_role_row.role, db_role_row.scope_id
    else:
        role, scope_id = _map_groups_to_role(group_cns)

    claims = build_claims(sub=body.username, role=role, scope_id=scope_id)
    token = create_token(claims)

    return LoginResponse(access_token=token)
