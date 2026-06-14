"""Global DEMO MODE switch (single source of truth).

A SINGLE environment flag, ``DEMO_MODE``, that short-circuits ALL access
enforcement for controlled executive demonstrations:

  * authentication middleware  -> transparent pass-through (no token required)
  * RBAC enforcement           -> disabled (legacy allow-all behaviour)
  * page / dashboard guards     -> disabled (no 403s)

Design constraints (intentional):
  * Default OFF.  Absent / blank / unknown -> False (production stays secure).
  * Read from the environment at call time so it is immune to config caching
    and startup ordering, and so it can never be "stuck on" by a stale cache.
  * NOT for production.  Use only on an isolated, non-production demo host.
  * Adds NO new behaviour to production and removes NO authentication, RBAC,
    Azure AD / OIDC / JWT, or schema code — it only *bypasses* enforcement
    while the flag is on.
"""

from __future__ import annotations

import os

_TRUTHY = {"1", "true", "yes", "on"}


def demo_mode() -> bool:
    """Return True only when DEMO_MODE is explicitly enabled. Never raises."""
    try:
        return str(os.environ.get("DEMO_MODE", "")).strip().lower() in _TRUTHY
    except Exception:  # noqa: BLE001 - any failure -> secure default (off)
        return False
