"""Dashboard DTOs (Phase 8 of 5.4).

Reusable, presentation-ready cards built FROM the evidence-intelligence
assessments. Pure data — no I/O, no rendering, and NO modification to any existing
dashboard. They let a future UI render evidence intelligence without recomputation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.evidence_intel.models import (
    EvidenceChangeAssessment,
    EvidenceVersionHistory,
    LineageGraph,
    LineageSummary,
    ObservationClosureAssessment,
    QueryResult,
    ReuseScore,
    SufficiencyAssessment,
)


@dataclass
class EvidenceVersionCard:
    evidence_id: str = ""
    version_count: int = 0
    latest_version: int | None = None
    latest_status: str = ""
    latest_at: str = ""
    history: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_history(cls, h: EvidenceVersionHistory) -> "EvidenceVersionCard":
        latest = h.latest
        return cls(evidence_id=h.evidence_id, version_count=len(h.versions),
                   latest_version=latest.version_number if latest else None,
                   latest_status=latest.evidence_status if latest else "",
                   latest_at=latest.created_at if latest else "",
                   history=[v.to_dict() for v in h.versions])

    def to_dict(self) -> dict[str, Any]:
        return {"evidence_id": self.evidence_id, "version_count": self.version_count,
                "latest_version": self.latest_version, "latest_status": self.latest_status,
                "latest_at": self.latest_at, "history": list(self.history)}


@dataclass
class EvidenceLineageCard:
    root_key: str = ""
    node_count: int = 0
    edge_count: int = 0
    frameworks: list[str] = field(default_factory=list)
    controls: list[str] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    versions: list[str] = field(default_factory=list)

    @classmethod
    def from_graph(cls, graph: LineageGraph, summary: LineageSummary | None = None
                   ) -> "EvidenceLineageCard":
        s = summary or LineageSummary()
        return cls(root_key=s.root_key, node_count=len(graph.nodes),
                   edge_count=len(graph.edges), frameworks=list(s.frameworks),
                   controls=list(s.controls), observations=list(s.observations),
                   evidence=list(s.evidence), versions=list(s.versions))

    def to_dict(self) -> dict[str, Any]:
        return {"root_key": self.root_key, "node_count": self.node_count,
                "edge_count": self.edge_count, "frameworks": self.frameworks,
                "controls": self.controls, "observations": self.observations,
                "evidence": self.evidence, "versions": self.versions}


@dataclass
class SufficiencyCard:
    subject: str = ""
    score: float = 0.0
    band: str = ""
    evidence_count: int = 0
    enabled: bool = False
    dimensions: dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_assessment(cls, a: SufficiencyAssessment) -> "SufficiencyCard":
        return cls(subject=a.subject, score=a.score, band=a.band,
                   evidence_count=a.evidence_count, enabled=a.enabled,
                   dimensions={r.dimension: r.score for r in a.results})

    def to_dict(self) -> dict[str, Any]:
        return {"subject": self.subject, "score": self.score, "band": self.band,
                "evidence_count": self.evidence_count, "enabled": self.enabled,
                "dimensions": dict(self.dimensions)}


@dataclass
class ReadinessCard:
    observation_id: str = ""
    score: float = 0.0
    level: str = ""
    enabled: bool = False
    blocking: list[str] = field(default_factory=list)
    factors: dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_assessment(cls, a: ObservationClosureAssessment) -> "ReadinessCard":
        return cls(observation_id=a.observation_id, score=a.score, level=a.level,
                   enabled=a.enabled, blocking=list(a.blocking), factors=dict(a.factors))

    def to_dict(self) -> dict[str, Any]:
        return {"observation_id": self.observation_id, "score": self.score,
                "level": self.level, "enabled": self.enabled,
                "blocking": self.blocking, "factors": self.factors}


@dataclass
class ReuseCard:
    source_id: str = ""
    candidate_id: str = ""
    score: float = 0.0
    band: str = ""
    enabled: bool = False
    factors: dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_score(cls, r: ReuseScore) -> "ReuseCard":
        return cls(source_id=r.source_id, candidate_id=r.candidate_id, score=r.score,
                   band=r.band, enabled=r.enabled, factors=dict(r.factors))

    def to_dict(self) -> dict[str, Any]:
        return {"source_id": self.source_id, "candidate_id": self.candidate_id,
                "score": self.score, "band": self.band, "enabled": self.enabled,
                "factors": self.factors}


@dataclass
class EvidenceChangeCard:
    evidence_id: str = ""
    change_class: str = ""
    enabled: bool = False
    summary: str = ""
    changed_fields: list[str] = field(default_factory=list)

    @classmethod
    def from_assessment(cls, a: EvidenceChangeAssessment) -> "EvidenceChangeCard":
        return cls(evidence_id=a.evidence_id, change_class=a.change_class,
                   enabled=a.enabled, summary=a.summary,
                   changed_fields=[c.field_name for c in a.changes])

    def to_dict(self) -> dict[str, Any]:
        return {"evidence_id": self.evidence_id, "change_class": self.change_class,
                "enabled": self.enabled, "summary": self.summary,
                "changed_fields": list(self.changed_fields)}


@dataclass
class QueryResultCard:
    total: int = 0
    enabled: bool = False
    filters: dict[str, Any] = field(default_factory=dict)
    aggregations: dict[str, dict[str, int]] = field(default_factory=dict)
    timeline: list[dict[str, Any]] = field(default_factory=list)
    sample_rows: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_result(cls, r: QueryResult, *, sample: int = 10) -> "QueryResultCard":
        return cls(total=r.total, enabled=r.enabled, filters=dict(r.filters),
                   aggregations=dict(r.aggregations), timeline=list(r.timeline),
                   sample_rows=[dict(x) for x in r.rows[:sample]])

    def to_dict(self) -> dict[str, Any]:
        return {"total": self.total, "enabled": self.enabled, "filters": self.filters,
                "aggregations": self.aggregations, "timeline": self.timeline,
                "sample_rows": self.sample_rows}
