"""Enterprise scheduler intelligence — cron timeline, scan results, failures, upcoming plan."""

from __future__ import annotations

from app import ecs_state

APPLICATIONS = [
    "Net Banking",
    "Mobile Banking",
    "UPI",
    "Cards",
    "Payments",
    "Treasury",
    "Loan Origination",
    "Internet Banking",
]

INTEGRATIONS = [
    "ServiceNow",
    "SharePoint",
    "Teams",
    "Confluence",
    "Jira",
    "Prisma Cloud",
    "SonarQube",
    "Checkmarx",
    "Tripwire",
]

FRAMEWORKS = ["PCI DSS", "DPSC", "ITPP", "AppSec", "VAPT", "CSITE", "OS Baselining", "DB Baselining"]


def yesterday_summary() -> dict:
    return {
        "applications_scanned": 42,
        "evidence_collected": 1248,
        "controls_auto_validated": 317,
        "controls_pending_review": 61,
        "failed_collections": 7,
        "compliance_delta_pct": 3.2,
        "reuse_mapped": 28,
        "high_risk_gaps": 14,
    }


_CRON_JOBS = [
    ("PCI DSS", "Net Banking", "02:00 AM IST"),
    ("DPSC", "UPI", "06:00 AM IST"),
    ("AppSec", "Mobile Banking", "12:00 PM IST"),
    ("ITPP", "Treasury", "06:00 PM IST"),
]


def cron_timeline() -> list[dict]:
    base = [
        {
            "run_id": "CRON-20260523-0200",
            "label": "Yesterday 02:00 AM IST",
            "timestamp": "2026-05-23 02:00:12 IST",
            "scheduled_time": "Daily 02:00 AM IST",
            "last_execution": "2026-05-23 02:00:12 IST",
            "duration_sec": 34,
            "applications_scanned": 38,
            "evidence_collected": 286,
            "controls_validated": 72,
            "failures": 1,
            "health": "Success",
            "retry_count": 0,
            "failure_reason": "",
            "details": [
                "SharePoint library sync — 142 files ingested",
                "ServiceNow GRC control mapping — 72 controls validated",
                "Net Banking PCI scan — 38 applications covered",
            ],
        },
        {
            "run_id": "CRON-20260523-0600",
            "label": "Yesterday 06:00 AM IST",
            "timestamp": "2026-05-23 06:00:08 IST",
            "scheduled_time": "Daily 06:00 AM IST",
            "last_execution": "2026-05-23 06:00:08 IST",
            "duration_sec": 41,
            "applications_scanned": 42,
            "evidence_collected": 312,
            "controls_validated": 81,
            "failures": 2,
            "health": "Partial",
            "retry_count": 1,
            "failure_reason": "Prisma Cloud API rate limit; SharePoint timeout on Mobile Banking",
            "details": [
                "Prisma Cloud API rate limit — Treasury pull deferred",
                "SharePoint timeout on Mobile Banking folder — 2 retries queued",
                "DPSC log retention evidence — partial collection (81 controls validated)",
            ],
        },
        {
            "run_id": "CRON-20260523-1200",
            "label": "Yesterday 12:00 PM IST",
            "timestamp": "2026-05-23 12:00:15 IST",
            "scheduled_time": "Daily 12:00 PM IST",
            "last_execution": "2026-05-23 12:00:15 IST",
            "duration_sec": 38,
            "applications_scanned": 40,
            "evidence_collected": 298,
            "controls_validated": 76,
            "failures": 0,
            "health": "Success",
            "retry_count": 0,
            "failure_reason": "",
            "details": [
                "Midday AppSec gate scan — SonarQube + Checkmarx linked",
                "UPI integrity scan — Tripwire agent queue cleared",
                "All 40 applications scanned without failures",
            ],
        },
        {
            "run_id": "CRON-20260523-1800",
            "label": "Yesterday 06:00 PM IST",
            "timestamp": "2026-05-23 18:00:09 IST",
            "scheduled_time": "Daily 06:00 PM IST",
            "last_execution": "2026-05-23 18:00:09 IST",
            "duration_sec": 45,
            "applications_scanned": 41,
            "evidence_collected": 352,
            "controls_validated": 88,
            "failures": 4,
            "health": "Partial",
            "retry_count": 3,
            "failure_reason": "Jira token expired; SonarQube SAST pull failed for Loan Origination",
            "details": [
                "Jira auth token expired — remediation tickets not synced",
                "SonarQube SAST pull failed for Loan Origination",
                "Evening enterprise sync — 352 evidence files collected",
                "4 failures escalated to integration health dashboard",
            ],
        },
    ]
    for i, row in enumerate(base):
        fw, app, _ = _CRON_JOBS[i % len(_CRON_JOBS)]
        row.setdefault("framework", fw)
        row.setdefault("application", app)
        if row["health"] == "Running":
            row.setdefault("failure_reason", "")
    return base


