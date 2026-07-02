"""Central user-context abstraction for ECS.

`AuthenticatedUser` is the single, trusted identity object produced by the
authentication layer after a token (or dev-mode bypass) is validated. It is
attached to `request.state.principal` by the middleware and exposed everywhere
via the `get_current_principal` FastAPI dependency.

This object carries roles/groups, but makes NO authorization decisions — that is
deferred to later RBAC phases which will consume this identity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastapi import Request


@dataclass(frozen=True)
class AuthenticatedUser:
    """Immutable, server-validated identity for the current request."""

    user_id: str
    username: str = ""
    display_name: str = ""
    email: str = ""
    roles: tuple[str, ...] = field(default_factory=tuple)
    groups: tuple[str, ...] = field(default_factory=tuple)
    # Provider that authenticated this principal (azure_ad | oidc | dev).
    auth_source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "display_name": self.display_name,
            "email": self.email,
            "roles": list(self.roles),
            "groups": list(self.groups),
            "auth_source": self.auth_source,
        }

    @property
    def is_authenticated(self) -> bool:
        return bool(self.user_id)


def _as_tuple(value: Any) -> tuple[str, ...]:
    """Normalize a claim that may be a list, comma-string, or scalar to a tuple."""
    if value is None or value == "":
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(str(v).strip() for v in value if str(v).strip())
    return tuple(p.strip() for p in str(value).split(",") if p.strip())


def build_user_from_claims(claims: dict[str, Any], claim_map: dict[str, str],
                           *, auth_source: str) -> AuthenticatedUser:
    """Construct an AuthenticatedUser from validated token claims using the
    configured claim-name mapping (Azure AD vs generic OIDC differ)."""
    return AuthenticatedUser(
        user_id=str(claims.get(claim_map.get("user_id", "sub"), claims.get("sub", ""))),
        username=str(claims.get(claim_map.get("username", "preferred_username"), "")),
        display_name=str(claims.get(claim_map.get("display_name", "name"), "")),
        email=str(claims.get(claim_map.get("email", "email"), "")),
        roles=_as_tuple(claims.get(claim_map.get("roles", "roles"))),
        groups=_as_tuple(claims.get(claim_map.get("groups", "groups"))),
        auth_source=auth_source,
    )


def current_principal(request: Request) -> AuthenticatedUser | None:
    """Return the principal attached to the request (or None if unauthenticated)."""
    return getattr(request.state, "principal", None)


def get_current_principal(request: Request) -> AuthenticatedUser:
    """FastAPI dependency: return the authenticated user for the current request.

    By the time a protected route runs, the middleware has already validated and
    attached the principal. If it is somehow absent (e.g. dependency used on a
    public route while auth is disabled), raise rather than guess an identity.
    """
    principal = current_principal(request)
    if principal is None or not principal.is_authenticated:
        from app.auth.errors import AuthenticationError

        raise AuthenticationError("no_principal", "Authentication required")
    return principal
