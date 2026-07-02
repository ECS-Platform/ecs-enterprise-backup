"""Phase 2 Step 2D-critical — mutation authorization enforcement tests.

Validates app/auth/mutation_guard.guard_mutation, the helper wired into the critical
mutation endpoints. No Azure AD / LLM / Ollama / vector DB / live PostgreSQL needed.

Covered:
  * Feature flag RBAC_MUTATION_ENFORCEMENT_ENABLED defaults FALSE.
  * Flag OFF -> guard_mutation returns None (allow) for every role (existing behavior).
  * Flag ON  -> authorized role allowed; unauthorized/missing role denied.
  * Denial response shape: JSON 403 for APIs; 303 redirect for browser routes.
  * Identity source: authenticated principal preferred; legacy fallback role used
    when no principal is present.
  * Differential parity matrix: guard verdict == legacy predicate for the mapped
    capability across all roles, with the flag ON.
  * can_admin_platform restricts to administrators only.
  * Never raises.
"""

from __future__ import annotations

import types

import pytest

from fastapi.responses import JSONResponse, RedirectResponse

import app.auth.mutation_guard as mg
from modules.shared.services import role_permissions as rp


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


# Mapping of guarded mutations -> (capability, legacy predicate) used in the matrix.
CAP_PREDICATE = {
    "can_upload_evidence": rp.can_upload_evidence,        # reject-internal, sdlc upload
    "can_escalate": rp.can_escalate,                      # escalate, leadership reopen
    "can_assign_owner": rp.can_assign_owner,              # assign-owner
    "can_review_evidence": rp.can_review_evidence,        # sdlc review actions
    "can_admin_platform": rp.can_admin_platform,          # sync, rag reindex/warm
}

ROLES = ["owner", "auditor", "cio", "vertical_head", "compliance_head",
         "compliance_officer", "security_officer", "enterprise_admin", "admin",
         "system_admin", "operations_owner", "framework_owner", "", "unknown"]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv("RBAC_MUTATION_ENFORCEMENT_ENABLED", raising=False)
    monkeypatch.delenv("RBAC_ENFORCEMENT_ENABLED", raising=False)
    monkeypatch.delenv("ECS_RBAC_DELEGATION_ENABLED", raising=False)
    yield


def _enable(monkeypatch):
    monkeypatch.setenv("RBAC_MUTATION_ENFORCEMENT_ENABLED", "true")
    monkeypatch.setenv("RBAC_ENFORCEMENT_ENABLED", "true")


# --------------------------------------------------------------------------- #
# Flag behavior
# --------------------------------------------------------------------------- #
def test_flag_defaults_off():
    assert mg.mutation_enforcement_enabled() is False


@pytest.mark.parametrize("role", ROLES)
def test_flag_off_allows_everyone(role):
    r = _request(_Principal(role))
    assert mg.guard_mutation(r, "can_admin_platform", fallback_role=role) is None


def test_predicate_unchanged_when_off():
    # role_permissions predicates unaffected by the mutation flag alone.
    assert rp.can_escalate("owner") is True
    assert rp.can_admin_platform("owner") is False


# --------------------------------------------------------------------------- #
# Enforcement ON — allow / deny + response shape
# --------------------------------------------------------------------------- #
def test_authorized_principal_allowed(monkeypatch):
    _enable(monkeypatch)
    r = _request(_Principal("auditor"))
    assert mg.guard_mutation(r, "can_escalate", fallback_role="owner") is None


def test_unauthorized_principal_denied_json(monkeypatch):
    _enable(monkeypatch)
    r = _request(_Principal("owner"))
    deny = mg.guard_mutation(r, "can_admin_platform", fallback_role="owner", response="json")
    assert isinstance(deny, JSONResponse)
    assert deny.status_code == 403


def test_unauthorized_principal_denied_redirect(monkeypatch):
    _enable(monkeypatch)
    r = _request(_Principal("owner"))
    deny = mg.guard_mutation(r, "can_admin_platform", fallback_role="owner",
                             deny_redirect_to="/dashboard", role="owner", user="O")
    assert isinstance(deny, RedirectResponse)
    assert deny.status_code == 303


def test_admin_allowed_platform(monkeypatch):
    _enable(monkeypatch)
    for admin_role in ("system_admin", "enterprise_admin", "admin"):
        r = _request(_Principal(admin_role))
        assert mg.guard_mutation(r, "can_admin_platform", fallback_role="owner",
                                 response="json") is None, admin_role


def test_missing_role_denied_for_admin_cap(monkeypatch):
    _enable(monkeypatch)
    # No principal, no fallback -> not an admin -> denied for admin-only API.
    r = _request(None)
    deny = mg.guard_mutation(r, "can_admin_platform", fallback_role="", response="json")
    assert isinstance(deny, JSONResponse) and deny.status_code == 403


def test_legacy_fallback_role_used_without_principal(monkeypatch):
    _enable(monkeypatch)
    # No principal -> falls back to supplied role; auditor can escalate.
    r = _request(None)
    assert mg.guard_mutation(r, "can_escalate", fallback_role="auditor") is None
    # owner cannot admin platform even via fallback.
    deny = mg.guard_mutation(r, "can_admin_platform", fallback_role="owner", response="json")
    assert isinstance(deny, JSONResponse)


# --------------------------------------------------------------------------- #
# Differential parity matrix (flag ON): guard allow == legacy predicate
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("capability", list(CAP_PREDICATE))
def test_parity_matrix(role, capability, monkeypatch):
    expected = CAP_PREDICATE[capability](role)
    _enable(monkeypatch)
    r = _request(_Principal(role))
    allowed = mg.guard_mutation(r, capability, fallback_role="owner", response="json") is None
    assert allowed == expected, f"{capability}/{role}: guard={allowed} legacy={expected}"


def test_never_raises_on_garbage(monkeypatch):
    _enable(monkeypatch)
    # Bad request object -> is_allowed swallows error and allows (fail-safe).
    assert mg.guard_mutation(object(), "can_escalate", fallback_role="auditor") is None


def test_admin_platform_predicate_matrix():
    assert rp.can_admin_platform("system_admin") is True
    assert rp.can_admin_platform("enterprise_admin") is True
    assert rp.can_admin_platform("admin") is True
    assert rp.can_admin_platform("auditor") is False
    assert rp.can_admin_platform("cio") is False
    assert rp.can_admin_platform("owner") is False
