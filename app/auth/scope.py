"""Data scope filtering (Phase 2, Step 3 — final RBAC hardening).

Page/mutation enforcement (Steps 2B–2D) control WHICH pages and actions a principal
may use. This module controls WHAT DATA a principal may see within those pages: an
application owner should see only their applications, a vertical head only their
vertical, etc., while enterprise roles (CIO, auditor, compliance, security, admin)
see everything.

It builds on the existing scope model already encoded in config/rbac.yaml
(`rbac_catalog.role_scope` + `rbac_catalog.scope_filters`) and the PolicyEngine /
RbacPolicy helpers — it does NOT introduce a second scope model.

SCOPE — data visibility only:
  * No new dashboards, no dashboard redesign, no page guards, no mutation authz,
    no auth/audit/RAG redesign, no API response-schema changes.

Gated by RBAC_SCOPE_FILTERING_ENABLED (default FALSE):
  * OFF -> resolve_scope()/scope_filter() report intent, but apply_scope() and
           scope_sql() are PASS-THROUGH (rows/queries unchanged) -> existing ECS
           behavior is byte-for-byte preserved.
  * ON  -> apply_scope() filters in-memory row lists and scope_sql() yields a WHERE
           fragment, both derived from the AUTHENTICATED principal (role +
           assignments). Query/form parameters are never trusted for scope.

Best-effort: every public function tolerates a missing principal/engine and never
raises; on any error it falls back to PASS-THROUGH (show data) rather than hiding it
unexpectedly, because this is additive hardening, not a hard data firewall.
"""

from __future__ import annotations

import os
from typing import Any, Iterable, Sequence

# Assignment dimensions and the principal-group prefixes that populate them.
# A Phase 1 principal carries `groups` (e.g. from Azure AD). By convention a group
# like "app:payments-api" grants the application assignment "payments-api".
_GROUP_PREFIXES = {
    "vertical": ("vertical:", "vert:"),
    "function": ("function:", "func:"),
    "application": ("app:", "application:"),
    "control": ("control:", "ctrl:"),
}

# Default in-memory row keys checked for each scope field (any match passes).
_DEFAULT_ROW_FIELDS = {
    "vertical": ("vertical", "business_unit", "bu"),
    "function": ("function", "function_name"),
    "application": ("application", "app", "application_name", "app_name"),
    "control": ("control", "control_id"),
}


def scope_filtering_enabled() -> bool:
    """Feature flag. Default FALSE: scope filtering is pass-through (no change)."""
    return str(os.environ.get("RBAC_SCOPE_FILTERING_ENABLED", "")).strip().lower() in {
        "1", "true", "yes", "on",
    }


def _principal_of(request: Any):
    try:
        return getattr(getattr(request, "state", None), "principal", None)
    except Exception:  # noqa: BLE001
        return None


def resolve_scope(request: Any, fallback_role: str = "") -> str:
    """Return the scope dimension for the current request's effective role.

    One of: enterprise | vertical | function | application | control. Derived from
    the authenticated principal's canonical role (Step 2B).

    Fail-safe-to-show: if there is no authenticated principal AND no usable fallback
    role, returns 'enterprise' (no restriction) rather than collapsing to the default
    'application' scope — we never hide data for an unidentifiable caller. A restricted
    scope is returned ONLY when a scoped role is positively identified. Never raises."""
    try:
        from app.auth.enforcement import canonical_effective_role
        from app.auth.authz import get_policy_engine

        principal = _principal_of(request)
        has_principal_role = bool(
            principal is not None and getattr(principal, "is_authenticated", False)
            and (getattr(principal, "roles", ()) or ()))
        if not has_principal_role and not fallback_role:
            return "enterprise"
        role = canonical_effective_role(request, fallback_role)
        return get_policy_engine().scope_for(role) or "enterprise"
    except Exception:  # noqa: BLE001
        return "enterprise"


