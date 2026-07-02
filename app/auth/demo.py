"""Global DEMO / LOCAL-BYPASS switches (single source of truth).

Two environment flags short-circuit access enforcement for controlled,
NON-PRODUCTION use so the app is reachable through a normal browser without a
live Identity Provider (Azure AD / OIDC) minting Bearer tokens:

  * ``DEMO_MODE``              -> full demo pass-through (auth + RBAC + page guards)
  * ``ECS_LOCAL_AUTH_BYPASS``  -> local/dev auth pass-through (authentication only)

When EITHER flag is on the authentication middleware becomes a transparent
pass-through (no token required). ``DEMO_MODE`` additionally disables RBAC and
page/dashboard guards for executive demonstrations; ``ECS_LOCAL_AUTH_BYPASS`` is
the narrower "let me log in locally" switch and leaves RBAC flags as configured.

Why this is needed: the browser ``/login`` flow issues a server-side redirect and
does NOT mint a JWT/session cookie (the Azure AD / OIDC providers expect the SPA
to attach a Bearer token). So with ``ECS_AUTH_ENABLED=true`` and a token-based
provider, an ordinary browser request to ``/dashboard`` carries no credential and
is rejected with ``missing_token`` (401). These flags provide a safe local escape
hatch without weakening production.

Design constraints (intentional):
  * Default OFF. Absent / blank / unknown -> False (production stays secure).
  * Read from the environment at call time so they are immune to config caching
    and startup ordering, and can never be "stuck on" by a stale cache.
  * NOT for production. Use only on an isolated, non-production/local demo host.
  * Add NO new behaviour to production and remove NO authentication, RBAC,
    Azure AD / OIDC / JWT, or schema code — they only *bypass* enforcement while
    the flag is on. With both flags off, behaviour is exactly as before.
"""

from __future__ import annotations

import os

_TRUTHY = {"1", "true", "yes", "on"}


def _flag(name: str) -> bool:
    """Return True only when env var `name` is explicitly truthy. Never raises."""
    try:
        return str(os.environ.get(name, "")).strip().lower() in _TRUTHY
    except Exception:  # noqa: BLE001 - any failure -> secure default (off)
        return False


def demo_mode() -> bool:
    """Return True only when DEMO_MODE is explicitly enabled. Never raises."""
    return _flag("DEMO_MODE")


def local_auth_bypass() -> bool:
    """Return True only when ECS_LOCAL_AUTH_BYPASS is explicitly enabled.

    Narrow, clearly-named local/dev switch that bypasses ONLY authentication
    (not RBAC), so `/login` works through a browser without a live IdP. Never
    raises; secure default is OFF.
    """
    return _flag("ECS_LOCAL_AUTH_BYPASS")


def auth_bypassed() -> bool:
    """True when authentication should be bypassed for local/demo use.

    Enabled by EITHER ``DEMO_MODE`` or ``ECS_LOCAL_AUTH_BYPASS``. Used by the
    authentication middleware only. Production (both flags off) is unaffected.
    """
    return demo_mode() or local_auth_bypass()
