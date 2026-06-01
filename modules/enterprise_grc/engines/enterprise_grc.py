"""Enterprise GRC platform — Risk Register, Exceptions, CMDB, Regulatory Mapping, Heatmaps."""

from __future__ import annotations

from datetime import datetime, timezone

from app import ecs_state
from modules.executive_overview.engines.demo_metrics import BUSINESS_UNITS, display_framework_maturity
from modules.frameworks.engines.framework_catalog import FRAMEWORK_CATALOG, get_all_evidence_records
from modules.governance.engines.workflow_module import build_owner_work_queue

RISK_CATEGORIES = [
    "Cyber Risk", "Operational Risk", "Compliance Risk", "AppSec Risk",
    "Cloud Risk", "Baselining Risk", "DR Risk", "Third Party Risk",
]

RISK_TREATMENTS = ["Mitigate", "Accept", "Transfer", "Avoid"]


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _risk_level(seed: int) -> str:
    return ["Critical", "High", "Medium", "Low"][seed % 4]


def build_risk_register(role: str = "owner") -> dict:
    apps = ecs_state.BANKING_APPLICATIONS
    risks = [
        {
            "risk_id": "RSK-2026-001",
            "title": "Legacy TLS 1.0 on payment gateway edge",
            "description": "Internet-facing payment API still negotiates TLS 1.0 for legacy merchant integrations.",
            "category": "Cyber Risk",
            "business_unit": "Retail Banking",
            "application": "Payments",
            "owner": "K. Reddy (App Owner)",
            "inherent_risk": "Critical",
            "residual_risk": "High",
            "treatment": "Mitigate",
            "acceptance": "Pending CIO",
            "regulatory_impact": "PCI DSS, RBI Cyber",
            "open_date": "2026-03-12",
            "due_date": "2026-06-30",
            "aging_days": 73,
            "status": "Open",
            "linked_control": "PCI DSS::Req 4.1 — Encryption in Transit",
            "linked_framework": "PCI DSS",
        },
        {
            "risk_id": "RSK-2026-002",
            "title": "Delayed VAPT remediation — Mobile Banking",
            "description": "High-severity pen test findings exceed 90-day closure SLA.",
            "category": "AppSec Risk",
            "business_unit": "Digital Banking",
            "application": "Mobile Banking",
            "owner": "A. Sharma (App Owner)",
            "inherent_risk": "High",
            "residual_risk": "High",
            "treatment": "Mitigate",
            "acceptance": "Not accepted",
            "regulatory_impact": "VAPT, AppSec",
            "open_date": "2026-02-20",
            "due_date": "2026-05-15",
            "aging_days": 94,
            "status": "Escalated",
            "linked_control": "VAPT::Penetration Testing — Mobile Banking",
            "linked_framework": "VAPT",
        },
        {
            "risk_id": "RSK-2026-003",
            "title": "DR drill overdue — Treasury FX core",
            "description": "Semi-annual DR failover test not completed within ITPP policy window.",
            "category": "DR Risk",
            "business_unit": "Treasury",
            "application": "Treasury",
            "owner": "S. Banerjee (App Owner)",
            "inherent_risk": "High",
            "residual_risk": "Medium",
            "treatment": "Mitigate",
            "acceptance": "—",
            "regulatory_impact": "ITPP, RBI Cyber",
            "open_date": "2026-04-01",
            "due_date": "2026-05-31",
            "aging_days": 53,
            "status": "Open",
            "linked_control": "ITPP::DR Drill Conducted",
            "linked_framework": "ITPP",
        },
        {
            "risk_id": "RSK-2026-004",
            "title": "Cloud IAM excessive privileges — UPI cluster",
            "description": "Prisma Cloud flagged 14 over-privileged service accounts on UPI workloads.",
            "category": "Cloud Risk",
            "business_unit": "Digital Payments",
            "application": "UPI",
            "owner": "P. Iyer (App Owner)",
            "inherent_risk": "High",
            "residual_risk": "Medium",
            "treatment": "Mitigate",
            "acceptance": "—",
            "regulatory_impact": "DPSC, CSITE",
            "open_date": "2026-05-10",
            "due_date": "2026-07-10",
            "aging_days": 14,
            "status": "Open",
            "linked_control": "CSITE::Privileged Access Monitoring",
            "linked_framework": "CSITE",
        },
        {
            "risk_id": "RSK-2026-005",
            "title": "OS baselining drift — Net Banking middleware",
            "description": "Tripwire detected unauthorized sudo policy change on 3 production hosts.",
            "category": "Baselining Risk",
            "business_unit": "Retail Banking",
            "application": "Net Banking",
            "owner": "R. Mehta (App Owner)",
            "inherent_risk": "Medium",
            "residual_risk": "Medium",
            "treatment": "Mitigate",
            "acceptance": "—",
            "regulatory_impact": "OS Baselining",
            "open_date": "2026-05-18",
            "due_date": "2026-06-18",
            "aging_days": 6,
            "status": "Open",
            "linked_control": "OS Baselining::Privileged Command Logging",
            "linked_framework": "OS Baselining",
        },
        {
            "risk_id": "RSK-2026-006",
            "title": "Third-party PSP API key rotation overdue",
            "description": "Critical PSP integration keys exceed 180-day rotation policy.",
            "category": "Third Party Risk",
            "business_unit": "Payments",
            "application": "Payments",
            "owner": "K. Reddy (App Owner)",
            "inherent_risk": "High",
            "residual_risk": "High",
            "treatment": "Transfer",
            "acceptance": "Vendor SLA",
            "regulatory_impact": "DPSC, PCI DSS",
            "open_date": "2026-01-15",
            "due_date": "2026-04-30",
            "aging_days": 129,
            "status": "Open",
            "linked_control": "DPSC::Third-party PSP Integration",
            "linked_framework": "DPSC",
        },
        {
            "risk_id": "RSK-2026-007",
            "title": "DB encryption gap — Loan origination schema",
            "description": "Non-production loan DB snapshot detected without TDE on archive tablespace.",
            "category": "Compliance Risk",
            "business_unit": "Retail Lending",
            "application": "Loan System",
            "owner": "M. Joshi (App Owner)",
            "inherent_risk": "Medium",
            "residual_risk": "Low",
            "treatment": "Mitigate",
            "acceptance": "—",
            "regulatory_impact": "DB Baselining, PCI DSS",
            "open_date": "2026-05-05",
            "due_date": "2026-08-05",
            "aging_days": 19,
            "status": "Mitigation In Progress",
            "linked_control": "DB Baselining::Transparent Data Encryption",
            "linked_framework": "DB Baselining",
        },
        {
            "risk_id": "RSK-2026-008",
            "title": "Operational incident SLA breach — P1 net banking outage",
            "description": "Major incident MTTR exceeded ITPP P1 SLA by 42 minutes.",
            "category": "Operational Risk",
            "business_unit": "Retail Banking",
            "application": "Net Banking",
            "owner": "R. Mehta (App Owner)",
            "inherent_risk": "High",
            "residual_risk": "Medium",
            "treatment": "Accept",
            "acceptance": "CIO approved — root cause remediated",
            "regulatory_impact": "ITPP",
            "open_date": "2026-05-20",
            "due_date": "2026-05-28",
            "aging_days": 4,
            "status": "Accepted",
            "linked_control": "ITPP::Incident SLA Defined",
            "linked_framework": "ITPP",
        },
    ]
    high_open = [r for r in risks if r["residual_risk"] in ("Critical", "High") and r["status"] not in ("Closed", "Accepted")]
    bu_exposure = {}
    for r in risks:
        bu_exposure[r["business_unit"]] = bu_exposure.get(r["business_unit"], 0) + 1
    category_counts: dict[str, int] = {}
    for r in risks:
        category_counts[r["category"]] = category_counts.get(r["category"], 0) + 1
    severity_chart = [
        {"label": cat, "value": cnt, "tone": "red" if "Cyber" in cat or "AppSec" in cat else "orange"}
        for cat, cnt in sorted(category_counts.items(), key=lambda x: -x[1])
    ]
    aging_buckets = [0, 30, 60, 90, 120, 180]
    aging_trend = []
    for i, lo in enumerate(aging_buckets):
        hi = aging_buckets[i + 1] if i + 1 < len(aging_buckets) else 9999
        cnt = len([r for r in risks if lo <= r["aging_days"] < hi])
        aging_trend.append({"label": f"{lo}–{hi if hi < 9999 else '+'}d", "value": cnt})
    escalation_timeline = sorted(
        [
            {
                "risk_id": r["risk_id"],
                "title": r["title"][:50],
                "date": r["open_date"],
                "severity": r["residual_risk"],
                "status": r["status"],
            }
            for r in risks
            if r["status"] in ("Escalated", "Open") and r["residual_risk"] in ("Critical", "High")
        ],
        key=lambda x: x["date"],
        reverse=True,
    )[:8]
    for r in risks:
        obs_id = f"OBS-{r['risk_id'].replace('RSK-', '')}"
        r["linked_observations"] = [
            {
                "observation_id": obs_id,
                "title": r["title"],
                "status": r["status"],
                "framework": r.get("linked_framework", ""),
            }
        ]
        r["impacted_applications"] = [r["application"]]
        r["mitigation_plans"] = [
            f"{r['treatment']} — target {r['due_date']}",
            f"Owner: {r['owner']}",
        ]
        r["evidence_gaps"] = [
            f"Evidence pending for {r.get('linked_control', 'control')}",
        ]
    return {
        "rows": risks,
        "kpis": [
            {"label": "Total Risks", "value": len(risks), "tone": "primary"},
            {"label": "Open High/Critical", "value": len(high_open), "tone": "danger"},
            {"label": "Escalated", "value": len([r for r in risks if r["status"] == "Escalated"]), "tone": "warning"},
            {"label": "Avg Aging (days)", "value": round(sum(r["aging_days"] for r in risks) / len(risks)), "tone": "info"},
        ],
        "top_risks": sorted(risks, key=lambda x: -x["aging_days"])[:5],
        "high_open": high_open,
        "bu_exposure": [{"unit": k, "count": v} for k, v in sorted(bu_exposure.items(), key=lambda x: -x[1])],
        "heatmap": _risk_heatmap_matrix(risks),
        "severity_chart": severity_chart,
        "aging_trend": aging_trend,
        "escalation_timeline": escalation_timeline,
        "actions": _grc_actions(role, "risk"),
        "role": role,
    }


