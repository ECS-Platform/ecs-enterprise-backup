"""ECS authorization foundation — the consolidated PolicyEngine (Phase 2, Step 1).

This module is the FRAMEWORK for ECS authorization. It loads the canonical
permission catalog from config/rbac.yaml (`rbac_catalog` block), resolves a
caller's canonical role, and answers permission / page / scope questions.

ENFORCEMENT IS NOT WIRED. `require_permission()` and `require_page()` return
FastAPI dependency callables, but no route, dashboard, or API imports them yet.
`scope_filter()` computes a filter dict but nothing consumes it. Importing this
module changes no ECS behavior — it only makes the foundation available for the
later, separately-approved enforcement steps.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Callable

from app.auth.roles import DEFAULT_ROLE, normalize_role, role_scope


@dataclass(frozen=True)
class AuthorizationDecision:
    """Result of an authorization question. Carries a scope filter so the same
    decision can drive both API gating and data-row/vector filtering later."""

    allowed: bool
    reason: str = ""
    role: str = ""
    permission: str = ""
    scope: str = ""
    scope_filter: dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:  # convenient truthiness in future call sites
        return self.allowed


class AuthzError(RuntimeError):
    """Raised only on engine/config errors — never used for normal deny results."""


def _load_catalog() -> dict[str, Any]:
    try:
        from ecs_platform.config import load_rbac_config

        return (load_rbac_config() or {}).get("rbac_catalog", {}) or {}
    except Exception as exc:  # noqa: BLE001
        raise AuthzError(f"unable to load rbac_catalog: {exc}") from exc


class PolicyEngine:
    """Single authorization engine over the canonical catalog.

    Stateless w.r.t. requests: it reads the catalog once (cached) and answers
    questions about (role, permission) and (role, page). It makes NO decisions
    about HTTP requests by itself — the require_* dependencies do that, and they
    are not attached to any route in this step.
    """

    def __init__(self, catalog: dict[str, Any] | None = None) -> None:
        self._catalog = catalog if catalog is not None else _load_catalog()

    # ---- catalog accessors -------------------------------------------------
    @property
    def permissions(self) -> dict[str, str]:
        return self._catalog.get("permissions", {}) or {}

    @property
    def pages(self) -> dict[str, str]:
        return self._catalog.get("pages", {}) or {}

    @property
    def roles(self) -> dict[str, Any]:
        return self._catalog.get("roles", {}) or {}

    def role_permissions(self, role: str) -> list[str]:
        canonical = normalize_role(role)
        return list((self.roles.get(canonical, {}) or {}).get("permissions", []) or [])

    def role_pages(self, role: str) -> list[str]:
        canonical = normalize_role(role)
        return list((self.roles.get(canonical, {}) or {}).get("pages", []) or [])

    # ---- core questions ----------------------------------------------------
    def can(self, role: str, permission: str) -> bool:
        perms = self.role_permissions(role)
        return "*" in perms or permission in perms

    def can_view_page(self, role: str, page: str) -> bool:
        pages = self.role_pages(role)
        return "*" in pages or page in pages

    def scope_for(self, role: str) -> str:
        scopes = self._catalog.get("role_scope", {}) or {}
        canonical = normalize_role(role)
        return scopes.get(canonical) or role_scope(canonical)

    def authorize(self, role: str, permission: str,
                  assignments: dict[str, list[str]] | None = None) -> AuthorizationDecision:
        """Answer a permission question and attach a (currently descriptive) scope
        filter. NOTE: scope_filter is computed for completeness but is NOT applied
        anywhere in this step — scope filtering is explicitly deferred."""
        canonical = normalize_role(role)
        allowed = self.can(canonical, permission)
        return AuthorizationDecision(
            allowed=allowed,
            reason="" if allowed else f"role '{canonical}' lacks '{permission}'",
            role=canonical,
            permission=permission,
            scope=self.scope_for(canonical),
            scope_filter=self._descriptive_scope_filter(canonical, assignments or {}),
        )

    def authorize_page(self, role: str, page: str) -> AuthorizationDecision:
        canonical = normalize_role(role)
        allowed = self.can_view_page(canonical, page)
        return AuthorizationDecision(
            allowed=allowed,
            reason="" if allowed else f"role '{canonical}' cannot view page '{page}'",
            role=canonical, permission=f"page:{page}", scope=self.scope_for(canonical),
        )

    def _descriptive_scope_filter(self, role: str,
                                  assignments: dict[str, list[str]]) -> dict[str, Any]:
        """Build the scope filter that *would* apply once scope filtering is
        enabled. Returns {} for enterprise scope (no restriction)."""
        scope = self.scope_for(role)
        if scope == "enterprise" or not scope:
            return {}
        field_name = {"vertical": "vertical", "function": "function",
                      "application": "application", "control": "control"}.get(scope)
        if not field_name:
            return {}
        values = assignments.get(field_name, [])
        return {"field": field_name, "values": list(values)}


@lru_cache(maxsize=1)
def get_policy_engine() -> PolicyEngine:
    """Process-wide singleton PolicyEngine (catalog cached)."""
    return PolicyEngine()


def reload_policy_engine() -> PolicyEngine:
    """Drop caches and rebuild (useful for tests / config changes)."""
    try:
        from ecs_platform.config import loader

        loader.load_config.cache_clear()
    except Exception:  # noqa: BLE001
        pass
    get_policy_engine.cache_clear()
    return get_policy_engine()


# ---------------------------------------------------------------------------
# Dependency FACTORIES. These return FastAPI-compatible dependency callables for
# future use. They are NOT attached to any route in this step. When enforcement
# is enabled later, routes will add `Depends(require_permission("evidence.read"))`.
# ---------------------------------------------------------------------------
def require_permission(permission: str) -> Callable:
    """Return a dependency that, when wired, will 403 callers lacking `permission`.

    Until enforcement is enabled, this factory simply produces the callable; it
    is not referenced by any route, so it has no runtime effect on ECS today.
    """

    def _dependency(request: "Any") -> AuthorizationDecision:  # noqa: F821
        principal = getattr(getattr(request, "state", None), "principal", None)
        role = _role_from_principal(principal)
        decision = get_policy_engine().authorize(role, permission,
                                                 _assignments_from_principal(principal))
        if not decision.allowed:
            from app.auth.errors import AuthenticationError

            # Reuse the auth error type for HTTP mapping; 403 semantics applied
            # at the call site when enforcement is enabled.
            err = AuthenticationError("forbidden", decision.reason or "Forbidden")
            err.http_status = 403
            raise err
        return decision

    _dependency.__name__ = f"require_permission[{permission}]"
    return _dependency


def require_page(page: str) -> Callable:
    """Return a dependency that, when wired, will gate access to a dashboard page."""

    def _dependency(request: "Any") -> AuthorizationDecision:  # noqa: F821
        principal = getattr(getattr(request, "state", None), "principal", None)
        role = _role_from_principal(principal)
        decision = get_policy_engine().authorize_page(role, page)
        if not decision.allowed:
            from app.auth.errors import AuthenticationError

            err = AuthenticationError("forbidden", decision.reason or "Forbidden")
            err.http_status = 403
            raise err
        return decision

    _dependency.__name__ = f"require_page[{page}]"
    return _dependency


def scope_filter(role: str, assignments: dict[str, list[str]] | None = None) -> dict[str, Any]:
    """Compute the data scope filter for a role. NOT applied anywhere yet —
    scope filtering is explicitly out of scope for this step."""
    return get_policy_engine()._descriptive_scope_filter(  # noqa: SLF001
        normalize_role(role), assignments or {})


# ---- principal helpers (tolerant of both Phase 1 AuthenticatedUser and None) --
def _role_from_principal(principal: Any) -> str:
    if principal is None:
        return DEFAULT_ROLE
    roles = getattr(principal, "roles", ()) or ()
    return normalize_role(roles[0]) if roles else DEFAULT_ROLE


def _assignments_from_principal(principal: Any) -> dict[str, list[str]]:
    # Phase 1 principal does not carry scope assignments yet; placeholder for the
    # future scope-filtering step.
    return {}
