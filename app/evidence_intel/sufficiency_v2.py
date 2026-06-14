"""Sufficiency Engine V2 — aggregation layer (Phase 3 of 5.4).

This is NOT a second sufficiency engine. It is a deterministic aggregation /
orchestration layer that scores an OBSERVATION or CONTROL by:

  * delegating per-evidence-item scoring to the existing Phase 5.2-A engine
    (app.sufficiency.calculate_evidence_score), then
  * combining that with control/observation-level signals: evidence count,
    mandatory evidence types present, approval state, and recency.

It REUSES the existing SUFFICIENCY_ENGINE_ENABLED flag (no new flag, no second
engine). Read-only, no LLM, fail-safe.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from app.evidence_intel._common import clamp, load_policy, merge_block, normalize_weights
from app.evidence_intel.models import (
    Band,
    SufficiencyAssessment,
    SufficiencyResult,
    SufficiencyRule,
)

_DEFAULTS = {
    "weights": {"item_quality": 0.35, "evidence_count": 0.15, "mandatory_types": 0.20,
                "approval_state": 0.15, "recency": 0.15},
    "bands": {"green_min": 80, "amber_min": 55},
    "target_evidence_count": 3,
    "mandatory_types_by_framework": {
        "pci-dss": ["policy", "quality_gate", "test_result"],
        "iso27001": ["policy", "document"],
        "rbi-csf": ["policy", "document", "quality_gate"],
        "soc2": ["pull_request", "quality_gate"],
        "default": ["policy"],
    },
}

_APPROVED = {"approved", "auditor approved"}
_FRESH_OK = {"approved", "collected", "underreview", "submitted for review", "uploaded"}


def sufficiency_enabled() -> bool:
    """Reuses the Phase 5.2-A flag. Env wins, then config, then False."""
    try:
        from app.sufficiency.engine import sufficiency_engine_enabled
        return sufficiency_engine_enabled()
    except Exception:  # noqa: BLE001
        from app.evidence_intel._common import flag_enabled
        return flag_enabled("SUFFICIENCY_ENGINE_ENABLED", "sufficiency_enabled")


def _policy() -> dict[str, Any]:
    return merge_block(_DEFAULTS, {"sufficiency": load_policy().get("sufficiency", {})},
                       "sufficiency")


def _item_scores(evidence_items: Sequence[Mapping[str, Any]]) -> list[float]:
    """Delegate per-item scoring to the 5.2-A engine (force=True for raw scores)."""
    scores: list[float] = []
    try:
        from app.sufficiency.engine import calculate_evidence_score
    except Exception:  # noqa: BLE001
        calculate_evidence_score = None  # type: ignore[assignment]
    for item in evidence_items or []:
        if not isinstance(item, Mapping):
            continue
        if calculate_evidence_score is not None:
            try:
                res = calculate_evidence_score(item, force=True)
                scores.append(float(getattr(res, "score", 0.0)))
                continue
            except Exception:  # noqa: BLE001
                pass
        scores.append(0.0)
    return scores


def _mandatory_types(framework: str, policy: Mapping[str, Any]) -> list[str]:
    table = policy.get("mandatory_types_by_framework", {})
    key = str(framework or "").strip().lower()
    return [t.lower() for t in table.get(key, table.get("default", []))]


def _evidence_type(item: Mapping[str, Any]) -> str:
    for k in ("object_type", "evidence_type", "evidence_category", "type"):
        v = item.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip().lower()
    return ""


def assess_sufficiency(subject: str, evidence_items: Sequence[Mapping[str, Any]], *,
                       framework: str = "", now: datetime | None = None,
                       force: bool = False) -> SufficiencyAssessment:
    """Aggregate sufficiency for an observation/control. Never raises."""
    if not force and not sufficiency_enabled():
        return SufficiencyAssessment(
            subject=subject, enabled=False,
            note="sufficiency engine disabled (SUFFICIENCY_ENGINE_ENABLED=false)")
    try:
        now = now or datetime.now(timezone.utc)
        policy = _policy()
        weights = normalize_weights(policy["weights"], list(_DEFAULTS["weights"]))
        items = [i for i in (evidence_items or []) if isinstance(i, Mapping)]
        count = len(items)

        item_scores = _item_scores(items)
        item_quality = round(sum(item_scores) / len(item_scores), 1) if item_scores else 0.0

        target = max(1, int(policy.get("target_evidence_count", 3)))
        count_score = clamp(100.0 * min(count, target) / target)

        mandatory = _mandatory_types(framework, policy)
        present_types = {_evidence_type(i) for i in items if _evidence_type(i)}
        if mandatory:
            have = [t for t in mandatory if t in present_types]
            mand_score = clamp(100.0 * len(have) / len(mandatory))
            missing = [t for t in mandatory if t not in present_types]
        else:
            mand_score = 100.0
            missing = []

        def _status(i: Mapping[str, Any]) -> str:
            for k in ("review_status", "status", "evidence_status"):
                v = i.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip().lower()
            return ""

        if items:
            from app.evidence_intel._common import parse_dt
            approved = sum(1 for i in items if _status(i) in _APPROVED)
            approval_score = clamp(100.0 * approved / len(items))
            fresh = 0
            for i in items:
                vd = parse_dt(i.get("valid_until"))
                expired = vd is not None and vd < now
                if not expired and (vd is not None or _status(i) in _FRESH_OK):
                    fresh += 1
            recency_score = clamp(100.0 * fresh / len(items))
        else:
            approval_score = 0.0
            recency_score = 0.0

        dim_scores = {
            "item_quality": item_quality, "evidence_count": count_score,
            "mandatory_types": mand_score, "approval_state": approval_score,
            "recency": recency_score,
        }
        composite = round(sum(dim_scores[k] * weights.get(k, 0.0) for k in dim_scores), 1)

        bands = policy["bands"]
        if composite >= float(bands.get("green_min", 80)):
            band = Band.GREEN
        elif composite >= float(bands.get("amber_min", 55)):
            band = Band.AMBER
        else:
            band = Band.RED

        rules = [
            SufficiencyRule("item_quality", round(weights.get("item_quality", 0), 3),
                            item_quality, item_quality >= 55,
                            f"mean per-item 5.2-A score across {count} item(s)"),
            SufficiencyRule("evidence_count", round(weights.get("evidence_count", 0), 3),
                            count_score, count >= target, f"{count}/{target} target items"),
            SufficiencyRule("mandatory_types", round(weights.get("mandatory_types", 0), 3),
                            mand_score, not missing,
                            ("all mandatory types present" if not missing
                             else "missing: " + ", ".join(missing))),
            SufficiencyRule("approval_state", round(weights.get("approval_state", 0), 3),
                            approval_score, approval_score >= 50, "proportion approved"),
            SufficiencyRule("recency", round(weights.get("recency", 0), 3),
                            recency_score, recency_score >= 50, "proportion fresh / not expired"),
        ]
        results = [SufficiencyResult(k, v, "") for k, v in dim_scores.items()]

        return SufficiencyAssessment(
            subject=subject, enabled=True, score=composite, band=band.value,
            evidence_count=count, rules=rules, results=results, item_scores=item_scores)
    except Exception as exc:  # noqa: BLE001 - fail safe
        return SufficiencyAssessment(
            subject=subject, enabled=False,
            note=f"sufficiency aggregation error (ignored): {type(exc).__name__}")
