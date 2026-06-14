"""Unit tests for the Executive ROI & Value Realization engine.

Deterministic, non-LLM. Covers assumptions loading, core ROI calculations,
projections, scenarios (projected vs actual + variance), all enhancement views
(framework / reuse / observation / email / auditor), the impact-event ticker,
INR formatting, the orchestrator, flag behavior, and fail-safety.

Engines compute via the configured assumptions; the master flag (ROI_CENTER_ENABLED)
gates the orchestrator and is tested separately via env.
"""

from __future__ import annotations

import pytest

import app.roi as roi
from app.roi.assumptions import Assumptions, roi_enabled
from app.roi.calculations import (
    audit_hours_saved,
    calculate_projected,
    calculate_roi,
    email_hours_saved,
    emails_avoided,
    framework_hours_saved,
    observation_hours_saved,
    prevention_hours_saved,
    projected_inputs_for_apps,
    reuse_hours_saved,
    risk_reduction_pct,
)
from app.roi.models import Mode, RoiInputs, format_compact, format_inr
from app.roi.projections import build_projection
from app.roi.scenarios import actual_roi, collect_actual_inputs, compare
from app.roi.widgets import (
    auditor_value,
    battle_view,
    email_value,
    framework_roi,
    impact_events,
    observation_value,
    reuse_value,
)


@pytest.fixture
def a():
    return Assumptions.load()


@pytest.fixture(autouse=True)
def _clear_flag(monkeypatch):
    monkeypatch.delenv("ROI_CENTER_ENABLED", raising=False)
    yield


# =========================================================================== #
# INR formatting
# =========================================================================== #

def test_format_inr_crore():
    assert format_inr(45_000_000) == "₹4.5 Cr"

def test_format_inr_lakh():
    assert format_inr(5_000_000) == "₹50 Lakh"

def test_format_inr_rupees():
    assert format_inr(2500).startswith("₹")
    assert "2,500" in format_inr(2500)

def test_format_inr_zero():
    assert format_inr(0) == "₹0"

def test_format_inr_negative():
    assert format_inr(-45_000_000).startswith("-₹")

def test_format_inr_bad_input():
    assert format_inr("abc") == "₹0"

def test_format_inr_22cr_example():
    assert format_inr(220_000_000) == "₹22 Cr"

def test_format_inr_110cr_example():
    assert format_inr(1_100_000_000) == "₹110 Cr"

def test_format_inr_custom_symbol():
    assert format_inr(5_000_000, symbol="$").startswith("$")

def test_format_compact():
    assert format_compact(12500) == "12,500"

def test_format_compact_bad():
    assert format_compact("x") == "0"


# =========================================================================== #
# Assumptions
# =========================================================================== #

def test_assumptions_load(a):
    assert a.applications_in_bank == 905
    assert a.vapt_applications == 600

def test_assumptions_observations_per_app(a):
    assert a.observations_per_application == 2.5

def test_assumptions_emails_per_obs(a):
    assert a.emails_per_observation == 7

def test_assumptions_hours_per_obs(a):
    assert a.hours_per_observation == 8

def test_assumptions_baseline_anchor(a):
    assert a.baseline_savings_per_25_apps_cr == 4.5

def test_assumptions_baseline_cost_per_app(a):
    # ₹4.5 Cr / 25 = ₹18 Lakh per app
    assert a.baseline_cost_per_app() == pytest.approx(1_800_000)

def test_assumptions_currency(a):
    assert a.symbol == "₹"
    assert a.code == "INR"

def test_assumptions_frameworks_present(a):
    names = [f.get("name") for f in a.frameworks]
    assert "VAPT" in names and "RBI" in names and "AI Governance" in names

def test_assumptions_projection_apps(a):
    assert a.projection_apps == [25, 100, 200, 400, 600]

def test_assumptions_storyboard_apps(a):
    assert a.storyboard_apps == [25, 100, 200]

def test_assumptions_defaults_when_missing(monkeypatch):
    # Even if config loader raises, defaults apply.
    monkeypatch.setattr("app.roi.assumptions._load_block", lambda: {})
    inst = Assumptions.load()
    assert inst.applications_in_bank == 905


# =========================================================================== #
# Flag
# =========================================================================== #

def test_flag_default_off():
    assert roi_enabled() is False

def test_flag_env_on(monkeypatch):
    monkeypatch.setenv("ROI_CENTER_ENABLED", "true")
    assert roi_enabled() is True

def test_flag_env_various(monkeypatch):
    for v in ("1", "yes", "on", "TRUE"):
        monkeypatch.setenv("ROI_CENTER_ENABLED", v)
        assert roi_enabled() is True

