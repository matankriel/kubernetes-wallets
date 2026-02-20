"""LDAP client abstraction for InfraHub authentication.

LDAPClient is an ABC so tests can inject MockLDAPClient without a real LDAP
server. RealLDAPClient uses ldap3:
  1. Bind with the user's credentials (password verification)
  2. Re-bind as the service account
  3. Search the user's entry for memberOf attribute
  4. Return the list of group CN strings
"""

from abc import ABC, abstractmethod

from ldap3 import Connection, Server, Tls
from ldap3.core.exceptions import LDAPBindError, LDAPException

from app.config import settings
from app.errors import UnauthorizedError


class LDAPClient(ABC):
    @abstractmethod
    async def authenticate(self, username: str, password: str) -> list[str]:
        """Verify credentials and return the user's group CN list.

        Raises UnauthorizedError if the credentials are invalid.
        """


class RealLDAPClient(LDAPClient):
    async def authenticate(self, username: str, password: str) -> list[str]:
        host = settings.LDAP_HOST
        port = settings.LDAP_PORT
        use_ssl = settings.LDAP_USE_SSL

        tls = Tls() if use_ssl else None
        srv = Server(host, port=port, use_ssl=use_ssl, tls=tls)

        user_dn = f"cn={username},{settings.LDAP_BASE_DN}"

        # Step 1: verify user password via direct bind
        try:
            user_conn = Connection(srv, user=user_dn, password=password, auto_bind=True)
            user_conn.unbind()
        except (LDAPBindError, LDAPException) as exc:
            raise UnauthorizedError("Invalid credentials") from exc

        # Step 2: re-bind as service account to read group membership
        try:
            svc_conn = Connection(
                srv,
                user=settings.LDAP_BIND_DN,
                password=settings.LDAP_BIND_PASSWORD,
                auto_bind=True,
            )
        except (LDAPBindError, LDAPException) as exc:
            raise UnauthorizedError("Service account bind failed") from exc

        # Step 3: fetch memberOf attribute
        svc_conn.search(
            search_base=settings.LDAP_BASE_DN,
            search_filter=f"(cn={username})",
            attributes=["memberOf"],
        )
        svc_conn.unbind()

        if not svc_conn.entries:
            return []

        member_of: list = svc_conn.entries[0].memberOf.values if hasattr(
            svc_conn.entries[0], "memberOf"
        ) else []

        # Extract just the CN part from each DN (e.g. "cn=foo,dc=..." → "foo")
        group_cns: list[str] = []
        for dn in member_of:
            parts = dn.split(",")
            if parts:
                cn_part = parts[0]
                if cn_part.lower().startswith("cn="):
                    group_cns.append(cn_part[3:])

        return group_cns
