"""Executive ROI & Value Realization Center.

A deterministic, NON-LLM, read-only engine that quantifies ECS business value:
hours/days saved, emails avoided, FTE equivalent, cost savings, risk reduction and
ROI %, plus multi-year projections, projected-vs-actual variance, and per-framework
/ reuse / observation / email / auditor value views.

All numbers come from this engine + config/roi.yaml; the UI hardcodes nothing.
Disabled by default (ROI_CENTER_ENABLED). Performs NO DB writes, NO schema changes,
NO LLM/embeddings/vector/RAG, and NO changes to RBAC/audit/observation/workflow.
"""

from __future__ import annotations

from typing import Any

from app.roi.assumptions import Assumptions, roi_enabled
from app.roi.workbook import build_board_deck, build_executive_view, load_workbook
from app.roi.calculations import (
    calculate_projected,
    calculate_roi,
    projected_inputs_for_apps,
    risk_reduction_pct,
)
from app.roi.models import (
    AgingReduction,
    AuditorValue,
    EmailValue,
    ExecutiveTakeaways,
    FrameworkRank,
    FrameworkRoi,
    InvestmentView,
    Mode,
    ObservationValue,
    PaybackAnalysis,
    PaybackHorizon,
    Projection,
    ProjectionPoint,
    ReuseValue,
    RoiEvent,
    RoiInputs,
    RoiResult,
    RolloutPoint,
    RolloutSimulator,
    ScenarioComparison,
    TakeawayCard,
    ValueDriver,
    ValueDriverBreakdown,
    Waterfall,
    WaterfallStep,
    WithoutVsWith,
    Workstream,
    format_compact,
    format_inr,
)
from app.roi.projections import build_projection
from app.roi.scenarios import actual_roi, collect_actual_inputs, compare
from app.roi.widgets import (
    aging_reduction,
    auditor_value,
    battle_view,
    build_waterfall,
    email_value,
    executive_takeaways,
    framework_ranking,
    framework_roi,
    impact_events,
    investment_view,
    observation_value,
    payback_analysis,
    reuse_value,
    rollout_simulator,
    value_drivers,
)

__all__ = [
    "Assumptions", "roi_enabled",
    "RoiInputs", "RoiResult", "Projection", "ProjectionPoint", "ScenarioComparison",
    "FrameworkRoi", "ReuseValue", "ObservationValue", "EmailValue", "AuditorValue",
    "WithoutVsWith", "RoiEvent", "Mode", "format_inr", "format_compact",
    "calculate_roi", "calculate_projected", "projected_inputs_for_apps",
    "risk_reduction_pct", "build_projection", "compare", "actual_roi",
    "collect_actual_inputs", "framework_roi", "reuse_value", "observation_value",
    "email_value", "auditor_value", "battle_view", "impact_events",
    "build_roi_center", "build_scenario_payload",
    # final executive value pass
    "Waterfall", "WaterfallStep", "AgingReduction", "RolloutPoint",
    "RolloutSimulator", "ExecutiveTakeaways", "TakeawayCard",
    "build_waterfall", "aging_reduction", "rollout_simulator", "executive_takeaways",
    # scenario + executive enhancement pass
    "ValueDriver", "ValueDriverBreakdown", "PaybackAnalysis", "PaybackHorizon",
    "FrameworkRank", "Workstream", "InvestmentView",
    "value_drivers", "payback_analysis", "framework_ranking", "investment_view",
]


# Workbook (ROI.xlsx) is the authoritative executive data source. Loaded once
# (read-only); failures degrade gracefully to an "unavailable" view.
_WB_MODEL = load_workbook()


