"""Phase 2 Step 3 — data scope filtering tests.

Validates app/auth/scope: resolve_scope / resolve_assignments / scope_filter /
apply_scope / scope_sql. No Azure AD / LLM / Ollama / vector DB / live PostgreSQL.

Covered:
  * RBAC_SCOPE_FILTERING_ENABLED defaults FALSE.
  * Flag OFF -> apply_scope / scope_sql are pass-through (existing behavior).
  * Scope matrix: CIO/auditor/compliance/security = enterprise (no restriction);
    vertical_head=vertical; functional_head=function; owner=application;
    control_owner=control.
  * Assignments derived from principal groups (app:/vertical:/function:/control:),
    never from query params.
  * apply_scope filters in-memory rows to the principal's assignments; enterprise
    roles see all rows.
  * scope_sql yields a WHERE fragment for restricted scopes, empty for enterprise.
  * Owner with no assignments sees nothing (own-data semantics).
  * Never raises.
"""

from __future__ import annotations

import types

import pytest

import app.auth.scope as sc


class _Principal:
    is_authenticated = True

    def __init__(self, role, groups=()):
        self.roles = (role,) if role else ()
        self.groups = tuple(groups)
        self.user_id = "u1"
        self.username = "u1"
        self.display_name = "U"
        self.auth_source = "dev"


def _request(principal=None):
    state = types.SimpleNamespace()
    if principal is not None:
        state.principal = principal
    return types.SimpleNamespace(state=state)


ROWS = [
    {"application": "payments-api", "vertical": "banking", "function": "finance", "title": "a"},
    {"application": "mobile-app", "vertical": "retail", "function": "ops", "title": "b"},
    {"application": "core-ledger", "vertical": "banking", "function": "finance", "title": "c"},
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv("RBAC_SCOPE_FILTERING_ENABLED", raising=False)
    monkeypatch.delenv("RBAC_ENFORCEMENT_ENABLED", raising=False)
    yield


def _enable(monkeypatch):
    monkeypatch.setenv("RBAC_SCOPE_FILTERING_ENABLED", "true")
    monkeypatch.setenv("RBAC_ENFORCEMENT_ENABLED", "true")


# --------------------------------------------------------------------------- #
# Flag + scope matrix
# --------------------------------------------------------------------------- #
def test_flag_defaults_off():
    assert sc.scope_filtering_enabled() is False


def test_flag_off_passthrough(monkeypatch):
    r = _request(_Principal("owner", ["app:payments-api"]))
    assert sc.apply_scope(r, ROWS) == list(ROWS)
    assert sc.scope_sql(r) == ("", [])


@pytest.mark.parametrize("role,expected", [
    ("cio", "enterprise"), ("auditor", "enterprise"),
    ("compliance_officer", "enterprise"), ("compliance_head", "enterprise"),
    ("security_officer", "enterprise"), ("system_admin", "enterprise"),
    ("vertical_head", "vertical"), ("functional_head", "function"),
    ("owner", "application"), ("application_owner", "application"),
    ("control_owner", "control"),
])
def test_scope_matrix(role, expected, monkeypatch):
    _enable(monkeypatch)
    assert sc.resolve_scope(_request(_Principal(role)), role) == expected


# --------------------------------------------------------------------------- #
# Assignments from principal groups (never query params)
# --------------------------------------------------------------------------- #
def test_assignments_from_groups():
    r = _request(_Principal("owner", ["app:payments-api", "app:core-ledger",
                                      "vertical:banking", "function:finance",
                                      "control:AC-2", "other:ignored"]))
    a = sc.resolve_assignments(r)
    assert a["application"] == ["payments-api", "core-ledger"]
    assert a["vertical"] == ["banking"]
    assert a["function"] == ["finance"]
    assert a["control"] == ["AC-2"]
    assert "other" not in a


def test_no_principal_no_assignments():
    assert sc.resolve_assignments(_request(None)) == {}


# --------------------------------------------------------------------------- #
# apply_scope — enterprise vs scoped
# --------------------------------------------------------------------------- #
def test_enterprise_sees_all(monkeypatch):
    _enable(monkeypatch)
    for role in ("cio", "auditor", "compliance_officer", "security_officer", "system_admin"):
        r = _request(_Principal(role))
        assert sc.apply_scope(r, ROWS) == list(ROWS), role


def test_owner_sees_only_assigned_applications(monkeypatch):
    _enable(monkeypatch)
    r = _request(_Principal("owner", ["app:payments-api"]))
    out = sc.apply_scope(r, ROWS)
    assert [x["title"] for x in out] == ["a"]


def test_vertical_head_sees_only_vertical(monkeypatch):
    _enable(monkeypatch)
    r = _request(_Principal("vertical_head", ["vertical:banking"]))
    out = sc.apply_scope(r, ROWS)
    assert sorted(x["title"] for x in out) == ["a", "c"]


def test_functional_head_sees_only_function(monkeypatch):
    _enable(monkeypatch)
    r = _request(_Principal("functional_head", ["function:ops"]))
    out = sc.apply_scope(r, ROWS)
    assert [x["title"] for x in out] == ["b"]


def test_owner_no_assignments_sees_nothing(monkeypatch):
    _enable(monkeypatch)
    r = _request(_Principal("owner", []))
    assert sc.apply_scope(r, ROWS) == []


def test_query_param_role_not_trusted(monkeypatch):
    _enable(monkeypatch)
    # Principal is owner (application scope) — a spoofed query role cannot widen it;
    # apply_scope uses the principal, so owner with no app assignments sees nothing.
    r = _request(_Principal("owner", []))
    assert sc.apply_scope(r, ROWS, fallback_role="cio") == []


# --------------------------------------------------------------------------- #
# scope_filter / scope_sql
# --------------------------------------------------------------------------- #
def test_scope_filter_shapes(monkeypatch):
    _enable(monkeypatch)
    assert sc.scope_filter(_request(_Principal("cio"))) == {}
    sf = sc.scope_filter(_request(_Principal("owner", ["app:payments-api"])))
    assert sf == {"field": "application", "values": ["payments-api"]}


def test_scope_sql(monkeypatch):
    _enable(monkeypatch)
    assert sc.scope_sql(_request(_Principal("auditor"))) == ("", [])
    sql, params = sc.scope_sql(_request(_Principal("owner", ["app:payments-api"])))
    assert "application = ANY(%s)" in sql and params == [["payments-api"]]
    # No assignments -> always-false (see nothing).
    sql2, params2 = sc.scope_sql(_request(_Principal("owner", [])))
    assert sql2 == "1 = 0"


def test_never_raises_on_garbage(monkeypatch):
    _enable(monkeypatch)
    # No principal AND no fallback role -> fail-safe to enterprise (show all rows).
    assert sc.apply_scope(object(), ROWS) == list(ROWS)
    assert sc.resolve_scope(object(), "") == "enterprise"
    # An explicit fallback role is honored (owner -> application scope).
    assert sc.resolve_scope(object(), "owner") == "application"
