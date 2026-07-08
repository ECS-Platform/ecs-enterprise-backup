"""DB Agent security extension points (PROTOTYPE — all OFF by default).

>>> THIS IS A PROTOTYPE. THIS IS NOT PRODUCTION SECURE. <<<

The prototype intentionally implements NONE of the enterprise security controls.
This module provides OPTIONAL, OFF-BY-DEFAULT extension points so a future
production deployment can enable them purely through configuration (the
``ENABLE_*`` flags) WITHOUT changing the DB Agent architecture.

Every gate below returns ``False`` unless its flag is explicitly enabled, and the
enforcement helpers are safe no-ops while disabled — so a missing security stack
never blocks the agent from starting or serving.

Future production deployment should enable and implement:
  * TLS / mTLS                (ENABLE_MTLS)
  * JWT / OIDC authentication (ENABLE_JWT, ENABLE_OIDC)
  * Vault / enterprise secret management (ENABLE_VAULT)
  * Certificate authentication (ENABLE_CERT_AUTH)
  * Centralized identity
  * Audit logging enhancements
"""

from __future__ import annotations

import os
from typing import Any

_TRUTHY = {"1", "true", "yes", "on"}


def _flag(name: str) -> bool:
    """True only when the ENABLE_* flag is explicitly truthy. Default OFF."""
    try:
        return str(os.environ.get(name, "")).strip().lower() in _TRUTHY
    except Exception:  # noqa: BLE001 - any failure -> secure-for-prototype default (off)
        return False


# --------------------------------------------------------------------------- #
# Optional feature gates (all default False)
# --------------------------------------------------------------------------- #
def mtls_enabled() -> bool:
    return _flag("ENABLE_MTLS")


def jwt_enabled() -> bool:
    return _flag("ENABLE_JWT")


def vault_enabled() -> bool:
    return _flag("ENABLE_VAULT")


def oidc_enabled() -> bool:
    return _flag("ENABLE_OIDC")


def cert_auth_enabled() -> bool:
    return _flag("ENABLE_CERT_AUTH")


def enabled_features() -> dict[str, bool]:
    """Snapshot of which optional security features are enabled (all off in demo)."""
    return {
        "ENABLE_MTLS": mtls_enabled(),
        "ENABLE_JWT": jwt_enabled(),
        "ENABLE_VAULT": vault_enabled(),
        "ENABLE_OIDC": oidc_enabled(),
        "ENABLE_CERT_AUTH": cert_auth_enabled(),
    }


def any_enabled() -> bool:
    return any(enabled_features().values())


# --------------------------------------------------------------------------- #
# Extension-point stubs — safe no-ops while disabled.
# These are where future production security integrations belong. Keeping them as
# explicit, disabled hooks means enabling security later is a config + drop-in
# change, not an architecture change.
# --------------------------------------------------------------------------- #
def resolve_secret(name: str, fallback: str = "") -> str:
    """Resolve a secret value.

    PROTOTYPE: reads the plain environment variable (or returns the fallback).

    TODO(prod-security): when ``ENABLE_VAULT`` is set, fetch ``name`` from the
    enterprise secret manager (HashiCorp Vault / cloud secret store) instead of
    the environment. Never log the resolved value.
    """
    if vault_enabled():
        # TODO(prod-security): integrate Vault/enterprise secret manager here.
        # Intentionally NOT implemented in the prototype — fall through to env so
        # enabling the flag before wiring Vault still starts (just uses env).
        pass
    val = os.environ.get(name)
    return val if val not in (None, "") else fallback


def authenticate_request(headers: dict[str, Any]) -> tuple[bool, str]:
    """Authenticate an inbound request.

    PROTOTYPE: authentication is DISABLED — every request is allowed. Returns
    ``(True, "prototype: auth disabled")`` so callers have a uniform contract.

    TODO(prod-security): when ``ENABLE_JWT`` / ``ENABLE_OIDC`` is set, validate
    the Bearer token (JWKS/OIDC discovery) here and reject invalid/absent tokens
    with a clear 401. Keep the return contract ``(ok, reason)``.
    """
    if jwt_enabled() or oidc_enabled():
        # TODO(prod-security): validate JWT/OIDC token from headers here.
        # Prototype does not enforce — allow, but signal that a hook is pending.
        return True, "prototype: token validation not implemented (hook pending)"
    return True, "prototype: auth disabled"


def tls_context() -> Any | None:
    """Return a TLS/mTLS context for the server, or ``None`` (plain HTTP).

    PROTOTYPE: returns ``None`` — the agent serves plain HTTP on an internal,
    secured network (jump server). No certificates are required to start.

    TODO(prod-security): when ``ENABLE_MTLS`` / ``ENABLE_CERT_AUTH`` is set, build
    an ``ssl.SSLContext`` with the server cert/key and (for mTLS) a client CA +
    ``verify_mode = CERT_REQUIRED`` here, and pass it to the ASGI server.
    """
    if mtls_enabled() or cert_auth_enabled():
        # TODO(prod-security): construct and return an ssl.SSLContext here.
        return None
    return None


def posture() -> dict[str, Any]:
    """Human-readable prototype security posture (for /security and logs)."""
    return {
        "prototype": True,
        "production_secure": False,
        "note": "PROTOTYPE — no enterprise security enforced. See db_agent/README.md.",
        "optional_features": enabled_features(),
        "any_enabled": any_enabled(),
    }
