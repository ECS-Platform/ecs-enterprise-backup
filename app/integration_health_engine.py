"""Framework-aware integration health rows, filtering, and analytics for Operations → Integrations."""

from __future__ import annotations

from app.integrations_module import get_integrations_hub_dashboard

ALL_FRAMEWORKS = [
    "PCI DSS", "DPSC", "OS Baselining", "DB Baselining", "Nginx Baselining",
    "AppSec", "VAPT", "CSITE", "ITTP",
]

INTEGRATION_STATUSES = [
    "Healthy", "Partial", "Failed", "Pending Setup", "Retry Pending", "Auth Expired", "Sync Delayed",
]

_APP_OWNERS: dict[str, str] = {
    "Net Banking": "R. Mehta",
    "Mobile Banking": "A. Sharma",
    "UPI": "P. Nair",
    "Treasury": "A. Sharma",
    "Loan System": "V. Rao",
    "Payments": "K. Iyer",
    "Wealth Portal": "V. Rao",
    "Internet Banking": "A. Sharma",
    "Card Platform": "R. Mehta",
    "Core Banking": "A. Sharma",
    "CBS Oracle": "A. Sharma",
    "Oracle Core DB": "S. Banerjee",
    "Retail Banking": "R. Mehta",
    "UPI Gateway": "P. Nair",
    "Mobile Banking Edge": "A. Sharma",
    "Payments DB": "K. Iyer",
}

_CONNECTOR_META: dict[str, dict] = {
    "ServiceNow GRC": {
        "purpose": "GRC control & exception tracking",
        "evidence_type": "Control attestations",
        "frameworks": ["ITPP", "CSITE", "PCI DSS"],
    },
    "ServiceNow CMDB": {
        "purpose": "Application & asset discovery",
        "evidence_type": "CMDB inventory export",
        "frameworks": ["PCI DSS", "OS Baselining", "DB Baselining", "CSITE", "ITPP"],
    },
    "SharePoint Evidence Library": {
        "purpose": "Firewall evidence archive",
        "evidence_type": "Firewall exports",
        "frameworks": ["PCI DSS", "DPSC", "ITPP", "CSITE", "VAPT"],
    },
    "Microsoft Teams Governance": {
        "purpose": "Approval & escalation threads",
        "evidence_type": "Workflow approvals",
        "frameworks": ["ITPP", "CSITE"],
    },
    "Confluence Governance Wiki": {
        "purpose": "Policy & SOP attestation",
        "evidence_type": "Policy documents",
        "frameworks": ["ITPP", "DPSC", "CSITE"],
    },
    "Jira Security Remediation": {
        "purpose": "Vulnerability remediation tracking",
        "evidence_type": "Remediation tickets",
        "frameworks": ["AppSec", "VAPT", "PCI DSS"],
    },
    "Prisma Cloud CSPM": {
        "purpose": "Cloud posture management",
        "evidence_type": "CSPM findings",
        "frameworks": ["CSITE", "OS Baselining", "DB Baselining", "PCI DSS"],
    },
    "Tripwire Enterprise": {
        "purpose": "Linux CIS validation",
        "evidence_type": "Host hardening scan",
        "frameworks": ["OS Baselining", "Nginx Baselining", "ITPP"],
    },
    "SonarQube Enterprise": {
        "purpose": "SAST quality gate",
        "evidence_type": "SAST findings",
        "frameworks": ["AppSec", "VAPT"],
    },
    "Checkmarx SAST": {
        "purpose": "Secure coding analysis",
        "evidence_type": "SAST report",
        "frameworks": ["AppSec"],
    },
    "Splunk Enterprise SIEM": {
        "purpose": "Log review & SIEM monitoring",
        "evidence_type": "SIEM use-case export",
        "frameworks": ["PCI DSS", "CSITE"],
    },
    "BMC Helix CMDB": {
        "purpose": "Legacy asset inventory",
        "evidence_type": "Asset relationship graph",
        "frameworks": ["OS Baselining", "DB Baselining", "ITPP"],
    },
}

