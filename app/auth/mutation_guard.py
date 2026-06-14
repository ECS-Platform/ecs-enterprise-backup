"""Critical-mutation authorization guard (Phase 2, Step 2D-critical).

A single helper that protects HIGH-RISK mutation endpoints by deriving the role from
the authenticated Phase 1 principal and evaluating a PolicyEngine-backed permission
via the Step 2B enforcement foundation (app/auth/enforcement.enforce_permission).

SCOPE — critical mutations only:
  * No page guards, no dashboard guards, no scope filtering, no GET restrictions.
  * Only the explicitly-wired mutation handlers call guard_mutation().

Gated by RBAC_MUTATION_ENFORCEMENT_ENABLED (default FALSE):
  * OFF -> guard_mutation() always returns None (allow); existing ECS behavior and
    UX are byte-for-byte unchanged.
  * ON  -> the effective role comes from the principal; if it lacks the required
    permission the guard returns a denial RESPONSE that the caller returns directly:
      - browser workflow routes: RedirectResponse(303) preserving existing UX
      - JSON APIs: JSONResponse(403) with a structured body

Best-effort and fail-safe-to-legacy: any internal error returns None (allow), so a
guard problem can never harden into an outage. (Hard-deny-on-error is deliberately
avoided in this additive step.)
"""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote

from fastapi.responses import JSONResponse, RedirectResponse


def mutation_enforcement_enabled() -> bool:
    """Feature flag. Default FALSE: no mutation is gated (legacy behavior)."""
    return str(os.environ.get("RBAC_MUTATION_ENFORCEMENT_ENABLED", "")).strip().lower() in {
        "1", "true", "yes", "on",
    }


def is_allowed(request: Any, capability: str, fallback_role: str = "") -> bool:
    """Return whether the current request may perform `capability`.

    Always True when the flag is off. When on, delegates to the Step 2B enforcement
    foundation (principal-derived role + PolicyEngine). Never raises."""
    if not mutation_enforcement_enabled():
        return True
    try:
        from app.auth.enforcement import enforce_permission

        return bool(enforce_permission(request, capability, fallback_role))
    except Exception:  # noqa: BLE001 - fail safe to allow (additive hardening)
        return True


def _denied_role(request: Any, fallback_role: str) -> str:
    try:
        from app.auth.enforcement import resolve_effective_role

        return resolve_effective_role(request, fallback_role) or fallback_role or "unknown"
    except Exception:  # noqa: BLE001
        return fallback_role or "unknown"


def guard_mutation(request: Any, capability: str, *, fallback_role: str = "",
                   response: str = "redirect", deny_redirect_to: str = "/dashboard",
                   role: str = "", user: str = "",
                   message: str = "") -> Any | None:
    """Authorize a critical mutation. Returns None to allow, or a denial response.

    Parameters:
      capability        - legacy-compat permission key (e.g. 'can_escalate').
      fallback_role     - the caller-supplied role used when enforcement is off or no
                          principal is present (preserves legacy behavior).
      response          - 'redirect' (browser routes) or 'json' (APIs).
      deny_redirect_to  - base path for the 303 redirect on browser denial.
      role/user         - echoed into the redirect URL to keep existing UX/context.
      message           - optional custom denial notice.

    When the flag is off this returns None immediately (no behavior change)."""
    if not mutation_enforcement_enabled():
        return None
    if is_allowed(request, capability, fallback_role):
        return None

    eff = _denied_role(request, fallback_role)
    detail = message or f"Access denied: role '{eff}' is not permitted to perform this action."
    if response == "json":
        return JSONResponse(
            {"ok": False, "error": "forbidden", "reason": "insufficient_permission",
             "capability": capability, "detail": detail},
            status_code=403,
        )
    # Browser workflow route: preserve the existing redirect UX.
    sep = "&" if "?" in deny_redirect_to else "?"
    url = (f"{deny_redirect_to}{sep}role={quote(role or fallback_role)}"
           f"&user={quote(user or '')}&notice={quote(detail)}")
    return RedirectResponse(url=url, status_code=303)