def build_exceptions_td(role: str = "owner") -> dict:
    from modules.governance.engines.exception_state_engine import build_exception_kpis, get_all_exceptions

    exceptions = get_all_exceptions(role)
    expired = [e for e in exceptions if e.get("expired")]
    by_fw: dict[str, int] = {}
    for e in exceptions:
        by_fw[e["framework"]] = by_fw.get(e["framework"], 0) + 1
    return {
        "rows": exceptions,
        "kpis": build_exception_kpis(exceptions),
        "expired": expired,
        "by_framework": [{"framework": k, "count": v} for k, v in sorted(by_fw.items(), key=lambda x: -x[1])],
        "actions": _grc_actions(role, "exception"),
        "role": role,
    }


def build_cmdb_inventory(role: str = "owner") -> dict:
    from modules.frameworks.engines.framework_catalog import APPLICATIONS, SERVERS

    assets = []
    types = ["Application", "Server", "Database", "API", "Cloud Asset", "Kubernetes Cluster", "Middleware", "Load Balancer", "Storage"]
    for i, app in enumerate(APPLICATIONS):
        assets.append({
            "asset_id": f"AST-APP-{i+1:03d}",
            "name": app,
            "type": "Application",
            "environment": "Production",
            "criticality": "Tier-1" if i < 3 else "Tier-2",
            "owner": ecs_state.BANKING_APPLICATIONS[i % len(ecs_state.BANKING_APPLICATIONS)] if i < len(ecs_state.BANKING_APPLICATIONS) else "Unassigned",
            "infra_owner": "Infrastructure Ops",
            "frameworks_mapped": list(FRAMEWORK_CATALOG.keys())[:4 + (i % 4)],
            "risk_rating": _risk_level(i),
            "internet_facing": i in (0, 1, 2, 3),
            "dr_covered": i != 5,
            "monitoring_enabled": i != 4,
        })
    for i, srv in enumerate(SERVERS[:8]):
        assets.append({
            "asset_id": f"AST-SRV-{i+1:03d}",
            "name": srv,
            "type": "Server" if "NGINX" not in srv else "Load Balancer",
            "environment": "Production" if i < 6 else "DR",
            "criticality": "Tier-1" if i < 4 else "Tier-2",
            "owner": "Infrastructure Ops",
            "infra_owner": "Platform Engineering",
            "frameworks_mapped": ["OS Baselining", "CSITE", "VAPT"][:2 + (i % 2)],
            "risk_rating": _risk_level(i + 3),
            "internet_facing": i in (0, 5, 6),
            "dr_covered": i in (4, 5),
            "monitoring_enabled": i != 7,
        })
    return {
        "rows": assets,
        "kpis": [
            {"label": "Total Assets", "value": len(assets), "tone": "primary"},
            {"label": "Critical (Tier-1)", "value": len([a for a in assets if a["criticality"] == "Tier-1"]), "tone": "danger"},
            {"label": "Internet Facing", "value": len([a for a in assets if a["internet_facing"]]), "tone": "warning"},
            {"label": "Unmonitored", "value": len([a for a in assets if not a["monitoring_enabled"]]), "tone": "info"},
            {"label": "No DR Coverage", "value": len([a for a in assets if not a["dr_covered"]]), "tone": "danger"},
        ],
        "critical_assets": [a for a in assets if a["criticality"] == "Tier-1"][:6],
        "non_compliant": [a for a in assets if a["risk_rating"] in ("Critical", "High")][:5],
        "actions": _grc_actions(role, "cmdb"),
        "role": role,
    }