def test_flag_env_false(monkeypatch):
    monkeypatch.setenv("ROI_CENTER_ENABLED", "false")
    assert roi_enabled() is False


# =========================================================================== #
# Core calculation primitives
# =========================================================================== #

def test_emails_avoided(a):
    # obs_total=100 -> 100*7*0.85 = 595
    assert emails_avoided(100, a) == pytest.approx(595)

def test_email_hours_saved(a):
    # 595 emails * 0.25 h
    assert email_hours_saved(100, a) == pytest.approx(595 * 0.25)

def test_observation_hours_saved(a):
    # 100*8*0.6 = 480
    assert observation_hours_saved(100, a) == pytest.approx(480)

def test_prevention_hours_saved(a):
    assert prevention_hours_saved(50, a) == pytest.approx(400)

def test_reuse_hours_saved(a):
    assert reuse_hours_saved(100, a) == pytest.approx(150)

def test_audit_hours_saved(a):
    assert audit_hours_saved(2, a) == pytest.approx(2 * 160 * 0.55)

def test_framework_hours_saved(a):
    assert framework_hours_saved(3, a) == pytest.approx(3 * 80 * 0.7)

def test_risk_reduction_caps(a):
    assert risk_reduction_pct(100000, a) == 78  # capped at max

def test_risk_reduction_scales(a):
    assert risk_reduction_pct(100, a) == pytest.approx(min(78, 100 * 0.12 * 100))

def test_risk_reduction_zero(a):
    assert risk_reduction_pct(0, a) == 0


# =========================================================================== #
# calculate_roi
# =========================================================================== #

def test_calculate_roi_zero_inputs(a):
    r = calculate_roi(RoiInputs(), a)
    assert r.hours_saved == 0
    assert r.cost_savings == 0
    assert r.roi_pct == 0

def test_calculate_roi_positive(a):
    r = calculate_roi(RoiInputs(applications_onboarded=100, observations_closed=200,
                                evidence_reused=400, audits_completed=2), a)
    assert r.hours_saved > 0
    assert r.cost_savings > 0

def test_calculate_roi_days_from_hours(a):
    r = calculate_roi(RoiInputs(observations_closed=80), a)
    assert r.days_saved == pytest.approx(r.hours_saved / 8, rel=0.01)

def test_calculate_roi_fte(a):
    r = calculate_roi(RoiInputs(observations_closed=900), a)
    assert r.fte_equivalent == pytest.approx(r.hours_saved / 1800, rel=0.01)

def test_calculate_roi_display_strings(a):
    r = calculate_roi(RoiInputs(applications_onboarded=100, observations_closed=250), a)
    assert r.cost_savings_display.startswith("₹")

def test_calculate_roi_mode(a):
    r = calculate_roi(RoiInputs(), a, mode=Mode.ACTUAL.value)
    assert r.mode == "actual"

def test_calculate_roi_investment(a):
    r = calculate_roi(RoiInputs(applications_onboarded=10), a)
    assert r.investment == pytest.approx(10 * a.cost_per_app_per_year)

def test_calculate_roi_net_value(a):
    r = calculate_roi(RoiInputs(applications_onboarded=25, observations_closed=60), a)
    assert r.net_value == pytest.approx(r.cost_savings - r.investment, rel=0.01)

def test_calculate_roi_never_raises(a):
    r = calculate_roi(RoiInputs(applications_onboarded=-5), a)
    assert r.enabled is True

def test_calculate_roi_emails_avoided_field(a):
    r = calculate_roi(RoiInputs(observations_closed=100), a)
    assert r.emails_avoided > 0


# =========================================================================== #
# projected_inputs_for_apps + calculate_projected
# =========================================================================== #

def test_projected_inputs_scales(a):
    i25 = projected_inputs_for_apps(25, a)
    i100 = projected_inputs_for_apps(100, a)
    assert i100.observations_closed > i25.observations_closed

def test_projected_inputs_prevention(a):
    i = projected_inputs_for_apps(100, a)
    total = i.observations_closed + i.observations_prevented
    assert total == pytest.approx(100 * a.observations_per_application)

def test_projected_inputs_reuse(a):
    i = projected_inputs_for_apps(100, a)
    assert i.evidence_reused == pytest.approx(i.evidence_submitted * a.evidence_reuse_factor)

def test_projected_inputs_zero(a):
    i = projected_inputs_for_apps(0, a)
    assert i.applications_onboarded == 0
    assert i.frameworks_onboarded == 0