def build_scenario_payload(a: "Assumptions",
                           actual_overrides: dict[str, Any] | None = None,
                           scenario_name: str | None = None) -> dict[str, Any]:
    """Build the complete ROI view-model for a single (scenario-adjusted) Assumptions.

    Pure/deterministic. Never raises.
    """
    storyboard_apps = [int(x) for x in a.storyboard_apps]
    year_results = [calculate_projected(n, a) for n in storyboard_apps]
    projection = build_projection(a)
    bank_result = calculate_projected(a.applications_in_bank, a)
    scenario_cmp = compare(a, actual_overrides=actual_overrides)

    return {
        "scenario": getattr(a, "active_scenario", "expected"),
        "scenario_label": getattr(a, "scenario_label", "Expected"),
        "adoption_pct": getattr(a, "adoption_pct", 1.0),
        "currency": {"symbol": a.symbol, "code": a.code},
        "assumptions": a.raw.get("assumptions", {}),
        "efficiency": a.raw.get("efficiency", {}),
        "bank_applications": a.applications_in_bank,
        "vapt_applications": a.vapt_applications,
        "storyboard_apps": storyboard_apps,
        "year_results": [r.to_dict() for r in year_results],
        "projection": projection.to_dict(),
        "bank_result": bank_result.to_dict(),
        "scenario_comparison": scenario_cmp.to_dict(),
        "framework_roi": [f.to_dict() for f in framework_roi(a)],
        "reuse_value": reuse_value(a).to_dict(),
        "observation_value": observation_value(a).to_dict(),
        "email_value": email_value(a).to_dict(),
        "auditor_value": auditor_value(a).to_dict(),
        "battle_view": [b.to_dict() for b in battle_view(a)],
        "impact_events": [e.to_dict() for e in impact_events(a)],
        "waterfall": build_waterfall(a).to_dict(),
        "aging_reduction": aging_reduction(a).to_dict(),
        "rollout_simulator": rollout_simulator(a).to_dict(),
        "executive_takeaways": executive_takeaways(a).to_dict(),
        # scenario + executive enhancement pass
        "value_drivers": value_drivers(a).to_dict(),
        "payback": payback_analysis(a).to_dict(),
        "framework_ranking": [r.to_dict() for r in framework_ranking(a)],
        "investment_view": investment_view(a).to_dict(),
        # Authoritative workbook executive view (read-only; ROI.xlsx is source of truth).
        "wb": build_executive_view(
            _WB_MODEL, scenario_name or getattr(a, "active_scenario", "expected")),
        # Boardroom 7-slide deck model (approved 5-year ROI model + scenario transforms).
        "deck": build_board_deck(scenario_name or getattr(a, "active_scenario", "expected")),
    }


def build_roi_center(*, actual_overrides: dict[str, Any] | None = None,
                     scenario: str | None = None,
                     force: bool = False) -> dict[str, Any]:
    """Assemble the full ROI Center view-model for the template. Never raises.

    Emits the active scenario's view-model at the top level (backward compatible)
    PLUS a ``scenarios`` map with all three precomputed scenario payloads so the
    UI toggle can switch instantly. When the feature flag is off (and not forced),
    returns a minimal disabled payload.
    """
    if not force and not roi_enabled():
        return {"enabled": False,
                "note": "ROI Center disabled (ROI_CENTER_ENABLED=false)"}
    try:
        base = Assumptions.load()
        names = base.scenario_names()
        active = scenario if scenario in names else base.default_scenario()

        scenarios: dict[str, Any] = {}
        for name in names:
            adj = base.for_scenario(name)
            scenarios[name] = build_scenario_payload(adj, actual_overrides, scenario_name=name)

        out = dict(scenarios[active])  # active scenario at top level (compat)
        out["enabled"] = True
        out["active_scenario"] = active
        out["scenario_names"] = names
        out["scenario_labels"] = {n: scenarios[n]["scenario_label"] for n in names}
        out["scenarios"] = scenarios
        # Back-compat alias: previous "scenario" key held the projected/actual compare.
        out["scenario"] = out["scenario_comparison"]
        return out
    except Exception as exc:  # noqa: BLE001 - fail safe
        return {"enabled": False,
                "note": f"ROI Center error (ignored): {type(exc).__name__}"}
