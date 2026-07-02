"""RBAC policy engine.

Loads roles/scopes from rbac.yaml and produces:
  * permission checks (can this principal perform an action?)
  * evidence scope filters (which rows/vectors may this principal see?)

The same scope filter dict is reused for SQL queries and vector search metadata
filters, so access control is consistent across the repository and the AI assistant.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ecs_platform.config import load_rbac_config


class RbacError(RuntimeError):
    pass


@dataclass
class Principal:
    """An authenticated caller. assignments hold the scope values they own."""

    user_id: str
    role: str
    # e.g. {"vertical": ["banking"], "application": ["payments-api"], "control": [...]}
    assignments: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class AccessDecision:
    allowed: bool
    reason: str = ""
    scope_filter: dict[str, Any] = field(default_factory=dict)


class RbacPolicy:
    def __init__(self, config: dict[str, Any] | None = None):
        cfg = (config or load_rbac_config()).get("rbac", {})
        self.enabled = bool(cfg.get("enabled", True))
        self.default_role = cfg.get("default_role", "application_owner")
        self.roles = cfg.get("roles", {})
        self.scope_filters = cfg.get("scope_filters", {})

    def _role(self, role: str) -> dict[str, Any]:
        return self.roles.get(role) or self.roles.get(self.default_role, {})

    def can(self, principal: Principal, action: str) -> bool:
        if not self.enabled:
            return True
        role = self._role(principal.role)
        perms = role.get("can", [])
        return "*" in perms or action in perms

    def scope_filter(self, principal: Principal) -> dict[str, Any]:
        """Return a metadata/SQL filter dict limiting evidence to the principal's scope.

        Enterprise scope -> {} (no restriction). Narrower scopes restrict by the
        configured field to the principal's owned assignment values.
        """
        if not self.enabled:
            return {}
        role = self._role(principal.role)
        scope = role.get("scope", "assigned")
        spec = self.scope_filters.get(scope, {})
        if not spec:  # enterprise / unrestricted
            return {}
        field_name = spec.get("field")
        if not field_name:
            return {}
        values = principal.assignments.get(field_name, [])
        # No assignments under a restricted scope => see nothing.
        return {field_name: values}

    def authorize(self, principal: Principal, action: str) -> AccessDecision:
        if not self.can(principal, action):
            return AccessDecision(False, f"role '{principal.role}' lacks '{action}'")
        return AccessDecision(True, scope_filter=self.scope_filter(principal))

    @staticmethod
    def to_sql(scope_filter: dict[str, Any]) -> tuple[str, list[Any]]:
        """Translate a scope filter into a SQL WHERE fragment + params.

        {} -> ("", []). {field: [a, b]} -> ("field = ANY(%s)", [[a, b]]).
        An empty value list yields an always-false clause (no access).
        """
        if not scope_filter:
            return "", []
        clauses, params = [], []
        for field_name, values in scope_filter.items():
            if not values:
                return "1 = 0", []
            clauses.append(f"{field_name} = ANY(%s)")
            params.append(list(values))
        return " AND ".join(clauses), params


def load_policy() -> RbacPolicy:
    return RbacPolicy()
