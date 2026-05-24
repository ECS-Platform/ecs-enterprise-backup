"""Enterprise audit trail, activity feed, and approval history."""

from datetime import datetime, timezone

_audit_events = []
_approval_history = []
_version_history = {}
_notifications = []


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def log_event(
    action: str,
    actor: str,
    framework: str = "",
    control: str = "",
    detail: str = "",
    evidence_id: str = "",
    role: str = "",
):
    event = {
        "timestamp": _ts(),
        "action": action,
        "actor": actor,
        "role": role or _infer_role(actor),
        "framework": framework,
        "control": control,
        "detail": detail,
        "evidence_id": evidence_id,
    }
    _audit_events.insert(0, event)
    if len(_audit_events) > 200:
        _audit_events.pop()

    _notifications.insert(
        0,
        {
            "timestamp": event["timestamp"],
            "message": f"{action}: {detail or control or framework}",
            "level": _level_for_action(action),
        },
    )
    if len(_notifications) > 30:
        _notifications.pop()


def _level_for_action(action: str) -> str:
    if "Reject" in action or "Tamper" in action or "Overdue" in action:
        return "danger"
    if "Approve" in action or "Closed" in action or "Sync" in action:
        return "success"
    if "Submit" in action or "Upload" in action:
        return "info"
    return "secondary"


def _infer_role(actor: str) -> str:
    al = actor.lower()
    if "auditor" in al:
        return "Auditor"
    if "cio" in al:
        return "CIO"
    if "compliance" in al:
        return "Compliance"
    if "owner" in al or "mehta" in al or "sharma" in al:
        return "App Owner"
    return "System"


def record_approval(framework: str, control: str, auditor: str, note: str = "Approved"):
    entry = {
        "timestamp": _ts(),
        "framework": framework,
        "control": control,
        "auditor": auditor,
        "note": note,
    }
    _approval_history.insert(0, entry)
    log_event("Evidence Approved", auditor, framework, control, note, role="Auditor")


def record_rejection(framework: str, control: str, auditor: str, reason: str):
    entry = {
        "timestamp": _ts(),
        "framework": framework,
        "control": control,
        "auditor": auditor,
        "reason": reason,
    }
    _approval_history.insert(0, {**entry, "note": f"Rejected: {reason}"})
    log_event("Evidence Rejected", auditor, framework, control, reason, role="Auditor")


def record_version(evidence_id: str, filename: str, version: int, actor: str):
    versions = _version_history.setdefault(evidence_id, [])
    versions.append(
        {
            "version": version,
            "filename": filename,
            "timestamp": _ts(),
            "actor": actor,
        }
    )


def get_audit_trail(limit: int = 25):
    return _audit_events[:limit]


def get_recent_activity(limit: int = 12):
    return _audit_events[:limit]


def get_approval_history(limit: int = 20):
    return _approval_history[:limit]


def get_notifications(limit: int = 8):
    return _notifications[:limit]


def get_version_history(evidence_id: str):
    return _version_history.get(evidence_id, [])


def seed_baseline_audit_events():
    """Pre-populate enterprise demo audit history (idempotent)."""
    if _audit_events:
        return
    samples = [
        ("Scheduled Pull", "ECS Scheduler", "PCI DSS", "", "Collected 10 PCI mock artefacts"),
        ("Evidence Uploaded", "R. Mehta (App Owner)", "PCI DSS", "Req 3.4 — Encryption at Rest", "MOCK-PCI-001 v2"),
        ("Observation Approved", "S. Nair (Auditor)", "PCI DSS", "Req 4.1 — Encryption in Transit", "Observation closed"),
        ("Observation Rejected", "S. Nair (Auditor)", "DPSC", "Fraud Monitoring", "Incomplete fraud sample period"),
        ("Integration Sync", "SharePoint Connector", "", "", "412 records synchronized"),
        ("Evidence Uploaded", "A. Khan (App Owner)", "CSITE", "SIEM Alerts", "SIEM alert screenshot Q1"),
        ("Observation Submitted", "P. Iyer (App Owner)", "Nginx Baselining", "WAF Enabled", "Submitted for review"),
        ("Compliance Review", "V. Desai (Compliance Officer)", "OS Baselining", "", "Quarterly attestation logged"),
    ]
    for action, actor, fw, ctrl, detail in samples:
        log_event(action, actor, fw, ctrl, detail)
