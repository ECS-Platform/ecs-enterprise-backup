"""Enterprise Integrations Hub — ServiceNow, SharePoint, Jira, Prisma, Tripwire, SonarQube, Checkmarx."""

from datetime import datetime, timezone

from app.evidence_repository import evidence_repository

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


def get_integration_dashboard():
    grouped = {
        "servicenow": [], "sharepoint": [], "collaboration": [], "jira": [],
        "cloud": [], "tripwire": [], "appsec": [], "siem": [], "cmdb": [],
    }
    for c in _connectors:
        cat = c.get("category", "servicenow")
        grouped.setdefault(cat, []).append(c.copy())
    return {
        "connectors": [c.copy() for c in _connectors],
        "grouped": grouped,
        "sync_log": _sync_log[-10:],
    }


def get_integrations_hub_dashboard():
    dash = get_integration_dashboard()
    total_evidence = sum(c.get("imported_evidence", 0) for c in _connectors)
    failed = sum(c.get("failed_syncs", 0) for c in _connectors)
    return {
        **dash,
        "kpis": [
            {"label": "Connectors", "value": len(_connectors), "tone": "primary"},
            {"label": "Healthy", "value": len([c for c in _connectors if c.get("sync_health") == "Healthy"]), "tone": "success"},
            {"label": "Failed Syncs", "value": failed, "tone": "danger"},
            {"label": "Imported Evidence", "value": total_evidence, "tone": "info"},
            {"label": "Mapped Controls", "value": sum(c.get("mapped_controls", 0) for c in _connectors), "tone": "primary"},
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
