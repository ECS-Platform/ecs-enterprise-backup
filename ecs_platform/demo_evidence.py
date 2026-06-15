"""Deterministic demo evidence repository — zero external dependencies.

Used as the fallback data source for the Evidence Explorer and Integration
Health pages when the PostgreSQL repository is unavailable (e.g. demo mode with
no psycopg2 / no database). Produces a large, realistic, fully deterministic set
of evidence records spanning the standard SaaS connectors so the UI never shows
"Repository unavailable" or an empty grid.

Pure standard library; safe to import anywhere.
"""

from __future__ import annotations

import hashlib
from datetime import date, timedelta
from typing import Any

# Connectors the demo evidence spans (matches the user's required source list).
DEMO_SOURCES: list[str] = [
    "GitHub", "Jira", "Confluence", "Figma", "Teams",
    "SharePoint", "SonarQube", "Jenkins", "GitLab", "ServiceNow",
]

# Object types per source — realistic evidence artefacts.
_SOURCE_TYPES: dict[str, list[str]] = {
    "GitHub": ["Pull Request", "Commit", "Branch Protection", "Code Review", "Secret Scan"],
    "GitLab": ["Merge Request", "Pipeline", "Commit", "Code Review"],
    "Jira": ["Change Request", "Incident", "Story", "Approval Workflow", "CAB Record"],
    "Confluence": ["Policy Document", "Runbook", "Design Doc", "Meeting Minutes", "SOP"],
    "Figma": ["Design Spec", "UX Review", "Wireframe Approval"],
    "Teams": ["Approval Chat", "Audit Discussion", "Channel Post", "Meeting Recording"],
    "SharePoint": ["Signed Policy", "Audit Report", "Evidence Pack", "Spreadsheet", "Attestation"],
    "SonarQube": ["Quality Gate", "Vulnerability Report", "Coverage Report", "Code Smell Report"],
    "Jenkins": ["Build Log", "Deployment Record", "Test Report", "Artifact Manifest"],
    "ServiceNow": ["Change Ticket", "Incident Record", "Problem Record", "CMDB Entry"],
}

_APPLICATIONS: list[str] = [
    "Net Banking", "Mobile Banking", "Payments", "Treasury", "Customer Onboarding",
    "Core Banking", "Trade Finance", "Cards", "Wealth Management", "CRM",
    "ATM Switch", "UPI Gateway", "Loan Origination", "Fraud Monitoring", "Data Lake",
    "API Gateway", "Reconciliation", "KYC Service", "Settlement Engine", "Reporting Hub",
]

_FRAMEWORKS: list[str] = [
    "PCI DSS", "DPSC", "VAPT", "ITPP", "ITDRM", "MBSS", "ASST", "IS Audit",
    "OS Baselining", "DB Baselining", "Middleware Baselining", "CSITE", "RBI Cyber Security",
]

_OWNERS: list[str] = [
    "R. Mehta", "A. Sharma", "K. Reddy", "S. Banerjee", "M. D'Souza",
    "P. Nair", "V. Desai", "S. Nair", "N. Iyer", "T. Kapoor", "L. Menon", "J. Patel",
]

_TITLE_VERBS: list[str] = [
    "Quarterly", "Annual", "Pre-Prod", "Production", "Baseline", "Remediation",
    "Validated", "Approved", "Reviewed", "Automated",
]

_URL_BASE: dict[str, str] = {
    "GitHub": "https://github.com/bank/",
    "GitLab": "https://gitlab.bank.internal/",
    "Jira": "https://bank.atlassian.net/browse/",
    "Confluence": "https://bank.atlassian.net/wiki/",
    "Figma": "https://figma.com/file/",
    "Teams": "https://teams.microsoft.com/l/message/",
    "SharePoint": "https://bank.sharepoint.com/sites/grc/",
    "SonarQube": "https://sonar.bank.internal/dashboard?id=",
    "Jenkins": "https://jenkins.bank.internal/job/",
    "ServiceNow": "https://bank.service-now.com/nav_to.do?uri=",
}

_ANCHOR = date(2026, 5, 29)


def _seed(*parts: Any) -> int:
    return int(hashlib.md5("::".join(str(p) for p in parts).encode()).hexdigest(), 16)


def _pick(s: int, items: list) -> Any:
    return items[s % len(items)]


def _build_record(i: int) -> dict[str, Any]:
    s = _seed("demo-evd", i)
    source = _pick(s, DEMO_SOURCES)
    obj_type = _pick(s >> 3, _SOURCE_TYPES[source])
    app = _pick(s >> 7, _APPLICATIONS)
    fw = _pick(s >> 11, _FRAMEWORKS)
    owner = _pick(s >> 15, _OWNERS)
    verb = _pick(s >> 19, _TITLE_VERBS)
    days_ago = (s >> 5) % 540
    collected = _ANCHOR - timedelta(days=days_ago)
    ref = f"{source[:3].upper()}-{1000 + (s % 9000)}"
    title = f"{verb} {obj_type} — {app} / {fw}"
    return {
        "uid": f"EVD-{i + 1:05d}",
        "source_system": source,
        "object_type": obj_type,
        "title": title,
        "application": app,
        "framework": fw,
        "owner": owner,
        "reference": ref,
        "status": _pick(s >> 21, ["Collected", "Validated", "Approved", "Reused", "Pending Review"]),
        "collected_timestamp": collected.strftime("%Y-%m-%d %H:%M UTC"),
        "collection_date": collected.strftime("%Y-%m-%d"),
        "url": f"{_URL_BASE[source]}{ref}",
    }