def resolve_assignments(request: Any) -> dict[str, list[str]]:
    """Derive the principal's scope assignments (the values they own).

    Reads the authenticated principal's `groups` using the documented prefix
    convention (e.g. 'app:payments-api' -> assignments['application'] += 'payments-api').
    Never trusts query/form parameters. Returns {} when no principal/groups exist."""
    principal = _principal_of(request)
    if principal is None:
        return {}
    groups = getattr(principal, "groups", ()) or ()
    out: dict[str, list[str]] = {}
    for g in groups:
        gl = str(g).strip()
        low = gl.lower()
        for field, prefixes in _GROUP_PREFIXES.items():
            for pref in prefixes:
                if low.startswith(pref):
                    out.setdefault(field, []).append(gl[len(pref):].strip())
                    break
    return out


def scope_filter(request: Any, fallback_role: str = "") -> dict[str, Any]:
    """Return the scope filter for the current request.

    {} -> no restriction (enterprise scope, or flag off). Otherwise
    {"field": <dim>, "values": [...]} where values are the principal's assignments
    for that dimension. An empty value list under a restricted scope means "see only
    your own" (no matching rows) when applied."""
    if not scope_filtering_enabled():
        return {}
    # Never restrict based on a query/form role: a restricted scope filter is only
    # produced for an authenticated principal. Without one, return {} (no restriction)
    # so scope can never be driven by spoofable parameters.
    principal = _principal_of(request)
    if principal is None or not getattr(principal, "is_authenticated", False):
        return {}
    scope = resolve_scope(request, fallback_role)
    if scope == "enterprise" or not scope:
        return {}
    field = {"vertical": "vertical", "function": "function",
             "application": "application", "control": "control"}.get(scope)
    if not field:
        return {}
    values = resolve_assignments(request).get(field, [])
    return {"field": field, "values": list(values)}


def _row_value(row: dict[str, Any], field: str) -> Any:
    for key in _DEFAULT_ROW_FIELDS.get(field, (field,)):
        if key in row and row[key] not in (None, ""):
            return row[key]
    return None


def apply_scope(request: Any, rows: Sequence[dict[str, Any]], *, fallback_role: str = "",
                fields: Iterable[str] | None = None) -> list[dict[str, Any]]:
    """Filter an in-memory list of dict rows to the principal's scope.

    PASS-THROUGH (returns rows unchanged) when the flag is off or the scope is
    enterprise. For a restricted scope, keeps rows whose scope field value is in the
    principal's assignment values. `fields` overrides which row keys identify the
    scope dimension. Never raises (returns the original rows on any error)."""
    if not scope_filtering_enabled():
        return list(rows)
    try:
        sf = scope_filter(request, fallback_role)
        if not sf:  # enterprise / unrestricted
            return list(rows)
        field = sf["field"]
        allowed = {str(v).strip().lower() for v in sf["values"]}
        keys = tuple(fields) if fields else _DEFAULT_ROW_FIELDS.get(field, (field,))

        def _match(row: dict[str, Any]) -> bool:
            for key in keys:
                val = row.get(key)
                if val not in (None, "") and str(val).strip().lower() in allowed:
                    return True
            return False

        return [r for r in rows if _match(r)]
    except Exception:  # noqa: BLE001 - additive hardening: never hide data on error
        return list(rows)


def scope_sql(request: Any, fallback_role: str = "") -> tuple[str, list[Any]]:
    """Translate the current scope into a SQL WHERE fragment + params for APIs/DB.

    Returns ("", []) for no restriction (flag off / enterprise). Otherwise reuses
    RbacPolicy.to_sql so SQL and in-memory filtering stay consistent. Never raises."""
    if not scope_filtering_enabled():
        return "", []
    try:
        sf = scope_filter(request, fallback_role)
        if not sf:
            return "", []
        from ecs_platform.rbac.policy import RbacPolicy

        return RbacPolicy.to_sql({sf["field"]: sf["values"]})
    except Exception:  # noqa: BLE001
        return "", []
