"""Enterprise banking mock data for Governance module pages — always populated."""

from __future__ import annotations

from modules.shared.services.ecs_state import BANKING_APPLICATIONS
from modules.frameworks.engines.framework_catalog import FRAMEWORK_CATALOG

APPLICATIONS = BANKING_APPLICATIONS + ["Cards", "Retail Banking", "Loan Origination"]
FRAMEWORKS = list(FRAMEWORK_CATALOG.keys())
OWNERS = ["R. Mehta", "A. Sharma", "K. Reddy", "P. Iyer", "S. Banerjee", "N. Joshi"]

_EVIDENCE_NAMES = [
    "DB TDE Encryption Report",
    "Firewall Rule Export",
    "SIEM Alert Correlation Log",
    "Vulnerability Scan Summary",
    "Access Review Certification",
    "Patch Compliance Matrix",
    "Network Segmentation Diagram",
    "Application Pen Test Report",
    "Change Management Ticket Bundle",
    "Backup Restore Test Evidence",
    "MFA Enrollment Report",
    "Data Classification Register",
    "Incident Response Runbook",
    "Cloud CSPM Posture Export",
    "API Security Gateway Config",
]


def _ev_id(prefix: str, n: int) -> str:
    return f"{prefix}-{n:04d}"


def lifecycle_enrichment() -> dict:
    rows = []
    states = ["Draft", "Active", "Active", "Active", "Expiring", "Expiring", "Archived", "Retired"]
    for i, name in enumerate(_EVIDENCE_NAMES):
        app = APPLICATIONS[i % len(APPLICATIONS)]
        fw = FRAMEWORKS[i % len(FRAMEWORKS)]
        st = states[i % len(states)]
        rows.append({
            "evidence_id": _ev_id("EV", 1000 + i),
            "name": name,
            "application": app,
            "framework": fw,
            "lifecycle_state": st,
            "status": "Approved" if st == "Active" else ("Pending Review" if st == "Draft" else st),
            "owner": OWNERS[i % len(OWNERS)],
            "upload_date": f"2026-0{(i % 5) + 1}-{(i % 20) + 5:02d}",
            "last_updated": f"2026-05-{(i % 20) + 1:02d}",
            "expiry_date": f"2026-0{6 + (i % 3)}-{(i % 25) + 1:02d}",
            "auto_refresh": i % 3 == 0,
        })
    framework_aging = []
    for fw in FRAMEWORKS[:8]:
        framework_aging.append({
            "framework": fw,
            "active": 18 + hash(fw) % 40,
            "expiring": 3 + hash(fw) % 8,
            "stale": 2 + hash(fw) % 6,
            "avg_age_days": 45 + hash(fw) % 90,
        })
    application_stale = []
    for app in APPLICATIONS[:8]:
        application_stale.append({
            "application": app,
            "stale_count": 2 + hash(app) % 9,
            "expiring_soon": 1 + hash(app) % 5,
            "owner": OWNERS[hash(app) % len(OWNERS)],
        })
    expiring_7, expiring_15, expiring_30, critical = [], [], [], []
    for i, r in enumerate(rows):
        band = i % 4
        entry = {**r, "days_to_expiry": [5, 12, 22, 28][band]}
        if band == 0:
            expiring_7.append(entry)
            if i % 2 == 0:
                critical.append(entry)
        elif band == 1:
            expiring_15.append(entry)
        else:
            expiring_30.append(entry)
    timeline_visual = []
    stages = ["Uploaded", "Reviewed", "Approved", "Expiring", "Archived"]
    for i, r in enumerate(rows[:12]):
        stage = stages[min(i % 5, 4)]
        timeline_visual.append({
            **r,
            "event": stage,
            "event_date": r["last_updated"],
            "actor": r["owner"] if stage != "Uploaded" else "Scheduler",
        })
    buckets = {"Draft": 0, "Active": 0, "Expiring": 0, "Archived": 0, "Retired": 0}
    bucket_items = {k: [] for k in buckets}
    for r in rows:
        st = r["lifecycle_state"]
        buckets[st] = buckets.get(st, 0) + 1
        bucket_items.setdefault(st, []).append(r)
    return {
        "rows": rows,
        "buckets": buckets,
        "bucket_items": bucket_items,
        "framework_aging": framework_aging,
        "application_stale": application_stale,
        "expiring_bands": {"7_days": expiring_7, "15_days": expiring_15, "30_days": expiring_30},
        "critical_expiring": critical,
        "timeline_visual": timeline_visual,
        "timeline_events": timeline_visual,
    }


