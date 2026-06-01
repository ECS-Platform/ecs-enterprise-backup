"""Enterprise operational mock data for upload tracker, integrations, and onboarding pipelines."""

from __future__ import annotations

MOCK_UPLOAD_SAMPLES = [
    {"name": "PCI_DSS_Firewall_Export_Q2.xlsx", "framework": "PCI DSS", "type": "Firewall exports"},
    {"name": "ITPP_DR_Plan_2026.pdf", "framework": "ITPP", "type": "DR plan"},
    {"name": "NetBanking_VAPT_Report_May2026.pdf", "framework": "VAPT", "type": "VAPT report"},
    {"name": "MobileBanking_AppSec_SonarQube.pdf", "framework": "AppSec", "type": "AppSec report"},
]

_TRACKER_STATUSES = ["Uploaded", "Pending Review", "Rejected", "Approved", "Expired"]
_OWNERS = ["R. Mehta", "A. Sharma", "K. Reddy", "P. Iyer", "S. Banerjee"]
_CONTROLS = [
    "Req 1.2 — Firewall config",
    "Req 10.6 — Log monitoring",
    "DR-04 — Recovery test",
    "AS-12 — SAST gate",
    "VAPT-03 — External scan",
]


def build_upload_tracker_rows(evidence_repository: list) -> list[dict]:
    """Populated tracker rows — merges live uploads with demo records."""
    rows: list[dict] = []
    for i, rec in enumerate(reversed(evidence_repository[-8:])):
        fw = rec.get("framework_tags", ["Cross-Framework"])
        fw_str = fw[0] if isinstance(fw, list) and fw else "Cross-Framework"
        status = rec.get("status", rec.get("lifecycle", "Uploaded"))
        if status in ("Draft", "Uploaded"):
            audit = "Pending Review" if i % 3 != 2 else "Approved"
        else:
            audit = status
        rows.append({
            "filename": rec.get("filename", rec.get("original_filename", f"Evidence-{i+1}")),
            "uploaded_at": rec.get("uploaded_at", "2026-05-24 08:30 UTC"),
            "uploaded_by": rec.get("uploaded_by", _OWNERS[i % len(_OWNERS)]),
            "framework": fw_str,
            "status": audit if audit in _TRACKER_STATUSES else "Uploaded",
            "mapped_controls": _CONTROLS[i % len(_CONTROLS)],
            "auditor_review": "Awaiting Review" if audit == "Pending Review" else audit,
            "tags": rec.get("application_tags", ["Net Banking"])[0] if rec.get("application_tags") else "Net Banking",
        })

    demo = [
        ("PCI_DSS_Firewall_Rules_May2026.csv", "PCI DSS", "Approved", "Req 1.2 — Firewall config", "R. Mehta"),
        ("ITPP_DR_Test_Results_Q1.pdf", "ITPP", "Pending Review", "DR-04 — Recovery test", "A. Sharma"),
        ("WealthPortal_VAPT_ExecutiveSummary.pdf", "VAPT", "Uploaded", "VAPT-03 — External scan", "K. Reddy"),
        ("UPI_AppSec_SonarGate_Report.pdf", "AppSec", "Rejected", "AS-12 — SAST gate", "P. Iyer"),
        ("Treasury_CSPM_Prisma_Export.json", "CSITE", "Expired", "CL-08 — Cloud posture", "S. Banerjee"),
        ("LoanOrigination_Checkmarx_SAST.pdf", "AppSec", "Pending Review", "AS-15 — Code review", "R. Mehta"),
        ("MobileBanking_MFA_Audit_Log.xlsx", "PCI DSS", "Approved", "Req 8.2 — MFA enrollment", "A. Sharma"),
        ("Cards_OS_Baseline_Tripwire.pdf", "OS Baselining", "Uploaded", "OS-03 — Integrity scan", "K. Reddy"),
    ]
    ts = ["2026-05-24 09:12 UTC", "2026-05-24 08:45 UTC", "2026-05-23 22:10 UTC", "2026-05-23 18:30 UTC",
          "2026-05-23 14:00 UTC", "2026-05-23 11:20 UTC", "2026-05-22 16:55 UTC", "2026-05-22 10:00 UTC"]
    for i, (fname, fw, status, ctrl, owner) in enumerate(demo):
        if any(r["filename"] == fname for r in rows):
            continue
        rows.append({
            "filename": fname,
            "uploaded_at": ts[i % len(ts)],
            "uploaded_by": owner,
            "framework": fw,
            "status": status,
            "mapped_controls": ctrl,
            "auditor_review": status if status != "Uploaded" else "Not Started",
            "tags": "Net Banking" if i % 2 == 0 else "Mobile Banking",
        })
    return rows[:16]


