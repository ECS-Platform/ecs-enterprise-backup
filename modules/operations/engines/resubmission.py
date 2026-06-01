"""Rejection / resubmission lifecycle helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from app import ecs_state

STAGES = {
    "owner_review": "Pending App Owner Review",
    "team_resubmission": "Team Re-upload Requested",
    "reevaluate": "Revised Evidence Uploaded",
    "ready_resubmit": "Ready to Resubmit to Auditor",
}


def init_rejection(key: str, reason: str, rejected_by: str, *, internal: bool = False) -> None:
    ecs_state.rejected_controls[key] = {
        "reason": reason,
        "rejected_by": rejected_by,
        "rejected_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "internal": internal,
        "resubmission_stage": "owner_review",
        "team_resubmission_requested": False,
        "revised_uploaded": False,
        "reevaluated": False,
    }


def get_stage(key: str) -> str:
    if key not in ecs_state.rejected_controls:
        return ""
    rej = ecs_state.rejected_controls[key]
    if "resubmission_stage" not in rej:
        rej["resubmission_stage"] = "owner_review"
        rej.setdefault("team_resubmission_requested", False)
        rej.setdefault("revised_uploaded", False)
        rej.setdefault("reevaluated", False)
    return rej.get("resubmission_stage", "owner_review")


def stage_label(key: str) -> str:
    return STAGES.get(get_stage(key), "Rejected by Auditor")


def can_resubmit_to_auditor(key: str) -> bool:
    if key not in ecs_state.rejected_controls:
        return False
    rej = ecs_state.rejected_controls[key]
    if rej.get("internal"):
        return True
    return rej.get("resubmission_stage") == "ready_resubmit" or rej.get("reevaluated")


def advance_stage(key: str, stage: str) -> None:
    if key not in ecs_state.rejected_controls:
        return
    ecs_state.rejected_controls[key]["resubmission_stage"] = stage
    if stage == "team_resubmission":
        ecs_state.rejected_controls[key]["team_resubmission_requested"] = True
    elif stage == "reevaluate":
        ecs_state.rejected_controls[key]["revised_uploaded"] = True
    elif stage == "ready_resubmit":
        ecs_state.rejected_controls[key]["reevaluated"] = True
