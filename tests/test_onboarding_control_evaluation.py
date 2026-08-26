"""Onboarding -> Common-Control evaluation -> report integration tests.

Covers the wiring added on top of the existing Application Onboarding UI flow
(``mvp_onboarding.html`` -> ``POST /api/onboarding/simulate`` ->
``onboarding_engine.simulate_onboarding``): a real, deterministic reusable
Common-Control evaluation is now attached to that same response
(``result["control_evaluation"]``), and the existing plain-text export
(``export_onboarding_summary`` -> ``POST /api/onboarding/export``) now
includes it too. No live connectors are used — every predefined-query
execution is stubbed via the evaluation engine's ``executor`` override.
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from modules.operations.engines.common_control_onboarding import onboard_from_intake_payload
from modules.operations.engines.common_control_rule_engine import (
    VERDICT_IMPLEMENTED,
    VERDICT_NOT_APPLICABLE,
    VERDICT_UNKNOWN,
)
from modules.operations.engines.onboarding_engine import (
    export_onboarding_summary,
    simulate_onboarding,
)


def _ok(output: str) -> dict:
    return {"ok": True, "output": output, "duration_ms": 5}


PG_ALL_PASS = {
    "PGX-001": _ok("ssl\n---\non"),
    "PGX-002": _ok("password_encryption\n-------------------\nscram-sha-256"),
    "PGX-004": _ok("rolname | rolsuper\n-------------------\npostgres | t"),
    "PGX-008": _ok("extname\n-------\npgaudit"),
    "PGX-013": _ok("name | setting\n--------------\nlog_connections | on\nlog_statement | ddl"),
}


def make_executor(fixtures: dict[str, dict]):
    def _run(control_id: str, user: str) -> dict:
        return fixtures.get(control_id, {"ok": False, "error": "connection refused", "error_type": "connection_error"})

    return _run


# --------------------------------------------------------------------------- #
# Onboarding triggers evaluation
# --------------------------------------------------------------------------- #
def test_intake_bridge_extracts_recognized_technology_and_evaluates():
    payload = {
        "application_name": "WealthX Portal",
        "environment": "UAT",
        "database_technology": "PostgreSQL",
    }
    report = onboard_from_intake_payload(payload, executor=make_executor(PG_ALL_PASS))
    assert report["ok"] is True
    assert report["assets"] == [
        {"asset_id": "wealthx-portal-db", "technology": "PostgreSQL", "submitted_technology": "PostgreSQL"}
    ]
    assert VERDICT_IMPLEMENTED in {c["verdict"] for c in report["controls"]}


def test_intake_bridge_extracts_both_db_and_middleware_technology():
    payload = {
        "application_name": "Trade Finance Hub",
        "database_technology": "PostgreSQL",
        "middleware_technology": "Tomcat",
    }
    report = onboard_from_intake_payload(payload, executor=make_executor(PG_ALL_PASS))
    techs = {a["technology"] for a in report["assets"]}
    assert techs == {"PostgreSQL", "Tomcat"}


def test_intake_bridge_no_recognized_technology_completes_gracefully():
    """Blank/unrecognized technology fields must not block onboarding."""
    report = onboard_from_intake_payload({"application_name": "Demo App X"}, executor=make_executor({}))
    assert report["ok"] is True
    assert report["assets"] == []
    assert "note" in report


def test_intake_bridge_does_not_hardcode_application_or_technology_names():
    import inspect

    from modules.operations.engines import common_control_onboarding as mod

    src = inspect.getsource(mod.onboard_from_intake_payload)
    for banned in ("WealthX", "Net Banking", "Mobile Banking", "PostgreSQL", "Oracle"):
        assert banned not in src


# --------------------------------------------------------------------------- #
# Report generation with mixed verdicts / honest coverage
# --------------------------------------------------------------------------- #
def test_report_mixed_verdicts_never_inflates_framework_compliance():
    fixtures = dict(PG_ALL_PASS)
    fixtures["PGX-013"] = _ok("name | setting\n--------------\nlog_connections | off\nlog_statement | none")
    report = onboard_from_intake_payload(
        {"application_name": "Demo", "database_technology": "PostgreSQL"},
        executor=make_executor(fixtures),
    )
    assert report["partial"], "audit-logging should be PARTIAL (pgaudit ok, log settings off)"
    assert report["coverage_pct"] < 100.0
    for fw in report["frameworks"]:
        # A framework can only show 100% coverage if every mapped control it
        # touches is fully implemented — never rounded up from partial/unknown.
        if fw["coverage_pct"] == 100.0:
            assert fw["partial"] == 0 and fw["unknown"] == 0


def test_report_never_marks_unmapped_technology_control_as_implemented():
    # Tomcat has no encryption-at-rest rule (PostgreSQL now does — see
    # EAR-CLOUD-POSTGRESQL — so it no longer represents "unmapped" here).
    report = onboard_from_intake_payload(
        {"application_name": "Demo", "middleware_technology": "Tomcat"},
        executor=make_executor({}),
    )
    ear = next(c for c in report["controls"] if c["control"] == "encryption-at-rest")
    assert ear["verdict"] == VERDICT_NOT_APPLICABLE


# --------------------------------------------------------------------------- #
# UNKNOWN / CONNECTIVITY_PENDING never blocks onboarding completion
# --------------------------------------------------------------------------- #
def test_all_connectivity_unavailable_still_completes():
    report = onboard_from_intake_payload(
        {"application_name": "Demo", "database_technology": "PostgreSQL", "middleware_technology": "Tomcat"},
        executor=make_executor({}),
    )
    assert report["ok"] is True
    assert report["connectivity_pending"]
    assert not report["implemented"]
    assert all(c["verdict"] != VERDICT_IMPLEMENTED for c in report["controls"])
    assert any(c["verdict"] == VERDICT_UNKNOWN for c in report["controls"])


def test_route_helper_never_raises_and_never_blocks_onboarding(monkeypatch):
    """The route-level wrapper must degrade gracefully even on an internal bug —
    onboarding completion can never depend on control evaluation succeeding."""
    import modules.operations.engines.common_control_onboarding as cco
    from modules.shared.routes.routes_mvp import _run_onboarding_control_evaluation

    def _boom(payload, **kwargs):
        raise RuntimeError("simulated engine failure")

    monkeypatch.setattr(cco, "onboard_from_intake_payload", _boom)
    result = _run_onboarding_control_evaluation({"application_name": "Demo"})
    assert result["ok"] is False
    assert "error" in result


def test_route_helper_delegates_to_intake_bridge(monkeypatch):
    from modules.shared.routes.routes_mvp import _run_onboarding_control_evaluation

    sentinel = {"ok": True, "controls": [], "coverage_pct": 0.0}
    called = {}

    def _fake(payload, **kwargs):
        called["payload"] = payload
        return sentinel

    import modules.shared.routes.routes_mvp as routes_mod

    monkeypatch.setattr(
        "modules.operations.engines.common_control_onboarding.onboard_from_intake_payload", _fake
    )
    payload = {"application_name": "Demo"}
    result = _run_onboarding_control_evaluation(payload)
    assert result is sentinel
    assert called["payload"] == payload


# --------------------------------------------------------------------------- #
# Report export (existing text-export pattern reused)
# --------------------------------------------------------------------------- #
def test_export_summary_includes_control_evaluation_section():
    payload = {"application_name": "WealthX Portal", "database_technology": "PostgreSQL", "owner": "R. Mehta"}
    result = simulate_onboarding(payload)
    result["control_evaluation"] = onboard_from_intake_payload(payload, executor=make_executor(PG_ALL_PASS))
    text = export_onboarding_summary(result)
    assert "REUSABLE COMMON CONTROL EVALUATION" in text
    assert "not full framework compliance" in text
    assert "Coverage:" in text


def test_export_summary_backward_compatible_without_control_evaluation():
    """Regression: existing callers that never attach control_evaluation must
    still get the exact original export (no new section, no crash)."""
    payload = {"application_name": "Legacy App", "owner": "U"}
    result = simulate_onboarding(payload)
    text = export_onboarding_summary(result)
    assert "REUSABLE COMMON CONTROL EVALUATION" not in text
    assert "ECS APPLICATION ONBOARDING SUMMARY" in text


def test_export_summary_handles_no_technology_note():
    payload = {"application_name": "Demo App X", "owner": "U"}
    result = simulate_onboarding(payload)
    result["control_evaluation"] = onboard_from_intake_payload(payload, executor=make_executor({}))
    text = export_onboarding_summary(result)
    assert "REUSABLE COMMON CONTROL EVALUATION" in text
    assert "No recognized technology submitted" in text


# --------------------------------------------------------------------------- #
# Regression — existing (mock) onboarding simulator untouched
# --------------------------------------------------------------------------- #
def test_simulate_onboarding_output_shape_unchanged():
    result = simulate_onboarding({"application_name": "Demo App X", "owner": "U", "pci_dss_in_scope": "No"})
    for key in ("metadata", "framework_results", "discovered_controls", "overall_readiness", "remediation_gaps"):
        assert key in result
    assert "control_evaluation" not in result  # only the route attaches it, not the engine itself
    assert "PCI DSS" not in [f["framework"] for f in result["framework_results"]]


def test_api_route_wiring_via_testclient():
    """End-to-end through the actual FastAPI route, when httpx is available."""
    try:
        from fastapi.testclient import TestClient
    except Exception as exc:  # noqa: BLE001 - environment-dependent optional dep
        pytest.skip(f"TestClient unavailable in this environment: {exc}")

    from app.main import app

    client = TestClient(app)

    # run_onboarder / status actions must be unaffected (early-return branches).
    r0 = client.post("/api/onboarding/simulate", json={"action": "run_onboarder", "role": "owner"})
    assert r0.status_code == 200
    assert "control_evaluation" not in r0.json()

    r1 = client.post(
        "/api/onboarding/simulate",
        json={"application_name": "Demo App X", "owner": "U", "database_technology": "PostgreSQL", "role": "owner"},
    )
    assert r1.status_code == 200
    body = r1.json()
    assert "control_evaluation" in body
    assert body["control_evaluation"]["ok"] is True

    r2 = client.post("/api/onboarding/export", json={"result": body, "role": "owner"})
    assert r2.status_code == 200
    assert b"REUSABLE COMMON CONTROL EVALUATION" in r2.content
