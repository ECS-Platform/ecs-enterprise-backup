"""Evidence reuse scoring (Phase 5 of 5.4).

Deterministically scores how reusable a CANDIDATE evidence item is for a SOURCE
requirement (another control/framework need), comparing framework mappings,
control mappings, evidence type, age, status, and approval history.

  * ASSESSMENT ONLY — never performs automatic reuse.
  * READ-ONLY, NO-LLM (no semantic match, no embeddings). FLAG-GATED by
    EVIDENCE_REUSE_SCORING_ENABLED (default off).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from app.evidence_intel._common import (
    age_days,
    age_score,
    clamp,
    flag_enabled,
    load_policy,
    merge_block,
    normalize_weights,
)
from app.evidence_intel.models import ReuseBand, ReuseScore

_DEFAULTS = {
    "weights": {"framework_overlap": 0.25, "control_overlap": 0.25, "type_match": 0.15,
                "age": 0.15, "status": 0.10, "approval_history": 0.10},
    "bands": {"high_min": 70, "medium_min": 40},
    "age_target_days": 90, "age_max_days": 365,
}

_STATUS_SCORE = {"approved": 100.0, "auditor approved": 100.0, "collected": 80.0,
                 "underreview": 60.0, "submitted for review": 60.0, "uploaded": 60.0,
                 "rejected": 0.0, "expired": 10.0, "superseded": 20.0}


def reuse_scoring_enabled() -> bool:
    return flag_enabled("EVIDENCE_REUSE_SCORING_ENABLED", "reuse_scoring_enabled")


def _policy() -> dict[str, Any]:
    return merge_block(_DEFAULTS, {"reuse": load_policy().get("reuse", {})}, "reuse")


def _norm_set(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {value.strip().lower()} if value.strip() else set()
    if isinstance(value, (list, tuple, set)):
        out: set[str] = set()
        for v in value:
            if isinstance(v, (list, tuple)) and v:
                out.add(str(v[0]).strip().lower())
            elif v is not None and str(v).strip():
                # Normalize "SOC2-CC8.1" -> "soc2" base for framework overlap.
                out.add(str(v).strip().lower())
        return out
    return set()


def _frameworks(item: Mapping[str, Any]) -> set[str]:
    raw = set()
    for k in ("framework_mapping", "frameworks", "framework_tags", "framework", "framework_refs"):
        raw |= _norm_set(item.get(k))
    # Reduce to base framework code (split on - or :).
    return {t.split("-", 1)[0].split(":", 1)[0] for t in raw if t}


def _controls(item: Mapping[str, Any]) -> set[str]:
    out = set()
    for k in ("control_mapping", "controls", "control", "control_id"):
        out |= _norm_set(item.get(k))
    return out


def _type(item: Mapping[str, Any]) -> str:
    for k in ("object_type", "evidence_type", "evidence_category", "type"):
        v = item.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip().lower()
    return ""


def _status(item: Mapping[str, Any]) -> str:
    for k in ("review_status", "status", "evidence_status"):
        v = item.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip().lower()
    return ""


def _overlap(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b) or 1
    return clamp(100.0 * inter / union)


def score_reuse(source: Mapping[str, Any], candidate: Mapping[str, Any], *,
                now: datetime | None = None, force: bool = False) -> ReuseScore:
    """Score reuse of ``candidate`` evidence for the ``source`` requirement. Never raises."""
    src_id = str(source.get("id") or source.get("control_id") or source.get("evidence_id") or "") \
        if isinstance(source, Mapping) else ""
    cand_id = str(candidate.get("evidence_id") or candidate.get("id") or "") \
        if isinstance(candidate, Mapping) else ""

    if not force and not reuse_scoring_enabled():
        return ReuseScore(source_id=src_id, candidate_id=cand_id, enabled=False,
                          note="reuse scoring disabled (EVIDENCE_REUSE_SCORING_ENABLED=false)")
    try:
        if not isinstance(source, Mapping) or not isinstance(candidate, Mapping):
            raise TypeError("source and candidate must be mappings")
        now = now or datetime.now(timezone.utc)
        policy = _policy()
        weights = normalize_weights(policy["weights"], list(_DEFAULTS["weights"]))

        fw_overlap = _overlap(_frameworks(source), _frameworks(candidate))
        ctl_overlap = _overlap(_controls(source), _controls(candidate))
        type_match = 100.0 if (_type(source) and _type(source) == _type(candidate)) else (
            50.0 if (not _type(source)) else 0.0)
        age_sc = age_score(age_days(candidate.get("collected_timestamp")
                                    or candidate.get("uploaded_at")
                                    or candidate.get("created_at"), now=now),
                           float(policy.get("age_target_days", 90)),
                           float(policy.get("age_max_days", 365)))
        status_sc = _STATUS_SCORE.get(_status(candidate), 40.0)
        history = candidate.get("approval_history") or candidate.get("evidence_approval_trail") or []
        approved_before = any(
            (isinstance(h, Mapping) and str(h.get("action", "")).lower().startswith("approv"))
            for h in history) if isinstance(history, (list, tuple)) else False
        approval_hist_sc = 100.0 if approved_before else (
            80.0 if _status(candidate) in ("approved", "auditor approved") else 30.0)

        factors = {
            "framework_overlap": fw_overlap, "control_overlap": ctl_overlap,
            "type_match": type_match, "age": age_sc, "status": status_sc,
            "approval_history": approval_hist_sc,
        }
        score = round(sum(factors[k] * weights.get(k, 0.0) for k in factors), 1)

        bands = policy["bands"]
        if score >= float(bands.get("high_min", 70)):
            band = ReuseBand.HIGH
        elif score >= float(bands.get("medium_min", 40)):
            band = ReuseBand.MEDIUM
        else:
            band = ReuseBand.LOW

        reasons = []
        if fw_overlap > 0:
            reasons.append(f"framework overlap {round(fw_overlap)}%")
        if ctl_overlap > 0:
            reasons.append(f"control overlap {round(ctl_overlap)}%")
        if type_match == 100.0:
            reasons.append("evidence type matches")
        if not reasons:
            reasons.append("low overlap with source requirement")

        return ReuseScore(source_id=src_id, candidate_id=cand_id, enabled=True,
                          score=score, band=band.value,
                          factors={k: round(v, 1) for k, v in factors.items()},
                          reasons=reasons)
    except Exception as exc:  # noqa: BLE001 - fail safe
        return ReuseScore(source_id=src_id, candidate_id=cand_id, enabled=False,
                          note=f"reuse scoring error (ignored): {type(exc).__name__}")
