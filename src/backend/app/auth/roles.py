"""Shared role helpers used across services.

platform_admin and center_admin are treated as super-admins that bypass
all scoped RBAC checks in the service layer.
"""

from app.auth.jwt import Claims

SUPER_ADMIN_ROLES: frozenset[str] = frozenset({"center_admin", "platform_admin"})


def is_super_admin(claims: Claims) -> bool:
    """Return True if the caller is center_admin or platform_admin."""
    return claims.role in SUPER_ADMIN_ROLES
