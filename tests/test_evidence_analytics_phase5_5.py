"""Unit tests for Evidence Analytics & Observation Assist Foundation (Phase 5.5).

Deterministic, non-LLM. Covers all six capabilities:
  A. Timeline engine           D. Closure assistant
  B. Difference engine         E. Search DSL
  C. Quality engine            F. Portfolio analytics

plus DTOs, edge cases, flag-OFF behavior, fail-safety, and composition with the
Phase 5.4 engines. Engines are exercised with force=True where we want to compute
regardless of default-off flags; flag behavior itself is tested via env.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

import app.evidence_analytics as ea
from app.evidence_analytics.closure import build_closure_plan, closure_assist_enabled
from app.evidence_analytics.difference import (
    diff_enabled,
    diff_latest_versions,
    diff_snapshots,
)
from app.evidence_analytics.dsl import execute as dsl_execute
from app.evidence_analytics.dsl import parse as dsl_parse
from app.evidence_analytics.dsl import search_dsl_enabled
from app.evidence_analytics.dtos import (
    ClosureCard,
    DifferenceCard,
    PortfolioCard,
    QualityCard,
    SearchCard,
    TimelineCard,
)
from app.evidence_analytics.models import EventType, QualityBand
from app.evidence_analytics.portfolio import build_portfolio, portfolio_enabled
from app.evidence_analytics.quality import assess_quality, quality_enabled
from app.evidence_analytics.timeline import (
    build_timeline,
    detect_approval_reversal,
    detect_quality_decline,
    timeline_enabled,
)

NOW = datetime(2026, 6, 14, 12, 0, 0, tzinfo=timezone.utc)

_ALL_FLAGS = [
    "EVIDENCE_TIMELINE_ENABLED", "EVIDENCE_SEARCH_DSL_ENABLED",
    "EVIDENCE_PORTFOLIO_ENABLED", "SUFFICIENCY_ENGINE_ENABLED",
    "EVIDENCE_CHANGE_DETECTION_ENABLED", "OBSERVATION_READINESS_ENABLED",
    "EVIDENCE_QUERY_ENABLED",
]


@pytest.fixture(autouse=True)
def _clear_flags(monkeypatch):
    for f in _ALL_FLAGS:
        monkeypatch.delenv(f, raising=False)
    yield


def _enable_all(monkeypatch):
    for f in _ALL_FLAGS:
        monkeypatch.setenv(f, "true")


def wf(action, ts, **over):
    base = {"action": action, "timestamp": ts, "actor": "u",
            "previous_status": "", "new_status": ""}
    base.update(over)
    return base


def ev(**over):
    base = {
        "evidence_id": "ev-1", "source_system": "github", "owner": "alice",
        "framework": "SOC2", "control_id": "c1",
        "submitted_controls": [{"control_id": "c1"}],
        "collected_timestamp": (NOW - timedelta(days=5)).isoformat(),
        "valid_until": (NOW + timedelta(days=60)).isoformat(),
        "approval_status": "approved", "version_count": 1,
    }
    base.update(over)
    return base


# =========================================================================== #
# A. Timeline engine
# =========================================================================== #

def test_timeline_disabled_by_default():
    t = build_timeline("ev-1", workflow_history=[wf("submit", "2026-01-01")])
    assert t.enabled is False
    assert "disabled" in t.note

def test_timeline_force_computes():
    t = build_timeline("ev-1", workflow_history=[wf("submit", "2026-01-01")], force=True)
    assert t.enabled is True
    assert len(t.events) == 1

def test_timeline_flag_enables(monkeypatch):
    _enable_all(monkeypatch)
    t = build_timeline("ev-1", workflow_history=[wf("submit", "2026-01-01")])
    assert t.enabled is True

def test_timeline_orders_by_timestamp():
    t = build_timeline("ev-1", workflow_history=[
        wf("approve", "2026-01-03"), wf("submit", "2026-01-01"),
        wf("update", "2026-01-02"),
    ], force=True)
    ts = [e.timestamp for e in t.events]
    assert ts == ["2026-01-01", "2026-01-02", "2026-01-03"]

def test_timeline_current_and_previous_state():
    t = build_timeline("ev-1", workflow_history=[
        wf("submit", "2026-01-01"), wf("approve", "2026-01-02"),
    ], force=True)
    assert t.current_state == EventType.EVIDENCE_APPROVED.value
    assert t.previous_state == EventType.EVIDENCE_SUBMITTED.value

def test_timeline_approval_reversal_detected():
    t = build_timeline("ev-1", workflow_history=[
        wf("approve", "2026-01-02"), wf("reject", "2026-01-03"),
    ], force=True)
    assert t.approval_reversed is True
    assert detect_approval_reversal(t) is True

def test_timeline_approval_reversal_via_reopen():
    t = build_timeline("ev-1", workflow_history=[
        wf("approve", "2026-01-02"), wf("reopen", "2026-01-03"),
    ], force=True)
    assert t.approval_reversed is True

def test_timeline_no_reversal_when_only_approved():
    t = build_timeline("ev-1", workflow_history=[
        wf("submit", "2026-01-01"), wf("approve", "2026-01-02"),
    ], force=True)
    assert t.approval_reversed is False

def test_timeline_reject_before_approve_not_reversal():
    t = build_timeline("ev-1", workflow_history=[
        wf("reject", "2026-01-01"), wf("approve", "2026-01-02"),
    ], force=True)
    assert t.approval_reversed is False

def test_timeline_quality_decline_detected():
    t = build_timeline("ev-1", workflow_history=[wf("submit", "2026-01-01")],
                       quality_by_version={1: 90, 2: 70}, force=True)
    assert t.quality_declining is True
    assert detect_quality_decline(t) is True

def test_timeline_quality_stable_not_declining():
    t = build_timeline("ev-1", workflow_history=[wf("submit", "2026-01-01")],
                       quality_by_version={1: 90, 2: 88}, force=True)
    assert t.quality_declining is False

def test_timeline_quality_improving_not_declining():
    t = build_timeline("ev-1", workflow_history=[wf("submit", "2026-01-01")],
                       quality_by_version={1: 60, 2: 90}, force=True)
    assert t.quality_declining is False

def test_timeline_from_audit_entries():
    t = build_timeline("ev-1", audit_entries=[
        {"action": "evidence.approve", "timestamp": "2026-01-02", "actor": "x"},
    ], force=True)
    assert len(t.events) == 1
    assert t.events[0].source == "audit_log"

def test_timeline_from_version_history():
    from app.evidence_intel.versioning import build_version_history
    h = build_version_history("ev-1", [{"hash": "h1"}, {"hash": "h2"}], force=True)
    t = build_timeline("ev-1", version_history=h, force=True)
    types = {e.event_type for e in t.events}
    assert EventType.EVIDENCE_CREATED.value in types
    assert EventType.EVIDENCE_UPDATED.value in types

def test_timeline_merges_multiple_sources():
    t = build_timeline("ev-1",
                       audit_entries=[{"action": "approve", "timestamp": "2026-01-02"}],
                       workflow_history=[wf("submit", "2026-01-01")],
                       observation_events=[{"action": "close", "timestamp": "2026-01-05"}],
                       force=True)
    sources = {e.source for e in t.events}
    assert {"audit_log", "workflow_history", "observation"} <= sources

def test_timeline_unknown_action_skipped():
    t = build_timeline("ev-1", workflow_history=[
        wf("comment", "2026-01-01"), wf("submit", "2026-01-02"),
    ], force=True)
    assert len(t.events) == 1

def test_timeline_empty_inputs():
    t = build_timeline("ev-1", force=True)
    assert t.enabled is True
    assert t.events == []
    assert t.current_state == ""

def test_timeline_missing_timestamp_sorted_last():
    t = build_timeline("ev-1", workflow_history=[
        wf("approve", ""), wf("submit", "2026-01-01"),
    ], force=True)
    assert t.events[0].timestamp == "2026-01-01"

def test_timeline_change_history_alias():
    t = build_timeline("ev-1", workflow_history=[wf("submit", "2026-01-01")], force=True)
    assert len(t.change_history) == len(t.events)

def test_timeline_to_dict_serializable():
    t = build_timeline("ev-1", workflow_history=[wf("submit", "2026-01-01")], force=True)
    d = t.to_dict()
    assert d["enabled"] is True
    assert "events" in d and "change_history" in d

def test_timeline_never_raises_on_bad_input():
    t = build_timeline("ev-1", workflow_history=[None, 123, "x"], force=True)
    assert t.enabled is True

def test_timeline_actor_captured():
    t = build_timeline("ev-1", workflow_history=[wf("approve", "2026-01-02", actor="bob")],
                       force=True)
    assert t.events[0].actor == "bob"

def test_timeline_states_captured():
    t = build_timeline("ev-1", workflow_history=[
        wf("approve", "2026-01-02", previous_status="Submitted", new_status="Approved")],
        force=True)
    assert t.events[0].previous_state == "Submitted"
    assert t.events[0].new_state == "Approved"

def test_timeline_quality_decline_below_threshold():
    t = build_timeline("ev-1", quality_by_version={1: 90, 2: 85}, force=True)
    assert t.quality_declining is False


# =========================================================================== #
# B. Difference engine
# =========================================================================== #

def test_diff_disabled_by_default():
    d = diff_snapshots({"status": "a"}, {"status": "b"}, evidence_id="e")
    assert d.enabled is False
    assert "disabled" in d.note

def test_diff_reuses_change_flag(monkeypatch):
    monkeypatch.setenv("EVIDENCE_CHANGE_DETECTION_ENABLED", "true")
    assert diff_enabled() is True
    d = diff_snapshots({"status": "Submitted"}, {"status": "Approved"}, evidence_id="e")
    assert d.enabled is True

def test_diff_snapshots_detects_change():
    d = diff_snapshots({"status": "Submitted"}, {"status": "Approved"},
                       evidence_id="e", force=True)
    assert d.enabled is True
    assert d.change_class in ("Major", "Minor")
    assert "approval_status" in d.changed_fields or d.changed_fields

def test_diff_snapshots_no_change():
    d = diff_snapshots({"status": "Approved"}, {"status": "Approved"},
                       evidence_id="e", force=True)
    assert d.change_class == "None"

def test_diff_latest_versions_two():
    snaps = [{"evidence_id": "e", "content_hash": "h1", "status": "Submitted"},
             {"evidence_id": "e", "content_hash": "h2", "status": "Approved"}]
    d = diff_latest_versions("e", snaps, force=True)
    assert d.from_version == 1
    assert d.to_version == 2
    assert d.enabled is True

def test_diff_latest_versions_single():
    d = diff_latest_versions("e", [{"evidence_id": "e", "content_hash": "h1"}], force=True)
    assert d.change_class == "None"
    assert "no prior" in d.summary

def test_diff_latest_versions_empty():
    d = diff_latest_versions("e", [], force=True)
    assert d.change_class == "None"

def test_diff_changed_fields_listed():
    d = diff_snapshots({"owner": "a", "status": "Submitted"},
                       {"owner": "b", "status": "Approved"}, evidence_id="e", force=True)
    assert "owner" in d.changed_fields

def test_diff_changes_detail_present():
    d = diff_snapshots({"status": "Submitted"}, {"status": "Approved"},
                       evidence_id="e", force=True)
    assert isinstance(d.changes, list)
    assert all(isinstance(c, dict) for c in d.changes)

def test_diff_evidence_id_from_new():
    d = diff_snapshots({"status": "a"}, {"evidence_id": "x", "status": "b"}, force=True)
    assert d.evidence_id == "x"

def test_diff_to_dict_serializable():
    d = diff_snapshots({"status": "a"}, {"status": "b"}, evidence_id="e", force=True)
    assert "change_class" in d.to_dict()

def test_diff_never_raises_bad_input():
    d = diff_snapshots(None, None, evidence_id="e", force=True)
    assert d.evidence_id == "e"

def test_diff_latest_collapses_identical_hash():
    snaps = [{"evidence_id": "e", "content_hash": "h1"},
             {"evidence_id": "e", "content_hash": "h1"}]
    d = diff_latest_versions("e", snaps, force=True)
    # identical hash collapses -> single version -> no comparison
    assert d.change_class == "None"


# =========================================================================== #
# C. Quality engine
# =========================================================================== #

def test_quality_disabled_by_default():
    q = assess_quality(ev())
    assert q.enabled is False
    assert "disabled" in q.note

def test_quality_reuses_sufficiency_flag(monkeypatch):
    monkeypatch.setenv("SUFFICIENCY_ENGINE_ENABLED", "true")
    assert quality_enabled() is True
    q = assess_quality(ev())
    assert q.enabled is True

def test_quality_force_computes():
    q = assess_quality(ev(), framework="SOC2", force=True)
    assert q.enabled is True
    assert 0 <= q.score <= 100

def test_quality_four_dimensions():
    q = assess_quality(ev(), force=True)
    names = {d.name for d in q.dimensions}
    assert names == {"sufficiency", "reuse_confidence", "version_stability",
                     "source_reliability"}

def test_quality_band_green():
    q = assess_quality(ev(source_system="sonarqube"), framework="SOC2", force=True)
    assert q.band in (QualityBand.GREEN.value, QualityBand.AMBER.value,
                      QualityBand.RED.value)

def test_quality_reliable_source_higher_than_manual():
    q_rel = assess_quality(ev(source_system="sonarqube"), force=True)
    q_man = assess_quality(ev(source_system="manual"), force=True)
    rel = next(d.score for d in q_rel.dimensions if d.name == "source_reliability")
    man = next(d.score for d in q_man.dimensions if d.name == "source_reliability")
    assert rel > man

def test_quality_unknown_source_default():
    q = assess_quality(ev(source_system="weird-thing"), force=True)
    s = next(d.score for d in q.dimensions if d.name == "source_reliability")
    assert s == 60

def test_quality_version_stability_penalizes_churn():
    q1 = assess_quality(ev(version_count=1), force=True)
    q5 = assess_quality(ev(version_count=5), force=True)
    s1 = next(d.score for d in q1.dimensions if d.name == "version_stability")
    s5 = next(d.score for d in q5.dimensions if d.name == "version_stability")
    assert s1 > s5

def test_quality_major_change_penalty():
    q = assess_quality(ev(version_count=1, last_change_class="major"), force=True)
    s = next(d.score for d in q.dimensions if d.name == "version_stability")
    assert s <= 75

def test_quality_reasons_present():
    q = assess_quality(ev(), force=True)
    assert len(q.reasons) == 4

def test_quality_weights_normalized():
    q = assess_quality(ev(), force=True)
    total = sum(d.weight for d in q.dimensions)
    assert abs(total - 1.0) < 0.01

def test_quality_to_dict_serializable():
    q = assess_quality(ev(), force=True)
    d = q.to_dict()
    assert d["band"] in ("Green", "Amber", "Red")

def test_quality_never_raises_bad_input():
    q = assess_quality("not a dict", force=True)
    assert q.enabled is False

def test_quality_missing_source_treated_manual():
    q = assess_quality({"evidence_id": "e"}, force=True)
    s = next(d.score for d in q.dimensions if d.name == "source_reliability")
    assert s == 50  # manual

def test_quality_version_history_object_counted():
    from app.evidence_intel.versioning import build_version_history
    h = build_version_history("e", [{"hash": "1"}, {"hash": "2"}, {"hash": "3"}], force=True)
    q = assess_quality(ev(version_history=h, version_count=None), force=True)
    s = next(d.score for d in q.dimensions if d.name == "version_stability")
    assert s < 100


# =========================================================================== #
# D. Closure assistant
# =========================================================================== #

def obs(**over):
    base = {"observation_id": "o1", "control_id": "c1"}
    base.update(over)
    return base

def test_closure_disabled_by_default():
    p = build_closure_plan(obs(), [])
    assert p.enabled is False
    assert "disabled" in p.note

def test_closure_reuses_readiness_flag(monkeypatch):
    monkeypatch.setenv("OBSERVATION_READINESS_ENABLED", "true")
    assert closure_assist_enabled() is True
    p = build_closure_plan(obs(), [])
    assert p.enabled is True

def test_closure_force_computes():
    p = build_closure_plan(obs(), [], force=True)
    assert p.enabled is True
    assert 0 <= p.closure_readiness_pct <= 100

def test_closure_no_evidence_recommends_attach():
    p = build_closure_plan(obs(), [], force=True)
    assert any("evidence" in a.lower() for a in p.recommended_next_actions)

def test_closure_band_present():
    p = build_closure_plan(obs(), [], force=True)
    assert p.readiness_band

def test_closure_blocking_items_listed():
    p = build_closure_plan(obs(), [], force=True)
    assert isinstance(p.blocking_items, list)

def test_closure_ready_observation_proceed():
    items = [ev(approval_status="approved")]
    p = build_closure_plan(
        obs(remediation_plan="done", evidence_count=1, status="approved"),
        items, force=True)
    assert p.enabled is True
    assert isinstance(p.recommended_next_actions, list)

def test_closure_to_dict_serializable():
    p = build_closure_plan(obs(), [], force=True)
    assert "recommended_next_actions" in p.to_dict()

def test_closure_never_raises_bad_input():
    p = build_closure_plan(None, None, force=True)
    assert p.enabled in (True, False)

def test_closure_observation_id_captured():
    p = build_closure_plan(obs(observation_id="obs-9"), [], force=True)
    assert p.observation_id == "obs-9"

def test_closure_recommendations_deduplicated():
    p = build_closure_plan(obs(), [], force=True)
    assert len(p.recommended_next_actions) == len(set(p.recommended_next_actions))


# =========================================================================== #
# E. Search DSL
# =========================================================================== #

def test_dsl_disabled_by_default():
    r = dsl_execute("framework=SOC2", [{"framework": "SOC2"}])
    assert r.enabled is False
    assert "disabled" in r.note

def test_dsl_flag_enables(monkeypatch):
    monkeypatch.setenv("EVIDENCE_SEARCH_DSL_ENABLED", "true")
    assert search_dsl_enabled() is True
    r = dsl_execute("framework=SOC2", [{"framework": "SOC2"}])
    assert r.enabled is True

def test_dsl_parse_single_condition():
    q = dsl_parse("framework=SOC2")
    assert q.valid is True
    assert len(q.conditions) == 1
    assert q.conditions[0].field_name == "framework"

def test_dsl_parse_and_conditions():
    q = dsl_parse("framework=SOC2 AND status=approved")
    assert q.valid is True
    assert len(q.conditions) == 2

def test_dsl_parse_quoted_value():
    q = dsl_parse('application="Payments API"')
    assert q.valid is True
    assert q.conditions[0].value == "Payments API"

def test_dsl_parse_numeric_operator():
    q = dsl_parse("age>90")
    assert q.valid is True
    assert q.conditions[0].operator == ">"
    assert q.conditions[0].value == 90

def test_dsl_parse_gte_lte():
    q = dsl_parse("quality>=80 AND age<=30")
    assert q.valid is True
    ops = [c.operator for c in q.conditions]
    assert ">=" in ops and "<=" in ops

def test_dsl_parse_not_equal():
    q = dsl_parse("status!=approved")
    assert q.valid is True
    assert q.conditions[0].operator == "!="

def test_dsl_parse_boolean_value():
    q = dsl_parse("reused=true")
    assert q.valid is True
    assert q.conditions[0].value is True

def test_dsl_parse_unknown_field():
    q = dsl_parse("nonsense=x")
    assert q.valid is False
    assert any("unknown field" in e for e in q.errors)

def test_dsl_parse_range_op_on_string_field():
    q = dsl_parse("status>5")
    assert q.valid is False

def test_dsl_parse_missing_and():
    q = dsl_parse("framework=SOC2 age>90")
    assert q.valid is False

def test_dsl_parse_incomplete_condition():
    q = dsl_parse("framework=")
    assert q.valid is False

def test_dsl_parse_empty():
    q = dsl_parse("")
    assert q.valid is False
    assert "empty query" in q.errors

def test_dsl_parse_trailing_and():
    q = dsl_parse("framework=SOC2 AND")
    assert q.valid is False

def test_dsl_parse_unterminated_quote():
    q = dsl_parse('application="Payments')
    assert q.valid is False

def test_dsl_parse_numeric_expects_number():
    q = dsl_parse("age>abc")
    assert q.valid is False

def test_dsl_execute_equality_filter():
    rows = [{"framework": "SOC2"}, {"framework": "PCI"}]
    r = dsl_execute("framework=SOC2", rows, force=True)
    assert r.total == 1

def test_dsl_execute_case_insensitive():
    rows = [{"framework": "soc2"}]
    r = dsl_execute("framework=SOC2", rows, force=True)
    assert r.total == 1

def test_dsl_execute_age_filter():
    rows = [
        {"collected_timestamp": (NOW - timedelta(days=120)).isoformat()},
        {"collected_timestamp": (NOW - timedelta(days=10)).isoformat()},
    ]
    r = dsl_execute("age>90", rows, now=NOW, force=True)
    assert r.total == 1

def test_dsl_execute_quality_filter():
    rows = [{"quality": 90}, {"quality": 40}]
    r = dsl_execute("quality>=80", rows, force=True)
    assert r.total == 1

def test_dsl_execute_boolean_reused():
    rows = [{"submitted_controls": ["c1", "c2"]}, {"submitted_controls": ["c1"]}]
    r = dsl_execute("reused=true", rows, force=True)
    assert r.total == 1

def test_dsl_execute_approved_boolean():
    rows = [{"approval_status": "approved"}, {"approval_status": "pending"}]
    r = dsl_execute("approved=true", rows, force=True)
    assert r.total == 1

def test_dsl_execute_and_combination():
    rows = [
        {"framework": "SOC2", "approval_status": "approved"},
        {"framework": "SOC2", "approval_status": "pending"},
    ]
    r = dsl_execute("framework=SOC2 AND approved=true", rows, force=True)
    assert r.total == 1

def test_dsl_execute_not_equal():
    rows = [{"status": "approved"}, {"status": "rejected"}]
    r = dsl_execute("status!=approved", rows, force=True)
    assert r.total == 1

def test_dsl_execute_invalid_returns_empty():
    r = dsl_execute("badfield=x", [{"a": 1}], force=True)
    assert r.total == 0
    assert "invalid" in r.note

def test_dsl_execute_year_filter():
    rows = [{"audit_year": 2026}, {"audit_year": 2024}]
    r = dsl_execute("audit_year=2026", rows, force=True)
    assert r.total == 1

def test_dsl_injection_safe_no_eval():
    # Attempting code-like input must not execute; just fail to parse.
    q = dsl_parse("__import__('os').system('echo x')=1")
    assert q.valid is False

def test_dsl_max_conditions(monkeypatch):
    parts = " AND ".join(["framework=SOC2"] * 25)
    q = dsl_parse(parts)
    assert q.valid is False

def test_dsl_to_dict_serializable():
    r = dsl_execute("framework=SOC2", [{"framework": "SOC2"}], force=True)
    d = r.to_dict()
    assert "query" in d and "rows" in d

def test_dsl_execute_never_raises():
    r = dsl_execute("framework=SOC2", [None, 5, "x"], force=True)
    assert r.enabled is True


# =========================================================================== #
# F. Portfolio analytics
# =========================================================================== #

def test_portfolio_disabled_by_default():
    p = build_portfolio("cio", [ev()], [])
    assert p.enabled is False
    assert "disabled" in p.note

def test_portfolio_flag_enables(monkeypatch):
    monkeypatch.setenv("EVIDENCE_PORTFOLIO_ENABLED", "true")
    assert portfolio_enabled() is True
    p = build_portfolio("cio", [ev()], [])
    assert p.enabled is True

def test_portfolio_force_computes():
    p = build_portfolio("cio", [ev(), ev(evidence_id="ev-2")], [], force=True)
    assert p.enabled is True
    assert p.evidence_count == 2

def test_portfolio_coverage_pct():
    rows = [ev(framework="SOC2"), {"evidence_id": "x"}]
    p = build_portfolio("cio", rows, [], force=True)
    assert p.coverage_pct == 50.0

def test_portfolio_reuse_pct():
    rows = [ev(submitted_controls=["c1", "c2"]), ev(submitted_controls=["c1"])]
    p = build_portfolio("cio", rows, [], force=True)
    assert p.reuse_pct == 50.0

def test_portfolio_staleness_pct():
    rows = [
        ev(collected_timestamp=(NOW - timedelta(days=200)).isoformat()),
        ev(collected_timestamp=(NOW - timedelta(days=5)).isoformat()),
    ]
    p = build_portfolio("cio", rows, [], now=NOW, force=True)
    assert p.staleness_pct == 50.0

def test_portfolio_approval_sla_within():
    rows = [ev(approval_status="approved",
               submitted_at="2026-01-01T00:00:00",
               approved_at="2026-01-05T00:00:00")]
    p = build_portfolio("cio", rows, [], force=True)
    assert p.approval_sla_pct == 100.0

def test_portfolio_approval_sla_breached():
    rows = [ev(approval_status="approved",
               submitted_at="2026-01-01T00:00:00",
               approved_at="2026-03-01T00:00:00")]
    p = build_portfolio("cio", rows, [], force=True)
    assert p.approval_sla_pct == 0.0

def test_portfolio_observation_count():
    p = build_portfolio("cio", [], [{"observation_id": "o1"}, {"observation_id": "o2"}],
                        force=True)
    assert p.observation_count == 2

def test_portfolio_closure_forecast():
    p = build_portfolio("cio", [], [{"observation_id": "o1"}], force=True)
    # one observation with blockers -> forecast > 0
    assert p.closure_forecast_days >= 0

def test_portfolio_empty_inputs():
    p = build_portfolio("cio", [], [], force=True)
    assert p.evidence_count == 0
    assert p.coverage_pct == 0.0

def test_portfolio_persona_captured():
    p = build_portfolio("application_owner", [ev()], [], scope_label="App X", force=True)
    assert p.persona == "application_owner"
    assert p.scope_label == "App X"

def test_portfolio_to_dict_serializable():
    p = build_portfolio("cio", [ev()], [], force=True)
    assert "coverage_pct" in p.to_dict()

def test_portfolio_never_raises_bad_input():
    p = build_portfolio("cio", [None, 5], [None], force=True)
    assert p.enabled is True

def test_portfolio_reuse_via_frameworks():
    rows = [ev(submitted_controls=["c1"], frameworks=["SOC2", "PCI"])]
    p = build_portfolio("cio", rows, [], force=True)
    assert p.reuse_pct == 100.0


# =========================================================================== #
# DTOs
# =========================================================================== #

def test_timeline_card():
    t = build_timeline("ev-1", workflow_history=[
        wf("approve", "2026-01-02"), wf("reject", "2026-01-03")], force=True)
    c = TimelineCard.from_timeline(t)
    assert "approval_reversed" in c.flags
    assert c.event_count == 2
    assert "current_state" in c.to_dict()

def test_difference_card():
    d = diff_snapshots({"status": "a"}, {"status": "b"}, evidence_id="e", force=True)
    c = DifferenceCard.from_difference(d)
    assert c.evidence_id == "e"
    assert "change_class" in c.to_dict()

def test_quality_card():
    q = assess_quality(ev(), force=True)
    c = QualityCard.from_report(q)
    assert c.band in ("Green", "Amber", "Red")
    assert "score" in c.to_dict()

def test_closure_card():
    p = build_closure_plan(obs(), [], force=True)
    c = ClosureCard.from_plan(p)
    assert "next_action" in c.to_dict()

def test_search_card():
    r = dsl_execute("framework=SOC2", [{"framework": "SOC2"}], force=True)
    c = SearchCard.from_result(r)
    assert c.valid is True
    assert "total" in c.to_dict()

def test_portfolio_card():
    p = build_portfolio("cio", [ev()], [], force=True)
    c = PortfolioCard.from_view(p)
    assert c.persona == "cio"
    assert "coverage_pct" in c.to_dict()


# =========================================================================== #
# Cross-cutting: flags OFF => inert; no LLM/network; package surface
# =========================================================================== #

def test_all_engines_disabled_with_no_env():
    assert timeline_enabled() is False
    assert diff_enabled() is False
    assert quality_enabled() is False
    assert closure_assist_enabled() is False
    assert search_dsl_enabled() is False
    assert portfolio_enabled() is False

def test_package_exports_complete():
    for name in ["build_timeline", "diff_snapshots", "assess_quality",
                 "build_closure_plan", "dsl_execute", "build_portfolio"]:
        assert hasattr(ea, name)

def test_no_llm_or_network_imports():
    import app.evidence_analytics as pkg
    import importlib
    import pkgutil
    forbidden = ("requests", "httpx", "openai", "ollama", "psycopg", "sqlalchemy",
                 "langchain", "sentence_transformers", "chromadb")
    for mod in pkgutil.iter_modules(pkg.__path__):
        m = importlib.import_module(f"app.evidence_analytics.{mod.name}")
        src = (m.__doc__ or "")
        for bad in forbidden:
            assert f"import {bad}" not in (open(m.__file__).read()), f"{mod.name} imports {bad}"

def test_disabled_engines_return_safe_objects():
    assert build_timeline("e").to_dict()["enabled"] is False
    assert diff_snapshots({}, {}, evidence_id="e").to_dict()["enabled"] is False
    assert assess_quality(ev()).to_dict()["enabled"] is False
    assert build_closure_plan(obs(), []).to_dict()["enabled"] is False
    assert dsl_execute("framework=SOC2", []).to_dict()["enabled"] is False
    assert build_portfolio("cio", [], []).to_dict()["enabled"] is False


# =========================================================================== #
# Config-driven behavior + additional edge cases
# =========================================================================== #

def test_config_loads():
    from ecs_platform.config.loader import load_config
    cfg = load_config("evidence_analytics")["evidence_analytics"]
    assert "quality" in cfg and "dsl" in cfg and "portfolio" in cfg

def test_env_flag_overrides_config(monkeypatch):
    monkeypatch.setenv("EVIDENCE_TIMELINE_ENABLED", "false")
    assert timeline_enabled() is False
    monkeypatch.setenv("EVIDENCE_TIMELINE_ENABLED", "true")
    assert timeline_enabled() is True

def test_env_flag_various_truthy(monkeypatch):
    for v in ("1", "yes", "on", "TRUE"):
        monkeypatch.setenv("EVIDENCE_PORTFOLIO_ENABLED", v)
        assert portfolio_enabled() is True

def test_quality_source_variety():
    for src, expect in [("gitea", 90), ("jira", 80), ("confluence", 75),
                        ("manual", 50), ("prisma", 88)]:
        q = assess_quality(ev(source_system=src), force=True)
        s = next(d.score for d in q.dimensions if d.name == "source_reliability")
        assert s == expect

def test_quality_score_bounded():
    q = assess_quality(ev(version_count=50, last_change_class="major",
                          source_system="manual"), force=True)
    assert 0 <= q.score <= 100

def test_quality_band_thresholds_consistent():
    q = assess_quality(ev(source_system="sonarqube"), framework="SOC2", force=True)
    if q.score >= 80:
        assert q.band == "Green"
    elif q.score >= 55:
        assert q.band == "Amber"
    else:
        assert q.band == "Red"

def test_timeline_priority_tie_break():
    # Same timestamp; created should sort before updated by priority.
    t = build_timeline("e", workflow_history=[
        wf("update", "2026-01-01"), wf("create", "2026-01-01")], force=True)
    assert t.events[0].event_type == EventType.EVIDENCE_CREATED.value

def test_timeline_observation_close_event():
    t = build_timeline("o1", observation_events=[
        {"action": "observation.close", "timestamp": "2026-02-01"}], force=True)
    assert t.events[0].event_type == EventType.OBSERVATION_CLOSED.value

def test_timeline_substring_action_match():
    t = build_timeline("e", workflow_history=[wf("evidence.approve", "2026-01-01")],
                       force=True)
    assert t.events[0].event_type == EventType.EVIDENCE_APPROVED.value

def test_dsl_field_owner():
    rows = [{"owner": "alice"}, {"owner": "bob"}]
    r = dsl_execute("owner=alice", rows, force=True)
    assert r.total == 1

def test_dsl_field_source_system():
    rows = [{"source_system": "github"}, {"source_system": "jira"}]
    r = dsl_execute("source_system=github", rows, force=True)
    assert r.total == 1

def test_dsl_field_control():
    rows = [{"control": "AC-2"}, {"control": "AC-3"}]
    r = dsl_execute("control=AC-2", rows, force=True)
    assert r.total == 1

def test_dsl_quoted_field_with_spaces():
    rows = [{"application": "Payments API"}, {"application": "Other"}]
    r = dsl_execute('application="Payments API"', rows, force=True)
    assert r.total == 1

def test_dsl_lt_operator():
    rows = [{"quality": 30}, {"quality": 90}]
    r = dsl_execute("quality<50", rows, force=True)
    assert r.total == 1

def test_dsl_gt_strict():
    rows = [{"quality": 80}, {"quality": 81}]
    r = dsl_execute("quality>80", rows, force=True)
    assert r.total == 1

def test_dsl_gte_inclusive():
    rows = [{"quality": 80}, {"quality": 79}]
    r = dsl_execute("quality>=80", rows, force=True)
    assert r.total == 1

def test_dsl_missing_numeric_field_excluded():
    rows = [{"framework": "SOC2"}]  # no quality field
    r = dsl_execute("quality>50", rows, force=True)
    assert r.total == 0

def test_dsl_three_conditions():
    rows = [{"framework": "SOC2", "owner": "alice", "approval_status": "approved"}]
    r = dsl_execute("framework=SOC2 AND owner=alice AND approved=true", rows, force=True)
    assert r.total == 1

def test_dsl_no_match():
    rows = [{"framework": "PCI"}]
    r = dsl_execute("framework=SOC2", rows, force=True)
    assert r.total == 0

def test_dsl_reused_false():
    rows = [{"submitted_controls": ["c1"]}, {"submitted_controls": ["c1", "c2"]}]
    r = dsl_execute("reused=false", rows, force=True)
    assert r.total == 1

def test_dsl_parse_lowercase_and():
    q = dsl_parse("framework=SOC2 and owner=alice")
    assert q.valid is True

def test_portfolio_sla_no_timing_neutral():
    rows = [ev(approval_status="approved", submitted_at="", approved_at="")]
    p = build_portfolio("cio", rows, [], force=True)
    assert p.approval_sla_pct == 100.0  # approved w/o timing counts as met

def test_portfolio_sla_excludes_unapproved():
    rows = [ev(approval_status="pending")]
    p = build_portfolio("cio", rows, [], force=True)
    assert p.approval_sla_pct == 0.0  # no eligible -> 0

def test_portfolio_coverage_full():
    rows = [ev(framework="SOC2"), ev(control_id="c9")]
    p = build_portfolio("cio", rows, [], force=True)
    assert p.coverage_pct == 100.0

def test_portfolio_reuse_zero():
    rows = [ev(submitted_controls=["c1"], frameworks=["SOC2"])]
    p = build_portfolio("cio", rows, [], force=True)
    assert p.reuse_pct == 0.0

def test_portfolio_staleness_zero():
    rows = [ev(collected_timestamp=(NOW - timedelta(days=1)).isoformat())]
    p = build_portfolio("cio", rows, [], now=NOW, force=True)
    assert p.staleness_pct == 0.0

def test_portfolio_observations_ready_counts():
    ready_obs = {"observation_id": "o", "status": "approved",
                 "remediation_plan": "x", "evidence_count": 1,
                 "evidence_items": [ev(approval_status="approved")]}
    p = build_portfolio("cio", [], [ready_obs], force=True)
    assert p.observations_ready >= 0

def test_closure_stale_evidence_action():
    items = [ev(collected_timestamp=(NOW - timedelta(days=400)).isoformat(),
                valid_until=(NOW - timedelta(days=10)).isoformat())]
    p = build_closure_plan(obs(), items, force=True)
    assert p.enabled is True

def test_diff_minor_change_class():
    d = diff_snapshots({"title": "a"}, {"title": "b"}, evidence_id="e", force=True)
    assert d.change_class in ("Minor", "Major", "None")

def test_diff_from_to_versions_set():
    snaps = [{"evidence_id": "e", "content_hash": str(i)} for i in range(3)]
    d = diff_latest_versions("e", snaps, force=True)
    assert d.from_version == 2 and d.to_version == 3

def test_quality_dim_weights_sum_in_dict():
    q = assess_quality(ev(), force=True)
    total = sum(d["weight"] for d in q.to_dict()["dimensions"])
    assert abs(total - 1.0) < 0.02

def test_timeline_card_no_flags_when_clean():
    t = build_timeline("e", workflow_history=[
        wf("submit", "2026-01-01"), wf("approve", "2026-01-02")], force=True)
    c = TimelineCard.from_timeline(t)
    assert c.flags == []

def test_search_card_invalid():
    r = dsl_execute("badfield=x", [], force=True)
    c = SearchCard.from_result(r)
    assert c.valid is False
    assert c.errors

def test_quality_enabled_via_sufficiency(monkeypatch):
    monkeypatch.setenv("SUFFICIENCY_ENGINE_ENABLED", "true")
    q = assess_quality(ev())
    assert q.enabled is True

def test_diff_enabled_via_change(monkeypatch):
    monkeypatch.setenv("EVIDENCE_CHANGE_DETECTION_ENABLED", "true")
    d = diff_snapshots({"a": 1}, {"a": 2}, evidence_id="e")
    assert d.enabled is True

def test_closure_enabled_via_readiness(monkeypatch):
    monkeypatch.setenv("OBSERVATION_READINESS_ENABLED", "true")
    p = build_closure_plan(obs(), [])
    assert p.enabled is True

def test_models_to_dict_all_serializable():
    import json
    objs = [
        build_timeline("e", workflow_history=[wf("submit", "2026-01-01")], force=True),
        diff_snapshots({"a": 1}, {"a": 2}, evidence_id="e", force=True),
        assess_quality(ev(), force=True),
        build_closure_plan(obs(), [], force=True),
        dsl_execute("framework=SOC2", [{"framework": "SOC2"}], force=True),
        build_portfolio("cio", [ev()], [], force=True),
    ]
    for o in objs:
        json.dumps(o.to_dict())  # must not raise

def test_timeline_quality_decline_threshold_config():
    # default threshold 10; a 10-point drop should trip.
    t = build_timeline("e", quality_by_version={1: 80, 2: 70}, force=True)
    assert t.quality_declining is True
