"""Enterprise Integrations Hub — ServiceNow, SharePoint, Jira, Prisma, Tripwire, SonarQube, Checkmarx."""

from datetime import datetime, timezone

from modules.operations.engines.evidence_repository import evidence_repository

_connectors = [
    {
        "name": "ServiceNow GRC",
        "type": "ServiceNow",
        "category": "servicenow",
        "status": "Connected",
        "last_sync": "2026-05-24 06:12 UTC",
        "records": 926,
        "records_pulled": 926,
        "failed_syncs": 0,
        "imported_evidence": 142,
        "mapped_controls": 89,
        "api_status": "Healthy",
        "sync_status": "Synced",
        "sync_health": "Healthy",
        "ingestion": ["Incidents", "Problem Records", "RCA", "Change Tickets", "CAB Approvals", "SLA Breaches"],
        "maps_to": ["ITPP", "Incident Management", "Problem Management", "Change Management"],
    },
    {
        "name": "ServiceNow CMDB",
        "type": "ServiceNow",
        "category": "cmdb",
        "status": "Connected",
        "last_sync": "2026-05-24 06:10 UTC",
        "records": 12408,
        "records_pulled": 12408,
        "failed_syncs": 1,
        "imported_evidence": 0,
        "mapped_controls": 156,
        "api_status": "Healthy",
        "sync_status": "Synced",
        "sync_health": "Healthy",
        "ingestion": ["Applications", "Servers", "Relationships"],
        "maps_to": ["CMDB / Asset Inventory"],
    },
    {
        "name": "SharePoint Evidence Library",
        "type": "SharePoint",
        "category": "sharepoint",
        "status": "Connected",
        "last_sync": "2026-05-24 06:08 UTC",
        "records": 1842,
        "records_pulled": 1842,
        "failed_syncs": 0,
        "imported_evidence": 412,
        "mapped_controls": 203,
        "api_status": "Healthy",
        "sync_status": "Synced",
        "sync_health": "Healthy",
        "ingestion": ["Policies", "SOPs", "DR Plans", "Audit Documents", "Evidence Files"],
        "maps_to": ["All Frameworks", "ITPP", "Audit Prep"],
    },
    {
        "name": "Microsoft Teams Governance",
        "type": "Teams",
        "category": "collaboration",
        "status": "Connected",
        "last_sync": "2026-05-24 05:55 UTC",
        "records": 328,
        "records_pulled": 328,
        "failed_syncs": 0,
        "imported_evidence": 45,
        "mapped_controls": 12,
        "api_status": "Healthy",
        "sync_status": "Synced",
        "sync_health": "Healthy",
        "ingestion": ["Approval Discussions", "Audit Threads", "Escalation Chats"],
        "maps_to": ["Workflow", "Executive Escalations"],
    },
    {
        "name": "Confluence Governance Wiki",
        "type": "Confluence",
        "category": "collaboration",
        "status": "Connected",
        "last_sync": "2026-05-24 05:50 UTC",
        "records": 567,
        "records_pulled": 567,
        "failed_syncs": 0,
        "imported_evidence": 78,
        "mapped_controls": 34,
        "api_status": "Healthy",
        "sync_status": "Synced",
        "sync_health": "Healthy",
        "ingestion": ["Policies", "SOPs", "Governance Wiki Pages"],
        "maps_to": ["ITPP", "Regulatory Mapping"],
    },
    {
        "name": "Jira Security Remediation",
        "type": "Jira",
        "category": "jira",
        "status": "Connected",
        "last_sync": "2026-05-24 06:05 UTC",
        "records": 2104,
        "records_pulled": 2104,
        "failed_syncs": 2,
        "imported_evidence": 0,
        "mapped_controls": 67,
        "api_status": "Healthy",
        "sync_status": "Synced",
        "sync_health": "Degraded",
        "ingestion": ["Remediation Tickets", "AppSec Fixes", "Vulnerability Backlog", "Sprint Mappings"],
        "maps_to": ["AppSec", "VAPT", "Cross-Tool Correlation"],
    },
    {
        "name": "Prisma Cloud CSPM",
        "type": "Prisma Cloud",
        "category": "cloud",
        "status": "Connected",
        "last_sync": "2026-05-24 06:00 UTC",
        "records": 8842,
        "records_pulled": 8842,
        "failed_syncs": 0,
        "imported_evidence": 156,
        "mapped_controls": 44,
        "api_status": "Healthy",
        "sync_status": "Synced",
        "sync_health": "Healthy",
        "ingestion": ["Cloud Vulnerabilities", "IAM Findings", "CSPM Findings", "Exposed Storage", "Risky Workloads"],
        "maps_to": ["CSITE", "Cloud Risk Register"],
    },
    {
        "name": "Tripwire Enterprise",
        "type": "Tripwire",
        "category": "tripwire",
        "status": "Connected",
        "last_sync": "2026-05-24 05:58 UTC",
        "records": 3420,
        "records_pulled": 3420,
        "failed_syncs": 1,
        "imported_evidence": 89,
        "mapped_controls": 52,
        "api_status": "Healthy",
        "sync_status": "Synced",
        "sync_health": "Healthy",
        "ingestion": ["Configuration Drift", "Integrity Violations", "Unauthorized Changes", "CIS Deviations"],
        "maps_to": ["OS Baselining", "Nginx Baselining", "ITPP Change Management"],
    },
    {
        "name": "SonarQube Enterprise",
        "type": "SonarQube",
        "category": "appsec",
        "status": "Connected",
        "last_sync": "2026-05-24 06:02 UTC",
        "records": 1567,
        "records_pulled": 1567,
        "failed_syncs": 0,
        "imported_evidence": 234,
        "mapped_controls": 38,
        "api_status": "Healthy",
        "sync_status": "Synced",
        "sync_health": "Healthy",
        "ingestion": ["SAST Findings", "Code Smells", "Secrets Exposure", "Insecure Dependencies", "OWASP Violations"],
        "maps_to": ["AppSec", "VAPT"],
    },
    {
        "name": "Checkmarx SAST",
        "type": "Checkmarx",
        "category": "appsec",
        "status": "Connected",
        "last_sync": "2026-05-24 05:52 UTC",
        "records": 892,
        "records_pulled": 892,
        "failed_syncs": 0,
        "imported_evidence": 178,
        "mapped_controls": 31,
        "api_status": "Healthy",
        "sync_status": "Synced",
        "sync_health": "Healthy",
        "ingestion": ["SAST Findings", "OWASP Top 10", "API Security Issues"],
        "maps_to": ["AppSec"],
    },
    {
        "name": "Splunk Enterprise SIEM",
        "type": "SIEM",
        "category": "siem",
        "status": "Connected",
        "last_sync": "2026-05-24 05:50 UTC",
        "records": 42800,
        "records_pulled": 42800,
        "failed_syncs": 0,
        "imported_evidence": 520,
        "mapped_controls": 67,
        "api_status": "Healthy",
        "sync_status": "Synced",
        "sync_health": "Healthy",
        "ingestion": ["SIEM Alerts", "SOC Events"],
        "maps_to": ["CSITE"],
    },
    {
        "name": "BMC Helix CMDB",
        "type": "CMDB",
        "category": "cmdb",
        "status": "Degraded",
        "last_sync": "2026-05-23 18:00 UTC",
        "records": 8900,
        "records_pulled": 8850,
        "failed_syncs": 3,
        "imported_evidence": 0,
        "mapped_controls": 98,
        "api_status": "Degraded",
        "sync_status": "Retry scheduled",
        "sync_health": "Degraded",
        "ingestion": ["Legacy asset records"],
        "maps_to": ["CMDB / Asset Inventory"],
    },
]

