"""Evidence Analytics — domain models (Phase 5.5).

Deterministic, non-LLM dataclasses/enums for the auditor-productivity analytics
that compose the Phase 5.4 evidence intelligence engines. No network/DB/RAG/LLM
imports. JSON-serializable via ``to_dict()``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


def _val(v: Any) -> Any:
    return v.value if isinstance(v, Enum) else v


class QualityBand(str, Enum):
    GREEN = "Green"
    AMBER = "Amber"
    RED = "Red"


class EventType(str, Enum):
    EVIDENCE_CREATED = "evidence_created"
    EVIDENCE_UPDATED = "evidence_updated"
    EVIDENCE_SUBMITTED = "evidence_submitted"
    EVIDENCE_APPROVED = "evidence_approved"
    EVIDENCE_REJECTED = "evidence_rejected"
    EVIDENCE_REOPENED = "evidence_reopened"
    OBSERVATION_CLOSED = "observation_closed"
    OBSERVATION_REOPENED = "observation_reopened"


# --------------------------------------------------------------------------- #
# Capability A — Timeline
# --------------------------------------------------------------------------- #

@dataclass
class TimelineEvent:
    event_type: str = ""
    timestamp: str = ""
    actor: str = ""
    previous_state: str = ""
    new_state: str = ""
    detail: str = ""
    source: str = ""           # "audit_log" | "workflow_history" | "version" | "observation"

    def to_dict(self) -> dict[str, Any]:
        return {"event_type": _val(self.event_type), "timestamp": self.timestamp,
                "actor": self.actor, "previous_state": self.previous_state,
                "new_state": self.new_state, "detail": self.detail, "source": self.source}


@dataclass
class EvidenceTimeline:
    subject: str = ""
    enabled: bool = False
    current_state: str = ""
    previous_state: str = ""
    events: list[TimelineEvent] = field(default_factory=list)
    approval_reversed: bool = False
    quality_declining: bool = False
    note: str = ""

    @property
    def change_history(self) -> list[TimelineEvent]:
        return list(self.events)

    def to_dict(self) -> dict[str, Any]:
        return {"subject": self.subject, "enabled": self.enabled,
                "current_state": self.current_state, "previous_state": self.previous_state,
                "events": [e.to_dict() for e in self.events],
                "change_history": [e.to_dict() for e in self.events],
                "approval_reversed": self.approval_reversed,
                "quality_declining": self.quality_declining, "note": self.note}


# --------------------------------------------------------------------------- #
# Capability B — Difference (version N vs N-1)
# --------------------------------------------------------------------------- #

@dataclass
class VersionDifference:
    evidence_id: str = ""
    enabled: bool = False
    from_version: int | None = None
    to_version: int | None = None
    change_class: str = "None"
    changed_fields: list[str] = field(default_factory=list)
    summary: str = ""
    changes: list[dict[str, Any]] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"evidence_id": self.evidence_id, "enabled": self.enabled,
                "from_version": self.from_version, "to_version": self.to_version,
                "change_class": self.change_class, "changed_fields": list(self.changed_fields),
                "summary": self.summary, "changes": list(self.changes), "note": self.note}


# --------------------------------------------------------------------------- #
# Capability C — Quality
# --------------------------------------------------------------------------- #

@dataclass
class QualityDimension:
    name: str = ""
    score: float = 0.0
    weight: float = 0.0
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "score": self.score, "weight": self.weight,
                "detail": self.detail}


@dataclass
class EvidenceQualityReport:
    evidence_id: str = ""
    enabled: bool = False
    score: float = 0.0
    band: str = QualityBand.RED.value
    dimensions: list[QualityDimension] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"evidence_id": self.evidence_id, "enabled": self.enabled,
                "score": self.score, "band": _val(self.band),
                "dimensions": [d.to_dict() for d in self.dimensions],
                "reasons": list(self.reasons), "note": self.note}


# --------------------------------------------------------------------------- #
# Capability D — Closure plan
# --------------------------------------------------------------------------- #

@dataclass
class ClosurePlan:
    observation_id: str = ""
    enabled: bool = False
    closure_readiness_pct: float = 0.0
    readiness_band: str = ""
    blocking_items: list[str] = field(default_factory=list)
    recommended_next_actions: list[str] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"observation_id": self.observation_id, "enabled": self.enabled,
                "closure_readiness_pct": self.closure_readiness_pct,
                "readiness_band": self.readiness_band,
                "blocking_items": list(self.blocking_items),
                "recommended_next_actions": list(self.recommended_next_actions),
                "note": self.note}


# --------------------------------------------------------------------------- #
# Capability E — Search DSL
# --------------------------------------------------------------------------- #

@dataclass
class DSLCondition:
    field_name: str = ""
    operator: str = "="
    value: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {"field": self.field_name, "operator": self.operator, "value": self.value}


@dataclass
class DSLQuery:
    raw: str = ""
    valid: bool = False
    conditions: list[DSLCondition] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"raw": self.raw, "valid": self.valid,
                "conditions": [c.to_dict() for c in self.conditions],
                "errors": list(self.errors)}


@dataclass
class DSLResult:
    enabled: bool = False
    query: DSLQuery = field(default_factory=DSLQuery)
    total: int = 0
    rows: list[dict[str, Any]] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"enabled": self.enabled, "query": self.query.to_dict(),
                "total": self.total, "rows": list(self.rows), "note": self.note}


# --------------------------------------------------------------------------- #
# Capability F — Portfolio analytics
# --------------------------------------------------------------------------- #

@dataclass
class PortfolioView:
    persona: str = ""
    scope_label: str = ""
    enabled: bool = False
    evidence_count: int = 0
    coverage_pct: float = 0.0
    reuse_pct: float = 0.0
    staleness_pct: float = 0.0
    approval_sla_pct: float = 0.0
    observation_count: int = 0
    observations_ready: int = 0
    closure_forecast_days: float = 0.0
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"persona": self.persona, "scope_label": self.scope_label,
                "enabled": self.enabled, "evidence_count": self.evidence_count,
                "coverage_pct": self.coverage_pct, "reuse_pct": self.reuse_pct,
                "staleness_pct": self.staleness_pct, "approval_sla_pct": self.approval_sla_pct,
                "observation_count": self.observation_count,
                "observations_ready": self.observations_ready,
                "closure_forecast_days": self.closure_forecast_days, "note": self.note}
