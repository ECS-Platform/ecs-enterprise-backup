"""Observation closure readiness (Phase 4 of 5.4).

Deterministically assesses whether an observation is ready to be CLOSED, based on:
evidence present, evidence approved, remediation attached, observation age,
control coverage, and unresolved dependencies.

  * ASSESSMENT ONLY — no workflow changes, no state writes.
  * READ-ONLY, NO-LLM. FLAG-GATED by OBSERVATION_READINESS_ENABLED (default off).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from app.evidence_intel._common import (
    age_days,
    age_score,
    clamp,
    flag_enabled,
    load_policy,
    merge_block,
    normalize_weights,
)
from app.evidence_intel.models import ObservationClosureAssessment, ReadinessLevel

_DEFAULTS = {
    "weights": {"evidence_present": 0.25, "evidence_approved": 0.25,
                "remediation_attached": 0.15, "observation_age": 0.10,
                "control_coverage": 0.15, "unresolved_dependencies": 0.10},
    "bands": {"ready_min": 80, "nearly_ready_min": 55},
    "age_target_days": 30, "age_max_days": 120,
}

_APPROVED = {"approved", "auditor approved"}


def observation_readiness_enabled() -> bool:
    return flag_enabled("OBSERVATION_READINESS_ENABLED", "observation_readiness_enabled")


def _policy() -> dict[str, Any]:
    return merge_block(_DEFAULTS, {"readiness": load_policy().get("readiness", {})},
                       "readiness")


def _status(item: Mapping[str, Any]) -> str:
    for k in ("review_status", "status", "evidence_status"):
        v = item.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip().lower()
    return ""


def assess_closure_readiness(observation: Mapping[str, Any],
                             evidence_items: Sequence[Mapping[str, Any]] | None = None, *,
                             now: datetime | None = None,
                             force: bool = False) -> ObservationClosureAssessment:
    """Assess closure readiness for a single observation. Never raises."""
    obs_id = ""
    try:
        obs_id = str(observation.get("observation_id", "") or "") if isinstance(observation, Mapping) else ""
    except Exception:  # noqa: BLE001
        obs_id = ""

    if not force and not observation_readiness_enabled():
        return ObservationClosureAssessment(
            observation_id=obs_id, enabled=False,
            note="observation readiness disabled (OBSERVATION_READINESS_ENABLED=false)")
    try:
        if not isinstance(observation, Mapping):
            raise TypeError("observation must be a mapping")
        now = now or datetime.now(timezone.utc)
        policy = _policy()
        weights = normalize_weights(policy["weights"], list(_DEFAULTS["weights"]))
        items = [i for i in (evidence_items or []) if isinstance(i, Mapping)]

        blocking: list[str] = []
        reasons: list[str] = []

        # evidence_present
        has_evidence = bool(items) or bool(observation.get("upload_filename")
                                            or observation.get("evidence_id"))
        present_score = 100.0 if has_evidence else 0.0
        if not has_evidence:
            blocking.append("no evidence attached")

        # evidence_approved
        if items:
            approved = sum(1 for i in items if _status(i) in _APPROVED)
            approved_score = clamp(100.0 * approved / len(items))
        else:
            obs_status = str(observation.get("status", "")).strip().lower()
            approved_score = 100.0 if obs_status in _APPROVED or obs_status == "closed" else 0.0
        if approved_score < 100.0:
            reasons.append("not all evidence approved")
        if approved_score == 0.0:
            blocking.append("no approved evidence")

        # remediation_attached
        remediation = (observation.get("remediation_plan") or observation.get("remediation_notes")
                       or observation.get("remediation_owner"))
        remediation_score = 100.0 if (isinstance(remediation, str) and remediation.strip()) else 0.0
        if remediation_score == 0.0:
            reasons.append("no remediation attached")

        # observation_age (older within SLA window is fine; very old reduces readiness)
        created = (observation.get("created_at") or observation.get("uploaded_at")
                   or observation.get("requested_at"))
        age = age_days(created, now=now)
        age_sc = age_score(age, float(policy.get("age_target_days", 30)),
                           float(policy.get("age_max_days", 120)))

        # control_coverage
        coverage = 100.0 if str(observation.get("control_id") or observation.get("control") or "").strip() else 0.0
        if coverage == 0.0:
            reasons.append("no control mapping")

        # unresolved_dependencies (fewer = better; expects a list/int)
        deps = observation.get("unresolved_dependencies", observation.get("dependencies", []))
        if isinstance(deps, (list, tuple, set)):
            dep_count = len([d for d in deps if d])
        elif isinstance(deps, int):
            dep_count = max(0, deps)
        else:
            dep_count = 0
        dep_score = 100.0 if dep_count == 0 else clamp(max(0.0, 100.0 - 25.0 * dep_count))
        if dep_count > 0:
            reasons.append(f"{dep_count} unresolved dependency(ies)")
            if dep_count >= 4:
                blocking.append("too many unresolved dependencies")

        factors = {
            "evidence_present": present_score, "evidence_approved": approved_score,
            "remediation_attached": remediation_score, "observation_age": age_sc,
            "control_coverage": coverage, "unresolved_dependencies": dep_score,
        }
        score = round(sum(factors[k] * weights.get(k, 0.0) for k in factors), 1)

        bands = policy["bands"]
        # A hard blocker caps the level at Not Ready regardless of score.
        if blocking:
            level = ReadinessLevel.NOT_READY
        elif score >= float(bands.get("ready_min", 80)):
            level = ReadinessLevel.READY
        elif score >= float(bands.get("nearly_ready_min", 55)):
            level = ReadinessLevel.NEARLY_READY
        else:
            level = ReadinessLevel.NOT_READY

        if not reasons and not blocking:
            reasons.append("all closure criteria satisfied")

        return ObservationClosureAssessment(
            observation_id=obs_id, enabled=True, score=score, level=level.value,
            factors={k: round(v, 1) for k, v in factors.items()},
            reasons=reasons, blocking=blocking)
    except Exception as exc:  # noqa: BLE001 - fail safe
        return ObservationClosureAssessment(
            observation_id=obs_id, enabled=False,
            note=f"closure readiness error (ignored): {type(exc).__name__}")