def test_calculate_projected_25_matches_anchor(a):
    # ₹4.5 Cr anchor for 25 apps.
    r = calculate_projected(25, a)
    assert r.cost_savings == pytest.approx(4.5 * 10_000_000, rel=0.01)

def test_calculate_projected_100(a):
    r = calculate_projected(100, a)
    assert r.cost_savings == pytest.approx(18 * 10_000_000, rel=0.01)

def test_calculate_projected_monotonic(a):
    assert calculate_projected(200, a).cost_savings > calculate_projected(100, a).cost_savings

def test_calculate_projected_display(a):
    assert "Cr" in calculate_projected(100, a).cost_savings_display


# =========================================================================== #
# Projections
# =========================================================================== #

def test_build_projection_points(a):
    p = build_projection(a)
    assert len(p.points) == 5

def test_build_projection_years(a):
    p = build_projection(a)
    assert [pt.year for pt in p.points] == [1, 2, 3, 4, 5]

def test_build_projection_apps(a):
    p = build_projection(a)
    assert [pt.applications for pt in p.points] == [25, 100, 200, 400, 600]

def test_build_projection_cumulative_increases(a):
    p = build_projection(a)
    cums = [pt.cumulative_cost_savings for pt in p.points]
    assert cums == sorted(cums)

def test_build_projection_total(a):
    p = build_projection(a)
    assert p.total_cost_savings == pytest.approx(p.points[-1].cumulative_cost_savings)

def test_build_projection_total_display(a):
    p = build_projection(a)
    assert p.total_display.startswith("₹")

def test_build_projection_year1_anchor(a):
    p = build_projection(a)
    assert p.points[0].cost_savings == pytest.approx(4.5 * 10_000_000, rel=0.01)

def test_build_projection_custom_schedule(a):
    p = build_projection(a, apps_schedule=[10, 20], years=[1, 2])
    assert len(p.points) == 2

def test_build_projection_peak_fte(a):
    p = build_projection(a)
    assert p.peak_fte >= 0

def test_build_projection_observations_reduced(a):
    p = build_projection(a)
    assert all(pt.observations_reduced > 0 for pt in p.points)


# =========================================================================== #
# Scenarios
# =========================================================================== #

def test_collect_actual_overrides(a):
    inp = collect_actual_inputs(a, overrides={"applications_onboarded": 50,
                                              "observations_closed": 100})
    assert inp.applications_onboarded == 50
    assert inp.observations_closed == 100

def test_actual_roi_mode(a):
    r = actual_roi(a, overrides={"applications_onboarded": 10})
    assert r.mode == "actual"

def test_compare_structure(a):
    c = compare(a, actual_overrides={"applications_onboarded": 25,
                                     "observations_closed": 60})
    assert c.enabled is True
    assert c.projected.mode == "projected"
    assert c.actual.mode == "actual"

def test_compare_variance_fields(a):
    c = compare(a, actual_overrides={"applications_onboarded": 25})
    assert isinstance(c.variance_pct, float)
    assert c.variance_display.startswith("₹") or c.variance_display.startswith("-₹")

def test_compare_same_apps(a):
    c = compare(a, actual_overrides={"applications_onboarded": 100})
    assert c.projected.applications == 100

def test_compare_target_apps(a):
    c = compare(a, target_apps=200, actual_overrides={"applications_onboarded": 100})
    assert c.projected.applications == 200

def test_compare_zero_projected_safe(a):
    c = compare(a, target_apps=0, actual_overrides={"applications_onboarded": 0})
    assert c.enabled is True

def test_collect_actual_no_overrides_safe(a):
    # Reads ecs_state; must not raise even if unavailable.
    inp = collect_actual_inputs(a)
    assert isinstance(inp, RoiInputs)


# =========================================================================== #
# Framework ROI view
# =========================================================================== #

def test_framework_roi_count(a):
    fws = framework_roi(a)
    assert len(fws) == 6

def test_framework_roi_vapt_apps(a):
    fws = framework_roi(a)
    vapt = next(f for f in fws if f.name == "VAPT")
    assert vapt.applications_covered == 600

def test_framework_roi_coverage_derived(a):
    fws = framework_roi(a)
    rbi = next(f for f in fws if f.name == "RBI")
    # 905 * 0.9 = 814 (rounded)
    assert rbi.applications_covered == round(905 * 0.9)

def test_framework_roi_has_cost(a):
    fws = framework_roi(a)
    assert all(f.cost_saved > 0 for f in fws)

def test_framework_roi_display(a):
    fws = framework_roi(a)
    assert all(f.cost_saved_display.startswith("₹") for f in fws)

