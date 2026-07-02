"""Evidence Quality Engine (Capability C, Phase 5.5).

Produces a single 0-100 quality report (Green/Amber/Red + reasons) for an evidence
item by COMPOSING Phase 5.4:
  * sufficiency (delegated 5.2-A engine via evidence_intel) — covers freshness,
    completeness, traceability, coverage, approval/review,
  * reuse confidence (evidence_intel.score_reuse),
and adding two analytics-specific dimensions:
  * version_stability  — derived from the version chain (churn / recent major change),
  * source_reliability — from the evidence source_system.

It REUSES the Phase 5.4 flag SUFFICIENCY_ENGINE_ENABLED (no new flag).
Read-only, deterministic, fail-safe.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from app.evidence_analytics._common import (
    clamp,
    load_policy,
    merge_block,
    normalize_weights,
)
from app.evidence_analytics.models import (
    EvidenceQualityReport,
    QualityBand,
    QualityDimension,
)

_DEFAULTS = {
    "weights": {"sufficiency": 0.45, "reuse_confidence": 0.15,
                "version_stability": 0.20, "source_reliability": 0.20},
    "bands": {"green_min": 80, "amber_min": 55},
    "source_reliability_scores": {
        "gitea": 90, "github": 90, "gitlab": 90, "azure_devops": 88, "sonarqube": 92,
        "jenkins": 85, "jira": 80, "confluence": 75, "servicenow": 82,
        "sharepoint": 70, "prisma": 88, "manual": 50, "default": 60,
    },
    "version_penalty_per_extra": 8,
    "major_change_penalty": 25,
}


def quality_enabled() -> bool:
    """Reuses the Phase 5.4 sufficiency flag."""
    try:
        from app.evidence_intel.sufficiency_v2 import sufficiency_enabled
        return sufficiency_enabled()
    except Exception:  # noqa: BLE001
        from app.evidence_analytics._common import flag_enabled
        return flag_enabled("SUFFICIENCY_ENGINE_ENABLED", "sufficiency_enabled")


def _policy() -> dict[str, Any]:
    return merge_block(_DEFAULTS, {"quality": load_policy().get("quality", {})}, "quality")


def _sufficiency_score(evidence: Mapping[str, Any], framework: str,
                       now: datetime) -> tuple[float, str]:
    try:
        from app.evidence_intel.sufficiency_v2 import assess_sufficiency
        a = assess_sufficiency(str(evidence.get("evidence_id", "")), [evidence],
                               framework=framework, now=now, force=True)
        return float(a.score), f"sufficiency {a.band}"
    except Exception:  # noqa: BLE001
        return 0.0, "sufficiency unavailable"


def _reuse_score(evidence: Mapping[str, Any], now: datetime) -> tuple[float, str]:
    try:
        from app.evidence_intel.reuse import score_reuse
        # Self-reuse confidence: how reusable this item is for its own controls.
        r = score_reuse(evidence, evidence, now=now, force=True)
        return float(r.score), f"reuse {r.band}"
    except Exception:  # noqa: BLE001
        return 0.0, "reuse unavailable"


def _version_stability(evidence: Mapping[str, Any], policy: Mapping[str, Any]) -> tuple[float, str]:
    vcount = evidence.get("version_count")
    if vcount is None:
        history = evidence.get("version_history")
        vcount = len(getattr(history, "versions", history) or []) if history else 1
    try:
        vcount = max(1, int(vcount))
    except (TypeError, ValueError):
        vcount = 1
    penalty = float(policy.get("version_penalty_per_extra", 8)) * (vcount - 1)
    last_change = str(evidence.get("last_change_class", "")).lower()
    if last_change == "major":
        penalty += float(policy.get("major_change_penalty", 25))
    score = clamp(100.0 - penalty)
    return score, f"{vcount} version(s)" + (", recent major change" if last_change == "major" else "")


def _source_reliability(evidence: Mapping[str, Any], policy: Mapping[str, Any]) -> tuple[float, str]:
    table = policy.get("source_reliability_scores", {})
    src = str(evidence.get("source_system") or "").strip().lower()
    if not src and not str(evidence.get("url", "")).strip():
        src = "manual"
    score = float(table.get(src, table.get("default", 60)))
    return clamp(score), f"source={src or 'unknown'}"


def assess_quality(evidence: Mapping[str, Any], *, framework: str = "",
                   now: datetime | None = None, force: bool = False) -> EvidenceQualityReport:
    """Compute a composite evidence quality report. Never raises."""
    eid = str(evidence.get("evidence_id", "") or evidence.get("id", "")) \
        if isinstance(evidence, Mapping) else ""
    if not force and not quality_enabled():
        return EvidenceQualityReport(
            evidence_id=eid, enabled=False,
            note="quality disabled (SUFFICIENCY_ENGINE_ENABLED=false)")
    try:
        if not isinstance(evidence, Mapping):
            raise TypeError("evidence must be a mapping")
        now = now or datetime.now(timezone.utc)
        policy = _policy()
        weights = normalize_weights(policy["weights"], list(_DEFAULTS["weights"]))

        suff, suff_detail = _sufficiency_score(evidence, framework, now)
        reuse, reuse_detail = _reuse_score(evidence, now)
        vstab, vstab_detail = _version_stability(evidence, policy)
        srel, srel_detail = _source_reliability(evidence, policy)

        dims = [
            QualityDimension("sufficiency", suff, round(weights.get("sufficiency", 0), 3), suff_detail),
            QualityDimension("reuse_confidence", reuse, round(weights.get("reuse_confidence", 0), 3), reuse_detail),
            QualityDimension("version_stability", vstab, round(weights.get("version_stability", 0), 3), vstab_detail),
            QualityDimension("source_reliability", srel, round(weights.get("source_reliability", 0), 3), srel_detail),
        ]
        score = round(sum(d.score * weights.get(d.name, 0.0) for d in dims), 1)

        bands = policy["bands"]
        if score >= float(bands.get("green_min", 80)):
            band = QualityBand.GREEN
        elif score >= float(bands.get("amber_min", 55)):
            band = QualityBand.AMBER
        else:
            band = QualityBand.RED

        reasons = [f"{d.name}: {d.score} ({d.detail})" for d in dims]
        return EvidenceQualityReport(evidence_id=eid, enabled=True, score=score,
                                     band=band.value, dimensions=dims, reasons=reasons)
    except Exception as exc:  # noqa: BLE001 - fail safe
        return EvidenceQualityReport(evidence_id=eid, enabled=False,
                                     note=f"quality error (ignored): {type(exc).__name__}")