# Curated issue rows — realistic banking demo scenarios
_ISSUE_ROWS: list[dict] = [
    {
        "framework": "OS Baselining", "application": "Treasury", "connector": "Tripwire Enterprise",
        "issue": "Agent offline on 4 Linux hosts", "impact": "OS baseline evidence not collected",
        "health": "Failed", "sync_status": "Retry Pending", "risk": "High",
        "recommended_action": "Restart Tripwire collectors",
        "timestamp": "2026-05-24 05:58 UTC",
    },
    {
        "framework": "PCI DSS", "application": "Net Banking", "connector": "SharePoint Evidence Library",
        "issue": "API timeout after 30s", "impact": "Q2 evidence upload delayed",
        "health": "Partial", "sync_status": "Partial", "risk": "Medium",
        "recommended_action": "Increase timeout + retry",
        "timestamp": "2026-05-24 06:08 UTC",
    },
    {
        "framework": "AppSec", "application": "Loan System", "connector": "SonarQube Enterprise",
        "issue": "Quality gate project ID mismatch — SAST evidence not auto-imported",
        "impact": "AppSec gate evidence blocked", "health": "Failed", "sync_status": "Retry Pending",
        "risk": "High", "recommended_action": "Map SonarQube project ID in onboarding pipeline",
        "timestamp": "2026-05-24 06:02 UTC",
    },
    {
        "framework": "AppSec", "application": "Mobile Banking", "connector": "Jira Security Remediation",
        "issue": "Webhook auth token expired — 2 failed sync batches",
        "impact": "Remediation ticket sync stalled", "health": "Failed", "sync_status": "Auth Expired",
        "risk": "High", "recommended_action": "Rotate Jira webhook token",
        "timestamp": "2026-05-24 06:05 UTC",
    },
    {
        "framework": "VAPT", "application": "Loan System", "connector": "Jira Security Remediation",
        "issue": "Project key LOAN-SEC not mapped — remediation tickets not syncing",
        "impact": "VAPT closure evidence missing", "health": "Failed", "sync_status": "Retry Pending",
        "risk": "High", "recommended_action": "Configure LOAN-SEC project mapping",
        "timestamp": "2026-05-24 06:05 UTC",
    },
    {
        "framework": "OS Baselining", "application": "Treasury", "connector": "BMC Helix CMDB",
        "issue": "Legacy asset class not in scope — relationship graph incomplete",
        "impact": "Host inventory incomplete for baseline scope", "health": "Failed",
        "sync_status": "Failed", "risk": "Critical",
        "recommended_action": "Expand CMDB asset class filter",
        "timestamp": "2026-05-23 18:00 UTC",
    },
    {
        "framework": "DB Baselining", "application": "Oracle Core DB", "connector": "BMC Helix CMDB",
        "issue": "API rate limit exceeded — partial sync only",
        "impact": "DB asset mapping incomplete", "health": "Partial", "sync_status": "Sync Delayed",
        "risk": "High", "recommended_action": "Schedule off-peak full sync",
        "timestamp": "2026-05-23 18:00 UTC",
    },
    {
        "framework": "CSITE", "application": "Payments", "connector": "Prisma Cloud CSPM",
        "issue": "Cloud account tag PAY-PROD missing — workload scope incomplete",
        "impact": "CSPM evidence scope gap", "health": "Partial", "sync_status": "Partial",
        "risk": "Medium", "recommended_action": "Apply PAY-PROD tag to production workloads",
        "timestamp": "2026-05-24 06:00 UTC",
    },
    {
        "framework": "PCI DSS", "application": "Wealth Portal", "connector": "SharePoint Evidence Library",
        "issue": "Document library ACL — service account lacks read on /audit folder",
        "impact": "Evidence collection blocked for Wealth Portal", "health": "Failed",
        "sync_status": "Failed", "risk": "High",
        "recommended_action": "Grant service account read on audit library",
        "timestamp": "2026-05-24 06:08 UTC",
    },
    {
        "framework": "Nginx Baselining", "application": "Net Banking", "connector": "Tripwire Enterprise",
        "issue": "WAF baseline drift on ingress tier — 3 rule deviations",
        "impact": "Nginx hardening evidence incomplete", "health": "Partial", "sync_status": "Sync Delayed",
        "risk": "Medium", "recommended_action": "Reconcile WAF rules with approved baseline",
        "timestamp": "2026-05-24 05:58 UTC",
    },
    {
        "framework": "DPSC", "application": "Mobile Banking", "connector": "Confluence Governance Wiki",
        "issue": "Consent policy page not indexed — privacy attestation gap",
        "impact": "DPSC consent evidence not collected", "health": "Partial", "sync_status": "Partial",
        "risk": "Medium", "recommended_action": "Re-index consent policy wiki space",
        "timestamp": "2026-05-24 05:50 UTC",
    },
    {
        "framework": "ITPP", "application": "Net Banking", "connector": "ServiceNow GRC",
        "issue": "DR drill ticket not linked to control ITPP-DR-02",
        "impact": "DR evidence not mapped to ITPP controls", "health": "Partial", "sync_status": "Retry Pending",
        "risk": "Medium", "recommended_action": "Link DR drill record in ServiceNow GRC",
        "timestamp": "2026-05-24 06:12 UTC",
    },
    {
        "framework": "PCI DSS", "application": "Net Banking", "connector": "Splunk Enterprise SIEM",
        "issue": "Daily log review use-case export delayed 6h",
        "impact": "PCI log review evidence stale", "health": "Partial", "sync_status": "Sync Delayed",
        "risk": "Medium", "recommended_action": "Verify Splunk scheduled search job",
        "timestamp": "2026-05-24 05:50 UTC",
    },
    {
        "framework": "AppSec", "application": "Wealth Portal", "connector": "Checkmarx SAST",
        "issue": "SAST token expired — scan gate authentication failed",
        "impact": "Secure coding evidence not imported", "health": "Failed", "sync_status": "Auth Expired",
        "risk": "High", "recommended_action": "Renew Checkmarx API token",
        "timestamp": "2026-05-24 05:52 UTC",
    },
    {
        "framework": "VAPT", "application": "Internet Banking", "connector": "SonarQube Enterprise",
        "issue": "External VA scan pending — integration healthy but scan overdue",
        "impact": "VAPT evidence window exceeded", "health": "Partial", "sync_status": "Sync Delayed",
        "risk": "High", "recommended_action": "Schedule external VA scan",
        "timestamp": "2026-05-24 06:02 UTC",
    },
]