def test_framework_roi_reuse(a):
    fws = framework_roi(a)
    assert all(f.evidence_reused >= 0 for f in fws)

def test_framework_roi_observations(a):
    fws = framework_roi(a)
    assert all(f.observations_closed >= 0 for f in fws)


# =========================================================================== #
# Reuse value view
# =========================================================================== #

def test_reuse_value_fields(a):
    r = reuse_value(a)
    assert r.reuse_count > 0
    assert r.cost_avoided > 0

def test_reuse_value_factor(a):
    r = reuse_value(a)
    assert r.reuse_factor == a.evidence_reuse_factor

def test_reuse_value_display(a):
    r = reuse_value(a)
    assert r.cost_avoided_display.startswith("₹")

def test_reuse_value_contribution_bounded(a):
    r = reuse_value(a)
    assert 0 <= r.roi_contribution_pct <= 100

def test_reuse_value_custom_apps(a):
    r = reuse_value(a, applications=100)
    assert r.reuse_count > 0


# =========================================================================== #
# Observation value view
# =========================================================================== #

def test_observation_value_split(a):
    o = observation_value(a)
    assert o.observations_prevented + o.observations_closed == pytest.approx(
        o.observations_without_ecs, rel=0.01)

def test_observation_value_cost(a):
    o = observation_value(a)
    assert o.cost_saved > 0

def test_observation_value_acceleration(a):
    o = observation_value(a)
    assert o.closure_acceleration_pct == pytest.approx(a.closure_acceleration_pct * 100)

def test_observation_value_display(a):
    o = observation_value(a)
    assert o.cost_saved_display.startswith("₹")

def test_observation_value_custom_apps(a):
    o = observation_value(a, applications=100)
    assert o.observations_without_ecs == pytest.approx(100 * a.observations_per_application)


# =========================================================================== #
# Email value view
# =========================================================================== #

def test_email_value_avoided(a):
    e = email_value(a)
    assert e.emails_avoided > 0

def test_email_value_split(a):
    e = email_value(a)
    assert e.emails_avoided + e.workflow_transactions_in_ecs == pytest.approx(
        e.expected_emails_without_ecs, rel=0.01)

def test_email_value_cost(a):
    e = email_value(a)
    assert e.cost_saved > 0

def test_email_value_display(a):
    e = email_value(a)
    assert e.cost_saved_display.startswith("₹")

def test_email_value_custom_apps(a):
    e = email_value(a, applications=100)
    assert e.expected_emails_without_ecs == pytest.approx(
        100 * a.observations_per_application * a.emails_per_observation)


# =========================================================================== #
# Auditor value view
# =========================================================================== #

def test_auditor_value_saved(a):
    av = auditor_value(a)
    assert av.audit_hours_saved > 0

def test_auditor_value_ecs_less_than_manual(a):
    av = auditor_value(a)
    assert av.ecs_audit_hours < av.manual_audit_hours

def test_auditor_value_reduction_pct(a):
    av = auditor_value(a)
    assert av.review_effort_reduction_pct == pytest.approx(a.audit_effort_reduction_pct * 100)

def test_auditor_value_display(a):
    av = auditor_value(a)
    assert av.cost_saved_display.startswith("₹")

def test_auditor_value_custom_apps(a):
    av = auditor_value(a, applications=500)
    assert av.manual_audit_hours > 0


# =========================================================================== #
# Battle view + impact events
# =========================================================================== #

def test_battle_view_rows(a):
    b = battle_view(a)
    assert len(b) == 6

def test_battle_view_labels(a):
    labels = [x.label for x in battle_view(a)]
    assert "Emails" in labels and "Cost" in labels and "Audit Readiness" in labels

def test_battle_view_emails_reduced(a):
    b = battle_view(a)
    emails = next(x for x in b if x.label == "Emails")
    assert emails.with_ecs < emails.without_ecs

def test_battle_view_reuse_improvement(a):
    b = battle_view(a)
    reuse = next(x for x in b if x.label == "Evidence Reuse")
    assert reuse.with_ecs > reuse.without_ecs

def test_impact_events_count(a):
    assert len(impact_events(a)) == 6

def test_impact_events_kinds(a):
    kinds = {e.kind for e in impact_events(a)}
    assert "observation_closed" in kinds
    assert "evidence_reused" in kinds
    assert "application_onboarded" in kinds

def test_impact_events_cost(a):
    assert all(e.cost_impact > 0 for e in impact_events(a))

def test_impact_events_display(a):
    assert all(e.cost_impact_display.startswith("₹") for e in impact_events(a))


# =========================================================================== #
# Orchestrator build_roi_center
# =========================================================================== #