def application_scans() -> list[dict]:
    scans = []
    for i, app in enumerate(APPLICATIONS):
        fw = FRAMEWORKS[i % len(FRAMEWORKS)]
        passed = 28 + (i * 3) % 15
        pending = 4 + i % 6
        missing = i % 4
        risk = "High" if missing >= 3 else ("Medium" if pending > 5 else "Low")
        health = "Healthy" if missing == 0 else ("Attention" if missing < 3 else "Degraded")
        scans.append({
            "application": app,
            "framework": fw,
            "evidence_collected": 86 + i * 12,
            "controls_passed": passed,
            "controls_pending": pending,
            "missing_evidence": missing,
            "risk": risk,
            "last_scan": f"2026-05-23 {(18 - i % 6):02d}:00 IST",
            "health": health,
            "drill_down": _scan_drill_down(app, fw, i),
        })
    return scans


def _scan_drill_down(app: str, fw: str, idx: int) -> dict:
    collected = [
        f"{fw} Req 10.6: Log monitoring evidence collected successfully",
        f"{fw} Req 3.4: Encryption at rest report ingested from SharePoint",
        "SIEM correlation export mapped to CSITE controls",
    ]
    missing = []
    if idx % 3 == 0:
        missing.append("PCI DSS Req 11.3: External VAPT report missing")
    if idx % 4 == 1:
        missing.append("ITPP DR Control: DR drill evidence stale (92 days old)")
    if idx % 5 == 2:
        missing.append("AppSec SAST gate: SonarQube scan not linked")
    failed_integrations = []
    if idx % 2 == 0:
        failed_integrations.append("SharePoint folder timeout — Net Banking evidence library")
    if idx == 3:
        failed_integrations.append("Prisma Cloud API rate limit during CSPM pull")
    validated = [
        f"{fw} — Access review certification auto-validated",
        f"{fw} — Patch compliance matrix passed integrity check",
    ]
    pending = [
        f"{fw} Req 8.2: MFA enrollment report pending auditor review",
        "DPSC log retention policy — metadata incomplete",
    ]
    recommendations = [
        "Upload missing VAPT report before PCI audit window (14 days)",
        "Renew stale DR drill evidence for ITPP continuity control",
        f"Re-link {app} ServiceNow GRC connector for automated control mapping",
    ]
    return {
        "collected": collected,
        "missing": missing or ["No critical missing evidence detected"],
        "failed_integrations": failed_integrations or ["All integration pulls succeeded"],
        "validated": validated,
        "pending": pending,
        "recommendations": recommendations[:2 + idx % 2],
    }


def run_history() -> list[dict]:
    rows = []
    triggers = ["Cron", "Cron", "Manual", "Cron", "Retry", "Cron", "Manual", "Cron"]
    statuses = ["Success", "Success", "Partial", "Success", "Retry Pending", "Failed", "Success", "Partial"]
    for i in range(12):
        rows.append({
            "run_id": f"RUN-2026052{4 - i // 4}-{i + 1:03d}",
            "trigger_type": triggers[i % len(triggers)],
            "started": f"2026-05-{24 - i // 3:02d} {(6 + i * 2) % 24:02d}:00:08 UTC",
            "completed": f"2026-05-{24 - i // 3:02d} {(6 + i * 2) % 24:02d}:00:{38 + i % 20} UTC",
            "duration_sec": 35 + i * 3,
            "apps_covered": 38 + i % 5,
            "evidence_count": 280 + i * 18,
            "status": statuses[i % len(statuses)],
            "initiated_by": "Cron" if triggers[i % len(triggers)] == "Cron" else "R. Mehta (App Owner)",
            "log_preview": [
                f"[{(6 + i * 2) % 24:02d}:00:01] Collection orchestrator started",
                f"[{(6 + i * 2) % 24:02d}:00:08] Scanning {38 + i % 5} applications",
                f"[{(6 + i * 2) % 24:02d}:00:{30 + i % 10}] {280 + i * 18} evidence files ingested",
            ],
        })
    return rows


def scheduler_failures() -> list[dict]:
    from modules.operations.engines.scheduler_intelligence import _seed_scheduler_failures
    return _seed_scheduler_failures()


