"""Enterprise governance time-series analytics — framework-scoped only."""

from __future__ import annotations

from typing import Any

from app.governance_relational_model import get_framework_graph

CONTROL_PREFIX_REGISTRY: dict[str, list[str]] = {
    "PCI DSS": ["PCI-"],
    "AppSec": ["AS-C-"],
    "VAPT": ["VP-C-"],
    "OS Baselining": ["OS-C-", "OS-B-"],
    "DB Baselining": ["DB-C-", "DB-B-"],
    "Nginx Baselining": ["NGX-C-"],
    "DPSC": ["DP-C-"],
    "CSITE": ["CS-C-"],
    "ITPP": ["IT-C-"],
}


def validate_control_mapping(framework_name: str, control_id: str) -> bool:
    prefixes = CONTROL_PREFIX_REGISTRY.get(framework_name, [])
    if not prefixes:
        return True
    return any(control_id.startswith(p) for p in prefixes)


def _months() -> list[str]:
    return ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]


def _framework_metric_sets(framework_name: str) -> dict[str, Any]:
    sets = {
        "PCI DSS": {
            "primary_label": "MFA compliance evolution",
            "metrics": [
                {"key": "mfa_compliance_pct", "label": "MFA Compliance %"},
                {"key": "priv_access_review_pct", "label": "Privileged Access Review %"},
                {"key": "firewall_review_pct", "label": "Firewall Review Completion %"},
                {"key": "siem_freshness_pct", "label": "SIEM Evidence Freshness %"},
                {"key": "audit_readiness_pct", "label": "Audit Readiness %"},
            ],
            "seed": [88, 90, 92, 94, 96, 97],
        },
        "VAPT": {
            "primary_label": "Exploitability & retest closure",
            "metrics": [
                {"key": "exploitable_vulns", "label": "Exploitable Vulns"},
                {"key": "retest_closure_pct", "label": "Retest Closure %"},
                {"key": "cve_remediation_days", "label": "CVE Remediation Aging (days)"},
                {"key": "internet_risk_score", "label": "Internet-Facing Risk Score"},
            ],
            "seed": [9, 7, 5, 4, 3, 2],
        },
        "AppSec": {
            "primary_label": "SDLC & dependency posture",
            "metrics": [
                {"key": "sast_finding_reduction", "label": "SAST Finding Reduction"},
                {"key": "dependency_vulns", "label": "Open Dependency CVEs"},
                {"key": "secrets_exposure", "label": "Secrets Exposure"},
                {"key": "sdlc_compliance_pct", "label": "SDLC Compliance %"},
            ],
            "seed": [48, 42, 35, 28, 22, 18],
        },
        "OS Baselining": {
            "primary_label": "Server hardening posture",
            "metrics": [
                {"key": "hardened_server_pct", "label": "Hardened Server %"},
                {"key": "cis_compliance_pct", "label": "CIS Compliance %"},
                {"key": "stale_server_evidence", "label": "Stale Server Evidence"},
                {"key": "patch_sla_pct", "label": "Patch SLA %"},
            ],
            "seed": [84, 86, 87, 88, 89, 91],
        },
        "DB Baselining": {
            "primary_label": "Database security posture",
            "metrics": [
                {"key": "db_encryption_pct", "label": "DB Encryption Compliance %"},
                {"key": "privileged_db_review_pct", "label": "Privileged DB Access Review %"},
                {"key": "archival_policy_pct", "label": "Archival Policy Compliance %"},
            ],
            "seed": [82, 85, 88, 90, 91, 93],
        },
        "Nginx Baselining": {
            "primary_label": "Edge & TLS posture",
            "metrics": [
                {"key": "tls_hardening_pct", "label": "TLS Hardening %"},
                {"key": "proxy_validation_pct", "label": "Reverse Proxy Validation %"},
                {"key": "expired_certs", "label": "Expired Certificates"},
            ],
            "seed": [86, 88, 90, 91, 92, 94],
        },
        "DPSC": {
            "primary_label": "Privacy & data protection",
            "metrics": [
                {"key": "consent_compliance_pct", "label": "Consent Compliance %"},
                {"key": "retention_violations", "label": "Retention Violations"},
                {"key": "data_subject_sla_pct", "label": "DSR SLA Compliance %"},
            ],
            "seed": [84, 86, 88, 90, 91, 93],
        },
        "CSITE": {
            "primary_label": "Audit observation closure",
            "metrics": [
                {"key": "closure_pct", "label": "Observation Closure %"},
                {"key": "open_observations", "label": "Open Observations"},
                {"key": "repeat_observations", "label": "Repeat Observations"},
                {"key": "rejection_reduction_pct", "label": "Rejection Reduction %"},
            ],
            "seed": [72, 76, 80, 82, 84, 86],
        },
        "ITPP": {
            "primary_label": "DR & change governance",
            "metrics": [
                {"key": "dr_success_pct", "label": "DR Success %"},
                {"key": "change_success_pct", "label": "Change Success %"},
                {"key": "restore_test_pct", "label": "Restore Test Completion %"},
            ],
            "seed": [92, 93, 94, 95, 96, 97],
        },
    }
    return sets.get(framework_name, {
        "primary_label": f"{framework_name} governance posture",
        "metrics": [{"key": "compliance_pct", "label": "Compliance %"}],
        "seed": [75, 78, 80, 82, 84, 86],
    })


