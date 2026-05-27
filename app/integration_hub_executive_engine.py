"""Enterprise Integration Command Center — executive dashboard data engine."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from app.integrations_module import get_integration_dashboard
from app.operations_catalog import ALL_FRAMEWORKS, BANKING_APPLICATIONS

CONNECTOR_CHIPS = [
    "SharePoint", "ServiceNow", "Jira", "Prisma", "SonarQube",
    "Checkmarx", "Tripwire", "Confluence", "Teams", "CMDB",
]

_PRIMARY_CONNECTORS = {
    "ServiceNow": "ServiceNow GRC",
    "SharePoint": "SharePoint Evidence Library",
    "Jira": "Jira Security Remediation",
    "Prisma": "Prisma Cloud CSPM",
    "SonarQube": "SonarQube Enterprise",
    "Checkmarx": "Checkmarx SAST",
    "Tripwire": "Tripwire Enterprise",
    "Confluence": "Confluence Governance Wiki",
    "Teams": "Microsoft Teams Governance",
    "CMDB": "ServiceNow CMDB",
}

_FRAMEWORK_HINTS: dict[str, list[str]] = {
    "ServiceNow GRC": ["ITPP", "PCI DSS", "AppSec", "VAPT"],
    "SharePoint Evidence Library": ["PCI DSS", "ITPP", "DPSC", "AppSec"],
    "Jira Security Remediation": ["AppSec", "VAPT", "PCI DSS"],
    "Prisma Cloud CSPM": ["CSITE", "PCI DSS", "Cloud Risk"],
    "Tripwire Enterprise": ["OS Baselining", "Nginx Baselining", "ITPP"],
    "SonarQube Enterprise": ["AppSec", "VAPT"],
    "Checkmarx SAST": ["AppSec", "VAPT"],
    "Confluence Governance Wiki": ["ITPP", "DPSC", "Regulatory Mapping"],
    "Microsoft Teams Governance": ["ITPP", "Workflow"],
    "ServiceNow CMDB": ["ITPP", "CMDB / Asset Inventory"],
    "Splunk Enterprise SIEM": ["CSITE", "PCI DSS"],
    "BMC Helix CMDB": ["CMDB / Asset Inventory", "ITPP"],
}

_LOG_MESSAGES = [
    ("Info", "Scheduled sync completed — {n} records ingested"),
    ("Info", "Evidence batch validated for {app}"),
    ("Warning", "Rate limit approaching — throttling sync for {app}"),
    ("Error", "Sync job failed — authentication token expired for {app}"),
    ("Error", "Partial sync — {n} records skipped due to schema mismatch"),
    ("Critical", "Connector unreachable — circuit breaker open for {app}"),
    ("Info", "Business process webhook delivered — CAB approval for {app}"),
    ("Warning", "Stale evidence detected — re-pull scheduled for {app}"),
]

_SEVERITIES = ["Info", "Warning", "Error", "Critical"]


def _short_label(name: str, ctype: str) -> str:
    if "SharePoint" in name or ctype == "SharePoint":
        return "SharePoint"
    if "ServiceNow GRC" in name:
        return "ServiceNow"
    if "CMDB" in name or ctype == "CMDB":
        return "CMDB"
    if ctype == "Jira":
        return "Jira"
    if "Prisma" in name:
        return "Prisma"
    if "SonarQube" in name:
        return "SonarQube"
    if "Checkmarx" in name:
        return "Checkmarx"
    if "Tripwire" in name:
        return "Tripwire"
    if ctype == "Confluence":
        return "Confluence"
    if ctype == "Teams":
        return "Teams"
    if ctype == "SIEM":
        return "Splunk"
    return ctype.split()[0] if ctype else name.split()[0]


def _health_status(c: dict) -> str:
    challenges = c.get("sync_challenges", [])
    if any(ch.get("severity") == "Critical" and ch.get("status") == "Open" for ch in challenges):
        return "Critical"
    if c.get("sync_health") == "Degraded" or c.get("api_status") == "Degraded":
        if any(ch.get("severity") == "High" and ch.get("status") == "Open" for ch in challenges):
            return "Warning"
        return "Warning"
    if any(ch.get("severity") == "High" and ch.get("status") == "Open" for ch in challenges):
        return "Warning"
    if c.get("failed_syncs", 0) >= 4:
        return "Critical"
    if c.get("failed_syncs", 0) >= 2:
        return "Warning"
    return "Healthy"


def _success_pct(c: dict) -> int:
    base = 97 if _health_status(c) == "Healthy" else 84 if _health_status(c) == "Warning" else 62
    return max(55, min(99, base - c.get("failed_syncs", 0) * 3))


def _seed(key: str) -> int:
    return int(hashlib.md5(key.encode()).hexdigest()[:8], 16)


def _evidence_today(c: dict) -> int:
    return max(1, (c.get("imported_evidence", 0) // 14) + (c.get("failed_syncs", 0) == 0))


def _frameworks_for(c: dict) -> list[str]:
    hinted = _FRAMEWORK_HINTS.get(c["name"], [])
    mapped = [m for m in c.get("maps_to", []) if m in ALL_FRAMEWORKS or "CMDB" in m or "Cloud" in m]
    out = list(dict.fromkeys(hinted + mapped))
    return out[:5] if out else ["ITPP"]


def _generate_logs(connectors: list[dict]) -> list[dict]:
    logs: list[dict] = []
    now = datetime.now(timezone.utc)
    idx = 0
    for c in connectors:
        label = _short_label(c["name"], c.get("type", ""))
        apps = c.get("applications_connected", ["Net Banking"])
        for day in range(14):
            for slot in range(2):
                idx += 1
                sev_tpl = _LOG_MESSAGES[_seed(f"{c['name']}-{idx}") % len(_LOG_MESSAGES)]
                sev, tpl = sev_tpl
                app = apps[_seed(f"app-{idx}") % len(apps)]
                fw = _frameworks_for(c)[0]
                ts = (now - timedelta(hours=idx * 3 + day * 6)).strftime("%Y-%m-%d %H:%M UTC")
                logs.append({
                    "id": f"LOG-{idx:04d}",
                    "connector": label,
                    "connector_full": c["name"],
                    "application": app,
                    "framework": fw,
                    "severity": sev,
                    "message": tpl.format(app=app, n=_seed(f"n-{idx}") % 40 + 5),
                    "timestamp": ts,
                })
    logs.sort(key=lambda x: x["timestamp"], reverse=True)
    return logs


def _sync_jobs(connectors: list[dict]) -> list[dict]:
    rows = []
    for c in connectors:
        label = _short_label(c["name"], c.get("type", ""))
        for app in c.get("applications_connected", [])[:6]:
            fw = _frameworks_for(c)[_seed(app + c["name"]) % len(_frameworks_for(c))]
            st = "Success" if _health_status(c) == "Healthy" else "Partial" if _health_status(c) == "Warning" else "Failed"
            rows.append({
                "connector": label,
                "connector_full": c["name"],
                "application": app,
                "framework": fw,
                "job_type": "Evidence Pull" if c.get("imported_evidence") else "Metadata Sync",
                "last_run": c.get("last_sync", "—"),
                "status": st,
                "records": c.get("records_pulled", 0) // max(1, len(c.get("applications_connected", [1]))),
                "duration_sec": 12 + _seed(app) % 90,
            })
    return rows


def _evidence_rows(connectors: list[dict]) -> list[dict]:
    rows = []
    for c in connectors:
        label = _short_label(c["name"], c.get("type", ""))
        for ev in c.get("ingestion", [])[:5]:
            for app in c.get("applications_connected", [])[:3]:
                fw = _frameworks_for(c)[_seed(ev + app) % len(_frameworks_for(c))]
                rows.append({
                    "connector": label,
                    "connector_full": c["name"],
                    "application": app,
                    "framework": fw,
                    "evidence_type": ev,
                    "imported_today": _evidence_today(c) // max(1, len(c.get("ingestion", [1]))),
                    "success_pct": _success_pct(c),
                    "status": "Active" if c.get("evidence_collection_enabled") else "Blocked",
                })
    return rows


def _connector_detail(c: dict, logs: list[dict]) -> dict:
    label = _short_label(c["name"], c.get("type", ""))
    status = _health_status(c)
    conn_logs = [lg for lg in logs if lg["connector_full"] == c["name"]][:10]
    failed_jobs = [
        {"job": f"Sync-{i+1}", "application": app, "error": ch.get("issue", "Sync failure"), "when": c.get("last_sync", "—")}
        for i, ch in enumerate(c.get("sync_challenges", [])[:5])
        for app in [ch.get("application", "Net Banking")]
    ]
    if not failed_jobs and c.get("failed_syncs", 0):
        failed_jobs = [{
            "job": "Sync-Retry",
            "application": c.get("applications_connected", ["Net Banking"])[0],
            "error": f"{c['failed_syncs']} failed sync batch(es) in last cycle",
            "when": c.get("last_sync", "—"),
        }]
    timeline = []
    for i, lg in enumerate(conn_logs[:6]):
        timeline.append({"time": lg["timestamp"], "event": lg["message"][:60], "status": lg["severity"]})
    return {
        "name": c["name"],
        "label": label,
        "status": status,
        "applications": c.get("applications_connected", []),
        "frameworks": _frameworks_for(c),
        "evidence_types": c.get("ingestion", []),
        "sync_timeline": timeline,
        "failed_jobs": failed_jobs,
        "open_issues": [
            {**ch, "connector": label, "evidence_impact": "Blocked" if not ch.get("evidence_collection_ok") else "Low"}
            for ch in c.get("sync_challenges", []) if ch.get("status") == "Open"
        ],
        "business_processes": c.get("business_processes", []),
        "evidence_collection": "Enabled" if c.get("evidence_collection_enabled") else "Blocked",
        "sync_activities": conn_logs,
        "success_pct": _success_pct(c),
        "last_sync": c.get("last_sync", "—"),
        "application_count": c.get("application_count", 0),
    }


def _filter_match(row: dict, framework: str, application: str) -> bool:
    if framework and not framework.startswith("All ") and row.get("framework") and row["framework"] != framework:
        if framework not in str(row.get("frameworks", "")):
            return False
    if application and not application.startswith("All "):
        apps = row.get("applications") or row.get("applications_connected")
        if apps and application not in apps:
            if row.get("application") and row["application"] != application:
                return False
        elif row.get("application") and row["application"] != application:
            return False
    return True


def build_integration_hub_executive_view(role: str = "owner") -> dict:
    dash = get_integration_dashboard()
    connectors = dash["connectors"]
    logs = _generate_logs(connectors)

    health_matrix = []
    for chip in CONNECTOR_CHIPS:
        full = _PRIMARY_CONNECTORS.get(chip)
        c = next((x for x in connectors if x["name"] == full), None)
        if not c:
            c = next((x for x in connectors if chip in x.get("type", "") or chip in x["name"]), None)
        if not c:
            continue
        health_matrix.append({
            "connector": chip,
            "connector_full": c["name"],
            "status": _health_status(c),
            "apps": c.get("application_count", 0),
            "last_sync": c.get("last_sync", "—"),
            "failures": c.get("failed_syncs", 0),
            "frameworks": _frameworks_for(c),
            "applications": c.get("applications_connected", []),
        })

    connector_status = []
    for c in connectors:
        label = _short_label(c["name"], c.get("type", ""))
        connector_status.append({
            "connector": label,
            "connector_full": c["name"],
            "status": _health_status(c),
            "applications": c.get("application_count", 0),
            "frameworks": ", ".join(_frameworks_for(c)[:3]),
            "framework_list": _frameworks_for(c),
            "applications_list": c.get("applications_connected", []),
            "last_sync": c.get("last_sync", "—"),
            "success_pct": _success_pct(c),
            "failures": c.get("failed_syncs", 0),
        })

    issue_rows = []
    for c in connectors:
        label = _short_label(c["name"], c.get("type", ""))
        for ch in c.get("sync_challenges", []):
            fw = _frameworks_for(c)[0]
            issue_rows.append({
                "connector": label,
                "connector_full": c["name"],
                "application": ch["application"],
                "framework": fw,
                "issue": ch["issue"],
                "severity": ch["severity"],
                "status": ch["status"],
                "evidence_impact": "Blocked" if not ch.get("evidence_collection_ok") else "Low",
            })
    issue_rows.sort(key=lambda x: {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}.get(x["severity"], 4))

    process_cards = []
    seen = set()
    for c in connectors:
        label = _short_label(c["name"], c.get("type", ""))
        if label in seen:
            continue
        seen.add(label)
        process_cards.append({
            "connector": label,
            "connector_full": c["name"],
            "processes": c.get("business_processes", []),
            "applications": c.get("application_count", 0),
            "applications_list": c.get("applications_connected", []),
            "frameworks": _frameworks_for(c),
            "evidence_collection": "Enabled" if c.get("evidence_collection_enabled") else "Blocked",
        })

    bars_map: dict[str, int] = {}
    for c in connectors:
        label = _short_label(c["name"], c.get("type", ""))
        bars_map[label] = bars_map.get(label, 0) + c.get("application_count", 0)
    bar_chart = [{"connector": k, "count": v} for k, v in sorted(bars_map.items(), key=lambda x: -x[1])]

    healthy = sum(1 for c in connectors if _health_status(c) == "Healthy")
    total_evidence_today = sum(_evidence_today(c) for c in connectors)
    failed = sum(c.get("failed_syncs", 0) for c in connectors)
    open_issues = len([i for i in issue_rows if i["status"] == "Open"])
    healthy_pct = round(healthy / len(connectors) * 100) if connectors else 0

    success_slices = {"success": 0, "partial": 0, "failed": 0}
    for c in connectors:
        st = _health_status(c)
        if st == "Healthy":
            success_slices["success"] += 1
        elif st == "Warning":
            success_slices["partial"] += 1
        else:
            success_slices["failed"] += 1
    total_sl = sum(success_slices.values()) or 1
    evidence_donut = {
        "success_pct": round(success_slices["success"] / total_sl * 100),
        "partial_pct": round(success_slices["partial"] / total_sl * 100),
        "failed_pct": round(success_slices["failed"] / total_sl * 100),
    }

    trend = []
    base = healthy_pct
    for i in range(7):
        d = (datetime.now(timezone.utc) - timedelta(days=6 - i)).strftime("%d %b")
        trend.append({"day": d, "pct": max(72, min(99, base - 3 + i + (i % 2)))})

    details = {c["name"]: _connector_detail(c, logs) for c in connectors}

    return {
        "kpis": [
            {"label": "Active Connectors", "value": len(connectors), "tone": "primary", "hint": "Live enterprise connectors", "icon": "⬡"},
            {"label": "Applications Integrated", "value": sum(c.get("application_count", 0) for c in connectors), "tone": "success", "icon": "◈"},
            {"label": "Evidence Imports Today", "value": total_evidence_today, "tone": "teal", "icon": "▣"},
            {"label": "Failed Syncs", "value": failed, "tone": "danger", "icon": "⚠"},
            {"label": "Open Connector Issues", "value": open_issues, "tone": "warning", "icon": "◉"},
            {"label": "Healthy Integrations %", "value": f"{healthy_pct}%", "tone": "success" if healthy_pct >= 85 else "warning", "icon": "✓"},
        ],
        "connector_chips": CONNECTOR_CHIPS,
        "health_matrix": health_matrix,
        "insights": {
            "bar_chart": bar_chart,
            "evidence_donut": evidence_donut,
            "issue_summary": issue_rows[:5],
            "sync_trend": trend,
        },
        "connector_status": connector_status,
        "sync_monitoring": _sync_jobs(connectors),
        "evidence_collection": _evidence_rows(connectors),
        "business_process_cards": process_cards,
        "open_issues": issue_rows,
        "connector_logs": logs,
        "connector_details": details,
        "connectors": connectors,
        "grouped": dash.get("grouped", {}),
        "rows": connector_status,
        "operations_dataset": {
            "health_matrix": health_matrix,
            "connector_status": connector_status,
            "sync_monitoring": _sync_jobs(connectors),
            "evidence_collection": _evidence_rows(connectors),
            "open_issues": issue_rows,
            "connector_logs": logs,
            "business_process_cards": process_cards,
            "insights": {
                "bar_chart": bar_chart,
                "evidence_donut": evidence_donut,
                "sync_trend": trend,
            },
            "connector_details": details,
            "frameworks": ["All Frameworks"] + ALL_FRAMEWORKS,
            "applications": ["All Applications"] + BANKING_APPLICATIONS,
        },
    }
