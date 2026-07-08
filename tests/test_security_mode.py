"""Tests for centralized security-mode resolution + non-blocking demo startup.

Covers the required prototype-mode behaviors:
  * demo mode requires no JWT/OIDC, TLS, Vault, or secrets, and starts fine;
  * demo/UAT config-validation issues warn but do not abort startup;
  * PROD stays strict (aborts on config errors; rejects localhost);
  * connector workbench parser mode + audit-LLM deterministic fallback work with
    no credentials / no LLM server;
  * config validator returns warnings (not errors) for local/demo.

All offline. Env is isolated per-test so ambient vars never skew results.
"""

from __future__ import annotations

import os

import pytest

# Flags that influence security-mode resolution; cleared before each test.
_SECURITY_ENV = [
    "ECS_SECURITY_MODE", "ECS_ENV", "DEMO_MODE", "ECS_LOCAL_AUTH_BYPASS",
    "ECS_AUTH_ENABLED", "ECS_RBAC_ENFORCEMENT", "RBAC_ENFORCEMENT_ENABLED",
    "ECS_REQUIRE_TLS", "ECS_REQUIRE_VAULT", "ECS_REQUIRE_SECRETS",
    "ECS_REQUIRE_OIDC", "ECS_ALLOW_DEMO_AUTH", "ECS_ALLOW_IN_MEMORY",
    "ECS_CONNECTOR_EXECUTION_ENABLED", "ECS_STRICT_CONFIG_VALIDATION",
    "ECS_STARTUP_FAIL_ON_CONFIG_ERROR", "ECS_VALIDATE_CONFIG",
    "ECS_VALIDATE_SECRETS",
]


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in _SECURITY_ENV:
        monkeypatch.delenv(name, raising=False)
    yield


def _sm():
    # Import fresh each call; module reads env at call time (no caching).
    from app import security_mode
    return security_mode


# --------------------------------------------------------------------------- #
# Mode resolution
# --------------------------------------------------------------------------- #
def test_default_mode_is_demo():
    assert _sm().security_mode() == "demo"


