"""ROI & Value Realization — domain models.

Deterministic, non-LLM dataclasses/enums plus INR (₹ / Lakh / Crore) formatting
helpers. No network/DB/RAG/LLM imports. All values are computed by the engine; the
UI renders these objects and never hardcodes numbers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

_LAKH = 100_000
_CRORE = 10_000_000


def format_inr(amount: float, *, symbol: str = "₹", lakh: int = _LAKH,
               crore: int = _CRORE) -> str:
    """Format a rupee amount using Indian Lakh/Crore scaling. Never raises."""
    try:
        a = float(amount)
    except (TypeError, ValueError):
        return f"{symbol}0"
    sign = "-" if a < 0 else ""
    a = abs(a)
    if a >= crore:
        return f"{sign}{symbol}{round(a / crore, 2):g} Cr"
    if a >= lakh:
        return f"{sign}{symbol}{round(a / lakh, 2):g} Lakh"
    return f"{sign}{symbol}{round(a):,.0f}"


def format_compact(n: float) -> str:
    """Compact integer-ish formatting for counters (e.g. 12,500)."""
    try:
        return f"{round(float(n)):,}"
    except (TypeError, ValueError):
        return "0"


class Mode(str, Enum):
    PROJECTED = "projected"
    ACTUAL = "actual"


# --------------------------------------------------------------------------- #
# Core ROI
# --------------------------------------------------------------------------- #

@dataclass
class RoiInputs:
    """Activity volumes that drive ROI (either projected or actual)."""
    applications_onboarded: int = 0
    frameworks_onboarded: int = 0
    observations_closed: int = 0
    observations_prevented: int = 0
    evidence_submitted: int = 0
    evidence_approved: int = 0
    evidence_reused: int = 0
    audits_completed: int = 0
    emails_in_ecs: int = 0     # actual workflow transactions inside ECS (actual mode)

    def to_dict(self) -> dict[str, Any]:
        return {
            "applications_onboarded": self.applications_onboarded,
            "frameworks_onboarded": self.frameworks_onboarded,
            "observations_closed": self.observations_closed,
            "observations_prevented": self.observations_prevented,
            "evidence_submitted": self.evidence_submitted,
            "evidence_approved": self.evidence_approved,
            "evidence_reused": self.evidence_reused,
            "audits_completed": self.audits_completed,
            "emails_in_ecs": self.emails_in_ecs,
        }


@dataclass
class RoiResult:
    """Computed ROI outputs for a given set of inputs."""
    mode: str = Mode.PROJECTED.value
    enabled: bool = True
    applications: int = 0

    hours_saved: float = 0.0
    days_saved: float = 0.0
    emails_avoided: float = 0.0
    fte_equivalent: float = 0.0
    cost_savings: float = 0.0
    investment: float = 0.0
    net_value: float = 0.0
    risk_reduction_pct: float = 0.0
    roi_pct: float = 0.0

    # Pre-formatted INR strings for the UI (still derived from numbers above).
    cost_savings_display: str = ""
    net_value_display: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode, "enabled": self.enabled, "applications": self.applications,
            "hours_saved": self.hours_saved, "days_saved": self.days_saved,
            "emails_avoided": self.emails_avoided, "fte_equivalent": self.fte_equivalent,
            "cost_savings": self.cost_savings, "investment": self.investment,
            "net_value": self.net_value, "risk_reduction_pct": self.risk_reduction_pct,
            "roi_pct": self.roi_pct, "cost_savings_display": self.cost_savings_display,
            "net_value_display": self.net_value_display, "note": self.note,
        }


# --------------------------------------------------------------------------- #
# Projection
# --------------------------------------------------------------------------- #

@dataclass
class ProjectionPoint:
    year: int = 0
    applications: int = 0
    hours_saved: float = 0.0
    cost_savings: float = 0.0
    fte_equivalent: float = 0.0
    observations_reduced: float = 0.0
    roi_pct: float = 0.0
    cumulative_cost_savings: float = 0.0
    cost_savings_display: str = ""
    cumulative_display: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "year": self.year, "applications": self.applications,
            "hours_saved": self.hours_saved, "cost_savings": self.cost_savings,
            "fte_equivalent": self.fte_equivalent,
            "observations_reduced": self.observations_reduced, "roi_pct": self.roi_pct,
            "cumulative_cost_savings": self.cumulative_cost_savings,
            "cost_savings_display": self.cost_savings_display,
            "cumulative_display": self.cumulative_display,
        }


@dataclass
class Projection:
    enabled: bool = True
    points: list[ProjectionPoint] = field(default_factory=list)
    total_cost_savings: float = 0.0
    total_hours_saved: float = 0.0
    peak_fte: float = 0.0
    total_display: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled, "points": [p.to_dict() for p in self.points],
            "total_cost_savings": self.total_cost_savings,
            "total_hours_saved": self.total_hours_saved, "peak_fte": self.peak_fte,
            "total_display": self.total_display, "note": self.note,
        }


# --------------------------------------------------------------------------- #
# Scenario (projected vs actual)
# --------------------------------------------------------------------------- #

@dataclass
class ScenarioComparison:
    enabled: bool = True
    projected: RoiResult = field(default_factory=RoiResult)
    actual: RoiResult = field(default_factory=RoiResult)
    variance_cost: float = 0.0
    variance_pct: float = 0.0
    projected_display: str = ""
    actual_display: str = ""
    variance_display: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled, "projected": self.projected.to_dict(),
            "actual": self.actual.to_dict(), "variance_cost": self.variance_cost,
            "variance_pct": self.variance_pct, "projected_display": self.projected_display,
            "actual_display": self.actual_display, "variance_display": self.variance_display,
            "note": self.note,
        }


# --------------------------------------------------------------------------- #
# Enhancement views
# --------------------------------------------------------------------------- #

@dataclass
class FrameworkRoi:
    name: str = ""
    applications_covered: int = 0
    observations_closed: int = 0
    evidence_reused: int = 0
    emails_avoided: float = 0.0
    hours_saved: float = 0.0
    cost_saved: float = 0.0
    roi_pct: float = 0.0
    roi_contribution_pct: float = 0.0
    cost_saved_display: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name, "applications_covered": self.applications_covered,
            "observations_closed": self.observations_closed,
            "evidence_reused": self.evidence_reused,
            "emails_avoided": self.emails_avoided, "hours_saved": self.hours_saved,
            "cost_saved": self.cost_saved, "roi_pct": self.roi_pct,
            "roi_contribution_pct": self.roi_contribution_pct,
            "cost_saved_display": self.cost_saved_display,
        }


@dataclass
class ReuseValue:
    evidence_submitted: int = 0
    reuse_factor: float = 0.0
    reuse_count: int = 0
    hours_avoided: float = 0.0
    cost_avoided: float = 0.0
    roi_contribution_pct: float = 0.0
    cost_avoided_display: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_submitted": self.evidence_submitted, "reuse_factor": self.reuse_factor,
            "reuse_count": self.reuse_count, "hours_avoided": self.hours_avoided,
            "cost_avoided": self.cost_avoided,
            "roi_contribution_pct": self.roi_contribution_pct,
            "cost_avoided_display": self.cost_avoided_display,
        }


@dataclass
class ObservationValue:
    observations_without_ecs: float = 0.0
    observations_prevented: float = 0.0
    observations_closed: float = 0.0
    hours_saved: float = 0.0
    cost_saved: float = 0.0
    closure_acceleration_pct: float = 0.0
    cost_saved_display: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "observations_without_ecs": self.observations_without_ecs,
            "observations_prevented": self.observations_prevented,
            "observations_closed": self.observations_closed,
            "hours_saved": self.hours_saved, "cost_saved": self.cost_saved,
            "closure_acceleration_pct": self.closure_acceleration_pct,
            "cost_saved_display": self.cost_saved_display,
        }


@dataclass
class EmailValue:
    expected_emails_without_ecs: float = 0.0
    workflow_transactions_in_ecs: float = 0.0
    emails_avoided: float = 0.0
    hours_avoided: float = 0.0
    cost_saved: float = 0.0
    cost_saved_display: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "expected_emails_without_ecs": self.expected_emails_without_ecs,
            "workflow_transactions_in_ecs": self.workflow_transactions_in_ecs,
            "emails_avoided": self.emails_avoided, "hours_avoided": self.hours_avoided,
            "cost_saved": self.cost_saved, "cost_saved_display": self.cost_saved_display,
        }


@dataclass
class AuditorValue:
    manual_audit_hours: float = 0.0
    ecs_audit_hours: float = 0.0
    audit_hours_saved: float = 0.0
    review_effort_reduction_pct: float = 0.0
    closure_acceleration_pct: float = 0.0
    cost_saved: float = 0.0
    cost_saved_display: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "manual_audit_hours": self.manual_audit_hours,
            "ecs_audit_hours": self.ecs_audit_hours,
            "audit_hours_saved": self.audit_hours_saved,
            "review_effort_reduction_pct": self.review_effort_reduction_pct,
            "closure_acceleration_pct": self.closure_acceleration_pct,
            "cost_saved": self.cost_saved, "cost_saved_display": self.cost_saved_display,
        }


@dataclass
class WithoutVsWith:
    """Screen 1 / Screen 7 battle-view metric pair."""
    label: str = ""
    without_ecs: float = 0.0
    with_ecs: float = 0.0
    unit: str = ""
    improvement_pct: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label, "without_ecs": self.without_ecs,
            "with_ecs": self.with_ecs, "unit": self.unit,
            "improvement_pct": self.improvement_pct,
        }


@dataclass
class RoiEvent:
    """A single ROI-impact ticker event."""
    kind: str = ""
    label: str = ""
    cost_impact: float = 0.0
    hours_impact: float = 0.0
    cost_impact_display: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind, "label": self.label, "cost_impact": self.cost_impact,
            "hours_impact": self.hours_impact,
            "cost_impact_display": self.cost_impact_display,
        }


# --------------------------------------------------------------------------- #
# Final executive value pass
# --------------------------------------------------------------------------- #

@dataclass
class WaterfallStep:
    label: str = ""
    value: float = 0.0
    cumulative: float = 0.0
    pct_of_total: float = 0.0
    is_total: bool = False
    value_display: str = ""
    cumulative_display: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label, "value": self.value, "cumulative": self.cumulative,
            "pct_of_total": self.pct_of_total, "is_total": self.is_total,
            "value_display": self.value_display,
            "cumulative_display": self.cumulative_display,
        }


@dataclass
class Waterfall:
    steps: list[WaterfallStep] = field(default_factory=list)
    total: float = 0.0
    total_display: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"steps": [s.to_dict() for s in self.steps], "total": self.total,
                "total_display": self.total_display}


@dataclass
class AgingReduction:
    before_days: float = 0.0
    after_days: float = 0.0
    days_saved: float = 0.0
    reduction_pct: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {"before_days": self.before_days, "after_days": self.after_days,
                "days_saved": self.days_saved, "reduction_pct": self.reduction_pct}


@dataclass
class RolloutPoint:
    applications: int = 0
    roi_pct: float = 0.0
    cost_savings: float = 0.0
    hours_saved: float = 0.0
    emails_avoided: float = 0.0
    fte_equivalent: float = 0.0
    cost_savings_display: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "applications": self.applications, "roi_pct": self.roi_pct,
            "cost_savings": self.cost_savings, "hours_saved": self.hours_saved,
            "emails_avoided": self.emails_avoided, "fte_equivalent": self.fte_equivalent,
            "cost_savings_display": self.cost_savings_display,
        }


@dataclass
class RolloutSimulator:
    points: list[RolloutPoint] = field(default_factory=list)
    default_index: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"points": [p.to_dict() for p in self.points],
                "default_index": self.default_index}


@dataclass
class TakeawayCard:
    key: str = ""
    title: str = ""
    value: str = ""
    sub: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"key": self.key, "title": self.title, "value": self.value,
                "sub": self.sub}


@dataclass
class ExecutiveTakeaways:
    cards: list[TakeawayCard] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"cards": [c.to_dict() for c in self.cards]}
