"""Presentation DTOs for Evidence Analytics (Phase 5.5).

UI-friendly, read-only view objects. These are NOT wired into any route/dashboard
in this phase; they exist so a future read-only surface can render analytics without
re-deriving them. No LLM, no DB, no network.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.evidence_analytics.models import (
    ClosurePlan,
    DSLResult,
    EvidenceQualityReport,
    EvidenceTimeline,
    PortfolioView,
    VersionDifference,
)


@dataclass
class TimelineCard:
    subject: str = ""
    enabled: bool = False
    current_state: str = ""
    event_count: int = 0
    flags: list[str] = field(default_factory=list)

    @classmethod
    def from_timeline(cls, t: EvidenceTimeline) -> "TimelineCard":
        flags = []
        if t.approval_reversed:
            flags.append("approval_reversed")
        if t.quality_declining:
            flags.append("quality_declining")
        return cls(subject=t.subject, enabled=t.enabled, current_state=t.current_state,
                   event_count=len(t.events), flags=flags)

    def to_dict(self) -> dict[str, Any]:
        return {"subject": self.subject, "enabled": self.enabled,
                "current_state": self.current_state, "event_count": self.event_count,
                "flags": list(self.flags)}


@dataclass
class DifferenceCard:
    evidence_id: str = ""
    enabled: bool = False
    change_class: str = "None"
    changed_field_count: int = 0
    summary: str = ""

    @classmethod
    def from_difference(cls, d: VersionDifference) -> "DifferenceCard":
        return cls(evidence_id=d.evidence_id, enabled=d.enabled,
                   change_class=d.change_class, changed_field_count=len(d.changed_fields),
                   summary=d.summary)

    def to_dict(self) -> dict[str, Any]:
        return {"evidence_id": self.evidence_id, "enabled": self.enabled,
                "change_class": self.change_class,
                "changed_field_count": self.changed_field_count, "summary": self.summary}


@dataclass
class QualityCard:
    evidence_id: str = ""
    enabled: bool = False
    score: float = 0.0
    band: str = "Red"
    top_reason: str = ""

    @classmethod
    def from_report(cls, r: EvidenceQualityReport) -> "QualityCard":
        return cls(evidence_id=r.evidence_id, enabled=r.enabled, score=r.score,
                   band=r.band, top_reason=r.reasons[0] if r.reasons else "")

    def to_dict(self) -> dict[str, Any]:
        return {"evidence_id": self.evidence_id, "enabled": self.enabled,
                "score": self.score, "band": self.band, "top_reason": self.top_reason}


@dataclass
class ClosureCard:
    observation_id: str = ""
    enabled: bool = False
    closure_readiness_pct: float = 0.0
    readiness_band: str = ""
    next_action: str = ""

    @classmethod
    def from_plan(cls, p: ClosurePlan) -> "ClosureCard":
        return cls(observation_id=p.observation_id, enabled=p.enabled,
                   closure_readiness_pct=p.closure_readiness_pct,
                   readiness_band=p.readiness_band,
                   next_action=p.recommended_next_actions[0]
                   if p.recommended_next_actions else "")

    def to_dict(self) -> dict[str, Any]:
        return {"observation_id": self.observation_id, "enabled": self.enabled,
                "closure_readiness_pct": self.closure_readiness_pct,
                "readiness_band": self.readiness_band, "next_action": self.next_action}


@dataclass
class SearchCard:
    raw: str = ""
    enabled: bool = False
    valid: bool = False
    total: int = 0
    errors: list[str] = field(default_factory=list)

    @classmethod
    def from_result(cls, r: DSLResult) -> "SearchCard":
        return cls(raw=r.query.raw, enabled=r.enabled, valid=r.query.valid,
                   total=r.total, errors=list(r.query.errors))

    def to_dict(self) -> dict[str, Any]:
        return {"raw": self.raw, "enabled": self.enabled, "valid": self.valid,
                "total": self.total, "errors": list(self.errors)}


@dataclass
class PortfolioCard:
    persona: str = ""
    enabled: bool = False
    evidence_count: int = 0
    coverage_pct: float = 0.0
    reuse_pct: float = 0.0
    staleness_pct: float = 0.0
    closure_forecast_days: float = 0.0

    @classmethod
    def from_view(cls, v: PortfolioView) -> "PortfolioCard":
        return cls(persona=v.persona, enabled=v.enabled, evidence_count=v.evidence_count,
                   coverage_pct=v.coverage_pct, reuse_pct=v.reuse_pct,
                   staleness_pct=v.staleness_pct,
                   closure_forecast_days=v.closure_forecast_days)

    def to_dict(self) -> dict[str, Any]:
        return {"persona": self.persona, "enabled": self.enabled,
                "evidence_count": self.evidence_count, "coverage_pct": self.coverage_pct,
                "reuse_pct": self.reuse_pct, "staleness_pct": self.staleness_pct,
                "closure_forecast_days": self.closure_forecast_days}
