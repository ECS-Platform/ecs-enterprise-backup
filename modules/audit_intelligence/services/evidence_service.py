"""Evidence service facade (Milestone 2).

Ties the Evidence Collection Orchestrator and the Evidence Validation Engine
together and returns serialization-friendly dicts for future REST/UI layers.
"""

from __future__ import annotations

from typing import Any, Callable

from modules.audit_intelligence.engines import evidence_orchestrator as orch
from modules.audit_intelligence.engines import evidence_validation as validation
from modules.audit_intelligence.engines import technology_control_mapping as mapping
from modules.audit_intelligence.models import EvidenceRun


# --------------------------------------------------------------------------- #
# Runs
# --------------------------------------------------------------------------- #
def start_run(
    *,
    scope_kind: str,
    scope_value: str = "",
    requested_by: str = "system",
    executor: Callable[[str, str], dict[str, Any]] | None = None,
    control_ids: list[str] | None = None,
    asset_id: str = "",
) -> dict[str, Any]:
    """Create + execute a run, returning the serialized run."""
    run = orch.run_scope(
        scope_kind=scope_kind, scope_value=scope_value, requested_by=requested_by,
        executor=executor, control_ids=control_ids, asset_id=asset_id,
    )
    return run.to_dict()


def get_run(run_id: str) -> dict[str, Any] | None:
    run = orch.get_run(run_id)
    return run.to_dict() if run else None


def list_runs() -> list[dict[str, Any]]:
    return [
        {
            "run_id": r.run_id,
            "scope_kind": r.scope_kind,
            "scope_value": r.scope_value,
            "status": r.status,
            "requested_by": r.requested_by,
            "created_at": r.created_at,
            "summary": r.summary(),
        }
        for r in orch.list_runs()
    ]


def retry_run(run_id: str, *, executor=None, user: str = "") -> dict[str, Any] | None:
    run = orch.retry_failed(run_id, executor=executor, user=user)
    return run.to_dict() if run else None


def cancel_run(run_id: str, *, user: str = "") -> dict[str, Any] | None:
    run = orch.cancel_run(run_id, user=user)
    return run.to_dict() if run else None


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def _controls_by_id_for(run: EvidenceRun) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for record in run.records:
        ctrl = mapping.get_control(record.control_id)
        if ctrl:
            out[record.control_id] = ctrl.to_dict()
    return out


def validate_run(run_id: str) -> dict[str, Any] | None:
    """Validate a completed run's evidence and return results + compliance summary.

    Also folds each per-control validation back onto the run's records (so a single
    fetch of the run shows validation inline).
    """
    run = orch.get_run(run_id)
    if run is None:
        return None
    controls = _controls_by_id_for(run)
    results = validation.validate_records(run.records, controls)
    by_control = {r.control_id: r for r in results}
    for record in run.records:
        vr = by_control.get(record.control_id)
        record.validation = vr.to_dict() if vr else None
    return {
        "run_id": run_id,
        "results": [r.to_dict() for r in results],
        "compliance": validation.compliance_summary(results),
    }


def run_and_validate(
    *,
    scope_kind: str,
    scope_value: str = "",
    requested_by: str = "system",
    executor: Callable[[str, str], dict[str, Any]] | None = None,
    control_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Convenience: execute a run then validate it, returning both."""
    run = orch.run_scope(
        scope_kind=scope_kind, scope_value=scope_value, requested_by=requested_by,
        executor=executor, control_ids=control_ids,
    )
    val = validate_run(run.run_id)
    return {"run": run.to_dict(), "validation": val}
