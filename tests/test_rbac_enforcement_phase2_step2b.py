"""Phase 2 Step 2B — RBAC enforcement foundation: differential parity tests.

Proves the enforcement foundation is behavior-preserving:

  * RBAC_ENFORCEMENT_ENABLED defaults FALSE.
  * resolve_effective_role(): OFF -> caller-supplied role; ON -> principal role.
  * enforce_permission() == the legacy predicate for every canonical role x every
    capability, with the flag OFF and with the flag ON (role carried on a principal).
  * The role_permissions.can_* predicates return identical booleans whether the
    enforcement flag is OFF or ON (decision logic unchanged; only the role source
    moves, at the route layer).
  * enforce_page() is non-restrictive while the flag is off; never raises.
  * Helpers never raise on a missing principal / engine.

No Azure AD, LLM, Ollama, vector DB, or live PostgreSQL required.
"""

from __future__ import annotations

import importlib
import types

import pytest

import app.auth.enforcement as enf
from modules.shared.services import role_permissions as rp


# Capability -> the legacy predicate function used as the source of truth.
CAP_TO_PREDICATE = {
    "can_upload_evidence": rp.can_upload_evidence,
    "can_submit_to_auditor": rp.can_submit_to_auditor,
    "can_review_evidence": rp.can_review_evidence,
    "can_export_reports": rp.can_export_reports,
    "can_manage_frameworks": rp.can_manage_frameworks,
    "can_assign_owner": rp.can_assign_owner,
    "can_escalate": rp.can_escalate,
    "can_request_reupload": rp.can_request_reupload,
    "can_raise_exception": rp.can_raise_exception,
}

# Every canonical + legacy/alias role we must preserve behavior for.
ROLES = [
    "owner", "auditor", "cio", "vertical_head", "functional_head",
    "compliance_head", "compliance_officer", "security_officer", "enterprise_admin",
    "admin", "system_admin", "application_owner", "control_owner",
    "operations_owner", "ai_governance_owner", "ai_sdlc_owner", "framework_owner",
    "", "unknown_role",
]


class _Principal:
    is_authenticated = True

    def __init__(self, role):
        self.roles = (role,) if role else ()
        self.user_id = "u1"
        self.username = "u1"
        self.display_name = "U"
        self.auth_source = "dev"


def _request(principal=None):
    state = types.SimpleNamespace()
    if principal is not None:
        state.principal = principal
    return types.SimpleNamespace(state=state)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv("RBAC_ENFORCEMENT_ENABLED", raising=False)
    monkeypatch.delenv("ECS_RBAC_DELEGATION_ENABLED", raising=False)
    yield


# --------------------------------------------------------------------------- #
# Flag + resolver
# --------------------------------------------------------------------------- #
def test_flag_defaults_off():
    assert enf.rbac_enforcement_enabled() is False


def test_resolver_off_returns_param_role():
    r = _request(_Principal("auditor"))
    # Flag off -> caller-supplied role is returned verbatim, principal ignored.
    assert enf.resolve_effective_role(r, "owner") == "owner"


def test_resolver_on_uses_principal(monkeypatch):
    monkeypatch.setenv("RBAC_ENFORCEMENT_ENABLED", "true")
    r = _request(_Principal("auditor"))
    # Flag on -> role derived from principal (normalized), NOT the param.
    assert enf.resolve_effective_role(r, "owner") == enf.normalize_role("auditor")


def test_resolver_on_no_principal_degrades_to_param(monkeypatch):
    monkeypatch.setenv("RBAC_ENFORCEMENT_ENABLED", "true")
    r = _request(None)
    assert enf.resolve_effective_role(r, "owner") == "owner"


def test_resolver_never_raises_on_garbage():
    assert enf.resolve_effective_role(object(), "owner") == "owner"


# --------------------------------------------------------------------------- #
# Differential parity: enforce_permission == legacy predicate
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("capability", list(CAP_TO_PREDICATE))
def test_parity_flag_off(role, capability):
    """Flag OFF: enforce_permission(role as fallback) == legacy predicate(role)."""
    expected = CAP_TO_PREDICATE[capability](role)
    r = _request(None)
    assert enf.enforce_permission(r, capability, role) == expected


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("capability", list(CAP_TO_PREDICATE))
def test_parity_flag_on_principal(role, capability, monkeypatch):
    """Flag ON: effective role from principal -> verdict == legacy predicate(role).

    The legacy expectation is computed WITHOUT the flag, then we enable enforcement
    and assert the principal-derived decision matches it for the same role."""
    expected = CAP_TO_PREDICATE[capability](role)
    monkeypatch.setenv("RBAC_ENFORCEMENT_ENABLED", "true")
    r = _request(_Principal(role))
    assert enf.enforce_permission(r, capability, "owner") == expected


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("capability", list(CAP_TO_PREDICATE))
def test_predicate_unchanged_off_vs_on(role, capability, monkeypatch):
    """role_permissions.can_*(role) returns the same bool with the flag OFF and ON."""
    fn = CAP_TO_PREDICATE[capability]
    monkeypatch.delenv("RBAC_ENFORCEMENT_ENABLED", raising=False)
    off = fn(role)
    monkeypatch.setenv("RBAC_ENFORCEMENT_ENABLED", "true")
    on = fn(role)
    assert off == on


# --------------------------------------------------------------------------- #
# Pages + robustness
# --------------------------------------------------------------------------- #
def test_enforce_page_noop_when_flag_off():
    r = _request(_Principal("owner"))
    assert enf.enforce_page(r, "cio_dashboard", "owner") is True


def test_enforce_page_never_raises_when_on(monkeypatch):
    monkeypatch.setenv("RBAC_ENFORCEMENT_ENABLED", "true")
    r = _request(_Principal("auditor"))
    # Whatever the catalog says, it must return a bool and never raise.
    assert isinstance(enf.enforce_page(r, "nonexistent_page", "auditor"), bool)


def test_enforce_permission_never_raises_unknown_capability(monkeypatch):
    monkeypatch.setenv("RBAC_ENFORCEMENT_ENABLED", "true")
    r = _request(_Principal("auditor"))
    # Unknown capability -> engine raises internally -> falls back to legacy
    # predicate lookup (also unknown) -> False, but never raises.
    assert enf.enforce_permission(r, "totally_unknown_cap", "auditor") is False


def test_public_api_importable():
    mod = importlib.import_module("app.auth")
    for name in ("resolve_effective_role", "enforce_permission", "enforce_page",
                 "rbac_enforcement_enabled"):
        assert hasattr(mod, name)