def build_regulatory_mapping(role: str = "owner") -> dict:
    mappings = [
        {"control_theme": "Encryption in Transit", "frameworks": ["PCI DSS", "DPSC", "Nginx Baselining", "ISO 27001"], "shared_evidence": "TLS certificate inventory", "coverage_pct": 92},
        {"control_theme": "Access Control / MFA", "frameworks": ["PCI DSS", "CSITE", "AppSec", "RBI Cyber"], "shared_evidence": "MFA enrollment report", "coverage_pct": 88},
        {"control_theme": "Vulnerability Management", "frameworks": ["VAPT", "AppSec", "PCI DSS", "CSITE"], "shared_evidence": "VA remediation tracker", "coverage_pct": 76},
        {"control_theme": "Logging & Monitoring", "frameworks": ["PCI DSS", "CSITE", "ITPP", "ISO 27001"], "shared_evidence": "SIEM use-case export", "coverage_pct": 94},
        {"control_theme": "Disaster Recovery", "frameworks": ["ITPP", "RBI Cyber", "ISO 27001"], "shared_evidence": "DR drill report", "coverage_pct": 81},
        {"control_theme": "Database Security", "frameworks": ["DB Baselining", "PCI DSS", "DPSC"], "shared_evidence": "TDE attestation", "coverage_pct": 85},
        {"control_theme": "OS Hardening", "frameworks": ["OS Baselining", "CSITE", "VAPT"], "shared_evidence": "CIS benchmark scan", "coverage_pct": 79},
        {"control_theme": "Change Management", "frameworks": ["ITPP", "ISO 27001", "RBI Cyber"], "shared_evidence": "CAB minutes", "coverage_pct": 90},
    ]
    all_fws = list(FRAMEWORK_CATALOG.keys()) + ["RBI Cyber", "ISO 27001"]
    return {
        "mappings": mappings,
        "frameworks": all_fws,
        "kpis": [
            {"label": "Mapped Themes", "value": len(mappings), "tone": "primary"},
            {"label": "Avg Coverage", "value": f"{round(sum(m['coverage_pct'] for m in mappings) / len(mappings))}%", "tone": "success"},
            {"label": "Reusable Evidence", "value": len(mappings), "tone": "info"},
            {"label": "Gap Themes", "value": 2, "tone": "warning"},
        ],
        "coverage_matrix": _coverage_matrix(mappings, all_fws),
        "missing_coverage": ["RBI Cyber — API security depth", "ISO 27001 — Supplier security"],
        "actions": _grc_actions(role, "regulatory"),
        "role": role,
    }