def reuse_enrichment() -> dict:
    groups = []
    mappings = [
        ("PCI DSS", "DPSC", "Encryption at Rest", "Data Protection Control", 94),
        ("PCI DSS", "AppSec", "Req 6.5 — Secure Development", "SAST Gate", 88),
        ("DPSC", "CSITE", "Log Monitoring", "SIEM Correlation", 91),
        ("VAPT", "AppSec", "Pen Test Findings", "Vulnerability Remediation", 86),
        ("ITPP", "PCI DSS", "Privileged Access Review", "Req 7.1 — Access Control", 92),
        ("DB Baselining", "PCI DSS", "DB Encryption Config", "Req 3.4 — Encryption", 95),
        ("OS Baselining", "DPSC", "Hardening Standard", "OS Baseline Compliance", 89),
        ("CSITE", "PCI DSS", "SIEM Alerts", "Req 10.6 — Log Review", 90),
        ("AppSec", "VAPT", "SAST Report", "Dynamic Scan Overlap", 84),
        ("PCI DSS", "ITPP", "Network Segmentation", "Zone Segregation", 87),
    ]
    for i, (src_fw, tgt_fw, src_ctrl, tgt_ctrl, conf) in enumerate(mappings):
        fname = f"{src_fw.replace(' ', '_')}_{APPLICATIONS[i % len(APPLICATIONS)].replace(' ', '_')}_evidence_{i + 1}.pdf"
        gid = f"REUSE-{i + 1:03d}"
        linked = [
            {"framework": src_fw, "control": src_ctrl},
            {"framework": tgt_fw, "control": tgt_ctrl},
        ]
        if i % 3 == 0:
            linked.append({"framework": FRAMEWORKS[(i + 2) % len(FRAMEWORKS)], "control": "Shared Control Mapping"})
        status = "Approved" if i % 3 != 2 else "Candidate"
        groups.append({
            "group_id": gid,
            "evidence_id": gid,
            "filename": fname,
            "frameworks_mapped": len({l["framework"] for l in linked}),
            "framework_mapping": ", ".join(sorted({l["framework"] for l in linked})),
            "controls_linked": len(linked),
            "reuse_candidates": len(linked),
            "duplicate_avoided": len(linked) - 1,
            "status": status,
            "last_refresh": f"2026-05-{(i % 20) + 1:02d}",
            "linked_controls": linked,
            "owner": OWNERS[i % len(OWNERS)],
            "risk": "Low" if status == "Approved" else "Medium",
            "source_framework": src_fw,
            "target_framework": tgt_fw,
            "mapping_confidence": conf,
        })
    workbench = []
    for i, g in enumerate(groups):
        src = g["linked_controls"][0]
        tgt = g["linked_controls"][1]
        workbench.append({
            "mapping_id": f"MAP-{i + 1:03d}",
            "evidence": g["filename"][:40],
            "source_framework": src["framework"],
            "source_control": src["control"],
            "target_framework": tgt["framework"],
            "target_control": tgt["control"],
            "similarity_pct": g["mapping_confidence"],
            "status": g["status"],
            "group_id": g["group_id"],
        })
    candidates = []
    for g in groups:
        for j, lc in enumerate(g["linked_controls"][1:], 1):
            candidates.append({
                "evidence": g["filename"][:45],
                "source_framework": g["linked_controls"][0]["framework"],
                "target_framework": lc["framework"],
                "mapping_confidence": g["mapping_confidence"] - j * 2,
                "duplicate_avoided": 1,
                "status": g["status"],
                "group_id": g["group_id"],
            })
    pending = [g for g in groups if g["status"] != "Approved"]
    return {"rows": groups, "pending_rows": pending, "candidates": candidates, "workbench": workbench}