_HEALTHY_SAMPLES: list[dict] = [
    {"framework": "PCI DSS", "application": "Card Platform", "connector": "ServiceNow CMDB", "sync_status": "Healthy"},
    {"framework": "CSITE", "application": "Retail Banking", "connector": "Splunk Enterprise SIEM", "sync_status": "Healthy"},
    {"framework": "DB Baselining", "application": "Payments DB", "connector": "Prisma Cloud CSPM", "sync_status": "Healthy"},
    {"framework": "OS Baselining", "application": "Core Banking", "connector": "Tripwire Enterprise", "sync_status": "Healthy"},
    {"framework": "AppSec", "application": "Mobile Banking", "connector": "Checkmarx SAST", "sync_status": "Healthy"},
    {"framework": "ITPP", "application": "Treasury", "connector": "SharePoint Evidence Library", "sync_status": "Healthy"},
    {"framework": "DPSC", "application": "Payments", "connector": "Confluence Governance Wiki", "sync_status": "Healthy"},
    {"framework": "Nginx Baselining", "application": "UPI Gateway", "connector": "Prisma Cloud CSPM", "sync_status": "Healthy"},
    {"framework": "VAPT", "application": "Net Banking", "connector": "Jira Security Remediation", "sync_status": "Healthy"},
    {"framework": "PCI DSS", "application": "Mobile Banking", "connector": "Microsoft Teams Governance", "sync_status": "Healthy"},
]


def _owner(app: str) -> str:
    return _APP_OWNERS.get(app, "R. Mehta")


def _enrich_row(base: dict) -> dict:
    conn = base["connector"]
    meta = _CONNECTOR_META.get(conn, {"purpose": "Evidence integration", "evidence_type": "Governance artefact", "frameworks": ALL_FRAMEWORKS})
    fw = base.get("framework") or meta["frameworks"][0]
    app = base["application"]
    health = base.get("health", "Healthy")
    sync = base.get("sync_status", "Healthy")
    risk = base.get("risk", "Low" if health == "Healthy" else "Medium")
    risk_filter = risk if risk in ("Critical", "High", "Medium", "Low") else (
        "High" if health == "Failed" else "Medium"
    )

    return {
        "timestamp": base.get("timestamp", "2026-05-24 06:00 UTC"),
        "framework": fw,
        "application": app,
        "connector": conn,
        "purpose": meta["purpose"],
        "evidence_type": meta["evidence_type"],
        "health": health,
        "issue": base.get("issue", "—"),
        "impact": base.get("impact", "No impact — integration operating normally"),
        "owner": _owner(app),
        "recommended_action": base.get("recommended_action", "No action required"),
        "sync_status": sync,
        "risk": risk_filter,
        "status": sync if sync in INTEGRATION_STATUSES else health,
    }


def build_integration_health_rows() -> list[dict]:
    rows = [_enrich_row(r) for r in _ISSUE_ROWS]
    for sample in _HEALTHY_SAMPLES:
        rows.append(_enrich_row({
            **sample,
            "health": "Healthy",
            "issue": "—",
            "impact": "Evidence flow active",
            "recommended_action": "Monitor scheduled sync",
            "risk": "Low",
        }))
    return rows


