"""Unit tests for the Evidence Sufficiency Engine (Phase 5.2-A).

Read-only, deterministic, no-LLM. These tests validate the rules library, the
composite engine, the feature-flag gate, fail-safe behavior, explanations, and
that scoring works against real ECS evidence shapes (EvidenceItem + repository
columns + evidence_reviews fields).

No database, RAG, network, or LLM is touched. The engine is exercised with
force=True where we want to compute regardless of the (default-off) flag.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.sufficiency.engine import (
    EvidenceScore,
    EvidenceScoreBreakdown,
    calculate_evidence_score,
    calculate_scores,
    explain_score,
    get_rules,
    sufficiency_engine_enabled,
)
from app.sufficiency.rules import (
    DimensionResult,
    SufficiencyRules,
    _as_bool,
    _clamp,
    _controls,
    _frameworks,
    _is_nonempty,
    _parse_dt,
    required_metadata_for,
)

NOW = datetime(2026, 6, 14, 12, 0, 0, tzinfo=timezone.utc)


# --------------------------------------------------------------------------- #
# Fixtures / builders
# --------------------------------------------------------------------------- #

def make_evidence(**overrides):
    """A fully-populated, high-quality evidence record (repository + review shape)."""
    base = {
        "evidence_uid": "ev-001",
        "source_system": "gitea",
        "source_object_id": "repo/app#42",
        "object_type": "pull_request",
        "title": "PR #42: enforce code review",
        "content": "Pull request merged after 2 approvals.",
        "owner": "alice",
        "url": "https://gitea.local/app/pulls/42",
        "application": "Net Banking",
        "collected_timestamp": (NOW - timedelta(days=2)).isoformat(),
        "reviewed_at": (NOW - timedelta(days=1)).isoformat(),
        "valid_until": (NOW + timedelta(days=30)).isoformat(),
        "review_status": "Approved",
        "control_mapping": ["code-review", "change-management"],
        "framework_mapping": ["SOC2-CC8.1", "ISO27001-A.12", "PCI-DSS-6.5"],
        "lineage": [{"operation": "merge", "actor": "alice"}],
        "metadata": {"merged": True, "approvals": 2, "state": "closed"},
    }
    base.update(overrides)
    return base


@pytest.fixture
def rules():
    return SufficiencyRules()


# --------------------------------------------------------------------------- #
# 1. Helper functions (12)
# --------------------------------------------------------------------------- #

def test_clamp_low():
    assert _clamp(-5) == 0.0

def test_clamp_high():
    assert _clamp(150) == 100.0

def test_clamp_mid_rounds():
    assert _clamp(73.456) == 73.5

@pytest.mark.parametrize("val", ["x", [1], {"a": 1}, 5, True])
def test_is_nonempty_true(val):
    assert _is_nonempty(val) is True

@pytest.mark.parametrize("val", ["", "   ", None, [], {}, set(), False])
def test_is_nonempty_false(val):
    assert _is_nonempty(val) is False

@pytest.mark.parametrize("val", [True, 1, "yes", "true", "OK", "merged"])
def test_as_bool_true(val):
    assert _as_bool(val) is True

@pytest.mark.parametrize("val", [False, 0, "no", "false", ""])
def test_as_bool_false(val):
    assert _as_bool(val) is False

def test_parse_dt_iso_z():
    dt = _parse_dt("2026-06-14T12:00:00Z")
    assert dt == NOW

def test_parse_dt_naive_gets_utc():
    dt = _parse_dt("2026-06-14 12:00:00")
    assert dt.tzinfo is not None and dt == NOW

def test_parse_dt_date_only():
    dt = _parse_dt("2026-06-14")
    assert dt.year == 2026 and dt.month == 6 and dt.day == 14

def test_parse_dt_invalid_returns_none():
    assert _parse_dt("not-a-date") is None

def test_parse_dt_none_and_empty():
    assert _parse_dt(None) is None and _parse_dt("") is None

def test_parse_dt_datetime_passthrough():
    assert _parse_dt(NOW) == NOW


# --------------------------------------------------------------------------- #
# 2. control/framework extraction (10)
# --------------------------------------------------------------------------- #

def test_controls_from_control_mapping():
    assert _controls({"control_mapping": ["a", "b"]}) == ["a", "b"]

def test_controls_from_controls_alias():
    assert _controls({"controls": ["x"]}) == ["x"]

def test_controls_string():
    assert _controls({"control_mapping": "single"}) == ["single"]

def test_controls_empty_string():
    assert _controls({"control_mapping": "  "}) == []

def test_controls_none():
    assert _controls({}) == []

def test_controls_filters_empty():
    assert _controls({"control_mapping": ["a", "", None]}) == ["a"]

def test_frameworks_from_mapping():
    assert "SOC2-CC8" in _frameworks({"framework_mapping": ["SOC2-CC8"]})

def test_frameworks_refs_pairs():
    out = _frameworks({"framework_refs": [("SOC2", "CC8.1"), ("ISO27001", "A.12")]})
    assert "SOC2" in out and "ISO27001" in out

def test_frameworks_string():
    assert _frameworks({"frameworks": "PCI-DSS"}) == ["PCI-DSS"]

def test_frameworks_empty():
    assert _frameworks({}) == []


# --------------------------------------------------------------------------- #
# 3. Freshness scoring (18)
# --------------------------------------------------------------------------- #

def test_freshness_fresh(rules):
    ev = make_evidence(reviewed_at=(NOW - timedelta(days=1)).isoformat(),
                       valid_until=None, object_type="pull_request")
    r = rules.score_freshness(ev, now=NOW)
    assert r.detail["band"] == "fresh" and r.score == 100

def test_freshness_aging(rules):
    ev = make_evidence(reviewed_at=(NOW - timedelta(days=60)).isoformat(),
                       valid_until=None, object_type="pull_request")  # max 90, 60>=45
    r = rules.score_freshness(ev, now=NOW)
    assert r.detail["band"] == "aging" and r.score == 70

def test_freshness_stale(rules):
    ev = make_evidence(reviewed_at=(NOW - timedelta(days=200)).isoformat(),
                       valid_until=None, object_type="pull_request")
    r = rules.score_freshness(ev, now=NOW)
    assert r.detail["band"] == "stale" and r.score == 30

def test_freshness_expired_overrides(rules):
    ev = make_evidence(reviewed_at=(NOW - timedelta(days=1)).isoformat(),
                       valid_until=(NOW - timedelta(days=1)).isoformat())
    r = rules.score_freshness(ev, now=NOW)
    assert r.detail["band"] == "expired" and r.score == 0

def test_freshness_unknown_neutral(rules):
    ev = make_evidence(reviewed_at=None, collected_timestamp=None, valid_until=None)
    r = rules.score_freshness(ev, now=NOW)
    assert r.detail["band"] == "unknown" and r.score == 50

def test_freshness_uses_collected_when_no_review(rules):
    ev = make_evidence(reviewed_at=None, valid_until=None,
                       collected_timestamp=(NOW - timedelta(days=1)).isoformat(),
                       object_type="pull_request")
    r = rules.score_freshness(ev, now=NOW)
    assert r.detail["band"] == "fresh"

@pytest.mark.parametrize("otype,days,band", [
    ("test_result", 5, "fresh"),    # max 14 -> 5<7
    ("test_result", 10, "aging"),   # 10>=7
    ("test_result", 20, "stale"),   # 20>14
    ("quality_gate", 10, "fresh"),  # max 30 -> 10<15
    ("quality_gate", 20, "aging"),
    ("quality_gate", 40, "stale"),
    ("branch_protection", 50, "fresh"),   # max 180 -> 50<90
    ("repository", 100, "fresh"),         # max 365 -> 100<182.5
])
def test_freshness_per_type_windows(rules, otype, days, band):
    ev = make_evidence(object_type=otype, valid_until=None,
                       reviewed_at=(NOW - timedelta(days=days)).isoformat())
    assert rules.score_freshness(ev, now=NOW).detail["band"] == band

def test_freshness_default_window_unknown_type(rules):
    ev = make_evidence(object_type="exotic_type", valid_until=None,
                       reviewed_at=(NOW - timedelta(days=30)).isoformat())  # default 90 -> fresh
    assert rules.score_freshness(ev, now=NOW).detail["band"] == "fresh"

def test_freshness_band_helper_direct(rules):
    ev = make_evidence(valid_until=(NOW - timedelta(days=1)).isoformat())
    assert rules.freshness_band(ev, now=NOW) == "expired"

def test_freshness_future_reviewed_at_is_fresh(rules):
    ev = make_evidence(reviewed_at=(NOW + timedelta(days=5)).isoformat(), valid_until=None)
    assert rules.score_freshness(ev, now=NOW).detail["band"] == "fresh"


# --------------------------------------------------------------------------- #
# 4. Completeness scoring (16)
# --------------------------------------------------------------------------- #

def test_completeness_full(rules):
    r = rules.score_completeness(make_evidence())
    assert r.score == 100 and r.detail["missing"] == []

def test_completeness_missing_owner(rules):
    r = rules.score_completeness(make_evidence(owner=""))
    assert r.score < 100 and "field:owner" in r.detail["missing"]

def test_completeness_missing_url(rules):
    r = rules.score_completeness(make_evidence(url=""))
    assert "field:url" in r.detail["missing"]

def test_completeness_missing_title(rules):
    r = rules.score_completeness(make_evidence(title=""))
    assert "field:title" in r.detail["missing"]

def test_completeness_missing_content(rules):
    r = rules.score_completeness(make_evidence(content=""))
    assert "field:content" in r.detail["missing"]

def test_completeness_missing_control_mapping(rules):
    r = rules.score_completeness(make_evidence(control_mapping=[]))
    assert "control_mapping" in r.detail["missing"]

def test_completeness_pr_requires_merged_approvals(rules):
    r = rules.score_completeness(make_evidence(object_type="pull_request", metadata={}))
    assert "metadata:merged" in r.detail["missing"]
    assert "metadata:approvals" in r.detail["missing"]

def test_completeness_quality_gate_metadata(rules):
    ev = make_evidence(object_type="quality_gate",
                       metadata={"alert_status": "OK"})
    r = rules.score_completeness(ev)
    assert "metadata:alert_status" not in r.detail["missing"]

def test_completeness_quality_gate_missing_metadata(rules):
    ev = make_evidence(object_type="quality_gate", metadata={})
    r = rules.score_completeness(ev)
    assert "metadata:alert_status" in r.detail["missing"]

def test_completeness_test_result_metadata(rules):
    ev = make_evidence(object_type="test_result",
                       metadata={"passCount": 10, "failCount": 0})
    r = rules.score_completeness(ev)
    assert all(m not in r.detail["missing"] for m in ("metadata:passCount", "metadata:failCount"))

def test_completeness_branch_protection(rules):
    ev = make_evidence(object_type="branch_protection", metadata={"protected": True})
    assert "metadata:protected" not in rules.score_completeness(ev).detail["missing"]

def test_completeness_cloud_finding(rules):
    ev = make_evidence(object_type="cloud_finding",
                       metadata={"severity": "high", "status": "open"})
    r = rules.score_completeness(ev)
    assert "metadata:severity" not in r.detail["missing"]

def test_completeness_unknown_type_no_metadata_required(rules):
    ev = make_evidence(object_type="repository", metadata={})
    # repository has no required metadata -> only base + control checks
    assert rules.score_completeness(ev).score == 100

def test_completeness_score_monotonic(rules):
    full = rules.score_completeness(make_evidence()).score
    one_missing = rules.score_completeness(make_evidence(owner="")).score
    two_missing = rules.score_completeness(make_evidence(owner="", url="")).score
    assert full > one_missing > two_missing

def test_completeness_passed_total_counts(rules):
    r = rules.score_completeness(make_evidence())
    assert r.detail["passed"] == r.detail["total"]

def test_completeness_metadata_none(rules):
    ev = make_evidence(object_type="pull_request", metadata=None)
    r = rules.score_completeness(ev)
    assert "metadata:merged" in r.detail["missing"]


# --------------------------------------------------------------------------- #
# 5. Traceability scoring (14)
# --------------------------------------------------------------------------- #

def test_traceability_full(rules):
    assert rules.score_traceability(make_evidence()).score == 100

def test_traceability_no_owner(rules):
    r = rules.score_traceability(make_evidence(owner=""))
    assert r.score == 80 and "has_owner" in r.detail["signals"] and not r.detail["signals"]["has_owner"]

def test_traceability_no_url(rules):
    assert rules.score_traceability(make_evidence(url="")).score == 80

def test_traceability_no_control_mapping(rules):
    assert rules.score_traceability(make_evidence(control_mapping=[])).score == 70

def test_traceability_no_lineage(rules):
    assert rules.score_traceability(make_evidence(lineage=[])).score == 80

def test_traceability_no_source_ref(rules):
    assert rules.score_traceability(make_evidence(source_object_id="")).score == 90

def test_traceability_empty_evidence(rules):
    r = rules.score_traceability({"source_system": "", "source_object_id": ""})
    assert r.score == 0

def test_traceability_only_owner(rules):
    r = rules.score_traceability({"owner": "bob"})
    assert r.score == 20

def test_traceability_only_control(rules):
    r = rules.score_traceability({"control_mapping": ["c1"]})
    assert r.score == 30

def test_traceability_source_ref_needs_both(rules):
    r = rules.score_traceability({"source_system": "gitea", "source_object_id": ""})
    assert r.detail["signals"]["has_source_ref"] is False

def test_traceability_source_ref_present(rules):
    r = rules.score_traceability({"source_system": "gitea", "source_object_id": "x"})
    assert r.detail["signals"]["has_source_ref"] is True

def test_traceability_signals_dict_keys(rules):
    sig = rules.score_traceability(make_evidence()).detail["signals"]
    assert set(sig) == {"has_owner", "has_url", "has_control_mapping", "has_lineage", "has_source_ref"}

def test_traceability_reasons_present(rules):
    r = rules.score_traceability(make_evidence(owner="", url=""))
    assert any("missing signals" in x for x in r.reasons)

def test_traceability_lineage_truthy_dict(rules):
    r = rules.score_traceability(make_evidence(lineage=[{"op": "x"}]))
    assert r.detail["signals"]["has_lineage"] is True


# --------------------------------------------------------------------------- #
# 6. Review confidence scoring (12)
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("status,expected", [
    ("Approved", 100), ("UnderReview", 50), ("Collected", 40),
    ("Rejected", 0), ("Expired", 0),
])
def test_review_known_statuses(rules, status, expected):
    assert rules.score_review(make_evidence(review_status=status)).score == expected

def test_review_unknown_status(rules):
    assert rules.score_review(make_evidence(review_status="Weird")).score == 30

def test_review_no_status(rules):
    ev = make_evidence()
    ev.pop("review_status")
    assert rules.score_review(ev).score == 30

def test_review_status_alias(rules):
    ev = make_evidence()
    ev.pop("review_status")
    ev["status"] = "Approved"
    assert rules.score_review(ev).score == 100

def test_review_empty_string_status(rules):
    assert rules.score_review(make_evidence(review_status="")).score == 30

def test_review_detail_status(rules):
    assert rules.score_review(make_evidence(review_status="Approved")).detail["status"] == "Approved"

def test_review_reasons(rules):
    assert rules.score_review(make_evidence(review_status="Approved")).reasons


# --------------------------------------------------------------------------- #
# 7. Coverage scoring (12)
# --------------------------------------------------------------------------- #

def test_coverage_three_frameworks_full(rules):
    assert rules.score_coverage(make_evidence()).score == 100

def test_coverage_one_framework(rules):
    ev = make_evidence(framework_mapping=["SOC2-CC8"])
    assert rules.score_coverage(ev).score == pytest.approx(33.3, abs=0.1)

def test_coverage_two_frameworks(rules):
    ev = make_evidence(framework_mapping=["SOC2-CC8", "ISO27001-A.12"])
    assert rules.score_coverage(ev).score == pytest.approx(66.7, abs=0.1)

def test_coverage_no_frameworks(rules):
    ev = make_evidence(framework_mapping=[], framework_refs=[], frameworks=[])
    assert rules.score_coverage(ev).score == 0

def test_coverage_dedup_same_base(rules):
    ev = make_evidence(framework_mapping=["SOC2-CC8.1", "SOC2-CC7.1"])
    # both normalize to SOC2 -> 1 distinct
    assert rules.score_coverage(ev).detail["frameworks"] == ["SOC2"]

def test_coverage_caps_at_target(rules):
    ev = make_evidence(framework_mapping=["A-1", "B-1", "C-1", "D-1", "E-1"])
    assert rules.score_coverage(ev).score == 100

def test_coverage_refs_pairs(rules):
    ev = make_evidence(framework_mapping=[], frameworks=[],
                       framework_refs=[("SOC2", "CC8"), ("PCI-DSS", "6.5")])
    assert rules.score_coverage(ev).score == pytest.approx(66.7, abs=0.1)

def test_coverage_normalizes_case(rules):
    ev = make_evidence(framework_mapping=["soc2-cc8"])
    assert "SOC2" in rules.score_coverage(ev).detail["frameworks"]

def test_coverage_colon_separator(rules):
    ev = make_evidence(framework_mapping=["ISO27001:A.12"])
    assert rules.score_coverage(ev).detail["frameworks"] == ["ISO27001"]

def test_coverage_distinct_helper(rules):
    fws = rules._distinct_frameworks(make_evidence())
    assert fws == {"SOC2", "ISO27001", "PCI"}

def test_coverage_reasons(rules):
    assert rules.score_coverage(make_evidence()).reasons


# --------------------------------------------------------------------------- #
# 8. Policy / weights / bands / config merge (14)
# --------------------------------------------------------------------------- #

def test_default_weights_sum_to_one(rules):
    assert abs(sum(rules.normalized_weights().values()) - 1.0) < 1e-9

def test_weights_renormalized():
    r = SufficiencyRules({"weights": {"completeness": 2, "freshness": 2,
                                      "traceability": 2, "coverage": 2, "review": 2}})
    w = r.normalized_weights()
    assert all(abs(v - 0.2) < 1e-9 for v in w.values())

def test_weights_zero_total_fallback_equal():
    r = SufficiencyRules({"weights": {"completeness": 0, "freshness": 0,
                                      "traceability": 0, "coverage": 0, "review": 0}})
    w = r.normalized_weights()
    assert abs(sum(w.values()) - 1.0) < 1e-9

def test_band_ready(rules):
    assert rules.band(85) == "Ready"

def test_band_at_risk(rules):
    assert rules.band(60) == "At Risk"

def test_band_not_ready(rules):
    assert rules.band(20) == "Not Ready"

def test_band_boundaries(rules):
    assert rules.band(80) == "Ready"
    assert rules.band(79.9) == "At Risk"
    assert rules.band(55) == "At Risk"
    assert rules.band(54.9) == "Not Ready"

def test_custom_bands():
    r = SufficiencyRules({"bands": {"ready_min": 90, "at_risk_min": 70}})
    assert r.band(85) == "At Risk" and r.band(95) == "Ready"

def test_merge_defaults_partial_freshness():
    r = SufficiencyRules({"freshness": {"default_max_age_days": 10}})
    assert r._max_age_days("unknown") == 10
    # nested defaults preserved
    assert r._max_age_days("test_result") == 14

def test_merge_defaults_partial_completeness():
    r = SufficiencyRules({"completeness": {"require_control_mapping": False}})
    ev = make_evidence(control_mapping=[])
    assert "control_mapping" not in r.score_completeness(ev).detail["missing"]

def test_merge_review_status_scores():
    r = SufficiencyRules({"review": {"status_scores": {"Approved": 90}}})
    assert r.score_review(make_evidence(review_status="Approved")).score == 90

def test_required_metadata_for_helper():
    assert "merged" in required_metadata_for("pull_request")

def test_required_metadata_for_unknown():
    assert list(required_metadata_for("repository")) == []

def test_policy_none_uses_defaults():
    r = SufficiencyRules(None)
    assert r.policy["weights"]["completeness"] == 0.30


# --------------------------------------------------------------------------- #
# 9. Composite engine: calculate_evidence_score (18)
# --------------------------------------------------------------------------- #

def test_engine_disabled_by_default():
    # No env var, config default false -> disabled result
    res = calculate_evidence_score(make_evidence())
    assert isinstance(res, EvidenceScore)
    assert res.enabled is False and res.score == 0.0
    assert "disabled" in res.note

def test_engine_force_computes():
    res = calculate_evidence_score(make_evidence(), force=True)
    assert res.enabled is True and res.score > 0

def test_engine_perfect_evidence_high_score():
    res = calculate_evidence_score(make_evidence(), force=True)
    assert res.score >= 95 and res.band == "Ready"

def test_engine_empty_evidence_low_score():
    res = calculate_evidence_score({"evidence_uid": "x"}, force=True)
    assert res.enabled is True and res.score < 55 and res.band == "Not Ready"

def test_engine_breakdown_shape():
    res = calculate_evidence_score(make_evidence(), force=True)
    bd = res.breakdown
    assert isinstance(bd, EvidenceScoreBreakdown)
    for dim in ("completeness", "freshness", "traceability", "coverage", "review"):
        assert 0 <= getattr(bd, dim) <= 100

def test_engine_contributions_sum_to_score():
    res = calculate_evidence_score(make_evidence(), force=True)
    total = sum(res.breakdown.contributions.values())
    assert abs(total - res.score) <= 0.5

def test_engine_weights_in_breakdown():
    res = calculate_evidence_score(make_evidence(), force=True)
    assert abs(sum(res.breakdown.weights.values()) - 1.0) < 1e-6

def test_engine_uid_propagated():
    res = calculate_evidence_score(make_evidence(evidence_uid="ev-XYZ"), force=True)
    assert res.evidence_uid == "ev-XYZ"

def test_engine_uid_alias():
    res = calculate_evidence_score({"uid": "alias-1", "title": "t", "content": "c"}, force=True)
    assert res.evidence_uid == "alias-1"

def test_engine_now_injection_freshness():
    old = make_evidence(reviewed_at="2020-01-01T00:00:00Z", valid_until=None)
    res = calculate_evidence_score(old, force=True, now=NOW)
    assert res.breakdown.freshness == 30  # stale

def test_engine_expired_lowers_score():
    fresh = calculate_evidence_score(make_evidence(), force=True, now=NOW).score
    expired = calculate_evidence_score(
        make_evidence(valid_until=(NOW - timedelta(days=1)).isoformat()),
        force=True, now=NOW).score
    assert expired < fresh

def test_engine_to_dict_roundtrip():
    res = calculate_evidence_score(make_evidence(), force=True)
    d = res.to_dict()
    assert d["enabled"] is True and "breakdown" in d and "weights" in d["breakdown"]

def test_engine_fail_safe_non_mapping():
    res = calculate_evidence_score("not-a-dict", force=True)  # type: ignore[arg-type]
    assert res.enabled is False and "error" in res.note.lower()

def test_engine_reasons_present_per_dim():
    res = calculate_evidence_score(make_evidence(owner=""), force=True)
    assert res.breakdown.reasons["completeness"]

def test_engine_score_deterministic():
    a = calculate_evidence_score(make_evidence(), force=True, now=NOW).score
    b = calculate_evidence_score(make_evidence(), force=True, now=NOW).score
    assert a == b

def test_engine_custom_rules_passthrough():
    custom = SufficiencyRules({"weights": {"completeness": 1, "freshness": 0,
                                           "traceability": 0, "coverage": 0, "review": 0}})
    res = calculate_evidence_score(make_evidence(), force=True, rules=custom)
    assert res.score == res.breakdown.completeness

def test_engine_band_assignment():
    res = calculate_evidence_score(make_evidence(), force=True)
    assert res.band in {"Ready", "At Risk", "Not Ready"}

def test_engine_partial_evidence_midrange():
    ev = {"evidence_uid": "p", "title": "t", "content": "c", "owner": "o", "url": "u",
          "control_mapping": ["c1"], "source_system": "s", "source_object_id": "x",
          "review_status": "UnderReview", "framework_mapping": ["SOC2-CC8"],
          "reviewed_at": (NOW - timedelta(days=1)).isoformat(), "valid_until": None,
          "object_type": "repository"}
    res = calculate_evidence_score(ev, force=True, now=NOW)
    assert 40 <= res.score <= 95


# --------------------------------------------------------------------------- #
# 10. explain_score (10)
# --------------------------------------------------------------------------- #

def test_explain_returns_summary():
    out = explain_score(make_evidence())
    assert "summary" in out and isinstance(out["summary"], str)

def test_explain_forced_by_default():
    out = explain_score(make_evidence())
    assert out["enabled"] is True

def test_explain_contains_score_line():
    out = explain_score(make_evidence())
    assert "Composite sufficiency score" in out["summary"]

def test_explain_lists_all_dimensions():
    out = explain_score(make_evidence())
    for dim in ("completeness", "freshness", "traceability", "coverage", "review"):
        assert dim in out["summary"]

def test_explain_includes_reasons():
    out = explain_score(make_evidence(owner=""))
    assert "missing" in out["summary"]

def test_explain_breakdown_dict():
    out = explain_score(make_evidence())
    assert isinstance(out["breakdown"], dict) and "weights" in out["breakdown"]

def test_explain_uid():
    out = explain_score(make_evidence(evidence_uid="ex-1"))
    assert out["evidence_uid"] == "ex-1"

def test_explain_disabled_when_not_forced(monkeypatch):
    monkeypatch.delenv("SUFFICIENCY_ENGINE_ENABLED", raising=False)
    out = explain_score(make_evidence(), force=False)
    assert out["enabled"] is False and "disabled" in out["summary"]

def test_explain_band_field():
    out = explain_score(make_evidence())
    assert out["band"] in {"Ready", "At Risk", "Not Ready"}

def test_explain_score_field_numeric():
    out = explain_score(make_evidence())
    assert isinstance(out["score"], (int, float))


# --------------------------------------------------------------------------- #
# 11. Feature flag gate (10)
# --------------------------------------------------------------------------- #

def test_flag_env_true(monkeypatch):
    monkeypatch.setenv("SUFFICIENCY_ENGINE_ENABLED", "true")
    assert sufficiency_engine_enabled() is True

def test_flag_env_false(monkeypatch):
    monkeypatch.setenv("SUFFICIENCY_ENGINE_ENABLED", "false")
    assert sufficiency_engine_enabled() is False

@pytest.mark.parametrize("val", ["1", "yes", "on", "TRUE", "On"])
def test_flag_env_truthy_variants(monkeypatch, val):
    monkeypatch.setenv("SUFFICIENCY_ENGINE_ENABLED", val)
    assert sufficiency_engine_enabled() is True

@pytest.mark.parametrize("val", ["0", "no", "off", "garbage", ""])
def test_flag_env_falsy_variants(monkeypatch, val):
    monkeypatch.setenv("SUFFICIENCY_ENGINE_ENABLED", val)
    # empty string -> treated as unset -> config default false
    assert sufficiency_engine_enabled() is False

def test_flag_default_off(monkeypatch):
    monkeypatch.delenv("SUFFICIENCY_ENGINE_ENABLED", raising=False)
    assert sufficiency_engine_enabled() is False

def test_flag_on_makes_calculate_compute(monkeypatch):
    monkeypatch.setenv("SUFFICIENCY_ENGINE_ENABLED", "true")
    res = calculate_evidence_score(make_evidence())  # no force needed
    assert res.enabled is True and res.score > 0

def test_flag_off_makes_calculate_noop(monkeypatch):
    monkeypatch.setenv("SUFFICIENCY_ENGINE_ENABLED", "false")
    res = calculate_evidence_score(make_evidence())
    assert res.enabled is False


# --------------------------------------------------------------------------- #
# 12. Batch scoring (5)
# --------------------------------------------------------------------------- #

def test_batch_scores_length():
    items = [make_evidence(evidence_uid=f"e{i}") for i in range(5)]
    out = calculate_scores(items, force=True)
    assert len(out) == 5 and all(isinstance(x, EvidenceScore) for x in out)

def test_batch_uids_preserved():
    items = [make_evidence(evidence_uid=f"e{i}") for i in range(3)]
    out = calculate_scores(items, force=True)
    assert [x.evidence_uid for x in out] == ["e0", "e1", "e2"]

def test_batch_disabled_default():
    out = calculate_scores([make_evidence()])
    assert out[0].enabled is False

def test_batch_empty_list():
    assert calculate_scores([], force=True) == []

def test_batch_mixed_quality():
    items = [make_evidence(), {"evidence_uid": "bad"}]
    out = calculate_scores(items, force=True)
    assert out[0].score > out[1].score


# --------------------------------------------------------------------------- #
# 13. Real ECS evidence-shape validation (12)
# --------------------------------------------------------------------------- #

def test_real_shape_gitea_pr():
    ev = {
        "evidence_uid": "uid-1", "source_system": "gitea",
        "source_object_id": "myrepo#7", "object_type": "pull_request",
        "title": "PR #7", "content": "merged PR", "owner": "dev",
        "url": "http://x", "application": "App", "content_hash": "abc",
        "collected_timestamp": (NOW - timedelta(days=1)).isoformat(),
        "metadata": {"state": "closed", "merged": True, "approvals": 1,
                     "reviewers": ["a"]},
        "control_mapping": ["code-review"], "framework_mapping": ["SOC2-CC8"],
    }
    res = calculate_evidence_score(ev, force=True, now=NOW)
    assert res.enabled and 0 < res.score <= 100

def test_real_shape_sonar_quality_gate():
    ev = {
        "evidence_uid": "uid-2", "source_system": "sonarqube",
        "source_object_id": "proj-x", "object_type": "quality_gate",
        "title": "Quality Gate", "content": "passed", "owner": "ci",
        "url": "http://sonar", "application": "App",
        "collected_timestamp": (NOW - timedelta(days=3)).isoformat(),
        "metadata": {"bugs": 0, "vulnerabilities": 0, "coverage": 85.0,
                     "alert_status": "OK"},
        "control_mapping": ["code-quality"], "framework_mapping": ["ISO27001-A.14"],
    }
    res = calculate_evidence_score(ev, force=True, now=NOW)
    assert res.breakdown.freshness in (100, 70)  # 3d within 30d window

def test_real_shape_jenkins_test_result():
    ev = {
        "evidence_uid": "uid-3", "source_system": "jenkins",
        "source_object_id": "build#10", "object_type": "test_result",
        "title": "Tests", "content": "all pass", "owner": "ci",
        "url": "http://jenkins", "application": "App",
        "collected_timestamp": (NOW - timedelta(days=1)).isoformat(),
        "metadata": {"passCount": 100, "failCount": 0, "skipCount": 2},
        "control_mapping": ["secure-sdlc"],
    }
    res = calculate_evidence_score(ev, force=True, now=NOW)
    assert "metadata:passCount" not in res.breakdown.detail["completeness"]["missing"]

def test_real_shape_evidenceitem_to_dict():
    # Mirrors EvidenceItem.to_dict() exactly (no review fields).
    ev = {
        "source_system": "github", "source_object_id": "r#1",
        "object_type": "branch_protection", "title": "BP", "content": "protected",
        "collected_timestamp": (NOW - timedelta(days=5)).isoformat(),
        "owner": "o", "url": "http://gh", "application": "A",
        "control_mapping": ["change-management"],
        "framework_mapping": ["SOC2-CC8"], "metadata": {"protected": True},
    }
    res = calculate_evidence_score(ev, force=True, now=NOW)
    assert res.enabled is True

def test_real_shape_missing_review_defaults():
    ev = make_evidence()
    ev.pop("review_status")
    ev.pop("reviewed_at")
    res = calculate_evidence_score(ev, force=True, now=NOW)
    assert res.breakdown.review == 30

def test_real_shape_prisma_cloud_finding():
    ev = {
        "evidence_uid": "uid-4", "source_system": "prisma",
        "source_object_id": "f-1", "object_type": "cloud_finding",
        "title": "Finding", "content": "open finding", "owner": "sec",
        "url": "http://prisma", "application": "A",
        "collected_timestamp": (NOW - timedelta(days=2)).isoformat(),
        "metadata": {"severity": "high", "status": "open"},
        "control_mapping": ["vulnerability-management"],
    }
    res = calculate_evidence_score(ev, force=True, now=NOW)
    assert res.enabled is True

def test_real_shape_with_review_columns():
    ev = make_evidence(review_status="Approved",
                       valid_until=(NOW + timedelta(days=10)).isoformat(),
                       reviewed_at=(NOW - timedelta(days=2)).isoformat())
    res = calculate_evidence_score(ev, force=True, now=NOW)
    assert res.breakdown.review == 100

def test_real_shape_lineage_list():
    ev = make_evidence(lineage=[{"operation": "derive", "parent_uid": "p"}])
    res = calculate_evidence_score(ev, force=True, now=NOW)
    assert res.breakdown.detail["traceability"]["signals"]["has_lineage"] is True

def test_real_shape_no_lineage_key():
    ev = make_evidence()
    ev.pop("lineage")
    res = calculate_evidence_score(ev, force=True, now=NOW)
    assert res.breakdown.detail["traceability"]["signals"]["has_lineage"] is False

def test_real_shape_framework_refs_canonical():
    ev = make_evidence(framework_mapping=[], frameworks=[],
                       framework_refs=[("SOC2", "CC8.1"), ("PCI-DSS", "6.5"),
                                       ("ISO27001", "A.12")])
    res = calculate_evidence_score(ev, force=True, now=NOW)
    assert res.breakdown.coverage == 100

def test_real_shape_minimal_only_uid():
    res = calculate_evidence_score({"evidence_uid": "min"}, force=True, now=NOW)
    assert res.enabled is True and res.score >= 0

def test_real_shape_score_jsonable():
    import json
    res = calculate_evidence_score(make_evidence(), force=True)
    json.dumps(res.to_dict())  # must not raise


# --------------------------------------------------------------------------- #
# 14. DimensionResult dataclass (3)
# --------------------------------------------------------------------------- #

def test_dimension_result_to_dict():
    d = DimensionResult("x", 50.0, ["r"], {"k": 1}).to_dict()
    assert d == {"dimension": "x", "score": 50.0, "reasons": ["r"], "detail": {"k": 1}}

def test_dimension_result_defaults():
    d = DimensionResult("y", 10.0)
    assert d.reasons == [] and d.detail == {}

def test_score_all_returns_five_dims(rules):
    out = rules.score_all(make_evidence(), now=NOW)
    assert set(out) == {"completeness", "freshness", "traceability", "coverage", "review"}