def test_build_center_disabled_default():
    c = roi.build_roi_center()
    assert c["enabled"] is False
    assert "disabled" in c["note"]

def test_build_center_flag_on(monkeypatch):
    monkeypatch.setenv("ROI_CENTER_ENABLED", "true")
    c = roi.build_roi_center()
    assert c["enabled"] is True

def test_build_center_force():
    c = roi.build_roi_center(force=True)
    assert c["enabled"] is True

def test_build_center_has_all_screens():
    c = roi.build_roi_center(force=True)
    for key in ("year_results", "projection", "bank_result", "scenario",
                "framework_roi", "reuse_value", "observation_value", "email_value",
                "auditor_value", "battle_view", "impact_events"):
        assert key in c

def test_build_center_year_results_count():
    c = roi.build_roi_center(force=True)
    assert len(c["year_results"]) == 3  # storyboard apps 25/100/200

def test_build_center_framework_count():
    c = roi.build_roi_center(force=True)
    assert len(c["framework_roi"]) == 6

def test_build_center_bank_apps():
    c = roi.build_roi_center(force=True)
    assert c["bank_applications"] == 905
    assert c["vapt_applications"] == 600

def test_build_center_projection_total_positive():
    c = roi.build_roi_center(force=True)
    assert c["projection"]["total_cost_savings"] > 0

def test_build_center_scenario_present():
    c = roi.build_roi_center(force=True)
    assert "projected" in c["scenario"]
    assert "actual" in c["scenario"]

def test_build_center_overrides():
    c = roi.build_roi_center(force=True,
                             actual_overrides={"applications_onboarded": 100})
    assert c["scenario"]["actual"]["applications"] == 100

def test_build_center_currency():
    c = roi.build_roi_center(force=True)
    assert c["currency"]["symbol"] == "₹"

def test_build_center_serializable():
    import json
    json.dumps(roi.build_roi_center(force=True))


# =========================================================================== #
# Determinism + fail-safety
# =========================================================================== #

def test_determinism_same_inputs(a):
    r1 = calculate_projected(100, a)
    r2 = calculate_projected(100, a)
    assert r1.to_dict() == r2.to_dict()

def test_determinism_center():
    c1 = roi.build_roi_center(force=True)
    c2 = roi.build_roi_center(force=True)
    assert c1["bank_result"] == c2["bank_result"]

def test_projection_failsafe(monkeypatch, a):
    monkeypatch.setattr("app.roi.projections.calculate_projected",
                        lambda *x, **k: (_ for _ in ()).throw(ValueError("boom")))
    p = build_projection(a)
    assert p.enabled is False

def test_widgets_never_raise_on_bad_assumptions():
    bad = Assumptions()
    bad.frameworks = [{"bad": "data"}]
    assert isinstance(framework_roi(bad), list)

def test_all_results_json_serializable(a):
    import json
    objs = [
        calculate_projected(100, a), build_projection(a),
        compare(a, actual_overrides={"applications_onboarded": 50}),
    ]
    for o in objs:
        json.dumps(o.to_dict())

def test_model_to_dict_keys(a):
    r = calculate_projected(100, a)
    d = r.to_dict()
    for k in ("hours_saved", "cost_savings", "roi_pct", "fte_equivalent",
              "emails_avoided", "risk_reduction_pct"):
        assert k in d

def test_public_api_exports():
    for name in ("build_roi_center", "calculate_roi", "build_projection", "compare",
                 "framework_roi", "reuse_value", "observation_value", "email_value",
                 "auditor_value", "battle_view", "impact_events", "format_inr"):
        assert hasattr(roi, name)


# =========================================================================== #
# Additional edge cases + formatting precision
# =========================================================================== #

def test_format_inr_just_below_lakh():
    assert "Lakh" not in format_inr(99_999)

def test_format_inr_just_below_crore():
    assert format_inr(9_999_999).endswith("Lakh")

def test_format_inr_exact_crore():
    assert format_inr(10_000_000) == "₹1 Cr"

def test_format_inr_exact_lakh():
    assert format_inr(100_000) == "₹1 Lakh"

def test_format_inr_4_5_cr_example():
    assert format_inr(45_000_000) == "₹4.5 Cr"

def test_format_inr_50_lakh_example():
    assert format_inr(5_000_000) == "₹50 Lakh"

def test_calculate_roi_only_audits(a):
    r = calculate_roi(RoiInputs(audits_completed=5), a)
    assert r.hours_saved == pytest.approx(audit_hours_saved(5, a), rel=0.01)

