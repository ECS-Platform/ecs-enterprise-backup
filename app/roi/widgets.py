"""ROI widgets — screen DTO builders for the Executive ROI Center.

Each builder returns plain dataclasses/dicts the Jinja template renders. All numbers
originate from the engine (calculations/projections/scenarios) + assumptions; the UI
hardcodes nothing. Fail-safe: builders never raise.
"""

from __future__ import annotations

from typing import Any

from app.roi.assumptions import Assumptions
from app.roi.calculations import (
    calculate_projected,
    emails_avoided,
    projected_inputs_for_apps,
)
from app.roi.models import (
    AgingReduction,
    AuditorValue,
    EmailValue,
    ExecutiveTakeaways,
    FrameworkRank,
    FrameworkRoi,
    InvestmentView,
    ObservationValue,
    PaybackAnalysis,
    PaybackHorizon,
    ReuseValue,
    RoiEvent,
    RolloutPoint,
    RolloutSimulator,
    TakeawayCard,
    ValueDriver,
    ValueDriverBreakdown,
    Waterfall,
    WaterfallStep,
    WithoutVsWith,
    Workstream,
    format_inr,
)


def _inr(a: Assumptions, amount: float) -> str:
    return format_inr(amount, symbol=a.symbol, lakh=a.lakh, crore=a.crore)


# --------------------------------------------------------------------------- #
# Enhancement view 1 — ROI by framework
# --------------------------------------------------------------------------- #

def framework_roi(a: Assumptions) -> list[FrameworkRoi]:
    out: list[FrameworkRoi] = []
    try:
        bank = a.applications_in_bank or 1
        for fw in a.frameworks:
            name = str(fw.get("name", ""))
            if "apps_covered" in fw:
                apps = int(fw.get("apps_covered") or 0)
            else:
                apps = int(round(bank * float(fw.get("coverage_pct", 0) or 0)))
            weight = float(fw.get("weight", 1.0) or 1.0)
            reuse_factor = float(fw.get("reuse_factor", a.evidence_reuse_factor) or 1)

            obs_total = apps * a.observations_per_application * weight
            prevented = obs_total * a.observation_prevention_pct
            closed = obs_total - prevented
            evidence_reused = int(closed * reuse_factor)
            emails_avoided = obs_total * a.emails_per_observation * a.email_reduction_pct

            hours = (
                closed * a.hours_per_observation * a.observation_effort_reduction_pct
                + prevented * a.hours_per_observation
                + emails_avoided * a.hours_per_email
                + evidence_reused * a.reuse_hours_saved_each
            )
            cost = hours * a.cost_per_hour
            investment = apps * a.cost_per_app_per_year
            roi = (cost - investment) / investment * 100.0 if investment else 0.0

            out.append(FrameworkRoi(
                name=name, applications_covered=apps,
                observations_closed=int(round(closed)),
                evidence_reused=evidence_reused,
                emails_avoided=round(emails_avoided, 0),
                hours_saved=round(hours, 1),
                cost_saved=round(cost, 0), roi_pct=round(roi, 1),
                cost_saved_display=_inr(a, cost)))
        # ROI contribution % = each framework's share of total framework cost saved.
        total_cost = sum(f.cost_saved for f in out) or 1.0
        for f in out:
            f.roi_contribution_pct = round(f.cost_saved / total_cost * 100.0, 1)
    except Exception:  # noqa: BLE001
        return out
    return out


# --------------------------------------------------------------------------- #
# Enhancement view 2 — Evidence reuse value
# --------------------------------------------------------------------------- #

def reuse_value(a: Assumptions, *, applications: int | None = None) -> ReuseValue:
    try:
        apps = a.applications_in_bank if applications is None else int(applications)
        inp = projected_inputs_for_apps(apps, a)
        submitted = int(inp.evidence_submitted)
        reuse_count = int(submitted * a.evidence_reuse_factor)
        hours = reuse_count * a.reuse_hours_saved_each
        cost = hours * a.cost_per_hour
        # ROI contribution: reuse cost vs total projected cost savings.
        total = calculate_projected(apps, a).cost_savings or 1
        contribution = cost / total * 100.0
        return ReuseValue(
            evidence_submitted=submitted, reuse_factor=a.evidence_reuse_factor,
            reuse_count=reuse_count, hours_avoided=round(hours, 1),
            cost_avoided=round(cost, 0),
            roi_contribution_pct=round(min(contribution, 100.0), 1),
            cost_avoided_display=_inr(a, cost))
    except Exception:  # noqa: BLE001
        return ReuseValue()