def build_executive_heatmaps(role: str = "cio") -> dict:
    stats = ecs_state.build_evidence_analytics()
    maturity = display_framework_maturity(stats["framework_stats"])
    apps = ecs_state.BANKING_APPLICATIONS + ["Wealth Portal"]
    from modules.executive_overview.engines.enterprise_mock_service import build_pan_india_posture
    pan_regions = build_pan_india_posture()["regions"]
    return {
        "kpis": [
            {"label": "Enterprise Maturity", "value": f"{round(sum(f.get('maturity_pct', f.get('compliance_pct', 0)) for f in maturity) / max(len(maturity), 1), 1)}%", "tone": "primary"},
            {"label": "Open High Risks", "value": len(build_risk_register(role)["high_open"]), "tone": "danger"},
            {"label": "TD Expired", "value": len(build_exceptions_td(role)["expired"]), "tone": "danger"},
            {"label": "SLA Breaches", "value": sum(1 for i in build_owner_work_queue(200) if i.get("sla") == "Breached"), "tone": "warning"},
            {"label": "Audit Readiness", "value": f"{round(stats['totals']['approved'] / max(stats['totals']['total'], 1) * 100, 1)}%", "tone": "success"},
        ],
        "framework_heatmap": [{"name": f["name"], "score": f.get("maturity_pct", f.get("compliance_pct", 0)), "risk": "High" if f.get("maturity_pct", f.get("compliance_pct", 100)) < 75 else "Low"} for f in maturity],
        "application_heatmap": [{"name": a, "score": 65 + (i * 7) % 30, "risk": _risk_level(i)} for i, a in enumerate(apps)],
        "business_unit_heatmap": [{"unit": u["unit"], "score": u["compliance_pct"], "gaps": u["open_gaps"]} for u in BUSINESS_UNITS],
        "regional_heatmap": [{"region": r["region"], "score": r["score"], "observations": r["observations_open"]} for r in pan_regions],
        "sla_heatmap": [{"framework": fw, "breaches": (i % 3)} for i, fw in enumerate(FRAMEWORK_CATALOG.keys())],
        "aging_heatmap": [{"bucket": b, "count": c} for b, c in [("0-15d", 42), ("16-30d", 28), ("31-45d", 15), ("46-60d", 8), ("60+d", 5)]],
        "top_risky_apps": sorted([{"application": a, "score": 65 + (i * 7) % 30} for i, a in enumerate(apps)], key=lambda x: x["score"])[:4],
        "actions": _grc_actions(role, "executive"),
        "role": role,
    }


