"""Phase 2 Step 2C — dashboard / page authorization tests.

Validates app/auth/page_guard.guard_page / can_view_page, wired into the persona
dashboard routes. No Azure AD / LLM / Ollama / vector DB / live PostgreSQL needed.

Covered:
  * RBAC_PAGE_ENFORCEMENT_ENABLED defaults FALSE.
  * Flag OFF -> guard_page returns None for every role (existing behavior; no bypass
    blocking yet).
  * Flag ON  -> role derived from principal; authorized role allowed, others denied.
  * Cross-persona matrix: CIO can view CIO page; auditor cannot; owner cannot view
    auditor; security officer only its (shared compliance/security) landing.
  * Direct-URL navigation with a spoofed query role is ignored when a principal
    exists (principal wins).
  * Denial response shape: HTML 403 (browser), JSON 403 (api), 303 (redirect).
  * Any-of page lists (compliance + security shared landing).
  * Never raises.
"""

from __future__ import annotations

import types

import pytest

from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

import app.auth.page_guard as pg


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
    monkeypatch.delenv("RBAC_PAGE_ENFORCEMENT_ENABLED", raising=False)
    monkeypatch.delenv("RBAC_ENFORCEMENT_ENABLED", raising=False)
    yield


def _enable(monkeypatch):
    monkeypatch.setenv("RBAC_PAGE_ENFORCEMENT_ENABLED", "true")
    monkeypatch.setenv("RBAC_ENFORCEMENT_ENABLED", "true")


# --------------------------------------------------------------------------- #
# Flag behavior
# --------------------------------------------------------------------------- #
def test_flag_defaults_off():
    assert pg.page_enforcement_enabled() is False


@pytest.mark.parametrize("role", ["owner", "auditor", "cio", "security_officer", "unknown"])
def test_flag_off_allows_everyone(role):
    r = _request(_Principal(role))
    assert pg.guard_page(r, "dashboard.cio", fallback_role=role) is None


# --------------------------------------------------------------------------- #
# Enforcement ON — cross-persona matrix
# --------------------------------------------------------------------------- #
def test_cio_can_view_cio(monkeypatch):
    _enable(monkeypatch)
    r = _request(_Principal("cio"))
    assert pg.guard_page(r, "dashboard.cio", fallback_role="cio") is None


def test_auditor_cannot_view_cio(monkeypatch):
    _enable(monkeypatch)
    r = _request(_Principal("auditor"))
    deny = pg.guard_page(r, "dashboard.cio", fallback_role="auditor")
    assert isinstance(deny, HTMLResponse) and deny.status_code == 403


def test_owner_cannot_view_auditor(monkeypatch):
    _enable(monkeypatch)
    r = _request(_Principal("owner"))
    deny = pg.guard_page(r, "dashboard.auditor", fallback_role="owner")
    assert deny is not None and deny.status_code == 403


def test_auditor_can_view_auditor(monkeypatch):
    _enable(monkeypatch)
    r = _request(_Principal("auditor"))
    assert pg.guard_page(r, "dashboard.auditor", fallback_role="auditor") is None


def test_security_officer_shared_landing_allowed(monkeypatch):
    _enable(monkeypatch)
    r = _request(_Principal("security_officer"))
    # Shared compliance/security landing (any-of) -> allowed via dashboard.security.
    assert pg.guard_page(r, ["dashboard.compliance", "dashboard.security"],
                         fallback_role="security_officer") is None


def test_security_officer_cannot_view_cio(monkeypatch):
    _enable(monkeypatch)
    r = _request(_Principal("security_officer"))
    assert pg.guard_page(r, "dashboard.cio", fallback_role="security_officer") is not None


def test_compliance_officer_can_view_compliance(monkeypatch):
    _enable(monkeypatch)
    r = _request(_Principal("compliance_officer"))
    assert pg.guard_page(r, ["dashboard.compliance", "dashboard.security"],
                         fallback_role="compliance_officer") is None


def test_system_admin_can_view_any(monkeypatch):
    _enable(monkeypatch)
    r = _request(_Principal("system_admin"))
    for page in ("dashboard.cio", "dashboard.auditor", "dashboard.compliance"):
        assert pg.guard_page(r, page, fallback_role="system_admin") is None, page


# --------------------------------------------------------------------------- #
# Principal wins over spoofed query role; response shapes; robustness
# --------------------------------------------------------------------------- #
def test_principal_overrides_query_role(monkeypatch):
    _enable(monkeypatch)
    # Auditor principal but caller-supplied (spoofed) role=cio -> still denied for CIO.
    r = _request(_Principal("auditor"))
    assert pg.guard_page(r, "dashboard.cio", fallback_role="cio") is not None


def test_no_principal_uses_fallback(monkeypatch):
    _enable(monkeypatch)
    r = _request(None)
    # No principal -> degrade to fallback role; cio fallback may view cio page.
    assert pg.guard_page(r, "dashboard.cio", fallback_role="cio") is None
    # owner fallback cannot view cio page.
    assert pg.guard_page(r, "dashboard.cio", fallback_role="owner") is not None


def test_json_denial_shape(monkeypatch):
    _enable(monkeypatch)
    r = _request(_Principal("owner"))
    deny = pg.guard_page(r, "dashboard.cio", fallback_role="owner", response="json")
    assert isinstance(deny, JSONResponse) and deny.status_code == 403


def test_redirect_denial_shape(monkeypatch):
    _enable(monkeypatch)
    r = _request(_Principal("owner"))
    deny = pg.guard_page(r, "dashboard.cio", fallback_role="owner", response="redirect")
    assert isinstance(deny, RedirectResponse) and deny.status_code == 303


def test_can_view_page_helper(monkeypatch):
    _enable(monkeypatch)
    assert pg.can_view_page(_request(_Principal("cio")), "dashboard.cio") is True
    assert pg.can_view_page(_request(_Principal("auditor")), "dashboard.cio") is False


def test_never_raises_on_garbage(monkeypatch):
    _enable(monkeypatch)
    assert pg.guard_page(object(), "dashboard.cio", fallback_role="cio") is None
