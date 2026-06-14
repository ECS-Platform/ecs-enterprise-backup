"""Readiness scoring + risk classification (Phase 5.3).

Deterministic. Turns per-category assessment outcomes into:
  * a weighted ReadinessScore (0-100) with a Green/Amber/Red status, and
  * a RiskClassification (Low/Medium/High/Critical) based on weighted gaps.

UNKNOWN outcomes (e.g. offline live checks) are treated as NEUTRAL so an offline
assessment is never unfairly penalized — they neither add nor remove readiness in
the category that is purely a live check, falling back to configuration signals.
"""

from __future__ import annotations

from typing import Any, Mapping

from app.connectivity.models import (
    Outcome,
    ReadinessScore,
    ReadinessStatus,
    RiskClassification,
    RiskLevel,
)

DEFAULT_WEIGHTS = {
    "connectivity": 0.30, "authentication": 0.25, "tls": 0.15,
    "discovery": 0.20, "configuration": 0.10,
}
DEFAULT_BANDS = {"green_min": 80, "amber_min": 55}

DEFAULT_RISK = {
    "critical_min": 75, "high_min": 50, "medium_min": 25,
    "gap_weights": {"connectivity": 0.35, "authentication": 0.30,
                    "discovery": 0.25, "configuration": 0.10},
}

# Outcome -> 0-100 contribution for a category whose score is outcome-only.
_OUTCOME_SCORE = {
    Outcome.PASS: 100.0,
    Outcome.WARNING: 60.0,
    Outcome.FAIL: 0.0,
    Outcome.UNKNOWN: None,   # neutral -> excluded from connectivity blend
}


def _normalize(weights: Mapping[str, float]) -> dict[str, float]:
    w = {k: float(v) for k, v in weights.items() if isinstance(v, (int, float)) and v >= 0}
    total = sum(w.values())
    if total <= 0:
        keys = list(DEFAULT_WEIGHTS)
        return {k: 1.0 / len(keys) for k in keys}
    return {k: v / total for k, v in w.items()}


def connectivity_category_score(dns_outcome: Outcome, net_outcome: Outcome,
                                tls_outcome: Outcome | None = None) -> float:
    """Blend DNS + network (+ optional tls) outcomes; UNKNOWN excluded as neutral."""
    parts = []
    for outc in (dns_outcome, net_outcome):
        val = _OUTCOME_SCORE.get(outc)
        if val is not None:
            parts.append(val)
    if not parts:
        # All live checks unknown (offline) -> neutral mid score.
        return 50.0
    return round(sum(parts) / len(parts), 1)


def calculate_readiness(category_scores: Mapping[str, float], *,
                        weights: Mapping[str, float] | None = None,
                        bands: Mapping[str, Any] | None = None) -> ReadinessScore:
    """Compute the weighted readiness score + Green/Amber/Red status."""
    w = _normalize(weights or DEFAULT_WEIGHTS)
    bands = {**DEFAULT_BANDS, **(bands or {})}

    composite = 0.0
    for cat, weight in w.items():
        composite += float(category_scores.get(cat, 0.0)) * weight
    composite = round(composite, 1)

    if composite >= float(bands["green_min"]):
        status = ReadinessStatus.GREEN
    elif composite >= float(bands["amber_min"]):
        status = ReadinessStatus.AMBER
    else:
        status = ReadinessStatus.RED

    return ReadinessScore(score=composite, status=status,
                          category_scores={k: round(float(category_scores.get(k, 0.0)), 1) for k in w},
                          weights={k: round(v, 4) for k, v in w.items()})


def classify_risk(category_scores: Mapping[str, float], *,
                  risk_config: Mapping[str, Any] | None = None) -> RiskClassification:
    """Classify onboarding risk from category gaps (100 - score per category)."""
    cfg = {**DEFAULT_RISK, **(risk_config or {})}
    gap_weights = _normalize(cfg.get("gap_weights", DEFAULT_RISK["gap_weights"]))

    factors: dict[str, float] = {}
    reasons: list[str] = []
    gap_score = 0.0
    for cat, weight in gap_weights.items():
        score = float(category_scores.get(cat, 0.0))
        gap = max(0.0, 100.0 - score)
        factors[cat] = round(gap, 1)
        gap_score += gap * weight
        if gap >= 50:
            reasons.append(f"{cat} gap {round(gap)}%")
    gap_score = round(gap_score, 1)

    if gap_score >= float(cfg["critical_min"]):
        level = RiskLevel.CRITICAL
    elif gap_score >= float(cfg["high_min"]):
        level = RiskLevel.HIGH
    elif gap_score >= float(cfg["medium_min"]):
        level = RiskLevel.MEDIUM
    else:
        level = RiskLevel.LOW

    if not reasons:
        reasons.append("no significant onboarding gaps")
    return RiskClassification(level=level, gap_score=gap_score, factors=factors, reasons=reasons)