def build_governance_analytics_module(role: str = "cio") -> dict:
    from modules.frameworks.engines.control_validation_engine import build_governance_analytics
    from modules.executive_overview.engines.demo_metrics import REJECTION_TRENDS, SLA_TRENDS, ENTERPRISE_MONTHLY_TRENDS

    gov = build_governance_analytics()
    records = get_all_evidence_records()
    reuse_pct = round(len([r for r in records if r.get("evidence_id", "").endswith("1")]) / max(len(records), 1) * 100, 1)
    return {
        "kpis": [
            {"label": "Enterprise Compliance", "value": f"{gov['audit_readiness_pct']}%", "tone": "primary"},
            {"label": "Evidence Reuse", "value": f"{reuse_pct}%", "tone": "success"},
            {"label": "Repeat Failures", "value": len(gov["repeat_failures"]), "tone": "danger"},
            {"label": "Stale Evidence", "value": f"{gov['stale_evidence_pct']}%", "tone": "warning"},
        ],
        "monthly_trends": ENTERPRISE_MONTHLY_TRENDS,
        "rejection_trends": REJECTION_TRENDS,
        "sla_trends": SLA_TRENDS,
        "framework_maturity": gov["framework_maturity"],
        "operational_maturity": gov.get("operational_maturity", {}),
        "control_effectiveness": gov["control_effectiveness"],
        "risk_trends": [{"month": t["month"], "opened": t["opened"], "closed": t["closed"]} for t in ENTERPRISE_MONTHLY_TRENDS],
        "exception_trends": [{"month": "Mar 2026", "active": 4, "expired": 1}, {"month": "Apr 2026", "active": 5, "expired": 2}, {"month": "May 2026", "active": 4, "expired": 2}],
        "top_reused": gov.get("most_reused_evidence", []),
        "repeat_failures": gov["repeat_failures"],
        "actions": _grc_actions(role, "analytics"),
        "role": role,
    }