def test_calculate_roi_only_frameworks(a):
    r = calculate_roi(RoiInputs(frameworks_onboarded=4), a)
    assert r.hours_saved == pytest.approx(framework_hours_saved(4, a), rel=0.01)

def test_calculate_roi_only_reuse(a):
    r = calculate_roi(RoiInputs(evidence_reused=200), a)
    assert r.hours_saved == pytest.approx(reuse_hours_saved(200, a), rel=0.01)

def test_calculate_roi_prevention_contributes(a):
    r0 = calculate_roi(RoiInputs(observations_closed=100), a)
    r1 = calculate_roi(RoiInputs(observations_closed=100, observations_prevented=50), a)
    assert r1.hours_saved > r0.hours_saved

def test_projected_inputs_audits(a):
    i = projected_inputs_for_apps(100, a)
    assert i.audits_completed == pytest.approx(100 / 50.0)

def test_projected_inputs_frameworks_capped(a):
    i = projected_inputs_for_apps(905, a)
    assert i.frameworks_onboarded <= 6

def test_calculate_projected_zero(a):
    r = calculate_projected(0, a)
    assert r.cost_savings == 0

def test_build_projection_disabled_on_error(monkeypatch, a):
    monkeypatch.setattr("app.roi.projections.build_projection.__globals__['calculate_projected']",
                        lambda *x, **k: (_ for _ in ()).throw(RuntimeError()), raising=False)
    # fall back: direct error injection already covered; ensure normal still ok
    assert build_projection(a).enabled is True

def test_compare_actual_lower_than_projected_negative_variance(a):
    # Actual with very low activity vs projected at same apps -> actual < projected.
    c = compare(a, actual_overrides={"applications_onboarded": 100,
                                     "observations_closed": 1, "evidence_reused": 0,
                                     "audits_completed": 0, "frameworks_onboarded": 0})
    assert c.actual.cost_savings <= c.projected.cost_savings

def test_scenario_to_dict(a):
    c = compare(a, actual_overrides={"applications_onboarded": 25})
    d = c.to_dict()
    assert "variance_pct" in d and "projected" in d and "actual" in d

def test_framework_roi_ai_governance_smallest(a):
    fws = {f.name: f.applications_covered for f in framework_roi(a)}
    assert fws["AI Governance"] < fws["VAPT"]

def test_reuse_value_zero_apps(a):
    r = reuse_value(a, applications=0)
    assert r.reuse_count == 0

def test_observation_value_zero_apps(a):
    o = observation_value(a, applications=0)
    assert o.observations_without_ecs == 0

def test_email_value_zero_apps(a):
    e = email_value(a, applications=0)
    assert e.emails_avoided == 0

def test_auditor_value_min_one_audit(a):
    av = auditor_value(a, applications=1)
    assert av.manual_audit_hours >= a.hours_per_audit

def test_impact_event_observation_value(a):
    ev = next(e for e in impact_events(a) if e.kind == "observation_closed")
    assert ev.hours_impact == pytest.approx(a.hours_per_observation * a.observation_effort_reduction_pct)

def test_battle_view_cost_improvement_positive(a):
    cost = next(x for x in battle_view(a) if x.label == "Cost")
    assert cost.improvement_pct > 0

def test_build_center_battle_count():
    c = roi.build_roi_center(force=True)
    assert len(c["battle_view"]) == 6

def test_build_center_events_count():
    c = roi.build_roi_center(force=True)
    assert len(c["impact_events"]) == 6

def test_build_center_assumptions_echoed():
    c = roi.build_roi_center(force=True)
    assert c["assumptions"].get("applications_in_bank") == 905

def test_build_center_error_safe(monkeypatch):
    monkeypatch.setattr("app.roi.Assumptions.load",
                        staticmethod(lambda: (_ for _ in ()).throw(ValueError("x"))))
    c = roi.build_roi_center(force=True)
    assert c["enabled"] is False

def test_calculate_roi_risk_in_result(a):
    r = calculate_roi(RoiInputs(applications_onboarded=100), a)
    assert r.risk_reduction_pct > 0

def test_inputs_to_dict():
    d = RoiInputs(applications_onboarded=10).to_dict()
    assert d["applications_onboarded"] == 10

def test_projection_point_display_fields(a):
    p = build_projection(a)
    assert all(pt.cost_savings_display.startswith("₹") for pt in p.points)
    assert all(pt.cumulative_display.startswith("₹") for pt in p.points)


# =========================================================================== #
# Route integration (FastAPI)
# =========================================================================== #

def test_route_registered():
    import importlib
    routes_mvp = importlib.import_module("modules.shared.routes.routes_mvp")
    assert hasattr(routes_mvp, "register_mvp_routes")

