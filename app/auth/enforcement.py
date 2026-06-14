"""RBAC enforcement foundation (Phase 2, Step 2B).

This module closes the core authorization gap identified in the Step 2B analysis:
ECS authorization historically trusts a `role` value supplied by the client (query
param / form field / JSON body), while the Phase 1 authenticated identity on
`request.state.principal` is ignored. This foundation introduces ONE place to derive
the *effective* role and to evaluate authorization decisions against the canonical
PolicyEngine.

SCOPE — foundation only:
  * It provides resolve_effective_role(), enforce_permission(), enforce_page().
  * It is NOT attached to any route, dashboard, or API in this step.
  * It does NOT implement page guards, API guards, scope filtering, or login changes.

Behavior is gated by RBAC_ENFORCEMENT_ENABLED (default FALSE):
  * OFF  -> resolve_effective_role() returns the caller-supplied role (legacy
           behavior); enforcement helpers evaluate exactly the legacy capability
           logic. ECS behaves byte-for-byte as before.
  * ON   -> the effective role is derived from the authenticated principal
           (principal.roles[0], canonically normalized); the client-supplied role
           is no longer trusted. The capability *decision logic* is unchanged
           (delegated to PolicyEngine.can_legacy), so for any fixed role the result
           is identical to today — only the SOURCE of the role changes.

Best-effort: every public function tolerates a missing principal / engine / config
and never raises, so once wired it can never break a request.
"""

from __future__ import annotations

import os
from typing import Any

from app.auth.roles import DEFAULT_ROLE, normalize_role


def rbac_enforcement_enabled() -> bool:
    """Feature flag. Default FALSE: authorization uses caller-supplied role.

    Global DEMO_MODE forces this OFF so RBAC never blocks a demo.
    """
    try:
        from app.auth.demo import demo_mode
        if demo_mode():
            return False
    except Exception:  # noqa: BLE001
        pass
    return str(os.environ.get("RBAC_ENFORCEMENT_ENABLED", "")).strip().lower() in {
        "1", "true", "yes", "on",
    }


def _principal_of(request: Any):
    """Return request.state.principal if present, else None. Never raises."""
    try:
        return getattr(getattr(request, "state", None), "principal", None)
    except Exception:  # noqa: BLE001
        return None


def _principal_role(principal: Any) -> str | None:
    """First role carried by an authenticated principal, or None."""
    if principal is None or not getattr(principal, "is_authenticated", False):
        return None
    roles = getattr(principal, "roles", ()) or ()
    return roles[0] if roles else None


def resolve_effective_role(request: Any, fallback_role: str = "") -> str:
    """Resolve the role that authorization should use for this request.

    Enforcement OFF -> the caller-supplied `fallback_role` (legacy behavior),
    returned verbatim so downstream legacy logic is unchanged.

    Enforcement ON  -> the role carried by the authenticated principal. The role is
    returned in its ORIGINAL namespace (trimmed/lower-cased only), NOT remapped into
    the canonical taxonomy here. This is deliberate: capability evaluation goes
    through the Step 2A legacy-compat path (PolicyEngine.can_legacy), which applies
    the legacy normalization itself; cross-mapping here too would double-normalize
    and break bug-for-bug parity (e.g. owner -> application_owner -> not in legacy
    `owner` sets). When no authenticated principal is available (e.g. auth disabled
    for a controlled demo) it falls back to `fallback_role`.

    Never raises.
    """
    if not rbac_enforcement_enabled():
        return fallback_role
    principal = _principal_of(request)
    pr = _principal_role(principal)
    if pr:
        return str(pr).strip().lower()
    # No usable principal -> degrade to the supplied role (do not hard-deny here;
    # hard-deny is an enforcement-call-site concern handled in later steps).
    return fallback_role


def canonical_effective_role(request: Any, fallback_role: str = "") -> str:
    """Like resolve_effective_role but mapped into the canonical taxonomy.

    Use this where a CANONICAL role key is required (e.g. page-catalog lookups via
    PolicyEngine.can_view_page). Capability checks must use resolve_effective_role
    (legacy namespace) instead, to preserve Step 2A parity.
    """
    return normalize_role(resolve_effective_role(request, fallback_role))


def enforce_permission(request: Any, capability: str, fallback_role: str = "") -> bool:
    """Authoritative capability check for the current request.

    Returns the SAME boolean the legacy predicate produces for the *effective* role:
      * Enforcement OFF -> effective role == fallback_role (caller-supplied), so the
        result equals the legacy predicate exactly.
      * Enforcement ON  -> effective role comes from the principal; the decision is
        still evaluated by PolicyEngine.can_legacy (the bug-for-bug legacy map from
        Step 2A), so for a fixed role the verdict is identical to legacy.

    Falls back to None-safe legacy evaluation if the engine is unavailable. Never
    raises.
    """
    role = resolve_effective_role(request, fallback_role)
    return _capability_verdict(role, capability, fallback_role)


def enforce_page(request: Any, page: str, fallback_role: str = "") -> bool:
    """Page-visibility check for the current request (foundation only; not wired).

    Uses the canonical PolicyEngine page catalog. Enforcement OFF returns True
    (legacy dashboards are not page-gated today), so attaching this later behind the
    flag introduces no behavior change while the flag is off. Never raises.
    """
    if not rbac_enforcement_enabled():
        return True
    # Page catalog is keyed by canonical role -> use the canonical mapping here.
    role = canonical_effective_role(request, fallback_role)
    try:
        from app.auth.authz import get_policy_engine

        return bool(get_policy_engine().can_view_page(role, page))
    except Exception:  # noqa: BLE001 - never block on engine/config errors
        return True


def _capability_verdict(role: str, capability: str, fallback_role: str) -> bool:
    """Evaluate a capability for a role via the legacy-compat PolicyEngine map.

    This deliberately reuses the Step 2A bug-for-bug `can_legacy` path so parity is
    guaranteed. If the engine cannot answer (unknown capability / config error), it
    falls back to the verbatim legacy predicate in role_permissions, preserving
    behavior. Never raises."""
    try:
        from app.auth.authz import get_policy_engine

        return bool(get_policy_engine().can_legacy(role, capability))
    except Exception:  # noqa: BLE001
        return _legacy_predicate(capability, role if role else fallback_role)


def _legacy_predicate(capability: str, role: str) -> bool:
    """Final fallback: call the verbatim legacy predicate by name. Never raises."""
    try:
        from modules.shared.services import role_permissions as rp

        fn = getattr(rp, capability, None)
        if callable(fn):
            return bool(fn(role))
    except Exception:  # noqa: BLE001
        pass
    return False
