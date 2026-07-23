"""Seed realistic enterprise workflow state for leadership demos (idempotent)."""

from app import ecs_state
from modules.shared.services.audit_trail import log_event, record_approval, record_rejection, seed_baseline_audit_events
from modules.frameworks.engines.framework_catalog import seed_workflow_targets


_seeded = False


def seed_demo_workflow_state():
    global _seeded
    if _seeded:
        return
    _seeded = True

    seed_baseline_audit_events()

    if ecs_state.approved_controls:
        return

    targets = seed_workflow_targets()

    for fw, ctrl, auditor in targets["approved"]:
        key = ecs_state.control_key(fw, ctrl)
        ecs_state.approved_controls[key] = {
            "status": "Auditor Approved",
            "approved_by": auditor,
            "approved_at": "2026-05-18 11:00:00 UTC",
            "note": "Observation Closed — Auditor Approved",
        }
        record_approval(fw, ctrl, auditor)

    for fw, ctrl in targets["submitted"]:
        key = ecs_state.control_key(fw, ctrl)
        if key not in ecs_state.approved_controls:
            ecs_state.submitted_controls[key] = "Pending Auditor Review"
            ecs_state.submitted_meta[key] = {
                "submitted_at": "2026-05-20 14:30:00 UTC",
                "submitted_by": "R. Mehta (App Owner)",
            }
            log_event(
                "Observation Submitted",
                "R. Mehta (App Owner)",
                fw,
                ctrl,
                "Evidence package submitted — awaiting auditor review",
            )

    for fw, ctrl, reason in targets["rejected"]:
        key = ecs_state.control_key(fw, ctrl)
        ecs_state.rejected_controls[key] = {
            "reason": reason,
            "rejected_by": "S. Nair (Auditor)",
            "rejected_at": "2026-05-20 14:00:00 UTC",
            "internal": False,
            "resubmission_stage": "owner_review",
            "team_resubmission_requested": False,
            "revised_uploaded": False,
            "reevaluated": False,
        }
        if key in ecs_state.submitted_controls:
            del ecs_state.submitted_controls[key]
        record_rejection(fw, ctrl, "S. Nair (Auditor)", reason)

    from modules.governance.engines.fcm_evidence_demo_seed import seed_fcm_evidence_progress_demo

    seed_fcm_evidence_progress_demo()
