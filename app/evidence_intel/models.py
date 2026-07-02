"""Evidence Intelligence Foundation — domain models (Phase 5.4).

Deterministic, non-LLM dataclasses and enums shared across the evidence
intelligence engines (versioning, lineage, sufficiency V2, closure readiness,
reuse scoring, change detection, query). No network/DB/RAG/LLM imports. All
dataclasses are JSON-serializable via ``to_dict()``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


def _val(v: Any) -> Any:
    return v.value if isinstance(v, Enum) else v


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #

class Band(str, Enum):
    GREEN = "Green"
    AMBER = "Amber"
    RED = "Red"


class ReadinessLevel(str, Enum):
    READY = "Ready"
    NEARLY_READY = "Nearly Ready"
    NOT_READY = "Not Ready"


class ReuseBand(str, Enum):
    HIGH = "High Reuse"
    MEDIUM = "Medium Reuse"
    LOW = "Low Reuse"


class ChangeClass(str, Enum):
    NONE = "None"
    MINOR = "Minor"
    MODERATE = "Moderate"
    MAJOR = "Major"


class EvidenceStatus(str, Enum):
    DRAFT = "Draft"
    COLLECTED = "Collected"
    SUBMITTED = "Submitted"
    UNDER_REVIEW = "UnderReview"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    EXPIRED = "Expired"
    SUPERSEDED = "Superseded"


# --------------------------------------------------------------------------- #
# Phase 1 — Evidence versioning
# --------------------------------------------------------------------------- #

@dataclass
class EvidenceVersion:
    """An immutable point-in-time version of an evidence artifact.

    Canonical fields: ``hash``, ``previous_version``, ``superseded_by``. The
    properties ``content_hash``, ``previous_version_id``, and
    ``superseded_by_version_id`` are stable aliases of these (and are also emitted
    by ``to_dict()``) to satisfy the explicit naming contract.
    """

    evidence_id: str = ""
    version_number: int = 1
    created_at: str = ""
    created_by: str = ""
    hash: str = ""
    previous_version: int | None = None
    superseded_by: int | None = None
    change_reason: str = ""
    evidence_status: str = EvidenceStatus.COLLECTED.value
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def content_hash(self) -> str:
        return self.hash

    @property
    def previous_version_id(self) -> int | None:
        return self.previous_version

    @property
    def superseded_by_version_id(self) -> int | None:
        return self.superseded_by

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "version_number": self.version_number,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "hash": self.hash,
            "content_hash": self.hash,
            "previous_version": self.previous_version,
            "previous_version_id": self.previous_version,
            "superseded_by": self.superseded_by,
            "superseded_by_version_id": self.superseded_by,
            "change_reason": self.change_reason,
            "evidence_status": _val(self.evidence_status),
            "metadata": dict(self.metadata),
        }


@dataclass
class EvidenceVersionHistory:
    evidence_id: str = ""
    versions: list[EvidenceVersion] = field(default_factory=list)

    @property
    def latest(self) -> EvidenceVersion | None:
        return self.versions[-1] if self.versions else None

    def to_dict(self) -> dict[str, Any]:
        return {"evidence_id": self.evidence_id,
                "version_count": len(self.versions),
                "latest_version": self.latest.version_number if self.latest else None,
                "versions": [v.to_dict() for v in self.versions]}


# --------------------------------------------------------------------------- #
# Phase 2 — Lineage
# --------------------------------------------------------------------------- #

@dataclass
class LineageNode:
    node_type: str = ""   # framework | control | observation | evidence | version
    node_id: str = ""
    label: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> str:
        return f"{self.node_type}:{self.node_id}"

    def to_dict(self) -> dict[str, Any]:
        return {"node_type": self.node_type, "node_id": self.node_id,
                "label": self.label, "key": self.key,
                "attributes": dict(self.attributes)}


@dataclass
class LineageRecord:
    """A directed edge parent -> child in the lineage graph."""

    parent_type: str = ""
    parent_id: str = ""
    child_type: str = ""
    child_id: str = ""
    relation: str = "contains"

    @property
    def parent_key(self) -> str:
        return f"{self.parent_type}:{self.parent_id}"

    @property
    def child_key(self) -> str:
        return f"{self.child_type}:{self.child_id}"

    def to_dict(self) -> dict[str, Any]:
        return {"parent_type": self.parent_type, "parent_id": self.parent_id,
                "child_type": self.child_type, "child_id": self.child_id,
                "relation": self.relation, "parent_key": self.parent_key,
                "child_key": self.child_key}


@dataclass
class LineageGraph:
    nodes: dict[str, LineageNode] = field(default_factory=dict)
    edges: list[LineageRecord] = field(default_factory=list)
    enabled: bool = False
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"enabled": self.enabled, "note": self.note,
                "node_count": len(self.nodes), "edge_count": len(self.edges),
                "nodes": [n.to_dict() for n in self.nodes.values()],
                "edges": [e.to_dict() for e in self.edges]}


@dataclass
class LineageSummary:
    root_key: str = ""
    frameworks: list[str] = field(default_factory=list)
    controls: list[str] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    versions: list[str] = field(default_factory=list)
    ancestor_count: int = 0
    descendant_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"root_key": self.root_key, "frameworks": list(self.frameworks),
                "controls": list(self.controls), "observations": list(self.observations),
                "evidence": list(self.evidence), "versions": list(self.versions),
                "ancestor_count": self.ancestor_count,
                "descendant_count": self.descendant_count}


# --------------------------------------------------------------------------- #
# Phase 3 — Sufficiency V2
# --------------------------------------------------------------------------- #

@dataclass
class SufficiencyRule:
    name: str = ""
    weight: float = 0.0
    score: float = 0.0
    passed: bool = False
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "weight": self.weight, "score": self.score,
                "passed": self.passed, "detail": self.detail}


@dataclass
class SufficiencyResult:
    dimension: str = ""
    score: float = 0.0
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"dimension": self.dimension, "score": self.score, "detail": self.detail}


@dataclass
class SufficiencyAssessment:
    subject: str = ""             # observation_id / control_id being assessed
    enabled: bool = False
    score: float = 0.0
    band: str = Band.RED.value
    evidence_count: int = 0
    rules: list[SufficiencyRule] = field(default_factory=list)
    results: list[SufficiencyResult] = field(default_factory=list)
    item_scores: list[float] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"subject": self.subject, "enabled": self.enabled, "score": self.score,
                "band": _val(self.band), "evidence_count": self.evidence_count,
                "rules": [r.to_dict() for r in self.rules],
                "results": [r.to_dict() for r in self.results],
                "item_scores": list(self.item_scores), "note": self.note}


# --------------------------------------------------------------------------- #
# Phase 4 — Observation closure readiness
# --------------------------------------------------------------------------- #

@dataclass
class ObservationClosureAssessment:
    observation_id: str = ""
    enabled: bool = False
    score: float = 0.0
    level: str = ReadinessLevel.NOT_READY.value
    factors: dict[str, float] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)
    blocking: list[str] = field(default_factory=list)
    note: str = ""

    # Explicit named outputs (aliases of score/level/blocking).
    @property
    def readiness_score(self) -> float:
        return self.score

    @property
    def readiness_band(self) -> str:
        return _val(self.level)

    @property
    def blocking_items(self) -> list[str]:
        return list(self.blocking)

    def to_dict(self) -> dict[str, Any]:
        return {"observation_id": self.observation_id, "enabled": self.enabled,
                "score": self.score, "level": _val(self.level),
                "readiness_score": self.score, "readiness_band": _val(self.level),
                "factors": dict(self.factors), "reasons": list(self.reasons),
                "blocking": list(self.blocking), "blocking_items": list(self.blocking),
                "note": self.note}


# --------------------------------------------------------------------------- #
# Phase 5 — Reuse scoring
# --------------------------------------------------------------------------- #

@dataclass
class ReuseScore:
    source_id: str = ""
    candidate_id: str = ""
    enabled: bool = False
    score: float = 0.0
    band: str = ReuseBand.LOW.value
    factors: dict[str, float] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)
    note: str = ""

    # Explicit named outputs (aliases of score/band + a joined reason string).
    @property
    def reuse_score(self) -> float:
        return self.score

    @property
    def reuse_band(self) -> str:
        return _val(self.band)

    @property
    def reuse_reason(self) -> str:
        return "; ".join(self.reasons)

    def to_dict(self) -> dict[str, Any]:
        return {"source_id": self.source_id, "candidate_id": self.candidate_id,
                "enabled": self.enabled, "score": self.score, "band": _val(self.band),
                "reuse_score": self.score, "reuse_band": _val(self.band),
                "reuse_reason": "; ".join(self.reasons),
                "factors": dict(self.factors), "reasons": list(self.reasons),
                "note": self.note}


# --------------------------------------------------------------------------- #
# Phase 6 — Change detection
# --------------------------------------------------------------------------- #

@dataclass
class FieldChange:
    field_name: str = ""
    old_value: Any = None
    new_value: Any = None
    severity: str = ChangeClass.MINOR.value

    def to_dict(self) -> dict[str, Any]:
        return {"field": self.field_name, "old": self.old_value,
                "new": self.new_value, "severity": _val(self.severity)}


@dataclass
class EvidenceChangeAssessment:
    evidence_id: str = ""
    enabled: bool = False
    change_class: str = ChangeClass.NONE.value
    changes: list[FieldChange] = field(default_factory=list)
    summary: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"evidence_id": self.evidence_id, "enabled": self.enabled,
                "change_class": _val(self.change_class),
                "changes": [c.to_dict() for c in self.changes],
                "summary": self.summary, "note": self.note}


# --------------------------------------------------------------------------- #
# Phase 7 — Query
# --------------------------------------------------------------------------- #

@dataclass
class QueryResult:
    enabled: bool = False
    total: int = 0
    rows: list[dict[str, Any]] = field(default_factory=list)
    aggregations: dict[str, dict[str, int]] = field(default_factory=dict)
    timeline: list[dict[str, Any]] = field(default_factory=list)
    filters: dict[str, Any] = field(default_factory=dict)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"enabled": self.enabled, "total": self.total, "rows": list(self.rows),
                "aggregations": dict(self.aggregations), "timeline": list(self.timeline),
                "filters": dict(self.filters), "note": self.note}
