"""Missing evidence / upload queue — observation-linked, persistent upload workflow."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from app import ecs_state
from modules.shared.services.ecs_state import BANKING_APPLICATIONS
from modules.frameworks.engines.framework_catalog import FRAMEWORK_CATALOG
from modules.governance.engines.governance_mock_data import OWNERS
from modules.shared.services.role_filter_scope import apply_role_scope

FRAMEWORKS = list(FRAMEWORK_CATALOG.keys())
APPLICATIONS = BANKING_APPLICATIONS
PREFIX = {
    "PCI DSS": "PCI", "DPSC": "DPSC", "AppSec": "APPSEC", "VAPT": "VAPT",
    "OS Baselining": "OSB", "DB Baselining": "DB", "Nginx Baselining": "NGX",
    "ITPP": "ITPP", "CSITE": "CSI",
}
CONTROL_IDS = {
    "PCI DSS": ["PCI-10.6", "PCI-7.2", "PCI-8.3", "PCI-3.4", "PCI-4.1"],
    "DPSC": ["DPSC-4.1", "DP-C-04", "DPSC-2.1"],
    "AppSec": ["APPSEC-12", "AS-C-02", "AS-C-04"],
    "VAPT": ["VAPT-9", "VP-C-01", "VP-C-03"],
    "OS Baselining": ["OSB-14", "OS-C-01"],
    "DB Baselining": ["DB-C-01", "DB-C-02"],
    "Nginx Baselining": ["NGX-C-01", "NGX-C-04"],
    "ITPP": ["IT-C-03", "IT-C-08"],
    "CSITE": ["CS-C-03", "CSI-7.1"],
}
CONTROL_DESCRIPTIONS = {
    "PCI-10.6": "Daily log review and retention validation",
    "PCI-7.2": "Firewall segmentation validation",
    "PCI-8.3": "MFA for privileged access",
    "OSB-14": "Linux CIS baseline hardening proof",
    "DPSC-4.1": "Consent management and data retention",
    "APPSEC-12": "Secure SDLC gate evidence",
    "VAPT-9": "External penetration test remediation",
}
MISSING_EVIDENCE = [
    "SOC monitoring log export missing",
    "Quarterly hardening report missing",
    "Firewall rule export not submitted",
    "MFA enrollment attestation missing",
    "Pen test retest evidence pending",
    "TDE attestation report expired",
    "Backup restore test log missing",
    "SIEM use-case export incomplete",
    "Access review certification missing",
    "Patch compliance matrix outdated",
]
EVIDENCE_TYPES = ["Log Export", "PDF Report", "Scan Report", "Configuration Export", "Access Review", "SIEM Export", "Attestation Pack"]
REQUESTERS = ["Auditor_RK", "Auditor_01", "Compliance_Lead", "QSA Reviewer", "CISO Office"]
SEVERITIES = ["Critical", "Major", "Medium", "Minor"]
STATUSES = ["Pending Upload", "Awaiting App Owner", "Overdue", "Submitted for Review", "Rejected"]


def _seed(key: str, lo: int, hi: int) -> int:
    h = int(hashlib.md5(key.encode()).hexdigest()[:8], 16)
    return lo + (h % (hi - lo + 1))


def _obs_id(fw: str, n: int) -> str:
    return f"OBS-{PREFIX.get(fw, 'EV')}-{1000 + n}"


def _due_date(i: int) -> str:
    return f"2026-0{6 + (i % 2)}-{(5 + (i % 25)):02d}"


def generate_missing_evidence(count: int = 120) -> list[dict]:
    records = []
    # Canonical demo rows referenced in audit operations UI
    records.extend([
        {
            "observation_id": "OBS-PCI-1021", "application": "Net Banking", "framework": "PCI DSS",
            "control_id": "PCI-10.6", "control_description": "Daily log review and retention validation",
            "control": "PCI-10.6", "missing_evidence": "SOC monitoring log export missing",
            "evidence_type": "Log Export", "risk": "High", "observation_severity": "Critical",
            "requested_by": "Auditor_RK", "due_date": "2026-06-05", "audit_impact": "Observation closure blocked",
            "status": "Pending Upload", "owner": OWNERS[0], "remediation_owner": OWNERS[1],
            "prior_uploads": ["v1.0 — 2026-01-15 (expired)"], "audit_comments": "Provide current-period SOC log export with retention attestation.",
            "rejection_reason": "", "remediation_notes": "Remediation tracked under GRC-1842",
            "history": [{"date": "2026-05-01", "action": "Requested", "actor": "Auditor_RK"}],
        },
        {
            "observation_id": "OBS-OSB-221", "application": "Treasury", "framework": "OS Baselining",
            "control_id": "OSB-14", "control_description": "Linux CIS baseline hardening proof",
            "control": "OSB-14", "missing_evidence": "Quarterly hardening report missing",
            "evidence_type": "PDF Report", "risk": "Medium", "observation_severity": "Major",
            "requested_by": "Compliance_Lead", "due_date": "2026-06-10", "audit_impact": "Audit readiness reduced",
            "status": "Awaiting App Owner", "owner": OWNERS[2], "remediation_owner": OWNERS[3],
            "prior_uploads": ["v0.9 — 2025-12-01 (superseded)"], "audit_comments": "Submit Q2 CIS hardening attestation with patch baseline.",
            "rejection_reason": "", "remediation_notes": "Remediation tracked under GRC-1920",
            "history": [{"date": "2026-05-08", "action": "Requested", "actor": "Compliance_Lead"}],
        },
    ])
    for i in range(count):
        fw = FRAMEWORKS[i % len(FRAMEWORKS)]
        app = APPLICATIONS[i % len(APPLICATIONS)]
        cids = CONTROL_IDS.get(fw, [f"{PREFIX.get(fw, 'C')}-{i + 1}"])
        cid = cids[i % len(cids)]
        desc = CONTROL_DESCRIPTIONS.get(cid, f"{fw} control validation — mandatory evidence required")
        missing = MISSING_EVIDENCE[i % len(MISSING_EVIDENCE)]
        risk = ["Critical", "High", "Medium", "Low"][_seed(f"risk-{i}", 0, 3)]
        sev = SEVERITIES[_seed(f"sev-{i}", 0, 3)]
        if risk in ("Critical", "High"):
            sev = "Critical" if risk == "Critical" else "Major"
        status = STATUSES[i % len(STATUSES)]
        if i % 11 == 0:
            status = "Overdue"
        oid = _obs_id(fw, i)
        records.append({
            "observation_id": oid,
            "application": app,
            "framework": fw,
            "control_id": cid,
            "control_description": desc,
            "control": cid,
            "missing_evidence": missing,
            "evidence_type": EVIDENCE_TYPES[i % len(EVIDENCE_TYPES)],
            "risk": risk,
            "observation_severity": sev,
            "requested_by": REQUESTERS[i % len(REQUESTERS)],
            "due_date": _due_date(i),
            "audit_impact": "Observation closure blocked" if sev == "Critical" else (
                "Audit readiness reduced" if sev == "Major" else "Minor audit finding risk"
            ),
            "status": status,
            "owner": OWNERS[i % len(OWNERS)],
            "remediation_owner": OWNERS[(i + 1) % len(OWNERS)],
            "prior_uploads": [f"v1.0 — 2026-0{(i % 3) + 1}-15 (expired)"],
            "audit_comments": "Provide current-period artifact with control owner attestation.",
            "rejection_reason": "Prior submission lacked timestamp" if status == "Rejected" else "",
            "remediation_notes": f"Remediation tracked under GRC-{1800 + i}",
            "history": [
                {"date": "2026-05-01", "action": "Requested", "actor": REQUESTERS[i % len(REQUESTERS)]},
            ],
        })
    return records


def _seed_registry() -> None:
    if getattr(ecs_state, "missing_evidence_seed_loaded", False):
        return
    ecs_state.missing_evidence_seed_loaded = True
    for rec in generate_missing_evidence(120):
        oid = rec["observation_id"]
        if oid not in ecs_state.missing_evidence_registry:
            ecs_state.missing_evidence_registry[oid] = dict(rec)


def get_all_missing_evidence(role: str = "owner", *, include_uploaded: bool = False) -> list[dict]:
    _seed_registry()
    rows = [dict(v) for v in ecs_state.missing_evidence_registry.values()]
    if not include_uploaded:
        rows = [r for r in rows if r.get("status") not in ("Uploaded", "Approved", "Closed")]
    return apply_role_scope(rows, role)


def get_missing_record(observation_id: str) -> dict | None:
    _seed_registry()
    rec = ecs_state.missing_evidence_registry.get(observation_id)
    return dict(rec) if rec else None


def apply_upload(
    observation_id: str,
    user: str,
    role: str,
    *,
    filename: str = "",
    comments: str = "",
    evidence_category: str = "",
    remediation_owner: str = "",
    expected_closure: str = "",
    submit_type: str = "submit_review",
) -> str:
    _seed_registry()
    rec = ecs_state.missing_evidence_registry.get(observation_id)
    if not rec:
        return f"Observation {observation_id} not found."

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    new_status = "Draft Saved" if submit_type == "upload_draft" else "Submitted for Review"
    if submit_type == "submit_review":
        new_status = "Submitted for Review"
    rec.update({
        "status": new_status,
        "uploaded_by": user,
        "uploaded_at": ts,
        "upload_filename": filename,
        "upload_comments": comments,
        "evidence_category": evidence_category or rec.get("evidence_type"),
        "remediation_owner": remediation_owner or rec.get("remediation_owner"),
        "expected_closure": expected_closure or rec.get("due_date"),
    })
    history = rec.setdefault("history", [])
    history.append({"date": ts, "action": new_status, "actor": user, "remarks": filename or comments})
    ecs_state.missing_evidence_registry[observation_id] = rec

    if submit_type == "submit_review":
        from modules.frameworks.engines.framework_catalog import resolve_framework_name
        fw = resolve_framework_name(rec["framework"])
        cname = rec.get("control_name") or rec.get("control_id", "")
        key = ecs_state.control_key(fw, cname)
        ts_full = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        ecs_state.submitted_controls[key] = {
            "submitted_by": user,
            "submitted_at": ts_full,
            "evidence_id": rec.get("evidence_id", ""),
        }
        ecs_state.submitted_meta[key] = {"submitted_at": ts_full, "observation_id": observation_id}
        from modules.operations.engines.evidence_repository import register_upload
        register_upload(
            filename or f"{observation_id}_evidence.pdf",
            b"ECS gap upload artefact",
            user,
            framework=fw,
            application=rec.get("application", "Net Banking"),
            control=cname,
        )
        ecs_state.operational_readiness_boost = min(12, ecs_state.operational_readiness_boost + 1)

    ecs_state.operational_uploads.append({
        "timestamp": ts,
        "observation_id": observation_id,
        "framework": rec["framework"],
        "control": rec["control_id"],
        "application": rec["application"],
        "filename": filename,
        "comments": comments,
        "uploaded_by": user,
        "status": new_status,
    })
    return f"Evidence {new_status.lower()} for {observation_id} — {rec['missing_evidence'][:50]}."


def apply_request_reupload(
    observation_id: str,
    user: str,
    role: str,
    *,
    comments: str = "",
) -> str:
    """Auditor requests App Owner to re-upload — auditor never uploads directly."""
    _seed_registry()
    rec = ecs_state.missing_evidence_registry.get(observation_id)
    if not rec:
        return f"Observation {observation_id} not found."

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    rec.update({
        "status": "Re-upload Requested by Auditor",
        "reupload_requested_by": user,
        "reupload_requested_at": ts,
        "audit_comments": comments or rec.get("audit_comments", "Auditor has requested re-upload. App Owner to coordinate."),
    })
    history = rec.setdefault("history", [])
    history.append({
        "date": ts,
        "action": "Re-upload Requested by Auditor",
        "actor": user,
        "remarks": comments or "Returned to App Owner queue for re-upload coordination.",
    })
    ecs_state.missing_evidence_registry[observation_id] = rec
    from modules.shared.services.audit_trail import log_event
    log_event(
        "Re-upload Requested by Auditor",
        user,
        rec["framework"],
        rec["control_id"],
        comments or "Evidence returned to App Owner for re-upload",
        role=role or "Auditor",
    )
    return f"Re-upload requested for {observation_id} — returned to App Owner queue."


def compute_upload_kpis(rows: list[dict]) -> dict:
    open_rows = [r for r in rows if r.get("status") not in ("Uploaded", "Approved", "Closed", "Submitted for Review")]
    overdue = [r for r in open_rows if r.get("status") == "Overdue" or r.get("due_date", "") < "2026-05-24"]
    critical = [r for r in open_rows if r.get("observation_severity") == "Critical" or r.get("risk") == "Critical"]
    pending = [r for r in open_rows if r.get("status") in ("Pending Upload", "Awaiting App Owner")]
    apps_blocked = len({r["application"] for r in critical})
    return {
        "total_missing": len(open_rows),
        "critical_missing": len(critical),
        "uploads_pending": len(pending),
        "overdue_uploads": len(overdue),
        "applications_blocked": apps_blocked,
        "audit_closure_impact": len([r for r in open_rows if "blocked" in r.get("audit_impact", "").lower()]),
    }


def compute_completeness_pct(rows: list[dict], detail_rows: list[dict]) -> float:
    """Dynamic completeness from evidence upload states + control implementation."""
    _seed_registry()
    all_recs = list(ecs_state.missing_evidence_registry.values())
    uploaded = len([r for r in all_recs if r.get("status") in ("Submitted for Review", "Uploaded", "Approved")])
    approved = len([r for r in all_recs if r.get("status") == "Approved"])
    rejected = len([r for r in all_recs if r.get("status") == "Rejected"])
    missing = len([r for r in all_recs if r.get("status") in ("Pending Upload", "Awaiting App Owner", "Overdue")])
    overdue = len([r for r in all_recs if r.get("status") == "Overdue"])
    total = max(len(all_recs), 1)
    evidence_score = round((uploaded + approved * 1.2) / total * 100, 1)
    if detail_rows:
        impl = sum(r.get("implemented", 0) for r in detail_rows)
        total_ctrl = sum(r.get("total_controls", 0) for r in detail_rows)
        ctrl_score = round(impl / max(total_ctrl, 1) * 100, 1)
        penalty = (missing * 0.15 + overdue * 0.25 + rejected * 0.1) / max(total, 1)
        return round(max(0, min(98, (ctrl_score * 0.6 + evidence_score * 0.4) - penalty * 10)), 1)
    return evidence_score
