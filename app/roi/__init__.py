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
    FrameworkRoi,
    Mode,
    ObservationValue,
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
    Waterfall,
    WaterfallStep,
    WithoutVsWith,
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
    framework_roi,
    impact_events,
    observation_value,
    reuse_value,
    rollout_simulator,
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
    "build_roi_center",
    # final executive value pass
    "Waterfall", "WaterfallStep", "AgingReduction", "RolloutPoint",
    "RolloutSimulator", "ExecutiveTakeaways", "TakeawayCard",
    "build_waterfall", "aging_reduction", "rollout_simulator", "executive_takeaways",
]


def build_roi_center(*, actual_overrides: dict[str, Any] | None = None,
                     force: bool = False) -> dict[str, Any]:
    """Assemble the full ROI Center view-model for the template. Never raises.

    Returns a dict with an ``enabled`` flag plus every screen's data. When the
    feature flag is off (and not forced), returns a minimal disabled payload.
    """
    if not force and not roi_enabled():
        return {"enabled": False,
                "note": "ROI Center disabled (ROI_CENTER_ENABLED=false)"}
    try:
        a = Assumptions.load()
        storyboard_apps = [int(x) for x in a.storyboard_apps]

        # Storyboard year results (Screens 3-5) and 5-year projection (Screen 8).
        year_results = [calculate_projected(n, a) for n in storyboard_apps]
        projection = build_projection(a)

        # Full bank potential (Screen 9 executive summary).
        bank_result = calculate_projected(a.applications_in_bank, a)
        scenario = compare(a, actual_overrides=actual_overrides)

        return {
            "enabled": True,
            "currency": {"symbol": a.symbol, "code": a.code},
            "assumptions": a.raw.get("assumptions", {}),
            "efficiency": a.raw.get("efficiency", {}),
            "bank_applications": a.applications_in_bank,
            "vapt_applications": a.vapt_applications,
            "storyboard_apps": storyboard_apps,
            "year_results": [r.to_dict() for r in year_results],
            "projection": projection.to_dict(),
            "bank_result": bank_result.to_dict(),
            "scenario": scenario.to_dict(),
            "framework_roi": [f.to_dict() for f in framework_roi(a)],
            "reuse_value": reuse_value(a).to_dict(),
            "observation_value": observation_value(a).to_dict(),
            "email_value": email_value(a).to_dict(),
            "auditor_value": auditor_value(a).to_dict(),
            "battle_view": [b.to_dict() for b in battle_view(a)],
            "impact_events": [e.to_dict() for e in impact_events(a)],
            # final executive value pass
            "waterfall": build_waterfall(a).to_dict(),
            "aging_reduction": aging_reduction(a).to_dict(),
            "rollout_simulator": rollout_simulator(a).to_dict(),
            "executive_takeaways": executive_takeaways(a).to_dict(),
        }
    except Exception as exc:  # noqa: BLE001 - fail safe
        return {"enabled": False,
                "note": f"ROI Center error (ignored): {type(exc).__name__}"}
