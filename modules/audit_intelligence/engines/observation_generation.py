"""Observation Generation Engine (Milestone 3).

Converts failed/warning validation outcomes into audit **observations** —
deterministically (no LLM). Each observation carries severity, impact, a
recommendation, an evidence reference, an owner, and a workflow status with a
transition history.

Workflow: Draft -> Submitted -> Approved -> (Remediated -> Closed) | Rejected.

Design:
  * Deterministic severity from verdict + framework weighting + assertion type.
  * In-memory observation store (durable persistence is out of scope for M1-M3);
    nothing stores credentials/secrets.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from modules.audit_intelligence.models import (
    OBS_STATUS_APPROVED,
    OBS_STATUS_CLOSED,
    OBS_STATUS_DRAFT,
    OBS_STATUS_REJECTED,
    OBS_STATUS_REMEDIATED,
    OBS_STATUS_SUBMITTED,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_INFO,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    Observation,
    ValidationResult,
    VERDICT_FAIL,
    VERDICT_WARNING,
)

# Frameworks whose failures are treated as higher severity (regulatory weight).
_HIGH_WEIGHT_FRAMEWORKS = {
    "PCI DSS", "RBI Cyber Security", "DPSC", "SOC2", "ISO27001",
}

# Allowed workflow transitions.
_TRANSITIONS: dict[str, set[str]] = {
    OBS_STATUS_DRAFT: {OBS_STATUS_SUBMITTED, OBS_STATUS_REJECTED},
    OBS_STATUS_SUBMITTED: {OBS_STATUS_APPROVED, OBS_STATUS_REJECTED},
    OBS_STATUS_APPROVED: {OBS_STATUS_REMEDIATED, OBS_STATUS_REJECTED},
    OBS_STATUS_REMEDIATED: {OBS_STATUS_CLOSED},
    OBS_STATUS_REJECTED: {OBS_STATUS_DRAFT},
    OBS_STATUS_CLOSED: set(),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"OBS-{uuid.uuid4().hex[:12]}"


def _invalidate_dashboard_cache() -> None:
    """Best-effort dashboard-cache drop after an observation change (never raises)."""
    try:
        from modules.audit_intelligence.services import dashboard_service

        dashboard_service.invalidate_dashboard_cache()
    except Exception:  # noqa: BLE001 - cache invalidation must never raise
        pass


# --------------------------------------------------------------------------- #
# In-memory store
# --------------------------------------------------------------------------- #
_OBSERVATIONS: dict[str, Observation] = {}


def reset_observations() -> None:
    _OBSERVATIONS.clear()
    _invalidate_dashboard_cache()


def get_observation(obs_id: str) -> Observation | None:
    return _OBSERVATIONS.get(obs_id)


def list_observations(
    *, status: str = "", severity: str = "", framework: str = "", technology: str = ""
) -> list[Observation]:
    out = list(_OBSERVATIONS.values())
    if status:
        out = [o for o in out if o.status == status]
    if severity:
        out = [o for o in out if o.severity == severity]
    if technology:
        out = [o for o in out if o.technology == technology]
    if framework:
        out = [o for o in out if framework in o.frameworks]
    out.sort(key=lambda o: (_severity_rank(o.severity), o.created_at), reverse=True)
    return out


_SEVERITY_ORDER = [SEVERITY_INFO, SEVERITY_LOW, SEVERITY_MEDIUM, SEVERITY_HIGH, SEVERITY_CRITICAL]


def _severity_rank(sev: str) -> int:
    return _SEVERITY_ORDER.index(sev) if sev in _SEVERITY_ORDER else 0


# --------------------------------------------------------------------------- #
# Severity + text derivation (deterministic)
# --------------------------------------------------------------------------- #
def derive_severity(result: ValidationResult) -> str:
    """Deterministic severity from verdict, framework weight, and rule type."""
    if result.verdict == VERDICT_WARNING:
        return SEVERITY_MEDIUM if _is_high_weight(result.frameworks) else SEVERITY_LOW
    if result.verdict == VERDICT_FAIL:
        high_weight = _is_high_weight(result.frameworks)
        is_assertion = result.rule_id.startswith("assertion")
        if high_weight and is_assertion:
            return SEVERITY_CRITICAL
        if high_weight or is_assertion:
            return SEVERITY_HIGH
        return SEVERITY_MEDIUM
    return SEVERITY_INFO


def _is_high_weight(frameworks: tuple[str, ...]) -> bool:
    return any(fw in _HIGH_WEIGHT_FRAMEWORKS for fw in frameworks)


def _impact_text(result: ValidationResult, severity: str) -> str:
    fw = ", ".join(result.frameworks) if result.frameworks else "applicable frameworks"
    return (
        f"{severity} risk to {fw} compliance: control {result.control_id} "
        f"({result.technology}) is {result.control_status.lower()}."
    )


def _recommendation_text(result: ValidationResult) -> str:
    if result.rule_id.startswith("assertion.negative"):
        return (
            f"Enable/enforce the required configuration for {result.control_id} on "
            f"the affected {result.technology} target and re-collect evidence."
        )
    if result.verdict == VERDICT_WARNING:
        return (
            f"Manually review {result.control_id}: evidence is inconclusive or empty. "
            f"Confirm the intended configuration and re-run collection."
        )
    return (
        f"Investigate and remediate {result.control_id} on {result.technology}; "
        f"re-run evidence collection to confirm closure."
    )


# --------------------------------------------------------------------------- #
# Generation
# --------------------------------------------------------------------------- #
def generate_observation(
    result: ValidationResult,
    *,
    asset_id: str = "",
    owner: str = "",
    evidence_reference: str = "",
    control_name: str = "",
) -> Observation | None:
    """Create an observation from a FAIL/WARNING validation result.

    PASS / NOT APPLICABLE produce no observation (returns None).
    """
    if result.verdict not in (VERDICT_FAIL, VERDICT_WARNING):
        return None
    severity = derive_severity(result)
    label = control_name or result.control_id
    obs = Observation(
        observation_id=_new_id(),
        technology=result.technology,
        asset_id=asset_id,
        control_id=result.control_id,
        frameworks=result.frameworks,
        severity=severity,
        observation=f"{label}: {result.rationale}",
        impact=_impact_text(result, severity),
        recommendation=_recommendation_text(result),
        evidence_reference=evidence_reference,
        owner=owner,
        status=OBS_STATUS_DRAFT,
        created_at=_now(),
        updated_at=_now(),
    )
    obs.history.append({"at": obs.created_at, "event": "created", "status": OBS_STATUS_DRAFT})
    _OBSERVATIONS[obs.observation_id] = obs
    _invalidate_dashboard_cache()
    return obs


def generate_from_results(
    results: list[ValidationResult],
    *,
    asset_id: str = "",
    owner: str = "",
    controls_by_id: dict[str, dict[str, Any]] | None = None,
    evidence_refs: dict[str, str] | None = None,
) -> list[Observation]:
    """Generate observations for all failing/warning results in a list."""
    controls_by_id = controls_by_id or {}
    evidence_refs = evidence_refs or {}
    out: list[Observation] = []
    for r in results:
        ctrl = controls_by_id.get(r.control_id) or {}
        obs = generate_observation(
            r,
            asset_id=asset_id,
            owner=owner,
            evidence_reference=evidence_refs.get(r.control_id, ""),
            control_name=str(ctrl.get("control_name") or ""),
        )
        if obs:
            out.append(obs)
    return out


# --------------------------------------------------------------------------- #
# Workflow transitions
# --------------------------------------------------------------------------- #
class InvalidTransition(ValueError):
    """Raised when an observation status transition is not allowed."""


def transition(obs_id: str, to_status: str, *, user: str = "", note: str = "") -> Observation:
    """Move an observation to a new workflow status (validated)."""
    obs = get_observation(obs_id)
    if obs is None:
        raise KeyError(f"Unknown observation: {obs_id}")
    allowed = _TRANSITIONS.get(obs.status, set())
    if to_status not in allowed:
        raise InvalidTransition(
            f"Cannot move {obs_id} from {obs.status} to {to_status}. "
            f"Allowed: {sorted(allowed) or 'none'}."
        )
    obs.status = to_status
    obs.updated_at = _now()
    obs.history.append(
        {"at": obs.updated_at, "event": "transition", "status": to_status,
         "user": user, "note": note}
    )
    _invalidate_dashboard_cache()
    return obs


def summary() -> dict[str, Any]:
    """Roll-up of open observations by severity/status/framework."""
    obs = list(_OBSERVATIONS.values())
    open_states = {OBS_STATUS_DRAFT, OBS_STATUS_SUBMITTED, OBS_STATUS_APPROVED}
    by_sev: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_fw: dict[str, int] = {}
    for o in obs:
        by_sev[o.severity] = by_sev.get(o.severity, 0) + 1
        by_status[o.status] = by_status.get(o.status, 0) + 1
        for fw in o.frameworks:
            by_fw[fw] = by_fw.get(fw, 0) + 1
    return {
        "total": len(obs),
        "open": sum(1 for o in obs if o.status in open_states),
        "by_severity": by_sev,
        "by_status": by_status,
        "by_framework": by_fw,
    }
