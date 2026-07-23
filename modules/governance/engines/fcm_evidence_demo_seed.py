"""DEMO_MODE-only FCM evidence progress seed — preserves production data."""

from __future__ import annotations

from app import ecs_state
from modules.frameworks.repositories.framework_control_repository import (
    FileFrameworkControlRepository,
)
from modules.governance.engines.fcm_evidence_progress_engine import (
    _fcm_enrollment_key,
)

_seeded = False


def _demo_mode() -> bool:
    try:
        from app.auth.demo import demo_mode

        return demo_mode()
    except Exception:  # noqa: BLE001
        import os

        return os.environ.get("DEMO_MODE", "").lower() in ("1", "true", "yes")


def seed_fcm_evidence_progress_demo() -> None:
    """Seed persisted enrollments + workflow states for all progress chart colours."""
    global _seeded
    if _seeded or not _demo_mode():
        return
    _seeded = True

    if any(
        isinstance(v, dict) and v.get("fcm_framework_id")
        for v in ecs_state.uploaded_evidence_enrollments.values()
    ):
        return

    repo = FileFrameworkControlRepository()

    seeds: list[dict] = [
        # Net Banking / PCI — closed control
        {
            "framework_id": "pci_dss",
            "control_id": "PCI-C-01",
            "evr_ids": ["PCI-EVR-011", "PCI-EVR-012"],
            "application": "Net Banking",
            "audit_status": "Approved",
            "workflow": "approved",
        },
        # Net Banking / ITPP — pending
        {
            "framework_id": "itpp",
            "control_id": "ITPP-C-03",
            "evr_ids": ["ITPP-EVR-031"],
            "application": "Net Banking",
            "audit_status": "Under Review",
            "workflow": "submitted",
        },
        # Payments / DPSC — blocked (rejected)
        {
            "framework_id": "dpsc",
            "control_id": "DPSC-C-02",
            "evr_ids": ["DPSC-EVR-021"],
            "application": "Payments",
            "audit_status": "Rejected",
            "workflow": "rejected",
        },
        # Mobile Banking / ASST — pending partial
        {
            "framework_id": "asst",
            "control_id": "ASST-C-01",
            "evr_ids": ["ASST-EVR-011"],
            "application": "Mobile Banking",
            "audit_status": "Submitted",
            "workflow": "submitted",
        },
        # Mobile Banking / middleware — blocked expired
        {
            "framework_id": "middleware_baseline",
            "control_id": "MWB-C-04",
            "evr_ids": ["MWB-EVR-041"],
            "application": "Mobile Banking",
            "audit_status": "Rejected",
            "evidence_status": "Expired",
            "workflow": "rejected",
        },
    ]

    for spec in seeds:
        fw_id = spec["framework_id"]
        doc = repo.get_framework(fw_id)
        if not doc:
            continue
        fw_name = (doc.get("framework") or {}).get("name") or fw_id
        control = next(
            (c for c in (doc.get("controls") or []) if c.get("id") == spec["control_id"]),
            None,
        )
        if not control:
            continue
        title = str(control.get("title") or "")
        ckey = ecs_state.control_key(fw_name, title)
        if spec["workflow"] == "approved":
            ecs_state.approved_controls[ckey] = {
                "status": "Auditor Approved",
                "approved_by": "S. Nair (Auditor)",
                "approved_at": "2026-05-18 11:00:00 UTC",
            }
        elif spec["workflow"] == "submitted":
            ecs_state.submitted_controls[ckey] = "Pending Auditor Review"
        elif spec["workflow"] == "rejected":
            ecs_state.rejected_controls[ckey] = {
                "reason": "Evidence package incomplete for demo seed.",
                "rejected_by": "S. Nair (Auditor)",
            }

        for idx, evr_id in enumerate(spec["evr_ids"], start=1):
            evr = next(
                (
                    e
                    for e in (control.get("evidence_requirements") or [])
                    if e.get("id") == evr_id
                ),
                {"id": evr_id, "title": f"{title} evidence {idx}"},
            )
            app = spec["application"]
            enroll_key = _fcm_enrollment_key(fw_id, spec["control_id"], evr_id, app)
            evidence_id = f"FCM-{fw_id[:3].upper()}-{spec['control_id'][-2:]}{idx}"
            row = {
                "key": ecs_state.control_key(fw_name, title),
                "fcm_framework_id": fw_id,
                "fcm_control_id": spec["control_id"],
                "fcm_evr_id": evr_id,
                "framework": fw_name,
                "control_name": title,
                "control_id": spec["control_id"],
                "application": app,
                "evidence_id": evidence_id,
                "evidence_name": evr.get("title"),
                "audit_status": spec.get("audit_status", "Submitted"),
                "evidence_status": spec.get("evidence_status", "Current"),
                "workflow_status": spec.get("audit_status", "Submitted"),
                "status": spec.get("audit_status", "Submitted"),
                "uploaded_at": "2026-05-20 10:00:00 UTC",
                "uploaded_by": "Demo Seed",
                "source_connector": "FCM_DEMO_SEED",
            }
            ecs_state.uploaded_evidence_enrollments[evidence_id] = row
            ecs_state.uploaded_evidence_enrollments[enroll_key] = row