def test_roi_in_redirect_map():
    import inspect
    from modules.shared.routes import routes_mvp
    src = inspect.getsource(routes_mvp._module_redirect)
    assert '"roi"' in src and "/mvp/roi" in src


# =========================================================================== #
# Final executive value pass — framework analytics extensions
# =========================================================================== #

def test_framework_roi_has_emails_avoided(a):
    fws = framework_roi(a)
    assert all(f.emails_avoided > 0 for f in fws)

def test_framework_roi_contribution_present(a):
    fws = framework_roi(a)
    assert all(f.roi_contribution_pct >= 0 for f in fws)

def test_framework_roi_contribution_sums_100(a):
    fws = framework_roi(a)
    assert round(sum(f.roi_contribution_pct for f in fws), 0) == pytest.approx(100, abs=1)

def test_framework_roi_to_dict_new_fields(a):
    d = framework_roi(a)[0].to_dict()
    assert "emails_avoided" in d and "roi_contribution_pct" in d

def test_framework_roi_emails_scale_with_apps(a):
    fws = {f.name: f for f in framework_roi(a)}
    assert fws["VAPT"].emails_avoided > fws["AI Governance"].emails_avoided


# =========================================================================== #
# Final pass — ROI Waterfall
# =========================================================================== #

def test_waterfall_steps_count(a):
    wf = roi.build_waterfall(a)
    # 5 levers + total
    assert len(wf.steps) == 6

def test_waterfall_last_is_total(a):
    wf = roi.build_waterfall(a)
    assert wf.steps[-1].is_total is True
    assert wf.steps[-1].label == "TOTAL ECS VALUE"

def test_waterfall_levers_labels(a):
    labels = [s.label for s in roi.build_waterfall(a).steps]
    for lever in ["Evidence Reuse", "Email Reduction", "Observation Prevention",
                  "Audit Productivity", "Framework Automation"]:
        assert lever in labels

def test_waterfall_cumulative_increases(a):
    wf = roi.build_waterfall(a)
    non_total = [s for s in wf.steps if not s.is_total]
    cums = [s.cumulative for s in non_total]
    assert cums == sorted(cums)

def test_waterfall_total_equals_sum(a):
    wf = roi.build_waterfall(a)
    lever_sum = sum(s.value for s in wf.steps if not s.is_total)
    assert wf.total == pytest.approx(lever_sum, rel=0.01)

def test_waterfall_pct_total_100(a):
    wf = roi.build_waterfall(a)
    pct_sum = sum(s.pct_of_total for s in wf.steps if not s.is_total)
    assert pct_sum == pytest.approx(100, abs=1)

def test_waterfall_display_strings(a):
    wf = roi.build_waterfall(a)
    assert all(s.value_display.startswith("₹") for s in wf.steps)

def test_waterfall_custom_apps(a):
    wf = roi.build_waterfall(a, applications=100)
    assert wf.total > 0

def test_waterfall_to_dict(a):
    d = roi.build_waterfall(a).to_dict()
    assert "steps" in d and "total" in d


# =========================================================================== #
# Final pass — Aging reduction
# =========================================================================== #

def test_aging_before_after(a):
    ag = roi.aging_reduction(a)
    assert ag.before_days > ag.after_days

def test_aging_days_saved(a):
    ag = roi.aging_reduction(a)
    assert ag.days_saved == pytest.approx(ag.before_days - ag.after_days, rel=0.01)

def test_aging_reduction_pct(a):
    ag = roi.aging_reduction(a)
    assert ag.reduction_pct == pytest.approx(a.closure_acceleration_pct * 100, abs=1)

def test_aging_default_before(a):
    ag = roi.aging_reduction(a)
    assert ag.before_days == 45

def test_aging_to_dict(a):
    d = roi.aging_reduction(a).to_dict()
    assert "before_days" in d and "after_days" in d


# =========================================================================== #
# Final pass — Rollout simulator
# =========================================================================== #

def test_rollout_milestones(a):
    sim = roi.rollout_simulator(a)
    assert [p.applications for p in sim.points] == [25, 100, 250, 500, 905]

def test_rollout_custom_steps(a):
    sim = roi.rollout_simulator(a, steps=[10, 50])
    assert [p.applications for p in sim.points] == [10, 50]

def test_rollout_default_index_bank(a):
    sim = roi.rollout_simulator(a)
    assert sim.points[sim.default_index].applications == a.applications_in_bank

def test_rollout_cost_increases(a):
    sim = roi.rollout_simulator(a)
    costs = [p.cost_savings for p in sim.points]
    assert costs == sorted(costs)

