"""Evidence Sufficiency Engine (Phase 5.2-A).

A read-only, deterministic, no-LLM scoring layer for ECS evidence. Disabled by
default via SUFFICIENCY_ENGINE_ENABLED. This package performs NO database, RAG,
network, or LLM access and never mutates ECS state.

Public surface:
    calculate_evidence_score(evidence) -> EvidenceScore
    explain_score(evidence)            -> dict (human-readable breakdown)
    calculate_scores(items)            -> list[EvidenceScore]
    sufficiency_engine_enabled()       -> bool
    EvidenceScore, EvidenceScoreBreakdown, SufficiencyRules
"""

from __future__ import annotations

from app.sufficiency.engine import (
    EvidenceScore,
    EvidenceScoreBreakdown,
    calculate_evidence_score,
    calculate_scores,
    explain_score,
    get_rules,
    sufficiency_engine_enabled,
)
from app.sufficiency.rules import DimensionResult, SufficiencyRules

__all__ = [
    "EvidenceScore",
    "EvidenceScoreBreakdown",
    "SufficiencyRules",
    "DimensionResult",
    "calculate_evidence_score",
    "calculate_scores",
    "explain_score",
    "get_rules",
    "sufficiency_engine_enabled",
]