_sync_log: list[dict] = []

_CONNECTOR_APP_MAP: dict[str, list[str]] = {
    "ServiceNow GRC": ["Net Banking", "Mobile Banking", "Payments", "Card Platform", "Retail Banking"],
    "ServiceNow CMDB": ["Net Banking", "UPI", "Treasury", "Core Banking", "CBS Oracle", "Payments DB"],
    "SharePoint Evidence Library": ["Net Banking", "Mobile Banking", "Payments", "UPI", "Card Platform", "Treasury", "Wealth Portal", "Internet Banking"],
    "Microsoft Teams Governance": ["Net Banking", "Mobile Banking", "Payments", "Treasury"],
    "Confluence Governance Wiki": ["Net Banking", "Payments", "ITPP", "CSITE"],
    "Jira Security Remediation": ["Mobile Banking", "Loan System", "UPI", "Internet Banking", "Wealth Portal"],
    "Prisma Cloud CSPM": ["Net Banking", "Payments", "UPI Gateway", "Mobile Banking Edge"],
    "Tripwire Enterprise": ["Net Banking", "Core Banking", "Treasury", "CBS Oracle"],
    "SonarQube Enterprise": ["Mobile Banking", "Internet Banking", "Loan System", "Wealth Portal"],
    "Checkmarx SAST": ["Mobile Banking", "Loan System", "Wealth Portal", "Payments"],
    "Splunk Enterprise SIEM": ["Net Banking", "Payments", "UPI", "Card Platform", "Retail Banking"],
    "BMC Helix CMDB": ["Treasury", "Oracle Core DB"],
}