# Build once at import — deterministic, ~1200 records.
_TOTAL = 1200
_RECORDS: list[dict[str, Any]] = [_build_record(i) for i in range(_TOTAL)]


def all_records() -> list[dict[str, Any]]:
    return _RECORDS


def search_evidence(*, application: str = "", source_system: str = "",
                    object_type: str = "", limit: int = 200) -> list[dict[str, Any]]:
    """Filtered evidence rows (deterministic). Filters are case-insensitive exact."""
    rows = _RECORDS
    if application:
        rows = [r for r in rows if r["application"].lower() == application.lower()]
    if source_system:
        rows = [r for r in rows if r["source_system"].lower() == source_system.lower()]
    if object_type:
        rows = [r for r in rows if r["object_type"].lower() == object_type.lower()]
    return rows[: max(limit, 1)]


def distinct_values() -> dict[str, list[str]]:
    return {
        "sources": sorted({r["source_system"] for r in _RECORDS}),
        "object_types": sorted({r["object_type"] for r in _RECORDS}),
        "applications": sorted({r["application"] for r in _RECORDS}),
    }


def counts() -> dict[str, Any]:
    by_source: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for r in _RECORDS:
        by_source[r["source_system"]] = by_source.get(r["source_system"], 0) + 1
        by_type[r["object_type"]] = by_type.get(r["object_type"], 0) + 1
    return {"total": len(_RECORDS), "by_source": by_source, "by_type": by_type}


def list_correlations(limit: int = 40) -> list[dict[str, Any]]:
    """CI/CD relationship chains (Commit → Build → Sonar Scan → Deploy).

    Shape matches the Evidence Explorer template: each group has a ``summary`` and
    a list of ``members`` with ``source`` and ``type`` fields.
    """
    out: list[dict[str, Any]] = []
    for i in range(limit):
        s = _seed("corr", i)
        app = _pick(s, _APPLICATIONS)
        fw = _pick(s >> 16, _FRAMEWORKS)
        commit = f"GIT-{2000 + (s % 7000)}"
        build = f"JEN-{1000 + ((s >> 4) % 9000)}"
        scan = f"SONAR-{100 + ((s >> 8) % 900)}"
        deploy = f"DEP-{500 + ((s >> 12) % 4000)}"
        out.append({
            "application": app,
            "framework": fw,
            "summary": f"{app} · {fw} — {commit} → {build} → {scan} → {deploy}",
            "members": [
                {"source": "GitHub", "type": "pull_request", "ref": commit},
                {"source": "Jenkins", "type": "ci_build", "ref": build},
                {"source": "SonarQube", "type": "quality_gate", "ref": scan},
                {"source": "ServiceNow", "type": "deployment", "ref": deploy},
            ],
            "status": _pick(s >> 20, ["Linked", "Verified", "Traced"]),
        })
    return out


def evidence_by_uid(uid: str) -> dict[str, Any] | None:
    for r in _RECORDS:
        if r["uid"] == uid:
            return r
    return None


def connector_health() -> list[dict[str, Any]]:
    """Per-connector health rows.

    Includes both the fields the Integration Health template reads
    (``name``/``type``/``connected``/``authenticated``/``latency_ms``/``detail``)
    and executive fields (``status``/``last_sync``/``evidence_count``/``health_score``).
    """
    cnts = counts()["by_source"]
    rows: list[dict[str, Any]] = []
    for src in DEMO_SOURCES:
        s = _seed("health", src)
        ev = cnts.get(src, 0)
        # Mostly healthy, a couple degraded — deterministic but realistic.
        score = 88 + (s % 12)
        status, connected = "Healthy", True
        if s % 17 == 0:
            status, score, connected = "Degraded", 64 + (s % 15), False
        last = _ANCHOR - timedelta(hours=(s % 20) + 1)
        rows.append({
            "name": src,
            "connector": src,
            "type": src.lower(),
            "connected": connected,
            "authenticated": True,
            "latency_ms": 40 + (s % 220),
            "detail": "ok" if connected else "degraded — retrying",
            "status": status,
            "health": status,
            "last_sync": last.strftime("%Y-%m-%d %H:%M UTC"),
            "evidence_count": ev,
            "health_score": score,
            "enabled": True,
        })
    return rows


def sync_runs(limit: int = 12) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i in range(limit):
        s = _seed("sync", i)
        src = _pick(s, DEMO_SOURCES)
        ts = _ANCHOR - timedelta(hours=i * 3 + (s % 3))
        ok = bool(s % 7)
        out.append({
            "connector": src,
            "started_at": ts.strftime("%Y-%m-%d %H:%M UTC"),
            "collected": 40 + (s % 160),
            "persisted": 38 + (s % 150),
            "ok": ok,
            "status": "ok" if ok else "partial",
        })
    return out


def audit_events(limit: int = 12) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    actors = ["S. Nair (Auditor)", "V. Desai (Compliance)", "Internal Audit", "AppSec CoE", "CIO"]
    actions = ["Evidence Collected", "Evidence Approved", "Connector Synced", "Reuse Applied", "Correlation Traced"]
    for i in range(limit):
        s = _seed("evd-audit", i)
        ts = _ANCHOR - timedelta(hours=i * 5 + (s % 4))
        src = _pick(s >> 8, DEMO_SOURCES)
        app = _pick(s >> 12, _APPLICATIONS)
        ts_str = ts.strftime("%Y-%m-%d %H:%M UTC")
        out.append({
            "timestamp": ts_str,
            "created_at": ts_str,
            "actor": _pick(s, actors),
            "action": _pick(s >> 4, actions),
            "resource": f"{src} — {app}",
            "detail": f"{src} — {app}",
        })
    return out