def health_enrichment() -> dict:
    rows = []
    issues = ["Stale", "Expired", "Missing Metadata", "Low Confidence", "Rejected", "Expiring Soon"]
    for i, name in enumerate(_EVIDENCE_NAMES):
        issue = issues[i % len(issues)]
        risk = {"Stale": "Medium", "Expired": "Critical", "Missing Metadata": "High",
                "Low Confidence": "Medium", "Rejected": "High", "Expiring Soon": "High"}[issue]
        rows.append({
            "evidence_id": _ev_id("EH", 2000 + i),
            "evidence_name": name,
            "framework": FRAMEWORKS[i % len(FRAMEWORKS)],
            "application": APPLICATIONS[i % len(APPLICATIONS)],
            "owner": OWNERS[i % len(OWNERS)],
            "issue": issue,
            "risk": risk,
            "health_score": max(30, 95 - i * 4),
            "expiry_date": f"2026-0{6 + (i % 3)}-{(i % 25) + 1:02d}",
            "rejection_count": i % 4,
        })
    rows.sort(key=lambda x: {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}[x["risk"]])
    categories = {
        "stale": [r for r in rows if r["issue"] == "Stale"],
        "expired": [r for r in rows if r["issue"] == "Expired"],
        "incomplete": [r for r in rows if r["issue"] in ("Missing Metadata", "Low Confidence")],
        "risky": [r for r in rows if r["risk"] in ("Critical", "High")],
        "missing": [r for r in rows if r["issue"] == "Missing Metadata"],
    }
    fw_breakdown = []
    for fw in FRAMEWORKS[:8]:
        fw_rows = [r for r in rows if r["framework"] == fw]
        fw_breakdown.append({
            "framework": fw, "total": len(fw_rows) or 3 + hash(fw) % 8,
            "stale": sum(1 for r in fw_rows if r["issue"] == "Stale") or hash(fw) % 4,
            "expired": sum(1 for r in fw_rows if r["issue"] == "Expired") or hash(fw) % 3,
            "high_risk": sum(1 for r in fw_rows if r["risk"] in ("Critical", "High")) or hash(fw) % 5,
        })
    app_breakdown = []
    for app in APPLICATIONS[:8]:
        app_rows = [r for r in rows if r["application"] == app]
        app_breakdown.append({
            "application": app,
            "issues": len(app_rows) or 2 + hash(app) % 6,
            "avg_score": 62 + hash(app) % 30,
            "owner": OWNERS[hash(app) % len(OWNERS)],
        })
    owner_breakdown = []
    for owner in OWNERS:
        o_rows = [r for r in rows if r["owner"] == owner]
        owner_breakdown.append({
            "owner": owner, "queue_size": len(o_rows) or 2 + hash(owner) % 5,
            "rejections": sum(r["rejection_count"] for r in o_rows),
            "critical": sum(1 for r in o_rows if r["risk"] == "Critical"),
        })
    rejection_trends = [
        {"month": "Jan", "rejections": 12, "rate_pct": 8.2},
        {"month": "Feb", "rejections": 9, "rate_pct": 6.1},
        {"month": "Mar", "rejections": 14, "rate_pct": 9.4},
        {"month": "Apr", "rejections": 7, "rate_pct": 4.8},
        {"month": "May", "rejections": 11, "rate_pct": 7.3},
    ]
    return {
        "rows": rows,
        "categories": categories,
        "framework_breakdown": fw_breakdown,
        "application_breakdown": app_breakdown,
        "owner_breakdown": owner_breakdown,
        "rejection_trends": rejection_trends,
    }


def completeness_enrichment() -> dict:
    control_rows = []
    for i, fw in enumerate(FRAMEWORKS):
        for j in range(3):
            impl = j != 2
            control_rows.append({
                "framework": fw,
                "control": f"{fw} Control {(i * 3) + j + 1}",
                "application": APPLICATIONS[(i + j) % len(APPLICATIONS)],
                "total_controls": 120 + i * 8,
                "implemented": 95 + j * 10 + i,
                "pending": 8 - j * 2,
                "gaps": 0 if impl else 2 + j,
                "readiness_pct": 88 + j * 3 - i,
                "status": "Implemented" if impl else "Pending",
            })
    app_readiness = []
    for app in APPLICATIONS:
        app_readiness.append({
            "application": app,
            "frameworks_covered": min(len(FRAMEWORKS), 5 + hash(app) % 4),
            "total_controls": 180 + hash(app) % 60,
            "implemented": 140 + hash(app) % 40,
            "pending": 12 + hash(app) % 10,
            "gaps": 4 + hash(app) % 8,
            "readiness_pct": 72 + hash(app) % 22,
            "overdue_evidence": hash(app) % 6,
        })
    missing = []
    for i in range(15):
        missing.append({
            "framework": FRAMEWORKS[i % len(FRAMEWORKS)],
            "control": f"Control gap {i + 1} — evidence required",
            "evidence": _EVIDENCE_NAMES[i % len(_EVIDENCE_NAMES)],
            "application": APPLICATIONS[i % len(APPLICATIONS)],
            "owner": OWNERS[i % len(OWNERS)],
            "priority": ["High", "Medium", "High", "Low"][i % 4],
        })
    return {"control_rows": control_rows, "application_readiness": app_readiness, "missing_rows": missing}