_CONNECTOR_CHALLENGES: dict[str, list[dict]] = {
    "Jira Security Remediation": [
        {"application": "Loan System", "issue": "Project key LOAN-SEC not mapped — remediation tickets not syncing", "severity": "High", "status": "Open", "evidence_collection_ok": False},
        {"application": "Mobile Banking", "issue": "Webhook auth token expired — 2 failed sync batches", "severity": "Medium", "status": "Resolved", "evidence_collection_ok": True},
    ],
    "BMC Helix CMDB": [
        {"application": "Treasury", "issue": "Legacy asset class not in scope — relationship graph incomplete", "severity": "Critical", "status": "Open", "evidence_collection_ok": False},
        {"application": "Oracle Core DB", "issue": "API rate limit exceeded — partial sync only", "severity": "High", "status": "Monitoring", "evidence_collection_ok": False},
    ],
    "Tripwire Enterprise": [
        {"application": "Treasury", "issue": "Agent offline on 4 Windows hosts — CIS scan stale; drift controls blocked", "severity": "Critical", "status": "Open", "evidence_collection_ok": False},
    ],
    "GitHub Advanced Security": [],
    "SonarQube Enterprise": [
        {"application": "Loan System", "issue": "Quality gate project ID mismatch — SAST evidence not auto-imported", "severity": "High", "status": "Open", "evidence_collection_ok": False},
    ],
    "Prisma Cloud CSPM": [
        {"application": "Payments", "issue": "Cloud account tag PAY-PROD missing — workload scope incomplete", "severity": "Medium", "status": "Resolved", "evidence_collection_ok": True},
    ],
    "SharePoint Evidence Library": [
        {"application": "Wealth Portal", "issue": "Document library ACL — service account lacks read on /audit folder", "severity": "Medium", "status": "Open", "evidence_collection_ok": False},
    ],
}

_BP_BY_CONNECTOR: dict[str, list[str]] = {
    "SharePoint": ["Evidence Repository", "Policy Storage", "Audit Package Export", "Evidence Upload"],
    "Jira": ["Remediation Tracking", "Observation Closure", "Sprint SLA Tracking", "Ticket Sync"],
    "Prisma Cloud": ["CSPM Posture Import", "Cloud Risk Scoring", "Workload Control Mapping"],
    "SonarQube": ["SAST Gate Validation", "Code Quality Evidence", "Observation Closure"],
    "Checkmarx": ["SAST Finding Import", "OWASP Evidence Collection", "Observation Closure"],
    "ServiceNow": ["Observation Closure", "Exception Tracking", "CAB Approval", "Audit Workflow Closure"],
    "Tripwire": ["CIS Drift Detection", "Baseline Validation", "Integrity Monitoring"],
    "Teams": ["Approval Workflow", "Executive Escalation Threads", "Audit Collaboration"],
    "Confluence": ["SOP References", "Policy Attestation", "Governance Wiki Evidence"],
    "Splunk": ["SIEM Use-Case Validation", "SOC Event Evidence"],
    "CMDB": ["Asset Inventory Mapping", "Application Discovery", "Relationship Graph Sync"],
}


def _short_type(connector_type: str) -> str:
    return connector_type.split()[0] if connector_type else "Other"


def _enrich_connector(c: dict) -> dict:
    out = c.copy()
    apps = _CONNECTOR_APP_MAP.get(c["name"], ["Net Banking", "Mobile Banking"])
    out["applications_connected"] = apps
    out["application_count"] = len(apps)
    challenges = _CONNECTOR_CHALLENGES.get(c["name"], [])
    if not challenges and c.get("failed_syncs", 0) > 0:
        challenges = [{
            "application": apps[0],
            "issue": f"Sync failure — {c['failed_syncs']} failed job(s) in last cycle",
            "severity": "High",
            "status": "Retry Pending",
            "evidence_collection_ok": False,
        }]
    out["sync_challenges"] = challenges
    st = _short_type(c.get("type", ""))
    bp_key = next((k for k in _BP_BY_CONNECTOR if k in st or k in c.get("type", "")), "Evidence Collection")
    out["business_processes"] = _BP_BY_CONNECTOR.get(bp_key, ["Evidence Collection", "Control Mapping"])
    out["business_process_count"] = len(out["business_processes"])
    ready = c.get("sync_health") == "Healthy" and not any(
        ch.get("evidence_collection_ok") is False and ch.get("status") == "Open" for ch in challenges
    )
    out["evidence_collection_enabled"] = ready
    out["evidence_collection_note"] = (
        "Evidence pull verified — business processes active"
        if ready else "Evidence collection blocked — resolve application-level sync issue"
    )
    return out


