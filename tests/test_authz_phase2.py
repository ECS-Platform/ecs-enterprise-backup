"""Phase 2 — Step 1 RBAC foundation tests.

Validates the canonical role catalog, alias mapping, permission lookups, and
catalog loading. NO routes / dashboards / APIs are exercised — this is the
additive foundation only. None of these assertions depend on the DB/LLM stack.
"""

from __future__ import annotations

from app.auth.authz import (
    AuthorizationDecision,
    PolicyEngine,
    get_policy_engine,
    require_page,
    require_permission,
    scope_filter,
)
from app.auth.roles import (
    CANONICAL_ROLES,
    DEFAULT_ROLE,
    ROLE_BY_KEY,
    all_role_keys,
    is_canonical_role,
    normalize_role,
    role_scope,
)


# --------------------------------------------------------------- role catalog
def test_nine_canonical_roles_present():
    expected = {
        "cio", "auditor", "application_owner", "compliance_officer",
        "security_officer", "vertical_head", "functional_head",
        "control_owner", "system_admin",
    }
    assert set(all_role_keys()) == expected
    assert len(CANONICAL_ROLES) == 9


def test_each_role_has_metadata():
    for r in CANONICAL_ROLES:
        assert r.title and r.description and r.scope
        assert r.scope in {"enterprise", "vertical", "function", "application", "control"}


# --------------------------------------------------------------- alias mapping
def test_alias_mapping_collapses_legacy_names():
    cases = {
        "owner": "application_owner",
        "operations_owner": "application_owner",
        "ai_sdlc_owner": "application_owner",
        "compliance_head": "compliance_officer",
        "framework_owner": "compliance_officer",
        "admin": "system_admin",
        "enterprise_admin": "system_admin",
        "ai_governance_owner": "cio",
    }
    for alias, canonical in cases.items():
        assert normalize_role(alias) == canonical, alias


def test_normalize_is_case_and_hyphen_insensitive():
    assert normalize_role("Compliance-Head") == "compliance_officer"
    assert normalize_role("SYSTEM_ADMIN") == "system_admin"
    assert normalize_role(" Auditor ") == "auditor"


def test_normalize_is_idempotent():
    for key in all_role_keys():
        assert normalize_role(key) == key
        assert normalize_role(normalize_role(key)) == key


def test_unknown_and_empty_fall_back_to_default():
    assert normalize_role("nonsense") == DEFAULT_ROLE
    assert normalize_role("") == DEFAULT_ROLE
    assert normalize_role(None) == DEFAULT_ROLE
    assert DEFAULT_ROLE == "application_owner"


def test_is_canonical_role():
    assert is_canonical_role("auditor")
    assert is_canonical_role("system-admin") is False or is_canonical_role("system_admin")
    assert not is_canonical_role("owner")  # alias, not canonical
    assert not is_canonical_role("")


def test_role_scope_lookup():
    assert role_scope("cio") == "enterprise"
    assert role_scope("vertical_head") == "vertical"
    assert role_scope("application_owner") == "application"
    assert role_scope("owner") == "application"  # via alias
    assert role_scope("control_owner") == "control"


# --------------------------------------------------------------- catalog load
def test_policy_engine_loads_catalog():
    eng = get_policy_engine()
    assert eng.permissions, "permission catalog must load from rbac.yaml"
    assert eng.pages, "page catalog must load"
    assert eng.roles, "role->permission map must load"
    # Every canonical role (except those intentionally page-less) is present.
    for key in all_role_keys():
        assert key in eng.roles, f"missing role in catalog: {key}"


def test_permission_lookups():
    eng = get_policy_engine()
    # Auditor can review/approve, cannot upload.
    assert eng.can("auditor", "evidence.review")
    assert eng.can("auditor", "evidence.approve")
    assert not eng.can("auditor", "evidence.upload")
    # Application owner can upload/submit, cannot approve.
    assert eng.can("application_owner", "evidence.upload")
    assert eng.can("owner", "evidence.submit")  # alias resolves
    assert not eng.can("application_owner", "evidence.approve")
    # Security officer can read security, not approve evidence.
    assert eng.can("security_officer", "security.read")
    assert not eng.can("security_officer", "evidence.approve")


def test_system_admin_wildcard():
    eng = get_policy_engine()
    for perm in eng.permissions:
        assert eng.can("system_admin", perm)
        assert eng.can("admin", perm)  # alias
    assert eng.can("system_admin", "anything.unknown")  # wildcard
    assert eng.can_view_page("system_admin", "dashboard.security")


def test_page_authorization_lookup():
    eng = get_policy_engine()
    assert eng.can_view_page("cio", "dashboard.cio")
    assert not eng.can_view_page("cio", "dashboard.security")
    assert eng.can_view_page("security_officer", "dashboard.security")


def test_authorize_returns_decision_with_scope():
    eng = get_policy_engine()
    d = eng.authorize("auditor", "evidence.review")
    assert isinstance(d, AuthorizationDecision)
    assert d.allowed and bool(d) is True
    assert d.role == "auditor" and d.scope == "enterprise"
    deny = eng.authorize("application_owner", "evidence.approve")
    assert not deny.allowed and "lacks" in deny.reason


def test_scope_filter_helper_not_enforced():
    # Enterprise roles -> no restriction.
    assert scope_filter("cio") == {}
    # Application role -> descriptive filter with assignments (computed, not applied).
    f = scope_filter("application_owner", {"application": ["payments-api"]})
    assert f == {"field": "application", "values": ["payments-api"]}


# --------------------------------------------------------------- dependency factories
def test_dependency_factories_are_callables_only():
    # Foundation-only: factories produce callables; they are not attached to routes.
    dep_p = require_permission("evidence.read")
    dep_pg = require_page("dashboard.cio")
    assert callable(dep_p) and callable(dep_pg)
    assert "evidence.read" in dep_p.__name__
    assert "dashboard.cio" in dep_pg.__name__


def test_isolated_engine_with_injected_catalog():
    # PolicyEngine accepts an explicit catalog (no global state needed).
    cat = {"permissions": {"x.y": "d"}, "pages": {}, "roles": {"auditor": {"permissions": ["x.y"]}},
           "role_scope": {"auditor": "enterprise"}}
    eng = PolicyEngine(cat)
    assert eng.can("auditor", "x.y")
    assert not eng.can("cio", "x.y")
