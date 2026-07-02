"""Evidence Analytics & Observation Assist Foundation (Phase 5.5).

A deterministic, NON-LLM suite of auditor-productivity analytics that COMPOSE the
Phase 5.4 evidence intelligence engines (app.evidence_intel). Capabilities:

  A. Evidence Timeline Engine        — EVIDENCE_TIMELINE_ENABLED (NEW)
  B. Evidence Difference Engine      — reuses EVIDENCE_CHANGE_DETECTION_ENABLED
  C. Evidence Quality Engine         — reuses SUFFICIENCY_ENGINE_ENABLED
  D. Observation Closure Assistant   — reuses OBSERVATION_READINESS_ENABLED
  E. Evidence Search DSL             — EVIDENCE_SEARCH_DSL_ENABLED (NEW)
  F. Evidence Portfolio Analytics    — EVIDENCE_PORTFOLIO_ENABLED (NEW)

Every engine is disabled by default, read-only, fail-safe, and performs NO DB
writes, NO schema changes, NO LLM/embeddings/vector/RAG, NO RBAC/audit/workflow
changes, and NO dashboard changes. The Phase 5.4 engines are consumed, never
modified.
"""

from __future__ import annotations

from app.evidence_analytics.closure import build_closure_plan, closure_assist_enabled
from app.evidence_analytics.difference import (
    diff_enabled,
    diff_latest_versions,
    diff_snapshots,
)
from app.evidence_analytics.dsl import (
    execute as dsl_execute,
    parse as dsl_parse,
    search_dsl_enabled,
)
from app.evidence_analytics.dtos import (
    ClosureCard,
    DifferenceCard,
    PortfolioCard,
    QualityCard,
    SearchCard,
    TimelineCard,
)
from app.evidence_analytics.models import (
    ClosurePlan,
    DSLCondition,
    DSLQuery,
    DSLResult,
    EventType,
    EvidenceQualityReport,
    EvidenceTimeline,
    PortfolioView,
    QualityBand,
    QualityDimension,
    TimelineEvent,
    VersionDifference,
)
from app.evidence_analytics.portfolio import build_portfolio, portfolio_enabled
from app.evidence_analytics.quality import assess_quality, quality_enabled
from app.evidence_analytics.timeline import (
    build_timeline,
    detect_approval_reversal,
    detect_quality_decline,
    timeline_enabled,
)

__all__ = [
    # enums / models
    "EventType", "QualityBand", "TimelineEvent", "EvidenceTimeline",
    "VersionDifference", "QualityDimension", "EvidenceQualityReport",
    "ClosurePlan", "DSLCondition", "DSLQuery", "DSLResult", "PortfolioView",
    # A timeline
    "timeline_enabled", "build_timeline", "detect_approval_reversal",
    "detect_quality_decline",
    # B difference
    "diff_enabled", "diff_snapshots", "diff_latest_versions",
    # C quality
    "quality_enabled", "assess_quality",
    # D closure
    "closure_assist_enabled", "build_closure_plan",
    # E search dsl
    "search_dsl_enabled", "dsl_parse", "dsl_execute",
    # F portfolio
    "portfolio_enabled", "build_portfolio",
    # dtos
    "TimelineCard", "DifferenceCard", "QualityCard", "ClosureCard",
    "SearchCard", "PortfolioCard",
]