def _build_series(framework_name: str, granularity: str) -> list[dict]:
    g = get_framework_graph(framework_name)
    base_trends = g.get("trends", {}).get("metrics", [])
    spec = _framework_metric_sets(framework_name)
    months = _months()
    if granularity == "weekly":
        labels = [f"W{i}" for i in range(1, 7)]
    elif granularity == "quarterly":
        labels = ["Q4 2025", "Q1 2026", "Q2 2026"]
    elif granularity == "audit_cycle":
        labels = ["Q4 2025 Audit", "Q1 2026 Audit", "Q2 2026 Audit"]
    else:
        labels = months

    series = []
    for i, lbl in enumerate(labels):
        row: dict[str, Any] = {"period": lbl}
        if granularity == "monthly" and i < len(base_trends):
            row.update({k: v for k, v in base_trends[i].items() if k != "month"})
            row["period"] = base_trends[i].get("month", lbl)
        for j, m in enumerate(spec["metrics"]):
            if m["key"] not in row:
                base = spec["seed"][min(j, len(spec["seed"]) - 1)]
                delta = i * (2 if "pct" in m["key"] else -1)
                row[m["key"]] = max(0, min(100, base + delta)) if "pct" in m["key"] else max(0, base - i)
        series.append(row)
    return series


def _compliance_evolution(framework_name: str) -> list[dict]:
    g = get_framework_graph(framework_name)
    apps = g.get("applications", [])
    months = _months()
    rows = []
    for app in apps[:4]:
        base = app.get("audit_readiness_pct", 75)
        timeline = []
        for i, m in enumerate(months):
            pct = max(55, min(99, base - (5 - i) * 3 + (i * 2)))
            timeline.append({"month": m, "pct": pct})
        rows.append({
            "application": app["name"],
            "owner": app.get("owner", "—"),
            "current_pct": base,
            "timeline": timeline,
            "controls_implemented_delta": f"+{2 + len(app['name']) % 4} since Jan",
            "findings_reduced": max(0, app.get("open_findings", 0) + 2 - len(months) // 2),
            "evidence_freshness_gain": f"+{5 + len(app['name']) % 8}%",
            "sla_reduction": app.get("sla_breaches", 0),
        })
    return rows


def _controls_implemented_by_application(framework_name: str) -> dict[str, list[dict]]:
    """Controls implemented per application over time — weekly/monthly/quarterly/yearly."""
    g = get_framework_graph(framework_name)
    apps = [a["name"] for a in g.get("applications", [])]
    if not apps:
        apps = ["Net Banking", "Mobile Banking", "Payments"]
    core = ["Net Banking", "Mobile Banking", "Payments"]
    for c in core:
        if c not in apps:
            apps.append(c)

    def _series(labels: list[str], step: int) -> list[dict]:
        rows = []
        for i, lbl in enumerate(labels):
            app_counts = {}
            for j, app in enumerate(apps[:6]):
                base = 8 + j * 2 + i * step
                app_counts[app] = min(28, base + (len(app) % 4))
            rows.append({"period": lbl, "applications": app_counts, "total_implemented": sum(app_counts.values())})
        return rows

    return {
        "weekly": _series([f"W{i}" for i in range(1, 7)], 1),
        "monthly": _series(_months(), 2),
        "quarterly": _series(["Q4 2025", "Q1 2026", "Q2 2026"], 3),
        "yearly": _series(["2024", "2025", "2026 YTD"], 4),
        "audit_cycle": _series(["Q4 2025 Audit", "Q1 2026 Audit", "Q2 2026 Audit"], 3),
        "application_columns": apps[:6],
    }


def build_framework_trends_analytics(framework_name: str) -> dict[str, Any]:
    g = get_framework_graph(framework_name)
    apps = g.get("applications", [])
    spec = _framework_metric_sets(framework_name)
    return {
        "framework": framework_name,
        "scope_label": f"{framework_name} governance analytics only",
        "application_scope": ", ".join(a["name"] for a in apps),
        "date_range": "Jan 2026 – Jun 2026",
        "primary_label": spec["primary_label"],
        "metric_definitions": spec["metrics"],
        "granularities": {
            "weekly": _build_series(framework_name, "weekly"),
            "monthly": _build_series(framework_name, "monthly"),
            "quarterly": _build_series(framework_name, "quarterly"),
            "audit_cycle": _build_series(framework_name, "audit_cycle"),
        },
        "compliance_evolution": _compliance_evolution(framework_name),
        "audit_evolution": {
            "readiness_change": "+4.2% since Q1 audit cycle",
            "findings_trend": "↓ 18% open observations",
            "repeat_observations": max(0, len(g.get("findings", [])) // 3),
            "reuse_efficiency_pct": 34,
            "rejection_reduction_pct": 22,
        },
        "validation_pass_fail": [
            {"period": m, "pass": 70 + i * 3, "warn": 12 - i, "fail": max(2, 8 - i * 2)}
            for i, m in enumerate(_months())
        ],
        "finding_aging": [
            {"period": m, "critical": max(1, 5 - i), "high": max(2, 8 - i), "medium": 10 + i}
            for i, m in enumerate(_months())
        ],
        "remediation_velocity": [
            {"period": m, "closed": 8 + i * 2, "opened": max(3, 10 - i)}
            for i, m in enumerate(_months())
        ],
        "sla_breach_trend": [
            {"period": m, "breaches": max(0, 6 - i)}
            for i, m in enumerate(_months())
        ],
        "controls_implemented_by_application": _controls_implemented_by_application(framework_name),
    }