def _build_hub_analytics(connectors: list[dict]) -> dict:
    bars = []
    for c in connectors:
        label = _short_type(c.get("type", c["name"]))
        if c["type"] == "SharePoint":
            label = "SharePoint"
        elif "ServiceNow" in c["name"]:
            label = "ServiceNow" if "GRC" in c["name"] else "ServiceNow CMDB"
        bars.append({
            "connector": label,
            "full_name": c["name"],
            "application_count": c.get("application_count", 0),
            "applications": c.get("applications_connected", []),
        })
    # dedupe bar labels by summing counts for same short label
    merged: dict[str, dict] = {}
    for b in bars:
        k = b["connector"]
        if k not in merged:
            merged[k] = {**b, "applications": list(b["applications"])}
        else:
            merged[k]["application_count"] += b["application_count"]
            merged[k]["applications"] = list(dict.fromkeys(merged[k]["applications"] + b["applications"]))
    bar_chart = sorted(merged.values(), key=lambda x: -x["application_count"])

    pie_slices = []
    for c in connectors:
        for bp in c.get("business_processes", []):
            pie_slices.append({"connector": _short_type(c.get("type", "")), "process": bp, "count": 1})
    process_totals: dict[str, int] = {}
    for s in pie_slices:
        key = f"{s['connector']}::{s['process']}"
        process_totals[key] = process_totals.get(key, 0) + 1
    pie_chart = [{"connector": k.split("::")[0], "process": k.split("::")[1], "count": v} for k, v in process_totals.items()]

    app_process_matrix = []
    for c in connectors:
        for app in c.get("applications_connected", [])[:4]:
            app_process_matrix.append({
                "application": app,
                "connector": _short_type(c.get("type", c["name"])),
                "process_count": c.get("business_process_count", 2),
            })

    issue_rows = []
    for c in connectors:
        for ch in c.get("sync_challenges", []):
            issue_rows.append({
                "connector": c["name"],
                "application": ch["application"],
                "issue": ch["issue"],
                "severity": ch["severity"],
                "status": ch["status"],
                "evidence_collection_ok": ch.get("evidence_collection_ok", c.get("evidence_collection_enabled", False)),
            })

    return {
        "connector_application_bars": bar_chart,
        "business_process_pie": pie_chart,
        "application_process_matrix": app_process_matrix,
        "sync_issue_rows": issue_rows,
    }


def get_integration_dashboard():
    enriched = [_enrich_connector(c) for c in _connectors]
    grouped = {
        "servicenow": [], "sharepoint": [], "collaboration": [], "jira": [],
        "cloud": [], "tripwire": [], "appsec": [], "siem": [], "cmdb": [],
    }
    for c in enriched:
        cat = c.get("category", "servicenow")
        grouped.setdefault(cat, []).append(c)
    return {
        "connectors": enriched,
        "grouped": grouped,
        "sync_log": _sync_log[-10:],
    }


def get_integrations_hub_dashboard():
    dash = get_integration_dashboard()
    connectors = dash["connectors"]
    analytics = _build_hub_analytics(connectors)
    total_evidence = sum(c.get("imported_evidence", 0) for c in connectors)
    failed = sum(c.get("failed_syncs", 0) for c in connectors)
    return {
        **dash,
        **analytics,
        "kpis": [
            {"label": "Connectors", "value": len(connectors), "tone": "primary"},
            {"label": "Applications Connected", "value": sum(c.get("application_count", 0) for c in connectors), "tone": "success"},
            {"label": "Failed Syncs", "value": failed, "tone": "danger"},
            {"label": "Imported Evidence", "value": total_evidence, "tone": "info"},
            {"label": "Open Sync Issues", "value": len(analytics["sync_issue_rows"]), "tone": "warning"},
        ],
    }


def simulate_sync(connector_name: str):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    for c in _connectors:
        if c["name"] == connector_name:
            c["last_sync"] = now
            c["status"] = "Synced"
            c["sync_status"] = "Synced"
            c["api_status"] = "Healthy"
            c["sync_health"] = "Healthy"
            c["failed_syncs"] = max(0, c.get("failed_syncs", 0) - 1)
            c["records_pulled"] = c.get("records", 0) + len(evidence_repository) % 50
            c["imported_evidence"] = c.get("imported_evidence", 0) + 3
            _sync_log.append({"connector": connector_name, "timestamp": now, "status": "Success", "records": 3})
            try:
                from modules.shared.services.ecs_logging import log_integration
                log_integration(connector_name, action="sync", records=3)
            except Exception:
                pass
            return c
    return None


def test_connection(connector_name: str) -> str:
    for c in _connectors:
        if c["name"] == connector_name:
            return f"Connection test passed — {connector_name} API healthy."
    return f"Connector {connector_name} not found."


def retry_failed_sync(connector_name: str) -> str:
    result = simulate_sync(connector_name)
    if result:
        return f"Retry successful for {connector_name}."
    return "Retry failed — connector not found."
