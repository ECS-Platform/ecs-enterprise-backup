"""Observation Closure Assistant (Capability D, Phase 5.5).

Wraps the Phase 5.4 closure-readiness engine (evidence_intel.assess_closure_readiness)
and adds deterministic recommended next actions derived from the detected blockers
and reasons. Produces: Closure Readiness %, Blocking Items, Recommended Next Actions.

It REUSES the Phase 5.4 flag OBSERVATION_READINESS_ENABLED (no new flag).
Non-LLM, read-only, fail-safe.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Sequence

from app.evidence_analytics._common import load_policy, merge_block
from app.evidence_analytics.models import ClosurePlan

_DEFAULTS = {
    "actions": {
        "no_evidence": "Attach supporting evidence for the observation",
        "no_approved": "Obtain auditor approval for submitted evidence",
        "no_remediation": "Attach a remediation plan or assign a remediation owner",
        "stale_evidence": "Refresh stale evidence (re-collect or re-upload)",
        "no_control": "Map the observation to a control",
        "dependencies": "Resolve outstanding dependency blockers",
    },
}

# Map reason/blocker substrings to action keys.
_REASON_TO_ACTION = [
    ("no evidence", "no_evidence"),
    ("no approved", "no_approved"),
    ("not all evidence approved", "no_approved"),
    ("no remediation", "no_remediation"),
    ("stale", "stale_evidence"),
    ("no control", "no_control"),
    ("dependency", "dependencies"),
    ("dependencies", "dependencies"),
]


def closure_assist_enabled() -> bool:
    """Reuses the Phase 5.4 observation-readiness flag."""
    try:
        from app.evidence_intel.readiness import observation_readiness_enabled
        return observation_readiness_enabled()
    except Exception:  # noqa: BLE001
        from app.evidence_analytics._common import flag_enabled
        return flag_enabled("OBSERVATION_READINESS_ENABLED", "observation_readiness_enabled")


def _policy() -> dict[str, Any]:
    return merge_block(_DEFAULTS, {"closure": load_policy().get("closure", {})}, "closure")


def build_closure_plan(observation: Mapping[str, Any],
                       evidence_items: Sequence[Mapping[str, Any]] | None = None, *,
                       now: datetime | None = None, force: bool = False) -> ClosurePlan:
    """Assess closure readiness and produce recommended next actions. Never raises."""
    obs_id = ""
    try:
        obs_id = str(observation.get("observation_id", "") or "") \
            if isinstance(observation, Mapping) else ""
    except Exception:  # noqa: BLE001
        obs_id = ""

    if not force and not closure_assist_enabled():
        return ClosurePlan(observation_id=obs_id, enabled=False,
                           note="closure assistant disabled (OBSERVATION_READINESS_ENABLED=false)")
    try:
        from app.evidence_intel.readiness import assess_closure_readiness

        assessment = assess_closure_readiness(observation, evidence_items, now=now, force=True)
        policy = _policy()
        actions_map = policy.get("actions", _DEFAULTS["actions"])

        # Derive next actions from blocking items + reasons (deterministic, ordered).
        signals = list(assessment.blocking) + list(assessment.reasons)
        action_keys: list[str] = []
        for sig in signals:
            low = str(sig).lower()
            for needle, key in _REASON_TO_ACTION:
                if needle in low and key not in action_keys:
                    action_keys.append(key)
        # Stale-evidence detection from the factors (freshness proxy) is optional;
        # the readiness reasons already carry most signals.
        recommended = [actions_map[k] for k in action_keys if k in actions_map]
        if not recommended and not assessment.blocking:
            recommended = ["Observation meets closure criteria; proceed to close"]

        return ClosurePlan(
            observation_id=obs_id, enabled=True,
            closure_readiness_pct=assessment.score,
            readiness_band=assessment.level,
            blocking_items=list(assessment.blocking),
            recommended_next_actions=recommended)
    except Exception as exc:  # noqa: BLE001 - fail safe
        return ClosurePlan(observation_id=obs_id, enabled=False,
                           note=f"closure assistant error (ignored): {type(exc).__name__}")
