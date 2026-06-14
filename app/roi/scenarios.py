"""ROI scenarios — Projected vs Actual + variance.

Projected ROI uses the configured assumptions and onboarding target.
Actual ROI reads live ECS demo statistics (the same in-memory data the dashboards
render) so leadership sees ROI grounded in what ECS actually contains.

Reading actual stats is best-effort and fail-safe: if a source is unavailable, the
field defaults to 0 and the engine still returns a valid comparison.
"""

from __future__ import annotations

from typing import Any

from app.roi.assumptions import Assumptions
from app.roi.calculations import calculate_projected, calculate_roi
from app.roi.models import (
    Mode,
    RoiInputs,
    RoiResult,
    ScenarioComparison,
    format_inr,
)


def collect_actual_inputs(a: Assumptions, *, overrides: dict[str, Any] | None = None) -> RoiInputs:
    """Build RoiInputs from live ECS statistics. Never raises.

    ``overrides`` lets callers/tests inject deterministic values without ECS state.
    """
    overrides = overrides or {}
    apps = frameworks = obs_closed = ev_submitted = ev_approved = ev_reused = 0
    audits = 0
    try:
        if not overrides:
            from app import ecs_state

            apps = len(getattr(ecs_state, "onboarded_applications", []) or [])
            frameworks = len(getattr(ecs_state, "frameworks", {}) or {})

            analytics = ecs_state.build_evidence_analytics()
            totals = analytics.get("totals", {}) if isinstance(analytics, dict) else {}
            ev_submitted = int(totals.get("submitted", 0)) + int(totals.get("approved", 0))
            ev_approved = int(totals.get("approved", 0))
            # Observations "closed" ~ approved controls in the demo model.
            obs_closed = int(totals.get("approved", 0))

            try:
                from modules.executive_overview.engines.demo_metrics import REUSE_METRICS
                ev_reused = int(REUSE_METRICS.get("evidences_reused", 0))
            except Exception:  # noqa: BLE001
                ev_reused = 0

            # Audits completed ~ one per framework with approved evidence (proxy).
            audits = max(0, frameworks // 2)
    except Exception:  # noqa: BLE001
        pass

    # Prevented observations are not directly tracked in actual data -> conservative 0
    # unless overridden.
    prevented = 0

    merged = {
        "applications_onboarded": apps,
        "frameworks_onboarded": frameworks,
        "observations_closed": obs_closed,
        "observations_prevented": prevented,
        "evidence_submitted": ev_submitted,
        "evidence_approved": ev_approved,
        "evidence_reused": ev_reused,
        "audits_completed": audits,
    }
    merged.update({k: v for k, v in overrides.items() if k in merged})
    return RoiInputs(**merged)


def actual_roi(a: Assumptions, *, overrides: dict[str, Any] | None = None) -> RoiResult:
    return calculate_roi(collect_actual_inputs(a, overrides=overrides), a,
                         mode=Mode.ACTUAL.value)


def compare(a: Assumptions, *, target_apps: int | None = None,
            actual_overrides: dict[str, Any] | None = None) -> ScenarioComparison:
    """Compare projected vs actual ROI and compute variance. Never raises."""
    try:
        actual = actual_roi(a, overrides=actual_overrides)
        # Project at the same app count as actual so the comparison is apples-to-apples,
        # unless an explicit target is given.
        apps = target_apps if target_apps is not None else actual.applications
        projected = calculate_projected(max(apps, 0), a)

        variance_cost = actual.cost_savings - projected.cost_savings
        variance_pct = (variance_cost / projected.cost_savings * 100.0) \
            if projected.cost_savings else 0.0

        return ScenarioComparison(
            enabled=True, projected=projected, actual=actual,
            variance_cost=round(variance_cost, 0), variance_pct=round(variance_pct, 1),
            projected_display=projected.cost_savings_display,
            actual_display=actual.cost_savings_display,
            variance_display=format_inr(variance_cost, symbol=a.symbol, lakh=a.lakh,
                                        crore=a.crore),
        )
    except Exception as exc:  # noqa: BLE001 - fail safe
        return ScenarioComparison(enabled=False,
                                  note=f"scenario error (ignored): {type(exc).__name__}")
