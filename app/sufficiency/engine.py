"""Evidence Sufficiency Engine (Phase 5.2-A) — read-only composite scorer.

Computes a single deterministic 0-100 quality/sufficiency score per evidence item
from five sub-scores (completeness, freshness, traceability, coverage, review),
using SufficiencyRules. It is:

  * READ-ONLY      : never mutates evidence, DB, RAG, or workflow state.
  * NO-LLM         : pure arithmetic over already-captured metadata.
  * FLAG-GATED     : disabled by default (SUFFICIENCY_ENGINE_ENABLED / config).
    When disabled, calculate_evidence_score() returns a neutral result marked
    enabled=False and computes nothing — preserving existing ECS behavior.
  * FAIL-SAFE      : any internal error yields a neutral, enabled=False result;
    it must never raise into a caller.

This module deliberately performs NO database, RAG, network, or LLM imports.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

from app.sufficiency.rules import DimensionResult, SufficiencyRules

_TRUTHY = {"1", "true", "yes", "on"}


# --------------------------------------------------------------------------- #
# Data structures
# --------------------------------------------------------------------------- #

@dataclass
class EvidenceScoreBreakdown:
    """Per-dimension sub-scores and their weighted contributions."""

    completeness: float = 0.0
    freshness: float = 0.0
    traceability: float = 0.0
    coverage: float = 0.0
    review: float = 0.0
    weights: dict[str, float] = field(default_factory=dict)
    contributions: dict[str, float] = field(default_factory=dict)
    reasons: dict[str, list[str]] = field(default_factory=dict)
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "completeness": self.completeness,
            "freshness": self.freshness,
            "traceability": self.traceability,
            "coverage": self.coverage,
            "review": self.review,
            "weights": dict(self.weights),
            "contributions": dict(self.contributions),
            "reasons": {k: list(v) for k, v in self.reasons.items()},
            "detail": dict(self.detail),
        }


@dataclass
class EvidenceScore:
    """The composite sufficiency score for one evidence item."""

    score: float = 0.0
    band: str = "Not Ready"
    enabled: bool = False
    evidence_uid: str = ""
    breakdown: EvidenceScoreBreakdown = field(default_factory=EvidenceScoreBreakdown)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "band": self.band,
            "enabled": self.enabled,
            "evidence_uid": self.evidence_uid,
            "breakdown": self.breakdown.to_dict(),
            "note": self.note,
        }


# --------------------------------------------------------------------------- #
# Feature flag + policy loading
# --------------------------------------------------------------------------- #

def _env_flag(name: str) -> bool | None:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return None
    return raw.strip().lower() in _TRUTHY


def _load_policy() -> dict[str, Any]:
    """Load the 'sufficiency' policy block from config, tolerating absence."""
    try:
        from ecs_platform.config.loader import load_config

        cfg = load_config("sufficiency") or {}
        block = cfg.get("sufficiency", cfg)
        return block if isinstance(block, dict) else {}
    except Exception:  # noqa: BLE001 - config must never break scoring
        return {}


def sufficiency_engine_enabled() -> bool:
    """Master gate. Env SUFFICIENCY_ENGINE_ENABLED wins; else config; else False."""
    env = _env_flag("SUFFICIENCY_ENGINE_ENABLED")
    if env is not None:
        return env
    policy = _load_policy()
    val = policy.get("enabled", False)
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in _TRUTHY
    return False


def get_rules() -> SufficiencyRules:
    """Build a SufficiencyRules from the current config policy (defaults if absent)."""
    return SufficiencyRules(_load_policy())


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def calculate_evidence_score(
    evidence: Mapping[str, Any],
    *,
    rules: SufficiencyRules | None = None,
    now: datetime | None = None,
    force: bool = False,
) -> EvidenceScore:
    """Compute the composite sufficiency score for one evidence item.

    Returns a neutral, ``enabled=False`` result (no scoring) when the engine is
    disabled, unless ``force=True`` (used by tests / explicit on-demand scoring).
    Never raises.
    """
    uid = ""
    try:
        uid = str(evidence.get("evidence_uid", "") or evidence.get("uid", "") or "")
    except Exception:  # noqa: BLE001
        uid = ""

    if not force and not sufficiency_engine_enabled():
        return EvidenceScore(
            score=0.0, band="Not Ready", enabled=False, evidence_uid=uid,
            note="sufficiency engine disabled (SUFFICIENCY_ENGINE_ENABLED=false)",
        )

    try:
        rules = rules or get_rules()
        now = now or datetime.now(timezone.utc)
        if not isinstance(evidence, Mapping):
            raise TypeError("evidence must be a mapping")

        dims: dict[str, DimensionResult] = rules.score_all(evidence, now=now)
        weights = rules.normalized_weights()

        contributions: dict[str, float] = {}
        composite = 0.0
        for name, result in dims.items():
            w = float(weights.get(name, 0.0))
            contribution = round(result.score * w, 2)
            contributions[name] = contribution
            composite += result.score * w

        composite = round(composite, 1)
        breakdown = EvidenceScoreBreakdown(
            completeness=dims["completeness"].score,
            freshness=dims["freshness"].score,
            traceability=dims["traceability"].score,
            coverage=dims["coverage"].score,
            review=dims["review"].score,
            weights={k: round(v, 4) for k, v in weights.items()},
            contributions=contributions,
            reasons={name: result.reasons for name, result in dims.items()},
            detail={name: result.detail for name, result in dims.items()},
        )
        return EvidenceScore(
            score=composite, band=rules.band(composite), enabled=True,
            evidence_uid=uid, breakdown=breakdown,
        )
    except Exception as exc:  # noqa: BLE001 - fail safe, never break callers
        return EvidenceScore(
            score=0.0, band="Not Ready", enabled=False, evidence_uid=uid,
            note=f"sufficiency scoring error (ignored): {type(exc).__name__}",
        )


def explain_score(
    evidence: Mapping[str, Any],
    *,
    rules: SufficiencyRules | None = None,
    now: datetime | None = None,
    force: bool = True,
) -> dict[str, Any]:
    """Return a structured, human-readable explanation of an evidence score.

    Defaults ``force=True`` so explanations are available on demand even when the
    engine gate is off (explanation is read-only and has no side effects).
    """
    score = calculate_evidence_score(evidence, rules=rules, now=now, force=force)
    lines: list[str] = []
    bd = score.breakdown
    if not score.enabled and score.note:
        lines.append(score.note)
    else:
        lines.append(f"Composite sufficiency score: {score.score}/100 ({score.band})")
        order = ["completeness", "freshness", "traceability", "coverage", "review"]
        for dim in order:
            sub = getattr(bd, dim)
            weight = bd.weights.get(dim, 0.0)
            contrib = bd.contributions.get(dim, 0.0)
            lines.append(
                f"  - {dim}: {sub}/100 (weight {weight:.0%}, contributes {contrib})")
            for reason in bd.reasons.get(dim, []):
                lines.append(f"      • {reason}")
    return {
        "evidence_uid": score.evidence_uid,
        "enabled": score.enabled,
        "score": score.score,
        "band": score.band,
        "summary": "\n".join(lines),
        "breakdown": bd.to_dict(),
    }


def calculate_scores(
    evidence_items: list[Mapping[str, Any]],
    *,
    rules: SufficiencyRules | None = None,
    now: datetime | None = None,
    force: bool = False,
) -> list[EvidenceScore]:
    """Score a batch of evidence items (read-only). Reuses one rules instance."""
    rules = rules or get_rules()
    now = now or datetime.now(timezone.utc)
    return [
        calculate_evidence_score(ev, rules=rules, now=now, force=force)
        for ev in evidence_items
    ]