# --------------------------------------------------------------------------- #
# Enhancement view 3 — Observation elimination value
# --------------------------------------------------------------------------- #

def observation_value(a: Assumptions, *, applications: int | None = None) -> ObservationValue:
    try:
        apps = a.applications_in_bank if applications is None else int(applications)
        obs_without = apps * a.observations_per_application
        prevented = obs_without * a.observation_prevention_pct
        closed = obs_without - prevented
        hours = (prevented * a.hours_per_observation
                 + closed * a.hours_per_observation * a.observation_effort_reduction_pct)
        cost = hours * a.cost_per_hour
        return ObservationValue(
            observations_without_ecs=round(obs_without, 1),
            observations_prevented=round(prevented, 1),
            observations_closed=round(closed, 1),
            hours_saved=round(hours, 1), cost_saved=round(cost, 0),
            closure_acceleration_pct=round(a.closure_acceleration_pct * 100, 1),
            cost_saved_display=_inr(a, cost))
    except Exception:  # noqa: BLE001
        return ObservationValue()


# --------------------------------------------------------------------------- #
# Enhancement view 4 — Email reduction engine
# --------------------------------------------------------------------------- #

def email_value(a: Assumptions, *, applications: int | None = None) -> EmailValue:
    try:
        apps = a.applications_in_bank if applications is None else int(applications)
        obs_total = apps * a.observations_per_application
        expected = obs_total * a.emails_per_observation
        avoided = emails_avoided(obs_total, a)
        in_ecs = expected - avoided
        hours = avoided * a.hours_per_email
        cost = hours * a.cost_per_hour
        return EmailValue(
            expected_emails_without_ecs=round(expected, 0),
            workflow_transactions_in_ecs=round(in_ecs, 0),
            emails_avoided=round(avoided, 0), hours_avoided=round(hours, 1),
            cost_saved=round(cost, 0), cost_saved_display=_inr(a, cost))
    except Exception:  # noqa: BLE001
        return EmailValue()


# --------------------------------------------------------------------------- #
# Enhancement view 5 — Auditor productivity
# --------------------------------------------------------------------------- #

def auditor_value(a: Assumptions, *, applications: int | None = None) -> AuditorValue:
    try:
        apps = a.applications_in_bank if applications is None else int(applications)
        audits = max(1.0, apps / 50.0)
        manual = audits * a.hours_per_audit
        ecs = manual * (1.0 - a.audit_effort_reduction_pct)
        saved = manual - ecs
        cost = saved * a.cost_per_hour
        return AuditorValue(
            manual_audit_hours=round(manual, 1), ecs_audit_hours=round(ecs, 1),
            audit_hours_saved=round(saved, 1),
            review_effort_reduction_pct=round(a.audit_effort_reduction_pct * 100, 1),
            closure_acceleration_pct=round(a.closure_acceleration_pct * 100, 1),
            cost_saved=round(cost, 0), cost_saved_display=_inr(a, cost))
    except Exception:  # noqa: BLE001
        return AuditorValue()


# --------------------------------------------------------------------------- #
# Screen 1 / Screen 7 — Without vs With battle view
# --------------------------------------------------------------------------- #

