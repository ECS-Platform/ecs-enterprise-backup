"""Scheduler wiring for the reusable Common-Control rule engine.

Proves the additive, opt-in wiring added to ``run_scheduler_collection``:
  * OFF by default (``ECS_REUSABLE_COMMON_CONTROL_SCHEDULER_ENABLED`` unset) —
    byte-for-byte unchanged existing scheduler behavior.
  * ON: re-evaluates every Phase-2 portfolio application via the same
    ``onboard_application`` used by the on-demand trigger, with
    ``persist=True``.
  * A failure inside this step never breaks the overall scheduler run.

No live connectors / no network: the asset planner is stubbed exactly like the
existing scheduler wiring tests, and ``onboard_application`` itself is stubbed
so no real predefined-query execution happens.
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from modules.audit_intelligence.services import asset_scheduler as sch
from modules.operations.engines import scheduler_module as sm


def _plan(jobs):
    p = sch.EvidencePlan()
    p.jobs = list(jobs)
    return p


@pytest.fixture(autouse=True)
def _stub_planner(monkeypatch):
    """Same minimal-plan stub the existing scheduler wiring tests use — keeps
    every OTHER collector a fast no-op so only the reusable-common-control
    block under test actually does anything."""
    monkeypatch.setenv("ECS_COMMON_CONTROLS_COLLECTION_ENABLED", "false")
    monkeypatch.setenv("ECS_PREDEFINED_QUERY_SCHEDULER_ENABLED", "false")
    monkeypatch.setenv("ECS_MOCK_EVIDENCE_COLLECTION_ENABLED", "false")
    monkeypatch.setattr(sch, "load_assets", lambda *a, **k: [])
    monkeypatch.setattr(sch, "plan_evidence", lambda *a, **k: _plan([]))
    monkeypatch.delenv("ECS_CONNECTOR_EXECUTION_ENABLED", raising=False)
    yield


def test_disabled_by_default_no_behavior_change():
    """Regression: with the flag unset, the new block must be a pure no-op."""
    result = sm.run_scheduler_collection(user="tester")
    assert result["reusable_common_controls"] == {}
    assert result["reusable_common_controls_evaluated"] == 0
    assert result["summary"]["environment_flags"]["ECS_REUSABLE_COMMON_CONTROL_SCHEDULER_ENABLED"] is False


def test_enabled_evaluates_every_portfolio_application(monkeypatch):
    monkeypatch.setenv("ECS_REUSABLE_COMMON_CONTROL_SCHEDULER_ENABLED", "true")

    calls: list[tuple[str, bool]] = []

    class _Profile:
        def __init__(self, app_id):
            self.id = app_id

    def _fake_profiles():
        return [_Profile("app_a"), _Profile("app_b")]

    def _fake_onboard(application_id, *, user="system", persist=False, **kwargs):
        calls.append((application_id, persist))
        return {
            "ok": True,
            "coverage_pct": 50.0,
            "controls": [{"control": "encryption-in-transit", "verdict": "IMPLEMENTED"}] * 3,
            "connectivity_pending": [],
        }

    monkeypatch.setattr(
        "modules.operations.engines.phase2_reusability.list_application_profiles", _fake_profiles
    )
    monkeypatch.setattr(
        "modules.operations.engines.common_control_onboarding.onboard_application", _fake_onboard
    )

    result = sm.run_scheduler_collection(user="scheduler-test")

    assert calls == [("app_a", True), ("app_b", True)]  # persist=True on every scheduled run
    rcc = result["reusable_common_controls"]
    assert [a["application_id"] for a in rcc["applications"]] == ["app_a", "app_b"]
    assert rcc["controls_evaluated"] == 6  # 3 controls x 2 apps
    assert result["reusable_common_controls_evaluated"] == 6
    steps = {e["step"] for e in result["progress"]}
    assert "reusable common controls" in steps


def test_failure_inside_step_does_not_break_the_run(monkeypatch):
    monkeypatch.setenv("ECS_REUSABLE_COMMON_CONTROL_SCHEDULER_ENABLED", "true")

    def _boom(**kwargs):
        raise RuntimeError("portfolio config unreadable")

    monkeypatch.setattr(
        "modules.operations.engines.phase2_reusability.list_application_profiles", _boom
    )

    result = sm.run_scheduler_collection(user="tester")

    assert result["ok"] is True  # overall run still completes
    assert "error" in result["reusable_common_controls"]


def test_connectivity_unavailable_reported_not_swallowed(monkeypatch):
    monkeypatch.setenv("ECS_REUSABLE_COMMON_CONTROL_SCHEDULER_ENABLED", "true")

    class _Profile:
        id = "app_a"

    def _fake_onboard(application_id, *, user="system", persist=False, **kwargs):
        return {
            "ok": True,
            "coverage_pct": 0.0,
            "controls": [{"control": "encryption-in-transit", "verdict": "UNKNOWN"}],
            "connectivity_pending": [{"control": "encryption-in-transit", "technology": "PostgreSQL"}],
        }

    monkeypatch.setattr(
        "modules.operations.engines.phase2_reusability.list_application_profiles", lambda: [_Profile()]
    )
    monkeypatch.setattr(
        "modules.operations.engines.common_control_onboarding.onboard_application", _fake_onboard
    )

    result = sm.run_scheduler_collection(user="tester")
    app_row = result["reusable_common_controls"]["applications"][0]
    assert app_row["connectivity_pending"] == 1
    assert app_row["ok"] is True  # UNKNOWN is a valid outcome, not a failure
