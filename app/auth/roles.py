"""Canonical ECS role catalog and alias mapping (Phase 2 — Step 1 foundation).

This module establishes ONE authoritative role taxonomy plus a single alias map
that collapses the historical, divergent role names used across the codebase
(`owner` vs `application_owner`, `compliance_head` vs `compliance_officer`,
`enterprise_admin`/`admin` vs `system_admin`, etc.).

IMPORTANT: This is foundation only. Nothing here is wired into existing
enforcement (`role_permissions.py`, routes, templates) yet — importing this
module changes no ECS behavior. Consolidation of the legacy engines happens in a
later, separately-approved step.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RoleDef:
    """A canonical role definition (metadata only; permissions live in rbac.yaml)."""

    key: str
    title: str
    description: str
    scope: str  # enterprise | vertical | function | application | control
    # Human-facing grouping; not an enforcement attribute.
    category: str = "general"
    aliases: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Canonical roles. `key` is the single value the future PolicyEngine reasons
# about. `scope` mirrors config/rbac.yaml so the two never drift.
# ---------------------------------------------------------------------------
CANONICAL_ROLES: tuple[RoleDef, ...] = (
    RoleDef("cio", "Chief Information Officer",
            "Enterprise-wide analytics and governance posture.", "enterprise",
            category="executive", aliases=("ai_governance_owner",)),
    RoleDef("auditor", "Lead Auditor",
            "Read-only oversight plus evidence review/approval across the enterprise.",
            "enterprise", category="assurance"),
    RoleDef("application_owner", "Application Owner",
            "Owns evidence for assigned applications (collect / upload / submit).",
            "application", category="operational",
            aliases=("owner", "operations_owner", "ai_sdlc_owner")),
    RoleDef("compliance_officer", "Compliance Officer",
            "Framework and control compliance oversight.", "enterprise",
            category="compliance", aliases=("compliance_head", "framework_owner")),
    RoleDef("security_officer", "Security Officer",
            "Security findings, vulnerabilities and hotspots.", "enterprise",
            category="security"),
    RoleDef("vertical_head", "Vertical Head",
            "Aggregated evidence across an owned vertical.", "vertical",
            category="executive"),
    RoleDef("functional_head", "Functional Head",
            "Aggregated evidence across an owned function.", "function",
            category="executive"),
    RoleDef("control_owner", "Control Owner",
            "Evidence for owned controls.", "control", category="operational"),
    RoleDef("system_admin", "System Administrator",
            "Full platform administration.", "enterprise",
            category="administration", aliases=("admin", "enterprise_admin")),
)

# Fast lookups derived from the catalog.
ROLE_BY_KEY: dict[str, RoleDef] = {r.key: r for r in CANONICAL_ROLES}

# Alias -> canonical key. Built from each role's declared aliases. The canonical
# key also maps to itself so normalize() is idempotent.
ROLE_ALIASES: dict[str, str] = {}
for _r in CANONICAL_ROLES:
    ROLE_ALIASES[_r.key] = _r.key
    for _a in _r.aliases:
        ROLE_ALIASES[_a] = _r.key

# Default canonical role when nothing usable is supplied (mirrors rbac.yaml
# default_role: application_owner).
DEFAULT_ROLE = "application_owner"


def normalize_role(role: str | None) -> str:
    """Return the canonical role key for any historical/alias role string.

    Unknown values fall back to DEFAULT_ROLE. Case-insensitive; hyphens treated
    as underscores. This does NOT replace existing `role_permissions.normalize_role`
    (that consolidation is a later step) — it is the new single source of truth.
    """
    if not role:
        return DEFAULT_ROLE
    key = role.strip().lower().replace("-", "_")
    return ROLE_ALIASES.get(key, DEFAULT_ROLE if key not in ROLE_BY_KEY else key)


def is_canonical_role(role: str | None) -> bool:
    return bool(role) and role.strip().lower().replace("-", "_") in ROLE_BY_KEY


def role_scope(role: str | None) -> str:
    """The scope dimension for a role (enterprise/vertical/.../control)."""
    rd = ROLE_BY_KEY.get(normalize_role(role))
    return rd.scope if rd else "application"


def all_role_keys() -> tuple[str, ...]:
    return tuple(r.key for r in CANONICAL_ROLES)