def _seed_scheduler_failures() -> list[dict]:
    """Mutable failure queue — seeded once into ecs_state."""
    if ecs_state.scheduler_failures:
        return ecs_state.scheduler_failures
    ecs_state.scheduler_failures = [
        {
            "failure_id": "FAIL-001",
            "type": "Integration Timeout",
            "source": "SharePoint",
            "description": "Stale SharePoint link — Net Banking evidence library folder unreachable",
            "severity": "High",
            "impact": "12 evidence files not collected for PCI DSS",
            "affected_applications": "Net Banking, Internet Banking",
            "remediation": "Refresh SharePoint OAuth token and re-map folder path",
            "retry_status": "Retry Pending",
        },
        {
            "failure_id": "FAIL-002",
            "type": "API Unavailable",
            "source": "Prisma Cloud",
            "description": "Prisma Cloud API unavailable during CSPM posture pull",
            "severity": "High",
            "impact": "Cloud compliance evidence gap for Treasury workload",
            "affected_applications": "Treasury",
            "remediation": "Verify Prisma API key rotation; retry after 15 minutes",
            "retry_status": "Retry Pending",
        },
        {
            "failure_id": "FAIL-003",
            "type": "Authentication Expired",
            "source": "SonarQube",
            "description": "SonarQube auth token expired — SAST evidence pull failed",
            "severity": "Medium",
            "impact": "AppSec gate evidence missing for Mobile Banking",
            "affected_applications": "Mobile Banking",
            "remediation": "Renew SonarQube service account token in Integrations Hub",
            "retry_status": "Queued",
        },
        {
            "failure_id": "FAIL-004",
            "type": "Service Timeout",
            "source": "ServiceNow",
            "description": "ServiceNow GRC API timeout after 30s",
            "severity": "Medium",
            "impact": "DPSC control mapping delayed for Payments",
            "affected_applications": "Payments",
            "remediation": "Increase timeout window; schedule off-peak retry",
            "retry_status": "Retry Pending",
        },
        {
            "failure_id": "FAIL-005",
            "type": "Scan Delayed",
            "source": "Tripwire",
            "description": "Tripwire integrity scan delayed — agent queue backlog",
            "severity": "Low",
            "impact": "OS Baselining evidence 4 hours late for UPI",
            "affected_applications": "UPI",
            "remediation": "Clear Tripwire agent queue; run manual integrity scan",
            "retry_status": "Scheduled",
        },
        {
            "failure_id": "FAIL-006",
            "type": "Missing Evidence Pull",
            "source": "Checkmarx",
            "description": "Checkmarx project mapping missing for Loan Origination",
            "severity": "Medium",
            "impact": "AppSec evidence not collected for loan portal",
            "affected_applications": "Loan Origination",
            "remediation": "Map Checkmarx project ID in onboarding pipeline",
            "retry_status": "Manual Required",
        },
        {
            "failure_id": "FAIL-007",
            "type": "Partial Collection",
            "source": "CMDB Agent",
            "description": "CMDB baselining agent returned partial asset inventory",
            "severity": "Low",
            "impact": "3 servers missing from OS Baselining scope",
            "affected_applications": "Cards",
            "remediation": "Sync CMDB discovery scope with ECS asset registry",
            "retry_status": "Retry Pending",
        },
    ]
    return ecs_state.scheduler_failures


def upcoming_plan() -> list[dict]:
    slots = [
        ("Tomorrow 02:00 AM", "Net Banking + PCI DSS", 142, 18, None),
        ("Tomorrow 06:00 AM", "All Applications — DPSC + CSITE", 386, 42, None),
        ("Tomorrow 12:00 PM", "Mobile Banking + AppSec", 98, 14, "SonarQube token renewal required"),
        ("Tomorrow 06:00 PM", "Treasury + Prisma Cloud", 76, 22, "Prisma API maintenance window"),
        ("May 25 02:00 AM", "Enterprise Wide — Full Sync", 512, 55, None),
    ]
    rows = []
    for i, (when, target, ev_count, runtime, warn) in enumerate(slots):
        rows.append({
            "schedule": when,
            "target": target,
            "frameworks": target.split("—")[-1].strip() if "—" in target else "Multi-framework",
            "expected_evidence": ev_count,
            "estimated_runtime_min": runtime,
            "dependency_warning": warn,
        })
    return rows


def compliance_impact() -> dict:
    return {
        "controls_validated_yesterday": 317,
        "manual_effort_saved_hours": 48,
        "compliance_uplift_pct": 3.2,
        "pending_human_reviews": 61,
        "reuse_savings_hours": 22,
        "auto_mapped_controls": 89,
    }


def integration_health() -> list[dict]:
    statuses = [
        ("ServiceNow", "Healthy", "Last sync 6m ago"),
        ("SharePoint", "Delayed", "Folder timeout on Net Banking"),
        ("Teams", "Healthy", "Notification webhooks OK"),
        ("Confluence", "Healthy", "Policy docs synced"),
        ("Jira", "Healthy", "Remediation tickets linked"),
        ("Prisma Cloud", "Retry Pending", "API unavailable 18:00 run"),
        ("SonarQube", "Authentication Issue", "Token expired"),
        ("Checkmarx", "Healthy", "SAST projects mapped"),
        ("Tripwire", "Delayed", "Agent queue backlog"),
    ]
    return [
        {"name": n, "status": s, "detail": d} for n, s, d in statuses
    ]


def build_scheduler_intelligence(paused: bool = False) -> dict:
    return {
        "yesterday_summary": yesterday_summary(),
        "cron_timeline": cron_timeline(),
        "application_scans": application_scans(),
        "run_history": run_history(),
        "failures": scheduler_failures(),
        "upcoming_plan": upcoming_plan(),
        "compliance_impact": compliance_impact(),
        "integration_health": integration_health(),
        "paused": paused,
        "live_status": "Paused" if paused else "Running",
    }
