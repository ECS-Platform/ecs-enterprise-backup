"""Evidence Intelligence Foundation (Phase 5.4).

A deterministic, NON-LLM suite of read-only engines over ECS evidence and
observation metadata:

  * Versioning      — immutable EvidenceVersion chains (EVIDENCE_VERSIONING_ENABLED)
  * Lineage         — Framework→Control→Observation→Evidence→Version graph
                      (EVIDENCE_LINEAGE_ENABLED)
  * Sufficiency V2  — aggregation delegating to the Phase 5.2-A engine
                      (reuses SUFFICIENCY_ENGINE_ENABLED)
  * Closure readiness (OBSERVATION_READINESS_ENABLED)
  * Reuse scoring   (EVIDENCE_REUSE_SCORING_ENABLED)
  * Change detection (EVIDENCE_CHANGE_DETECTION_ENABLED)
  * Query engine    (EVIDENCE_QUERY_ENABLED)

Every engine is disabled by default, read-only, fail-safe, and performs NO DB
writes, NO schema changes, NO LLM/embeddings/vector/RAG, and NO dashboard changes.
"""

from __future__ import annotations

from app.evidence_intel.change import assess_change, change_detection_enabled
from app.evidence_intel.dtos import (
    EvidenceChangeCard,
    EvidenceLineageCard,
    EvidenceVersionCard,
    QueryResultCard,
    ReadinessCard,
    ReuseCard,
    SufficiencyCard,
)
from app.evidence_intel.lineage import (
    ancestors,
    build_lineage_graph,
    descendants,
    impact_analysis,
    lineage_enabled,
    summarize,
)
from app.evidence_intel.models import (
    Band,
    ChangeClass,
    EvidenceChangeAssessment,
    EvidenceStatus,
    EvidenceVersion,
    EvidenceVersionHistory,
    FieldChange,
    LineageGraph,
    LineageNode,
    LineageRecord,
    LineageSummary,
    ObservationClosureAssessment,
    QueryResult,
    ReadinessLevel,
    ReuseBand,
    ReuseScore,
    SufficiencyAssessment,
    SufficiencyResult,
    SufficiencyRule,
)
from app.evidence_intel.query import aggregate, query_enabled, query_evidence
from app.evidence_intel.readiness import (
    assess_closure_readiness,
    observation_readiness_enabled,
)
from app.evidence_intel.reuse import reuse_scoring_enabled, score_reuse
from app.evidence_intel.sufficiency_v2 import assess_sufficiency, sufficiency_enabled
from app.evidence_intel.versioning import (
    build_version_history,
    compute_hash,
    get_version,
    latest_version,
    next_version,
    versioning_enabled,
)

__all__ = [
    # enums
    "Band", "ReadinessLevel", "ReuseBand", "ChangeClass", "EvidenceStatus",
    # models
    "EvidenceVersion", "EvidenceVersionHistory", "LineageNode", "LineageRecord",
    "LineageGraph", "LineageSummary", "SufficiencyRule", "SufficiencyResult",
    "SufficiencyAssessment", "ObservationClosureAssessment", "ReuseScore",
    "FieldChange", "EvidenceChangeAssessment", "QueryResult",
    # versioning
    "versioning_enabled", "build_version_history", "latest_version", "get_version",
    "next_version", "compute_hash",
    # lineage
    "lineage_enabled", "build_lineage_graph", "ancestors", "descendants",
    "impact_analysis", "summarize",
    # sufficiency v2
    "sufficiency_enabled", "assess_sufficiency",
    # readiness
    "observation_readiness_enabled", "assess_closure_readiness",
    # reuse
    "reuse_scoring_enabled", "score_reuse",
    # change
    "change_detection_enabled", "assess_change",
    # query
    "query_enabled", "query_evidence", "aggregate",
    # DTOs
    "EvidenceVersionCard", "EvidenceLineageCard", "SufficiencyCard", "ReadinessCard",
    "ReuseCard", "EvidenceChangeCard", "QueryResultCard",
]