def _risk_heatmap_matrix(risks: list) -> list:
    matrix = []
    for cat in RISK_CATEGORIES[:6]:
        for level in ("Critical", "High", "Medium", "Low"):
            count = len([r for r in risks if r["category"] == cat and r["residual_risk"] == level])
            if count:
                matrix.append({"category": cat, "level": level, "count": count})
    return matrix


def _coverage_matrix(mappings: list, frameworks: list) -> list:
    rows = []
    for m in mappings:
        row = {"theme": m["control_theme"], "cells": {}}
        for fw in frameworks:
            row["cells"][fw] = "●" if fw in m["frameworks"] else "○"
        rows.append(row)
    return rows


def _grc_actions(role: str, module: str) -> list[str]:
    base = {
        "risk": ["accept_risk", "escalate_risk", "mitigate_risk", "assign_owner", "request_exception", "link_observation", "link_control", "link_evidence"],
        "exception": ["approve_exception", "reject_exception", "extend_td", "escalate_expired_td", "renew_exception", "close_exception"],
        "cmdb": ["open_asset", "view_controls", "view_risks", "view_observations", "view_evidence", "compare_assets"],
        "regulatory": ["reuse_evidence", "link_control", "map_framework", "export_mapping"],
        "executive": ["drill_down", "escalate_risk", "view_rca", "view_exception", "approve_closure"],
        "analytics": ["export_chart", "drill_down", "view_trends"],
    }
    actions = base.get(module, [])
    if role == "auditor":
        return [a for a in actions if any(w in a for w in ("approve", "reject", "view", "link", "assign", "reassign", "escalate", "request_reupload"))]
    if role in ("cio", "vertical_head", "compliance_head"):
        return [a for a in actions if "upload" not in a and "replace" not in a]
    if role == "owner":
        return [a for a in actions if "escalate" not in a or "request" in a]
    return actions[:4]


def execute_grc_action(module: str, action: str, item_id: str, user: str, role: str) -> str:
    from modules.shared.services.audit_trail import log_event
    from modules.shared.services.role_permissions import action_allowed, permission_denied_message

    if not action_allowed(role, action):
        return permission_denied_message(action.replace("_", " "))

    if module in ("exceptions_td", "exception_governance") and item_id and action in (
        "approve_exception", "reject_exception", "extend_td", "renew_exception",
        "close_exception", "escalate_expired_td",
    ):
        from modules.governance.engines.exception_state_engine import apply_exception_action
        return apply_exception_action(item_id, action, user, role)

    key = f"{module}:{action}:{item_id}"
    ecs_state.grc_action_log.setdefault(key, {"count": 0})
    ecs_state.grc_action_log[key]["count"] += 1
    label = action.replace("_", " ").title()
    msg = f"{label} recorded" + (f" for {item_id}" if item_id else "") + f" in {module.replace('_', ' ')}."
    log_event(f"GRC {label}", user, "", item_id, msg, role=role)
    return msg
