"""Pluggable authentication providers.

Each provider knows how to turn an incoming request into an AuthenticatedUser
(or raise AuthenticationError). New IdPs are added by subclassing AuthProvider
and registering in PROVIDER_REGISTRY — no changes to middleware required.

Providers shipped in Phase 1:
    AzureADProvider - Azure AD via OIDC/JWT (primary target)
    OidcProvider    - generic OIDC/JWT (future IdPs)
    DevProvider     - local development bypass (explicitly opt-in, off by default)
"""

from __future__ import annotations

from typing import Any

from fastapi import Request

from app.auth.context import AuthenticatedUser, build_user_from_claims
from app.auth.errors import AuthenticationError
from app.auth.jwt_validator import validate_token


def _split_csv(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [p.strip() for p in str(value).split(",") if p.strip()]


def _bearer_token(request: Request) -> str:
    header = request.headers.get("authorization") or request.headers.get("Authorization") or ""
    if not header.lower().startswith("bearer "):
        raise AuthenticationError("missing_token", "Missing or malformed Authorization header.")
    token = header[7:].strip()
    if not token:
        raise AuthenticationError("missing_token", "Empty bearer token.")
    return token


class AuthProvider:
    """Base provider. Subclasses implement `authenticate`."""

    name = "base"

    def __init__(self, auth_cfg: dict[str, Any]) -> None:
        self.auth_cfg = auth_cfg
        self.jwt_cfg = auth_cfg.get("jwt", {}) or {}

    def _claim_map(self) -> dict[str, str]:
        return {k: str(v) for k, v in (self.jwt_cfg.get("claims", {}) or {}).items()}

    def _audiences(self) -> list[str]:
        return _split_csv(self.jwt_cfg.get("allowed_audiences"))

    def _leeway(self) -> int:
        try:
            return int(self.jwt_cfg.get("leeway_seconds", 60))
        except (TypeError, ValueError):
            return 60

    def authenticate(self, request: Request) -> AuthenticatedUser:  # pragma: no cover - abstract
        raise NotImplementedError


class _JwtProvider(AuthProvider):
    """Shared JWT/JWKS bearer-token validation for OIDC-style providers."""

    def _issuer(self) -> str:  # pragma: no cover - overridden
        return ""

    def _jwks_uri(self) -> str:  # pragma: no cover - overridden
        return ""

    def authenticate(self, request: Request) -> AuthenticatedUser:
        token = _bearer_token(request)
        claims = validate_token(
            token,
            jwks_uri=self._jwks_uri(),
            issuer=self._issuer(),
            audiences=self._audiences(),
            leeway=self._leeway(),
        )
        return build_user_from_claims(claims, self._claim_map(), auth_source=self.name)


class AzureADProvider(_JwtProvider):
    """Azure Active Directory (v2.0 endpoint). Issuer/JWKS derive from tenant id
    unless explicitly overridden (for sovereign/national clouds)."""

    name = "azure_ad"

    def _cfg(self) -> dict[str, Any]:
        return self.auth_cfg.get("azure_ad", {}) or {}

    def _tenant(self) -> str:
        return str(self._cfg().get("tenant_id", "")).strip()

    def _issuer(self) -> str:
        override = str(self._cfg().get("issuer", "")).strip()
        if override:
            return override
        tenant = self._tenant()
        return f"https://login.microsoftonline.com/{tenant}/v2.0" if tenant else ""

    def _jwks_uri(self) -> str:
        override = str(self._cfg().get("jwks_uri", "")).strip()
        if override:
            return override
        tenant = self._tenant()
        return f"https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys" if tenant else ""

    def _audiences(self) -> list[str]:
        auds = super()._audiences()
        # Default to the app's own client id as the expected audience.
        client_id = str(self._cfg().get("client_id", "")).strip()
        if not auds and client_id:
            auds = [client_id, f"api://{client_id}"]
        return auds


class OidcProvider(_JwtProvider):
    """Generic OIDC provider for future IdPs (Okta, Keycloak, ForgeRock, ...)."""

    name = "oidc"

    def _cfg(self) -> dict[str, Any]:
        return self.auth_cfg.get("oidc", {}) or {}

    def _issuer(self) -> str:
        return str(self._cfg().get("issuer", "")).strip()

    def _jwks_uri(self) -> str:
        return str(self._cfg().get("jwks_uri", "")).strip()

    def _audiences(self) -> list[str]:
        auds = super()._audiences()
        client_id = str(self._cfg().get("client_id", "")).strip()
        if not auds and client_id:
            auds = [client_id]
        return auds


class DevProvider(AuthProvider):
    """Local development bypass. Returns a static principal so engineers can run
    ECS without a live IdP. Activated ONLY when dev_mode.enabled is true; the
    middleware additionally refuses to use it unless that flag is set."""

    name = "dev"

    def authenticate(self, request: Request) -> AuthenticatedUser:
        p = (self.auth_cfg.get("dev_mode", {}) or {}).get("principal", {}) or {}
        return AuthenticatedUser(
            user_id=str(p.get("user_id", "dev-user")),
            username=str(p.get("username", "developer")),
            display_name=str(p.get("display_name", "Local Developer")),
            email=str(p.get("email", "developer@localhost")),
            roles=tuple(_split_csv(p.get("roles", "admin"))),
            groups=tuple(_split_csv(p.get("groups"))),
            auth_source="dev",
        )


PROVIDER_REGISTRY: dict[str, type[AuthProvider]] = {
    "azure_ad": AzureADProvider,
    "oidc": OidcProvider,
    "dev": DevProvider,
}


def build_provider(auth_cfg: dict[str, Any]) -> AuthProvider:
    """Instantiate the configured provider. Dev-mode forces the dev provider."""
    dev_enabled = bool((auth_cfg.get("dev_mode", {}) or {}).get("enabled", False))
    if dev_enabled:
        return DevProvider(auth_cfg)
    name = str(auth_cfg.get("provider", "azure_ad")).strip().lower()
    cls = PROVIDER_REGISTRY.get(name)
    if cls is None:
        raise AuthenticationError("unknown_provider", f"Unknown auth provider: {name}")
    return cls(auth_cfg)