def _filter_rows(rows: list[dict], filters: dict | None = None) -> list[dict]:
    if not filters:
        return rows
    out = rows
    fw = filters.get("framework", "")
    if fw and not fw.startswith("All "):
        out = [r for r in out if r["framework"] == fw]
    app = filters.get("application", "")
    if app and not app.startswith("All "):
        out = [r for r in out if r["application"] == app]
    risk = filters.get("risk", "")
    if risk and not risk.startswith("All "):
        if risk == "High":
            out = [r for r in out if r["risk"] in ("High", "Critical")]
        else:
            out = [r for r in out if r["risk"] == risk]
    status = filters.get("status", "")
    if status and not status.startswith("All "):
        out = [r for r in out if r["status"] == status or r["health"] == status or r["sync_status"] == status]
    owner = filters.get("owner", "")
    if owner and not owner.startswith("All "):
        out = [r for r in out if r["owner"] == owner]
    return out


def compute_kpis(rows: list[dict], connectors: list[dict]) -> list[dict]:
    active_connectors = len({r["connector"] for r in rows})
    healthy = sum(1 for r in rows if r["health"] == "Healthy")
    failed = sum(1 for r in rows if r["health"] == "Failed")
    blocked = sum(1 for r in rows if r["health"] in ("Failed", "Partial") and r["issue"] != "—")
    open_issues = sum(1 for r in rows if r["issue"] != "—")
    return [
        {"label": "Active Connectors", "value": active_connectors, "tone": "primary", "id": "kpi-connectors"},
        {"label": "Healthy Integrations", "value": healthy, "tone": "success", "id": "kpi-healthy"},
        {"label": "Failed Syncs", "value": failed, "tone": "danger", "id": "kpi-failed"},
        {"label": "Evidence Flows", "value": len(rows), "tone": "info", "id": "kpi-flows"},
        {"label": "Open Connector Issues", "value": open_issues, "tone": "warning", "id": "kpi-issues"},
        {"label": "Blocked Evidence", "value": blocked, "tone": "danger", "id": "kpi-blocked"},
    ]


def connector_usage_bars(rows: list[dict]) -> list[dict]:
    counts: dict[str, set[str]] = {}
    for r in rows:
        short = r["connector"].split()[0]
        if "SharePoint" in r["connector"]:
            short = "SharePoint"
        elif "ServiceNow" in r["connector"]:
            short = "ServiceNow" if "GRC" in r["connector"] else "ServiceNow CMDB"
        elif "Tripwire" in r["connector"]:
            short = "Tripwire"
        elif "SonarQube" in r["connector"]:
            short = "SonarQube"
        elif "Checkmarx" in r["connector"]:
            short = "Checkmarx"
        elif "Prisma" in r["connector"]:
            short = "Prisma"
        elif "Splunk" in r["connector"]:
            short = "Splunk"
        counts.setdefault(short, set()).add(r["application"])
    return sorted(
        [{"connector": k, "application_count": len(v), "applications": sorted(v)} for k, v in counts.items()],
        key=lambda x: -x["application_count"],
    )


def health_distribution(rows: list[dict]) -> list[dict]:
    buckets = {"Healthy": 0, "Partial": 0, "Failed": 0, "Pending": 0}
    for r in rows:
        h = r["health"]
        if h == "Healthy":
            buckets["Healthy"] += 1
        elif h == "Partial":
            buckets["Partial"] += 1
        elif h == "Failed":
            buckets["Failed"] += 1
        else:
            buckets["Pending"] += 1
    return [{"label": k, "count": v} for k, v in buckets.items() if v > 0]


def framework_dependency_map(rows: list[dict]) -> list[dict]:
    dep: dict[str, set[str]] = {}
    for r in rows:
        dep.setdefault(r["framework"], set()).add(r["connector"].split()[0] if "SharePoint" not in r["connector"] else "SharePoint")
    result = []
    for fw in ALL_FRAMEWORKS:
        conns = dep.get(fw, set())
        if conns:
            result.append({"framework": fw, "connectors": sorted(conns)})
    return result


def build_integration_health_dashboard(filters: dict | None = None) -> dict:
    hub = get_integrations_hub_dashboard()
    all_rows = build_integration_health_rows()
    filtered = _filter_rows(all_rows, filters)
    connectors = hub["connectors"]

    return {
        "health_rows": filtered,
        "all_health_rows": all_rows,
        "kpis": compute_kpis(filtered, connectors),
        "connector_usage_bars": connector_usage_bars(filtered),
        "health_distribution": health_distribution(filtered),
        "framework_dependencies": framework_dependency_map(filtered),
        "connectors": connectors,
        "sync_jobs": hub.get("sync_jobs", []),
        "event_logs": [],
        "filter_options": {
            "frameworks": ["All Frameworks"] + ALL_FRAMEWORKS,
            "applications": ["All Applications"] + sorted({r["application"] for r in all_rows}),
            "risks": ["All Risk", "Critical", "High", "Medium", "Low"],
            "statuses": ["All Status"] + INTEGRATION_STATUSES,
            "owners": ["All Owners"] + sorted({r["owner"] for r in all_rows}),
        },
    }
