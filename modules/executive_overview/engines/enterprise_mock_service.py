"""Centralized interconnected enterprise mock data — filters, regions, reuse, uploads."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from modules.shared.services.ecs_state import BANKING_APPLICATIONS
from modules.frameworks.engines.framework_catalog import FRAMEWORK_CATALOG
from modules.governance.engines.governance_mock_data import OWNERS, _EVIDENCE_NAMES

FRAMEWORKS = list(FRAMEWORK_CATALOG.keys())
REUSE_APPLICATIONS = BANKING_APPLICATIONS + ["Wealth Portal"]
REGIONS = ["East", "West", "North", "South", "Central"]

_FW_CONTROL_IDS: dict[str, list[str]] = {
    "PCI DSS": ["PCI-7.2", "PCI-10.6", "PCI-8.3", "PCI-3.4", "PCI-4.1", "PCI-6.5", "PCI-7.1"],
    "DPSC": ["DPSC-4.1", "DPSC-2.1", "DP-C-04", "DPSC-3.2"],
    "AppSec": ["APPSEC-12", "AS-C-01", "AS-C-02", "AS-C-04"],
    "VAPT": ["VAPT-9", "VP-C-01", "VP-C-03"],
    "OS Baselining": ["OSB-14", "OS-C-01", "OS-C-05"],
    "DB Baselining": ["DB-C-01", "DB-C-02", "DBB-3.1"],
    "Nginx Baselining": ["NGX-C-01", "NGX-C-04", "NGX-2.1"],
    "ITPP": ["IT-C-03", "IT-C-05", "IT-C-08"],
    "CSITE": ["CS-C-03", "CSI-7.1", "CS-C-01"],
}

_REVIEWERS = ["Auditor_01", "Auditor_02", "Compliance Head", "QSA Reviewer", "CISO Office"]

_REUSE_PAIRS = [
    ("PCI DSS", "DPSC", "Firewall Segmentation Validation", "Multi-Factor Authentication", "MFA Enrollment Report"),
    ("PCI DSS", "VAPT", "Firewall Rule Export", "Network Segmentation Test", "Firewall Evidence Pack"),
    ("AppSec", "VAPT", "SAST Report", "Penetration Testing", "Application Security Scan"),
    ("AppSec", "DPSC", "Dependency Scan", "Third-Party Risk Assessment", "Dependency Scan Export"),
    ("OS Baselining", "CSITE", "CIS Hardening Standard", "Endpoint Integrity Monitoring", "CIS Benchmark Scan"),
    ("DB Baselining", "PCI DSS", "Oracle Hardening Config", "Req 3.4 Encryption at Rest", "TDE Attestation Report"),
    ("VAPT", "AppSec", "Penetration Test Report", "Secure SDLC Gate", "Pen Test Findings Bundle"),
    ("CSITE", "PCI DSS", "SIEM Correlation Rules", "Req 10.6 Log Review", "SIEM Use-Case Export"),
    ("DPSC", "ITPP", "Data Classification Register", "Information Asset Inventory", "Data Classification Matrix"),
    ("ITPP", "PCI DSS", "Privileged Access Review", "Req 7.1 Access Control", "PAM Access Certification"),
    ("Nginx Baselining", "PCI DSS", "TLS Cipher Inventory", "Req 4.1 Encryption in Transit", "TLS Configuration Export"),
    ("PCI DSS", "AppSec", "Req 6.5 Secure Development", "SAST Quality Gate", "Secure Coding SOP"),
]

_REUSE_STATUSES = ["Approved", "Approved", "Approved", "Candidate", "Pending Review", "Approved"]
_EVIDENCE_TYPES = [
    "Policy Document", "Scan Report", "Configuration Export", "Access Review",
    "Pen Test Report", "SIEM Export", "Backup Test Log", "Change Ticket Bundle",
    "Firewall Config Export", "VAPT Report", "MFA Screenshot Pack", "Patch Compliance Report",
    "Hardening Baseline Export", "CAB Approval Minutes", "SAST Export", "IAM Evidence Pack",
    "Encryption Config Snapshot",
]

_DOC_SUFFIXES = [
    "firewall_rules", "vapt_report", "mfa_screenshots", "patch_report",
    "hardening_export", "cab_approval", "sast_export", "iam_evidence", "encryption_config",
]


def _seed(key: str, lo: int, hi: int) -> int:
    h = int(hashlib.md5(key.encode()).hexdigest()[:8], 16)
    return lo + (h % (hi - lo + 1))


def build_pan_india_posture() -> dict:
    """Unique regional governance posture with framework-level variance."""
    apps_by_region = {
        "East": ["Net Banking", "Loan System", "Retail Banking"],
        "West": ["Mobile Banking", "Payments", "Treasury"],
        "North": ["UPI", "Cards", "Net Banking"],
        "South": ["Mobile Banking", "UPI", "Payments", "Treasury"],
        "Central": ["Loan System", "Net Banking", "Payments"],
    }
    base_scores = {"East": 82.0, "West": 71.0, "North": 86.5, "South": 91.0, "Central": 78.5}
    regions = []
    framework_matrix = []
    for region in REGIONS:
        s = _seed(region, 0, 999)
        score = round(base_scores[region] + (s % 5) * 0.3, 1)
        apps = apps_by_region[region]
        obs = 18 + _seed(f"{region}-obs", 0, 45)
        failed = 4 + _seed(f"{region}-fail", 0, 14)
        stale = 6 + _seed(f"{region}-stale", 0, 22)
        branches = {"East": 980, "West": 1320, "North": 1240, "South": 1580, "Central": 1105}[region]
        risk = "High" if score < 75 else ("Medium" if score < 85 else "Low")
        regions.append({
            "region": region,
            "zone": region,
            "score": score,
            "compliance_pct": score,
            "branches": branches,
            "applications": len(apps),
            "application_list": apps,
            "observations_open": obs,
            "failed_controls": failed,
            "stale_evidence": stale,
            "sla_breaches": max(1, obs // 7 + failed // 3),
            "audit_readiness_pct": round(score - 3 + _seed(f"{region}-audit", 0, 8), 1),
            "maturity_index": round(score * 0.92, 1),
            "risk_level": risk,
            "risk": risk,
            "owner": OWNERS[_seed(region, 0, len(OWNERS) - 1)],
            # Regions span every framework (see framework_matrix below); a single
            # framework here would wrongly exclude the region under a framework
            # filter. Use a wildcard so the regions tab is never zeroed.
            "framework": "All Frameworks",
            "status": "At Risk" if risk == "High" else "Monitoring",
        })
        for fw in FRAMEWORKS[:10]:
            fw_score = round(
                base_scores[region] + _seed(f"{region}-{fw}", -12, 14),
                1,
            )
            framework_matrix.append({
                "region": region,
                "framework": fw,
                "readiness_pct": fw_score,
                "open_gaps": max(0, _seed(f"{region}-{fw}-gap", 1, 18)),
                "stale_evidence": max(0, _seed(f"{region}-{fw}-stale", 0, 12)),
                "audit_posture": "Ready" if fw_score >= 85 else ("At Risk" if fw_score < 72 else "In Progress"),
                "application": apps[_seed(f"{region}-{fw}-app", 0, len(apps) - 1)],
                "owner": OWNERS[_seed(f"{region}-{fw}-own", 0, len(OWNERS) - 1)],
                "risk": "High" if fw_score < 72 else ("Medium" if fw_score < 85 else "Low"),
                "status": "Monitoring",
            })
    from modules.shared.utils.data_source_marker import pan_india_posture_data_source

    return {
        "regions": regions,
        "framework_matrix": framework_matrix,
        "data_source": pan_india_posture_data_source(),
    }


def build_reuse_mappings(count: int = 120) -> dict:
    """Framework-specific evidence reuse mappings — 100+ unique rows."""
    groups = []
    workbench = []
    candidates = []
    for i in range(count):
        pair = _REUSE_PAIRS[i % len(_REUSE_PAIRS)]
        src_fw, tgt_fw, src_ctrl, tgt_ctrl, evidence = pair
        app = REUSE_APPLICATIONS[i % len(REUSE_APPLICATIONS)]
        alt_fw = FRAMEWORKS[(i + 3) % len(FRAMEWORKS)]
        if i % 7 == 0:
            src_fw, tgt_fw = tgt_fw, src_fw
        doc_suffix = _DOC_SUFFIXES[i % len(_DOC_SUFFIXES)]
        ev_name = f"{evidence} — {app} ({src_fw[:3]})"
        fname = f"{doc_suffix}_{src_fw.replace(' ', '_')}_{app.replace(' ', '_')}_{i + 1}.pdf"
        gid = f"REUSE-{i + 1:03d}"
        conf = 78 + _seed(f"reuse-{i}", 0, 20)
        status = _REUSE_STATUSES[i % len(_REUSE_STATUSES)]
        ctrl_ids = _FW_CONTROL_IDS.get(src_fw, [f"{src_fw[:3].upper()}-{i + 1}"])
        control_id = ctrl_ids[i % len(ctrl_ids)]
        reuse_type = "Cross-framework" if src_fw != tgt_fw else "Same-framework"
        approved_by = _REVIEWERS[i % len(_REVIEWERS)] if status == "Approved" else "—"
        last_reviewed = f"2026-0{(i % 4) + 1}-{(i % 22) + 1:02d}"
        audit_savings = 6 + _seed(f"sav-{i}", 0, 18)
        linked = [
            {"framework": src_fw, "control": src_ctrl, "control_id": control_id},
            {"framework": tgt_fw, "control": tgt_ctrl},
        ]
        if i % 4 == 0:
            linked.append({"framework": alt_fw, "control": f"{alt_fw} Shared Control"})
        risk = "Low" if status == "Approved" else ("Medium" if status == "Candidate" else "High")
        owner = OWNERS[i % len(OWNERS)]
        row = {
            "reuse_id": gid,
            "group_id": gid,
            "evidence_id": gid,
            "filename": fname,
            "reused_evidence_file": fname,
            "evidence_name": ev_name,
            "source_framework": src_fw,
            "target_framework": tgt_fw,
            "control_id": control_id,
            "control_name": src_ctrl,
            "target_control_name": tgt_ctrl,
            "reused_control": src_ctrl,
            "reused_evidence": evidence,
            "reuse_type": reuse_type,
            "reuse_status": status,
            "approved_by": approved_by,
            "last_reviewed": last_reviewed,
            "audit_savings_hrs": audit_savings,
            "audit_savings": f"{audit_savings} hrs",
            "application": app,
            "frameworks_mapped": len({l["framework"] for l in linked}),
            "framework_mapping": ", ".join(sorted({l["framework"] for l in linked})),
            "controls_linked": len(linked),
            "reuse_candidates": len(linked),
            "duplicate_avoided": len(linked) - 1,
            "status": status,
            "last_refresh": last_reviewed,
            "linked_controls": linked,
            "owner": owner,
            "risk": risk,
            "framework": src_fw,
            "mapping_confidence": conf,
            "evidence_type": _EVIDENCE_TYPES[i % len(_EVIDENCE_TYPES)],
            "reviewer": approved_by if status == "Approved" else owner,
        }
        groups.append(row)
        workbench.append({
            "mapping_id": f"MAP-{i + 1:03d}",
            "evidence": fname[:42],
            "source_framework": src_fw,
            "source_control": src_ctrl,
            "target_framework": tgt_fw,
            "target_control": tgt_ctrl,
            "similarity_pct": conf,
            "status": status,
            "group_id": gid,
            "application": app,
            "owner": owner,
            "framework": src_fw,
            "risk": risk,
        })
        candidates.append({
            "evidence": ev_name[:48],
            "source_framework": src_fw,
            "target_framework": tgt_fw,
            "mapping_confidence": conf,
            "duplicate_avoided": 1,
            "status": status,
            "group_id": gid,
            "application": app,
            "owner": owner,
            "framework": src_fw,
            "risk": risk,
        })
    pending = [g for g in groups if g["status"] != "Approved"]
    return {
        "rows": groups,
        "pending_rows": pending,
        "candidates": candidates,
        "workbench": workbench,
    }


def session_upload_records() -> list[dict]:
    """Convert live evidence_repository uploads into operations filter rows."""
    from modules.operations.engines.evidence_repository import evidence_repository

    rows = []
    for i, rec in enumerate(reversed(evidence_repository)):
        fw = rec["framework_tags"][0] if rec.get("framework_tags") else "Cross-Framework"
        app = rec["application_tags"][0] if rec.get("application_tags") else "Net Banking"
        ts = rec.get("uploaded_at", datetime.now(timezone.utc).isoformat())
        if "T" in ts:
            ts = ts.replace("T", " ")[:19] + " UTC"
        rows.append({
            "batch_id": f"SESSION-{i + 1:04d}",
            "filename": rec["filename"],
            "framework": fw,
            "application": app,
            "owner": rec.get("uploaded_by", OWNERS[0]),
            "risk": "Low",
            "status": "Validating" if rec.get("lifecycle") == "Draft" else "Approved",
            "evidence_type": "Uploaded Evidence",
            "control_id": rec.get("control") or "AUTO-MAP",
            "uploaded_at": ts,
            "uploaded_by": rec.get("uploaded_by", "User"),
            "mapped_controls": rec.get("control") or "AUTO-MAP",
            "error_count": 0,
            "progress_pct": 100,
            "session_upload": True,
        })
    return rows