def test_demo_mode_flag_implies_demo(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    assert _sm().is_demo() is True


def test_env_prod_derives_production(monkeypatch):
    monkeypatch.setenv("ECS_ENV", "prod")
    assert _sm().is_production() is True


def test_explicit_security_mode_wins(monkeypatch):
    monkeypatch.setenv("ECS_ENV", "prod")          # would derive production
    monkeypatch.setenv("ECS_SECURITY_MODE", "demo")  # explicit overrides
    assert _sm().is_demo() is True


# --------------------------------------------------------------------------- #
# 1-4: demo requires no JWT/OIDC, TLS, Vault, secrets
# --------------------------------------------------------------------------- #
def test_demo_requires_no_auth_or_oidc(monkeypatch):
    monkeypatch.setenv("ECS_SECURITY_MODE", "demo")
    sm = _sm()
    assert sm.auth_enabled() is False
    assert sm.require_oidc() is False


def test_demo_requires_no_tls(monkeypatch):
    monkeypatch.setenv("ECS_SECURITY_MODE", "demo")
    assert _sm().require_tls() is False


def test_demo_requires_no_vault_or_secrets(monkeypatch):
    monkeypatch.setenv("ECS_SECURITY_MODE", "demo")
    sm = _sm()
    assert sm.require_vault() is False
    assert sm.require_secrets() is False


def test_demo_allows_in_memory_and_no_rbac(monkeypatch):
    monkeypatch.setenv("ECS_SECURITY_MODE", "demo")
    sm = _sm()
    assert sm.allow_in_memory() is True
    assert sm.rbac_enforcement() is False


def test_demo_does_not_fail_startup_on_config_error(monkeypatch):
    monkeypatch.setenv("ECS_SECURITY_MODE", "demo")
    assert _sm().startup_fail_on_config_error() is False


# --------------------------------------------------------------------------- #
# 5: UAT non-strict warns but does not fail
# --------------------------------------------------------------------------- #
def test_uat_is_non_blocking_by_default(monkeypatch):
    monkeypatch.setenv("ECS_SECURITY_MODE", "uat")
    sm = _sm()
    assert sm.auth_enabled() is True          # stricter than demo
    assert sm.startup_fail_on_config_error() is False  # planning-tolerant
    assert sm.require_secrets() is False


def test_uat_strict_flag_makes_it_block(monkeypatch):
    monkeypatch.setenv("ECS_SECURITY_MODE", "uat")
    monkeypatch.setenv("ECS_STRICT_CONFIG_VALIDATION", "true")
    assert _sm().startup_fail_on_config_error() is True


# --------------------------------------------------------------------------- #
# 6-7: PROD strict — fails on config error, rejects localhost, requires security
# --------------------------------------------------------------------------- #
def test_prod_is_strict(monkeypatch):
    monkeypatch.setenv("ECS_SECURITY_MODE", "production")
    sm = _sm()
    assert sm.auth_enabled() is True
    assert sm.rbac_enforcement() is True
    assert sm.require_tls() is True
    assert sm.require_secrets() is True
    assert sm.require_oidc() is True
    assert sm.allow_in_memory() is False
    assert sm.startup_fail_on_config_error() is True


def test_prod_explicit_override_is_honored(monkeypatch):
    # Operators can deviate from a default, but it must be explicit.
    monkeypatch.setenv("ECS_SECURITY_MODE", "production")
    monkeypatch.setenv("ECS_STARTUP_FAIL_ON_CONFIG_ERROR", "false")
    assert _sm().startup_fail_on_config_error() is False


def test_prod_env_rejects_localhost_in_config_validation():
    # The validator (unchanged) treats localhost as an ERROR in prod/dr.
    from config.config_validation import validate_environment
    rep = validate_environment("prod")
    # prod.yaml is clean; assert the localhost rule is active by construction:
    # any localhost URL in a prod-like cfg would be an error. Here we assert the
    # rule set includes prod and that a synthetic localhost value is rejected.
    from config import config_validation as cv
    assert "prod" in cv._NO_LOCALHOST_ENVS
    assert cv._contains_localhost("http://127.0.0.1:8000") is True


def test_legacy_validate_config_off_forces_non_blocking(monkeypatch):
    monkeypatch.setenv("ECS_SECURITY_MODE", "production")
    monkeypatch.setenv("ECS_VALIDATE_CONFIG", "off")
    assert _sm().startup_fail_on_config_error() is False


# --------------------------------------------------------------------------- #
# 8-9: connector workbench + LLM fallback work with no infra
# --------------------------------------------------------------------------- #
def test_connector_workbench_parser_mode_without_credentials():
    from modules.audit_intelligence.services import connector_workbench as wb
    res = wb.parser_test("jira")   # mock transport; no creds, no network
    assert res.get("ok") is True
    assert res.get("evidence_objects_detected", 0) >= 1


def test_connector_execution_disabled_by_default():
    # Live execution must be opt-in in every mode.
    assert _sm().connector_execution_enabled() is False


def test_audit_llm_deterministic_fallback_without_llm_server():
    from modules.audit_intelligence.llm import execution_service as es
    res = es.execute(
        user_query="Summarize expired evidence",
        ram_profile="worst_case_enterprise_dry_run",
        use_rag=False,
    )
    assert res.get("execution_mode") == "dry_run"
    assert "deterministic_result" in res


# --------------------------------------------------------------------------- #
# 10: config validator returns warnings (not errors) for local/demo
# --------------------------------------------------------------------------- #
def test_config_validation_local_has_no_errors():
    from config.config_validation import validate_environment
    rep = validate_environment("local")
    assert rep.ok is True   # local integration gaps are warnings, not errors


def test_summary_is_secret_free_snapshot(monkeypatch):
    monkeypatch.setenv("ECS_SECURITY_MODE", "demo")
    s = _sm().summary()
    assert s["security_mode"] == "demo"
    for key in ("auth_enabled", "rbac_enforcement", "require_tls",
                "connector_execution_enabled", "startup_fail_on_config_error"):
        assert key in s
    # No secret-looking values in the snapshot.
    assert all("password" not in str(v).lower() and "token" not in str(v).lower()
               for v in s.values())