def build_integration_sync_jobs(connectors: list[dict]) -> list[dict]:
    """Active sync queue and recent job outcomes."""
    jobs = []
    for i, c in enumerate(connectors):
        name = c.get("name", f"Connector-{i}")
        health = c.get("sync_health", c.get("sync_status", "Healthy"))
        if health in ("Degraded", "Retry scheduled") or c.get("failed_syncs", 0) > 0:
            state = "Failed" if c.get("failed_syncs", 0) > 2 else "Retry Queued"
        elif i % 5 == 0:
            state = "Running"
        else:
            state = "Completed"
        jobs.append({
            "connector": name,
            "job_id": f"SYNC-{i+1:04d}",
            "status": state,
            "queued_at": f"2026-05-24 {(5 + i % 4):02d}:{(i * 7) % 60:02d} UTC",
            "records_ingested": c.get("imported_evidence", c.get("records", 0) // 10),
            "evidence_files": c.get("imported_evidence", 0),
            "latency_ms": 120 + i * 45,
            "auth_health": "OK" if c.get("api_status") == "Healthy" else "Token Expiring",
        })
    jobs.insert(0, {
        "connector": "SharePoint Evidence Library",
        "job_id": "SYNC-ACTIVE-001",
        "status": "Running",
        "queued_at": "2026-05-24 09:15 UTC",
        "records_ingested": 24,
        "evidence_files": 12,
        "latency_ms": 890,
        "auth_health": "OK",
    })
    return jobs


def build_integration_event_logs(connectors: list[dict]) -> list[dict]:
    """Connector event log stream."""
    events = [
        ("SharePoint Evidence Library", "API timeout after 30s — Net Banking folder", "Error", "Retry scheduled"),
        ("Jira Security Remediation", "OAuth token refreshed successfully", "Info", "Auth OK"),
        ("Prisma Cloud CSPM", "CSPM posture pull — 156 findings ingested", "Success", "Completed"),
        ("SonarQube Enterprise", "Authentication failed — token expired", "Warning", "Auth Failed"),
        ("ServiceNow GRC", "Control mapping sync — 89 controls updated", "Success", "Completed"),
        ("Tripwire Enterprise", "Integrity scan delayed — agent queue backlog", "Warning", "Delayed"),
        ("Checkmarx SAST", "SAST report imported for Loan Origination", "Success", "Completed"),
        ("Microsoft Teams Governance", "Approval thread linked to audit prep", "Info", "Completed"),
        ("Confluence Governance Wiki", "Policy page version conflict resolved", "Warning", "Resolved"),
        ("ServiceNow CMDB", "Asset discovery — 12408 records synced", "Success", "Completed"),
    ]
    rows = []
    for i, (conn, msg, level, outcome) in enumerate(events):
        rows.append({
            "timestamp": f"2026-05-24 {(8 + i // 3):02d}:{(i * 11) % 60:02d} UTC",
            "connector": conn,
            "message": msg,
            "level": level,
            "outcome": outcome,
        })
    for c in connectors[:3]:
        if c.get("failed_syncs", 0) > 0:
            rows.append({
                "timestamp": c.get("last_sync", "2026-05-24 06:00 UTC"),
                "connector": c["name"],
                "message": f"Failed sync count: {c['failed_syncs']} — auto-retry enabled",
                "level": "Error",
                "outcome": "Retry Pending",
            })
    return rows


def build_onboarding_pipelines(rows: list[dict]) -> list[dict]:
    """Pipeline drill-down data per onboarded application."""
    pipelines = []
    integrations_pool = [
        ["ServiceNow CMDB", "SharePoint", "Prisma Cloud"],
        ["SharePoint", "SonarQube", "Jira"],
        ["ServiceNow GRC", "Tripwire", "Teams"],
        ["Prisma Cloud", "Checkmarx", "Confluence"],
    ]
    stages_template = [
        {"stage": "Discovery", "status": "Complete", "items": 12},
        {"stage": "Framework Mapping", "status": "Complete", "items": 8},
        {"stage": "Integration Wiring", "status": "In Progress", "items": 5},
        {"stage": "Evidence Validation", "status": "Pending", "items": 0},
        {"stage": "Production Sign-off", "status": "Pending", "items": 0},
    ]
    for i, r in enumerate(rows):
        pct = r.get("progress_pct", 80)
        stages = []
        for j, st in enumerate(stages_template):
            if pct >= 90:
                s_status = "Complete"
            elif pct >= 70 and j <= 2:
                s_status = "Complete" if j < 2 else "In Progress"
            elif pct >= 50 and j <= 1:
                s_status = "Complete" if j == 0 else "In Progress"
            else:
                s_status = st["status"] if j == 0 else ("Pending" if j > 1 else st["status"])
            stages.append({**st, "status": s_status})
        failed = []
        if pct < 80:
            failed.append({"mapping": "SonarQube project ID", "reason": "Not mapped for application"})
        if pct < 70:
            failed.append({"mapping": "Prisma workload tag", "reason": "Cloud account not linked"})
        pipelines.append({
            "application": r["application"],
            "pipeline_id": f"PIPE-{i+1:03d}",
            "owner": r.get("owner", "TBD"),
            "progress_pct": pct,
            "stages": stages,
            "integrations": integrations_pool[i % len(integrations_pool)],
            "frameworks": ["PCI DSS", "ITPP", "AppSec", "VAPT", "CSITE"][: r.get("frameworks_mapped", 3)],
            "controls_onboarded": 42 + i * 8,
            "evidence_sources": 6 + i,
            "compliance_readiness_pct": min(95, pct + 5),
            "pending_gaps": max(0, 8 - r.get("frameworks_mapped", 3)),
            "failed_mappings": failed,
            "pending_actions": [
                "Assign control owner for AppSec gate",
                "Complete SharePoint evidence library mapping",
            ] if pct < 90 else ["Schedule production sign-off review"],
        })
    return pipelines


def build_post_onboarding_metrics(rows: list[dict]) -> list[dict]:
    """Post-onboarding governance outcomes per application."""
    metrics = []
    for i, r in enumerate(rows):
        pct = r.get("progress_pct", 80)
        complete = pct >= 90 or r.get("status") == "Production"
        metrics.append({
            "application": r["application"],
            "owner": r.get("owner", "TBD"),
            "onboarding_complete": complete,
            "evidence_collection_acceptance_pct": min(98, pct + 8) if complete else max(40, pct - 10),
            "observation_closures_count": (12 + i * 3) if complete else (2 + i),
            "audit_compliance_adherence_pct": min(96, pct + 5) if complete else max(55, pct - 5),
            "days_since_onboarding": 30 + i * 14 if complete else 0,
            "integrations_live": 4 + (i % 4) if complete else 1 + (i % 2),
            "pending_evidence_requests": max(0, 6 - i) if complete else 8 + i,
            "accepting_evidence": complete and pct >= 85,
        })
    return metrics


def build_onboarding_challenges(rows: list[dict]) -> list[dict]:
    """Applications that failed or stalled during onboarding."""
    challenges = []
    templates = [
        ("Integration Wiring", "SonarQube project ID not mapped", "V. Rao", 18, "Retry scheduled"),
        ("Framework Mapping", "PCI scope not assigned to CDE hosts", "R. Mehta", 24, "Blocked"),
        ("Evidence Validation", "SharePoint library ACL denied for service account", "A. Sharma", 12, "Open"),
        ("Owner Assignment", "No control owner assigned for AppSec gate", "TBD", 9, "Open"),
        ("Production Sign-off", "Audit readiness below 70% threshold", "K. Iyer", 31, "Escalated"),
    ]
    for i, r in enumerate(rows):
        if r.get("progress_pct", 0) >= 95 and r.get("status") == "Production":
            continue
        tpl = templates[i % len(templates)]
        challenges.append({
            "application": r["application"],
            "stage_failed": tpl[0],
            "blocker": tpl[1],
            "owner": r.get("owner", tpl[2]),
            "days_stuck": tpl[3] + i,
            "retry_status": tpl[4],
            "progress_pct": r.get("progress_pct", 0),
        })
    # Always include at least 2 failed examples
    if len(challenges) < 2:
        challenges.extend([
            {"application": "Loan Origination", "stage_failed": "Integration Wiring", "blocker": "Prisma Cloud account tag missing", "owner": "V. Rao", "days_stuck": 21, "retry_status": "Open", "progress_pct": 62},
            {"application": "Wealth Portal", "stage_failed": "Evidence Validation", "blocker": "Checkmarx scan gate not configured", "owner": "V. Rao", "days_stuck": 14, "retry_status": "Monitoring", "progress_pct": 74},
        ])
    return challenges