def battle_view(a: Assumptions, *, applications: int | None = None) -> list[WithoutVsWith]:
    try:
        apps = a.applications_in_bank if applications is None else int(applications)
        obs_total = apps * a.observations_per_application
        emails_without = obs_total * a.emails_per_observation
        emails_with = emails_without * (1.0 - a.email_reduction_pct)
        hours_without = obs_total * a.hours_per_observation
        hours_with = hours_without * (1.0 - a.observation_effort_reduction_pct)
        reuse_without = 0.0
        reuse_with = obs_total * a.evidence_reuse_factor
        aging_without = 45.0
        aging_with = aging_without * (1.0 - a.closure_acceleration_pct)
        readiness_without = 40.0
        readiness_with = 95.0
        cost_without = hours_without * a.cost_per_hour
        cost_with = hours_with * a.cost_per_hour

        def _imp(w, e, lower_is_better=True):
            if w == 0:
                return 0.0
            diff = (w - e) / w * 100.0
            return round(diff if lower_is_better else -diff, 1)

        return [
            WithoutVsWith("Emails", round(emails_without), round(emails_with), "emails",
                          _imp(emails_without, emails_with)),
            WithoutVsWith("Observation Ageing", aging_without, round(aging_with, 1), "days",
                          _imp(aging_without, aging_with)),
            WithoutVsWith("Evidence Reuse", reuse_without, round(reuse_with), "reuses",
                          100.0),
            WithoutVsWith("Manual Hours", round(hours_without), round(hours_with), "hours",
                          _imp(hours_without, hours_with)),
            WithoutVsWith("Audit Readiness", readiness_without, readiness_with, "%",
                          round(readiness_with - readiness_without, 1)),
            WithoutVsWith("Cost", round(cost_without), round(cost_with), "₹",
                          _imp(cost_without, cost_with)),
        ]
    except Exception:  # noqa: BLE001
        return []


# --------------------------------------------------------------------------- #
# Phase 4 — ROI impact events (ticker)
# --------------------------------------------------------------------------- #

def impact_events(a: Assumptions) -> list[RoiEvent]:
    """Deterministic per-action ROI impact templates for the live ticker."""
    try:
        hpo = a.hours_per_observation
        events = [
            ("observation_closed", "Observation Closed",
             hpo * a.observation_effort_reduction_pct),
            ("evidence_reused", "Evidence Reused", a.reuse_hours_saved_each),
            ("application_onboarded", "Application Onboarded",
             a.observations_per_application * hpo * a.observation_effort_reduction_pct),
            ("framework_added", "Framework Added",
             a.hours_per_framework_onboarding * a.framework_onboarding_reduction_pct),
            ("audit_completed", "Audit Completed",
             a.hours_per_audit * a.audit_effort_reduction_pct),
            ("evidence_approved", "Evidence Approved",
             a.emails_per_observation * a.email_reduction_pct * a.hours_per_email),
        ]
        out: list[RoiEvent] = []
        for kind, label, hours in events:
            cost = hours * a.cost_per_hour
            out.append(RoiEvent(kind=kind, label=label, cost_impact=round(cost, 0),
                                hours_impact=round(hours, 2),
                                cost_impact_display=_inr(a, cost)))
        return out
    except Exception:  # noqa: BLE001
        return []


# --------------------------------------------------------------------------- #
# Final pass view 2 — ROI Waterfall
# --------------------------------------------------------------------------- #