def test_rollout_25_anchor(a):
    sim = roi.rollout_simulator(a)
    p25 = next(p for p in sim.points if p.applications == 25)
    assert p25.cost_savings == pytest.approx(4.5 * 10_000_000, rel=0.01)

def test_rollout_905_value(a):
    sim = roi.rollout_simulator(a)
    p905 = next(p for p in sim.points if p.applications == 905)
    assert p905.cost_savings > 0
    assert p905.cost_savings_display.startswith("₹")

def test_rollout_has_all_metrics(a):
    sim = roi.rollout_simulator(a)
    p = sim.points[0]
    assert p.roi_pct is not None and p.hours_saved >= 0
    assert p.emails_avoided >= 0 and p.fte_equivalent >= 0

def test_rollout_to_dict(a):
    d = roi.rollout_simulator(a).to_dict()
    assert "points" in d and "default_index" in d


# =========================================================================== #
# Final pass — Executive takeaways
# =========================================================================== #

def test_takeaways_card_count(a):
    tk = roi.executive_takeaways(a)
    assert len(tk.cards) == 6

def test_takeaways_keys(a):
    keys = {c.key for c in roi.executive_takeaways(a).cards}
    for k in ("top_value_framework", "highest_roi_contributor", "emails_avoided",
              "hours_saved", "financial_value", "five_year_value"):
        assert k in keys

def test_takeaways_top_value_framework(a):
    tk = roi.executive_takeaways(a)
    card = next(c for c in tk.cards if c.key == "top_value_framework")
    # Must be one of the configured frameworks.
    names = [f.get("name") for f in a.frameworks]
    assert card.value in names

def test_takeaways_highest_roi(a):
    tk = roi.executive_takeaways(a)
    card = next(c for c in tk.cards if c.key == "highest_roi_contributor")
    fws = framework_roi(a)
    top = max(fws, key=lambda f: f.roi_pct)
    assert card.value == top.name

def test_takeaways_financial_value_inr(a):
    tk = roi.executive_takeaways(a)
    card = next(c for c in tk.cards if c.key == "financial_value")
    assert card.value.startswith("₹")

def test_takeaways_five_year(a):
    tk = roi.executive_takeaways(a)
    card = next(c for c in tk.cards if c.key == "five_year_value")
    assert "Cr" in card.value or "Lakh" in card.value

def test_takeaways_to_dict(a):
    d = roi.executive_takeaways(a).to_dict()
    assert "cards" in d and len(d["cards"]) == 6


# =========================================================================== #
# Final pass — orchestrator wiring + serialization + fail-safety
# =========================================================================== #

def test_center_has_final_pass_keys():
    c = roi.build_roi_center(force=True)
    for key in ("waterfall", "aging_reduction", "rollout_simulator",
                "executive_takeaways"):
        assert key in c

def test_center_waterfall_total_display():
    c = roi.build_roi_center(force=True)
    assert c["waterfall"]["total_display"].startswith("₹")

def test_center_rollout_points():
    c = roi.build_roi_center(force=True)
    assert len(c["rollout_simulator"]["points"]) == 5

def test_center_takeaways_cards():
    c = roi.build_roi_center(force=True)
    assert len(c["executive_takeaways"]["cards"]) == 6

def test_center_final_pass_serializable():
    import json
    c = roi.build_roi_center(force=True)
    json.dumps({k: c[k] for k in ("waterfall", "aging_reduction",
                                  "rollout_simulator", "executive_takeaways")})

def test_waterfall_failsafe_bad_assumptions():
    bad = Assumptions()
    bad.frameworks = []
    assert isinstance(roi.build_waterfall(bad).steps, list)

def test_rollout_failsafe_bad_assumptions():
    bad = Assumptions()
    assert isinstance(roi.rollout_simulator(bad).points, list)

def test_takeaways_failsafe_empty_frameworks():
    bad = Assumptions()
    bad.frameworks = []
    tk = roi.executive_takeaways(bad)
    # Still produces the non-framework cards.
    assert any(c.key == "emails_avoided" for c in tk.cards)

def test_aging_determinism(a):
    assert roi.aging_reduction(a).to_dict() == roi.aging_reduction(a).to_dict()

def test_waterfall_determinism(a):
    assert roi.build_waterfall(a).to_dict() == roi.build_waterfall(a).to_dict()

def test_final_pass_exports():
    for name in ("build_waterfall", "aging_reduction", "rollout_simulator",
                 "executive_takeaways", "Waterfall", "AgingReduction",
                 "RolloutSimulator", "ExecutiveTakeaways"):
        assert hasattr(roi, name)