def comparison_enrichment() -> dict:
    pairs = [
        ("Net Banking", "Mobile Banking"),
        ("Payments", "Loan System"),
        ("UPI", "Cards"),
        ("Treasury", "Retail Banking"),
        ("Net Banking", "UPI"),
        ("Mobile Banking", "Payments"),
    ]
    pair_rows = []
    for i, (a, b) in enumerate(pairs):
        score_a = 78 + (hash(a) % 15)
        score_b = 74 + (hash(b) % 18)
        pair_rows.append({
            "app_a": a, "app_b": b,
            "readiness_a": score_a, "readiness_b": score_b,
            "variance": abs(score_a - score_b),
            "risk": "High" if abs(score_a - score_b) > 10 else "Medium",
            "stale_a": 2 + hash(a) % 5, "stale_b": 2 + hash(b) % 5,
            "td_a": hash(a) % 3, "td_b": hash(b) % 4,
            "framework_posture": f"PCI {score_a}% vs {score_b}%",
        })
    rankings = sorted(
        [{"application": app, "compliance_pct": 70 + hash(app) % 25,
          "audit_readiness": 68 + hash(app) % 28, "risk": ["Low", "Medium", "High"][hash(app) % 3],
          "stale_evidence": hash(app) % 7, "open_td": hash(app) % 4} for app in APPLICATIONS],
        key=lambda x: -x["compliance_pct"],
    )
    return {"pair_rows": pair_rows, "rankings": rankings}


def audit_prep_enrichment() -> dict:
    submissions = []
    for i in range(12):
        submissions.append({
            "submission_id": f"SUB-{i + 1:04d}",
            "framework": FRAMEWORKS[i % len(FRAMEWORKS)],
            "control": f"Control submission {i + 1}",
            "application": APPLICATIONS[i % len(APPLICATIONS)],
            "owner": OWNERS[i % len(OWNERS)],
            "status": ["Pending", "Submitted", "Rejected", "Approved"][i % 4],
            "due": f"2026-06-{(i % 20) + 1:02d}",
        })
    remediation = []
    for i in range(10):
        remediation.append({
            "gap_id": f"GAP-{i + 1:04d}",
            "framework": FRAMEWORKS[i % len(FRAMEWORKS)],
            "control": f"Remediation item {i + 1}",
            "owner": OWNERS[i % len(OWNERS)],
            "progress_pct": min(100, 20 + i * 8),
            "sla_status": ["On Track", "At Risk", "Breached"][i % 3],
        })
    return {"pending_submissions": submissions, "remediation_progress": remediation}


def search_defaults() -> dict:
    results = []
    for i, name in enumerate(_EVIDENCE_NAMES):
        results.append({
            "evidence_id": _ev_id("SR", 3000 + i),
            "evidence": name,
            "framework": FRAMEWORKS[i % len(FRAMEWORKS)],
            "control": f"Control ref {(i % 12) + 1}",
            "application": APPLICATIONS[i % len(APPLICATIONS)],
            "owner": OWNERS[i % len(OWNERS)],
            "status": ["Approved", "Pending", "Submitted"][i % 3],
            "match_type": "Catalog" if i % 2 else "Semantic",
            "semantic_score": 55 + (i * 3) % 40,
            "tags": ["encryption", "access", "logging", "patch", "scan"][i % 5],
        })
    controls = [{"framework": fw, "control": f"{fw} — Access & Encryption", "applications": 4 + hash(fw) % 3}
                for fw in FRAMEWORKS[:10]]
    findings = [{"finding_id": f"FND-{i + 1:04d}", "framework": FRAMEWORKS[i % len(FRAMEWORKS)],
                 "summary": f"Audit finding {i + 1} — remediation tracked", "severity": ["High", "Medium", "Low"][i % 3],
                 "application": APPLICATIONS[i % len(APPLICATIONS)]} for i in range(10)]
    return {"default_results": results, "control_lookup": controls, "findings": findings}