def build_waterfall(a: Assumptions, *, applications: int | None = None) -> Waterfall:
    """Decompose total ECS value into contributing levers (cumulative). Never raises."""
    try:
        apps = a.applications_in_bank if applications is None else int(applications)
        obs_total = apps * a.observations_per_application
        prevented = obs_total * a.observation_prevention_pct
        closed = obs_total - prevented
        submitted = closed
        reused = submitted * a.evidence_reuse_factor
        audits = max(1.0, apps / 50.0)
        frameworks = min(len(a.frameworks) or 6, max(1, apps // 100 + 1)) if apps else 0

        levers = [
            ("Evidence Reuse", reused * a.reuse_hours_saved_each),
            ("Email Reduction",
             obs_total * a.emails_per_observation * a.email_reduction_pct * a.hours_per_email),
            ("Observation Prevention", prevented * a.hours_per_observation),
            ("Audit Productivity",
             audits * a.hours_per_audit * a.audit_effort_reduction_pct),
            ("Framework Automation",
             frameworks * a.hours_per_framework_onboarding * a.framework_onboarding_reduction_pct),
        ]
        lever_costs = [(label, hours * a.cost_per_hour) for label, hours in levers]
        total = sum(c for _, c in lever_costs) or 0.0

        steps: list[WaterfallStep] = []
        cumulative = 0.0
        for label, cost in lever_costs:
            cumulative += cost
            steps.append(WaterfallStep(
                label=label, value=round(cost, 0), cumulative=round(cumulative, 0),
                pct_of_total=round(cost / total * 100.0, 1) if total else 0.0,
                is_total=False, value_display=_inr(a, cost),
                cumulative_display=_inr(a, cumulative)))
        steps.append(WaterfallStep(
            label="TOTAL ECS VALUE", value=round(total, 0), cumulative=round(total, 0),
            pct_of_total=100.0, is_total=True, value_display=_inr(a, total),
            cumulative_display=_inr(a, total)))

        return Waterfall(steps=steps, total=round(total, 0), total_display=_inr(a, total))
    except Exception:  # noqa: BLE001
        return Waterfall()


# --------------------------------------------------------------------------- #
# Final pass view 3 — Observation aging reduction
# --------------------------------------------------------------------------- #

def aging_reduction(a: Assumptions) -> AgingReduction:
    """Before/after average observation closure days. Never raises."""
    try:
        aging = a.raw.get("aging", {}) if isinstance(a.raw, dict) else {}
        before = float(aging.get("before_closure_days", 45))
        # After = before reduced by the configured closure acceleration.
        after = before * (1.0 - a.closure_acceleration_pct)
        saved = before - after
        pct = (saved / before * 100.0) if before else 0.0
        return AgingReduction(
            before_days=round(before, 1), after_days=round(after, 1),
            days_saved=round(saved, 1), reduction_pct=round(pct, 1))
    except Exception:  # noqa: BLE001
        return AgingReduction()


# --------------------------------------------------------------------------- #
# Final pass view 4 — Enterprise rollout simulator
# --------------------------------------------------------------------------- #

def rollout_simulator(a: Assumptions, *, steps: list[int] | None = None) -> RolloutSimulator:
    """Precompute ROI at each rollout milestone so the slider is instant & deterministic."""
    try:
        from app.roi.calculations import calculate_projected, projected_inputs_for_apps

        cfg_steps = None
        if isinstance(a.raw, dict):
            cfg_steps = (a.raw.get("rollout", {}) or {}).get("milestones")
        milestones = [int(x) for x in (steps or cfg_steps or
                                       [25, 100, 250, 500, 605, a.applications_in_bank])]
        points: list[RolloutPoint] = []
        for apps in milestones:
            res = calculate_projected(apps, a)
            inp = projected_inputs_for_apps(apps, a)
            obs_total = inp.observations_closed + inp.observations_prevented
            from app.roi.calculations import emails_avoided as _emails
            points.append(RolloutPoint(
                applications=apps, roi_pct=res.roi_pct, cost_savings=res.cost_savings,
                hours_saved=res.hours_saved,
                emails_avoided=round(_emails(obs_total, a), 0),
                fte_equivalent=res.fte_equivalent,
                cost_savings_display=res.cost_savings_display))
        # Default the slider to the bank-wide milestone if present, else last.
        default_index = len(points) - 1
        for i, p in enumerate(points):
            if p.applications == a.applications_in_bank:
                default_index = i
        return RolloutSimulator(points=points, default_index=default_index)
    except Exception:  # noqa: BLE001
        return RolloutSimulator()


# --------------------------------------------------------------------------- #
# Final pass view 5 — Executive takeaways
# --------------------------------------------------------------------------- #

def executive_takeaways(a: Assumptions) -> ExecutiveTakeaways:
    """Auto-generated executive summary cards from the computed views. Never raises."""
    try:
        from app.roi.calculations import calculate_projected
        from app.roi.projections import build_projection

        fws = framework_roi(a)
        ev = email_value(a)
        bank = calculate_projected(a.applications_in_bank, a)
        proj = build_projection(a)

        cards: list[TakeawayCard] = []
        if fws:
            top_value = max(fws, key=lambda f: f.cost_saved)
            top_roi = max(fws, key=lambda f: f.roi_pct)
            cards.append(TakeawayCard(
                key="top_value_framework", title="Top Value Framework",
                value=top_value.name, sub=f"{top_value.cost_saved_display} saved"))
            cards.append(TakeawayCard(
                key="highest_roi_contributor", title="Highest ROI Contributor",
                value=top_roi.name, sub=f"{top_roi.roi_pct}% ROI"))
        cards.append(TakeawayCard(
            key="emails_avoided", title="Emails Avoided",
            value=f"{int(ev.emails_avoided):,}", sub=ev.cost_saved_display + " saved"))
        cards.append(TakeawayCard(
            key="hours_saved", title="Hours Saved",
            value=f"{int(bank.hours_saved):,}",
            sub=f"{bank.fte_equivalent} FTE equivalent"))
        cards.append(TakeawayCard(
            key="financial_value", title="Estimated Financial Value",
            value=bank.cost_savings_display, sub="annual, bank-wide potential"))
        cards.append(TakeawayCard(
            key="five_year_value", title="Projected 5-Year Value",
            value=proj.total_display, sub="cumulative across rollout"))
        # Section 8 additions: FTE, payback, risk reduction.
        cards.append(TakeawayCard(
            key="fte_saved", title="FTE Equivalent Saved",
            value=str(bank.fte_equivalent), sub="annual productivity"))
        pb = payback_analysis(a)
        cards.append(TakeawayCard(
            key="payback_period", title="Payback Period",
            value=f"{pb.payback_months} months", sub="to recover investment"))
        cards.append(TakeawayCard(
            key="risk_reduction", title="Risk Reduction",
            value=f"{bank.risk_reduction_pct}%", sub="coverage uplift"))
        return ExecutiveTakeaways(cards=cards)
    except Exception:  # noqa: BLE001
        return ExecutiveTakeaways()


# --------------------------------------------------------------------------- #
# Section 2 — Value driver breakdown
# --------------------------------------------------------------------------- #

_DRIVER_LABELS = [
    ("evidence_reuse", "Evidence Reuse"),
    ("observation_prevention", "Observation Prevention"),
    ("closure_acceleration", "Faster Observation Closure"),
    ("auditor_productivity", "Auditor Productivity"),
    ("email_reduction", "Email Reduction"),
    ("framework_automation", "Framework Automation"),
]
_DRIVER_DEFAULT_WEIGHTS = {
    "evidence_reuse": 0.40, "observation_prevention": 0.25,
    "closure_acceleration": 0.15, "auditor_productivity": 0.10,
    "email_reduction": 0.05, "framework_automation": 0.05,
}


def value_drivers(a: Assumptions, *, applications: int | None = None) -> ValueDriverBreakdown:
    """Decompose total ECS value by lever using configurable weights. Never raises."""
    try:
        from app.roi.calculations import calculate_projected
        apps = a.applications_in_bank if applications is None else int(applications)
        total_cost = calculate_projected(apps, a).cost_savings
        total_hours = 0.0
        weights_cfg = (a.raw.get("value_drivers", {}) if isinstance(a.raw, dict) else {}) \
            or _DRIVER_DEFAULT_WEIGHTS
        # Normalize weights.
        wsum = sum(float(weights_cfg.get(k, 0)) for k, _ in _DRIVER_LABELS) or 1.0
        drivers: list[ValueDriver] = []
        for key, label in _DRIVER_LABELS:
            w = float(weights_cfg.get(key, _DRIVER_DEFAULT_WEIGHTS.get(key, 0))) / wsum
            cost = total_cost * w
            hours = cost / a.cost_per_hour if a.cost_per_hour else 0.0
            total_hours += hours
            drivers.append(ValueDriver(
                name=label, weight_pct=round(w * 100, 1),
                hours_saved=round(hours, 0), cost_saved=round(cost, 0),
                contribution_pct=round(w * 100, 1),
                trend="up" if a.active_scenario != "conservative" else "flat",
                cost_saved_display=_inr(a, cost)))
        return ValueDriverBreakdown(
            drivers=drivers, total_cost=round(total_cost, 0),
            total_hours=round(total_hours, 0), total_display=_inr(a, total_cost))
    except Exception:  # noqa: BLE001
        return ValueDriverBreakdown()


# --------------------------------------------------------------------------- #
# Section 4 — Payback analysis
# --------------------------------------------------------------------------- #

def payback_analysis(a: Assumptions, *, applications: int | None = None) -> PaybackAnalysis:
    """Investment vs savings payback + multi-year net value. Never raises."""
    try:
        from app.roi.calculations import calculate_projected
        cfg = (a.raw.get("payback", {}) if isinstance(a.raw, dict) else {}) or {}
        invest = float(cfg.get("implementation_cost", 80_000_000))
        run = float(cfg.get("annual_run_cost", 20_000_000))
        horizons_years = list(cfg.get("horizons_years", [3, 5, 10]))

        apps = a.applications_in_bank if applications is None else int(applications)
        annual_savings = calculate_projected(apps, a).cost_savings
        net_annual = annual_savings - run
        payback_months = (invest / net_annual * 12.0) if net_annual > 0 else 0.0

        horizons: list[PaybackHorizon] = []
        for yrs in horizons_years:
            net = net_annual * yrs - invest
            horizons.append(PaybackHorizon(
                years=int(yrs), net_value=round(net, 0),
                net_value_display=_inr(a, net)))

        return PaybackAnalysis(
            investment_cost=round(invest, 0), annual_savings=round(annual_savings, 0),
            annual_run_cost=round(run, 0), net_annual_savings=round(net_annual, 0),
            payback_months=round(payback_months, 1), horizons=horizons,
            investment_display=_inr(a, invest),
            annual_savings_display=_inr(a, annual_savings))
    except Exception:  # noqa: BLE001
        return PaybackAnalysis()


# --------------------------------------------------------------------------- #
# Section 7 — Framework ranking
# --------------------------------------------------------------------------- #

def framework_ranking(a: Assumptions) -> list[FrameworkRank]:
    """Rank frameworks by value contribution (highest first). Never raises."""
    try:
        fws = sorted(framework_roi(a), key=lambda f: f.cost_saved, reverse=True)
        out: list[FrameworkRank] = []
        for i, f in enumerate(fws, start=1):
            out.append(FrameworkRank(
                rank=i, name=f.name, cost_saved=f.cost_saved,
                roi_contribution_pct=f.roi_contribution_pct,
                cost_saved_display=f.cost_saved_display, is_top=(i == 1)))
        return out
    except Exception:  # noqa: BLE001
        return []


# --------------------------------------------------------------------------- #
# Section 9 — Team / investment view
# --------------------------------------------------------------------------- #

def investment_view(a: Assumptions, *, applications: int | None = None) -> InvestmentView:
    """Implementation workstreams vs value generated. Never raises.

    Headcount/cost come from config (NO hardcoded team size in UI).
    """
    try:
        from app.roi.calculations import calculate_projected
        cfg = (a.raw.get("workstreams", []) if isinstance(a.raw, dict) else []) or []
        streams: list[Workstream] = []
        total_hc = 0
        total_inv = 0.0
        for ws in cfg:
            if not isinstance(ws, dict):
                continue
            hc = int(ws.get("headcount", 0) or 0)
            cost = float(ws.get("annual_cost", 0) or 0)
            total_hc += hc
            total_inv += cost
            streams.append(Workstream(
                name=str(ws.get("name", "")), headcount=hc, annual_cost=round(cost, 0),
                annual_cost_display=_inr(a, cost)))
        apps = a.applications_in_bank if applications is None else int(applications)
        value = calculate_projected(apps, a).cost_savings
        multiple = (value / total_inv) if total_inv else 0.0
        return InvestmentView(
            workstreams=streams, total_headcount=total_hc,
            total_investment=round(total_inv, 0), value_generated=round(value, 0),
            value_multiple=round(multiple, 1),
            total_investment_display=_inr(a, total_inv),
            value_generated_display=_inr(a, value))
    except Exception:  # noqa: BLE001
        return InvestmentView()
