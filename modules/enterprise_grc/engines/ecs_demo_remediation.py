"""Demo remediation helpers — enriched drill payloads, lineage, reuse wizard data."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from modules.shared.utils.demo_data_standards import (
    between,
    generate_audit_trail,
    pick,
    seed,
)

ANCHOR = date(2026, 5, 28)

_DEMO_APPS = [
    "Net Banking", "Mobile Banking", "UPI", "Treasury", "CRM",
    "Customer Service", "Payments Hub", "Data Lake", "Trade Finance", "Fraud Monitoring",
]

_FRAMEWORKS = ["PCI DSS", "DPSC", "AppSec", "VAPT", "OS Baselining", "AI Governance", "ITPP"]


def build_ai_analytics_trends() -> dict[str, Any]:
    """Chart-ready trend series for AI Governance posture page."""
    months = []
    for i in range(12):
        s = seed("aian", i)
        mk = (ANCHOR.replace(day=1) - timedelta(days=30 * (11 - i))).strftime("%Y-%m")
        months.append({
            "month_key": mk,
            "month": mk,
            "tokens": between(s, 7_200_000, 11_800_000),
            "cost_usd": round(between(s, 7_200_000, 11_800_000) / 1000 * 0.012, 0),
            "prompt_volume": between(s >> 2, 4200, 9800),
            "hallucinations": between(s >> 4, 0, 12),
            "policy_violations": between(s >> 6, 2, 18),
            "exceptions": between(s >> 8, 0, 8),
            "approvals": between(s >> 10, 8, 24),
        })
    by_app = []
    for app in _DEMO_APPS[:10]:
        s = seed("aiappc", app)
        by_app.append({
            "application": app,
            "tokens": between(s, 180_000, 4_200_000),
            "cost_usd": round(between(s, 180_000, 4_200_000) / 1000 * 0.012, 0),
            "prompt_volume": between(s >> 2, 120, 2400),
            "model_calls": between(s >> 4, 800, 42000),
        })
    return {
        "monthly_trends": months,
        "by_application": by_app,
        "summary": {
            "total_tokens_mtd": sum(a["tokens"] for a in by_app),
            "total_cost_mtd": sum(a["cost_usd"] for a in by_app),
            "avg_hallucination_rate": round(sum(m["hallucinations"] for m in months[-3:]) / 3, 1),
        },
    }


def build_registry_audit_trail() -> list[dict[str, str]]:
    actions = [
        "Model Approved", "Prompt Approved", "Model Registration", "Prompt Version Published",
        "Validation Completed", "Risk Assessment", "Red-team Review", "Policy Mapping Updated",
        "Exception Approved", "Audit Closure", "Evidence Upload", "Framework Mapping",
    ]
    return generate_audit_trail(
        55, ANCHOR, years_back=5,
        actions=actions,
        detail_builder=lambda i, action, actor: (
            f"{pick(seed('rga', i), _DEMO_APPS)} — "
            f"{pick(seed('rgm', i), ['GPT-4o Enterprise', 'Claude 3.5', 'FinGPT', 'Embeddings-v3'])} — {action}"
        ),
    )


def build_control_lineage_detail(control: dict, release: dict, framework: str) -> dict[str, Any]:
    cid = control.get("control_id", "CTRL-01")
    s = seed("clin", cid, release.get("id", ""))
    apps = _DEMO_APPS[:between(s >> 2, 5, 10)]
    return {
        "control_id": cid,
        "control_description": control.get("control_description", ""),
        "mapped_requirement": f"REQ-{release['id'].split('-')[-1]}-{between(s, 101, 199)}",
        "mapped_design": f"DSG-{release['id'].split('-')[-1]}-{between(s >> 4, 14, 99):03d}",
        "mapped_development": f"DEV-{cid}-IMPL",
        "mapped_test": f"TC-{between(s >> 6, 1000, 9999)}",
        "mapped_evidence": f"EVD-{cid}-001",
        "mapped_observations": f"OBS-202{between(s >> 8, 3, 5)}-{between(s >> 10, 100, 999)}",
        "historical_usage_count": between(s >> 12, 12, 48),
        "applications_using": apps,
        "observation_count": control.get("findings_count", 0) + between(s >> 14, 2, 8),
        "exception_count": control.get("exceptions_count", 0),
        "reuse_score": round(between(s >> 16, 62, 94) + (s % 9) / 10, 1),
        "first_implementation": (ANCHOR - timedelta(days=between(s >> 18, 400, 1200))).strftime("%Y-%m-%d"),
        "latest_implementation": (ANCHOR - timedelta(days=between(s >> 20, 7, 90))).strftime("%Y-%m-%d"),
        "framework_mappings": ", ".join(pick(seed("clfw", cid, i), _FRAMEWORKS) for i in range(3)),
        "reuse_recommendation": pick(s >> 22, [
            "Reuse approved — scope unchanged from FY2025 Net Banking release",
            "Delta analysis required — new API endpoints in scope",
            "Pattern eligible for Mobile Banking and UPI Gateway",
        ]),
    }


def enrich_framework_drill(row: dict, release: dict, summary: dict) -> dict[str, Any]:
    controls = row.get("control_records", [])
    ev_total = len(row.get("evidence_records", []))
    ev_approved = sum(1 for e in row.get("evidence_records", []) if e.get("status") == "Approved")
    ctrl_covered = row.get("controls_covered", 0)
    ctrl_total = row.get("controls_total", len(controls)) or 1
    return {
        "framework_summary": {
            "framework": row.get("framework"),
            "control_coverage_pct": round(ctrl_covered / ctrl_total * 100, 1),
            "evidence_coverage_pct": round(ev_approved / max(ev_total, 1) * 100, 1),
            "readiness_pct": summary.get("readiness_score", row.get("checklist_pct", 0)),
            "applications_covered": row.get("applications_impacted", []),
            "open_gaps": row.get("gaps", 0),
            "owner": row.get("owner"),
        },
        "control_lineage": [build_control_lineage_detail(c, release, row.get("framework", "")) for c in controls[:25]],
    }


def build_stage_card_drill(stage_key: str, detail: dict, release: dict) -> dict[str, Any]:
    sm = detail.get("summary", {})
    s = seed("stcard", stage_key, release["id"])
    base: dict[str, Any] = {
        "stage_key": stage_key,
        "stage_label": detail.get("stage", {}).get("label", stage_key),
        "readiness_score": sm.get("readiness_score", 0),
        "framework_coverage_pct": sm.get("framework_coverage_pct", 0),
        "control_coverage_pct": sm.get("control_coverage_pct", 0),
        "evidence_coverage_pct": sm.get("evidence_coverage_pct", round(
            sm.get("evidence_collected", 0) / max(sm.get("evidence_total", 1), 1) * 100, 1
        )),
        "open_gaps": sm.get("open_gaps", 0),
        "status": sm.get("status", sm.get("approval_status", "In Review")),
        "open_observations": between(s >> 2, 2, 8),
        "approval_status": sm.get("approval_status", "In Review"),
        "related_applications": sm.get("applications_impacted", _release_apps_safe(release)),
    }
    if stage_key == "requirement":
        base["historical_implementations"] = [
            {"application": pick(seed("hi", stage_key, i), _DEMO_APPS), "release": f"REL-202{4 + i % 2}-Q{(i % 4) + 1}",
             "status": "Closed", "closure_date": (ANCHOR - timedelta(days=90 + i * 40)).strftime("%Y-%m-%d")}
            for i in range(5)
        ]
        base["reuse_candidates"] = [
            {"control_id": f"APPSEC-{between(seed('rc', stage_key, i), 1, 99):02d}", "application": pick(seed("rca", i), _DEMO_APPS),
             "reuse_score": f"{between(seed('rcs', i), 72, 96)}%"}
            for i in range(6)
        ]
    elif stage_key == "design":
        base["reusable_patterns"] = [
            {"pattern": "Zero Trust API Gateway", "used_in": ["Net Banking", "Mobile Banking", "UPI"], "approvals": 3},
            {"pattern": "RAG Security Pipeline", "used_in": ["CRM", "Customer Service", "Data Lake"], "approvals": 2},
        ]
        base["historical_designs"] = detail.get("designs", [])[:8]
        base["similar_controls"] = [
            {"control_id": f"DPSC-{between(seed('sc', i), 1, 99):02d}", "application": pick(seed("sca", i), _DEMO_APPS)}
            for i in range(5)
        ]
    elif stage_key == "development":
        base["code_patterns"] = [
            {"pattern": "Input Validation Library", "repo": "gitlab.bank.com/platform/input-guard", "apps": 3},
            {"pattern": "Audit Log SDK", "repo": "gitlab.bank.com/platform/audit-sdk", "apps": 4},
        ]
        base["static_scan_history"] = [
            {"date": (ANCHOR - timedelta(days=14)).strftime("%Y-%m-%d"), "critical": 0, "high": 2, "status": "Remediated"},
            {"date": (ANCHOR - timedelta(days=45)).strftime("%Y-%m-%d"), "critical": 1, "high": 4, "status": "Closed"},
        ]
        base["historical_remediation"] = detail.get("development", [])[:6]
    elif stage_key == "testing":
        base["test_plans"] = detail.get("testing", [])[:8]
        base["vapt_history"] = [
            {"date": (ANCHOR - timedelta(days=18)).strftime("%Y-%m-%d"), "critical": 1, "high": 4, "status": "Closed"},
        ]
        base["reusable_packs"] = [
            {"pack": "Prompt Injection Tests", "pass_rate": "97%", "apps": 4},
            {"pack": "PCI Regression Pack", "pass_rate": "99%", "apps": 3},
        ]
    elif stage_key == "go-live":
        gl = detail.get("go_live", {})
        base["cab_approvals"] = [
            {"id": "CAB-2026-042", "date": "2026-06-10", "authority": "CAB Chair", "status": "Approved"},
        ]
        base["rollback_plans"] = [{"release": release["name"], "rto": "30 min", "last_drill": "2026-05-10"}]
        base["historical_releases"] = [
            {"application": pick(seed("hr", i), _DEMO_APPS), "release": f"REL-2025-Q{(i % 4) + 1}",
             "go_live_date": (ANCHOR - timedelta(days=60 + i * 80)).strftime("%Y-%m-%d"), "result": "Successful"}
            for i in range(5)
        ]
        base["open_observations"] = gl.get("open_observations", 0)
        base["exceptions_pending"] = gl.get("exceptions_pending", 0)
    return base


def _release_apps_safe(release: dict) -> list[str]:
    return release.get("impacted_applications", [release.get("application", "Net Banking")])


def build_reuse_wizard(doc: dict, release: dict, stage_key: str) -> dict[str, Any]:
    s = seed("reusewiz", doc.get("doc_id", ""), stage_key)
    return {
        "document_id": doc.get("doc_id"),
        "document_title": doc.get("title"),
        "stage_key": stage_key,
        "available_applications": _DEMO_APPS,
        "available_frameworks": _FRAMEWORKS,
        "suggested_controls": [
            f"APPSEC-{between(seed('rwc', s, i), 1, 99):02d}" for i in range(8)
        ],
        "preview_mappings": [
            {"application": pick(seed("rwa", s, i), _DEMO_APPS), "framework": pick(seed("rwf", s, i), _FRAMEWORKS),
             "control_id": f"APPSEC-{between(seed('rwcc', s, i), 1, 99):02d}", "status": "Ready"}
            for i in range(6)
        ],
        "cloned_package_id": f"PKG-REUSE-{release['id'].split('-')[-1]}-{between(s >> 4, 100, 999)}",
    }


def extend_document_tabs(tabs: dict[str, Any], stage_key: str, stage_kb: dict[str, Any], doc: dict, release: dict, s: int) -> dict[str, Any]:
    """Add stage-specific tab panels to document viewer."""
    if stage_key == "requirement":
        tabs["control_lineage"] = {
            "rows": [
                {"application": a, "first_implementation": (ANCHOR - timedelta(days=between(seed("cli", s, a), 200, 900))).strftime("%Y-%m-%d"),
                 "latest_implementation": (ANCHOR - timedelta(days=between(seed("cll", s, a), 7, 120))).strftime("%Y-%m-%d"),
                 "observations": between(seed("clo", s, a), 0, 4), "exceptions": between(seed("cle", s, a), 0, 2),
                 "reuse_recommendation": (stage_kb.get("recommended_language") or pick(seed("clr", s, a), ["Reuse approved", "Delta analysis required", "Pattern eligible"]))[:80]}
                for a in _DEMO_APPS[:6]
            ],
        }
        tabs["reuse_wizard"] = {"data": build_reuse_wizard(doc, release, stage_key)}
    elif stage_key == "design":
        tabs["design_patterns"] = {"rows": stage_kb.get("reusable_design_patterns", [])}
        tabs["architecture_lineage"] = {"rows": stage_kb.get("historical_design_knowledge_base", [])}
        tabs["design_reuse"] = {
            "rows": [{"pattern": p["pattern"], "frequency": len(p.get("used_in", [])), "used_in": ", ".join(p.get("used_in", []))}
                     for p in stage_kb.get("reusable_design_patterns", [])],
        }
    elif stage_key == "development":
        ib = stage_kb.get("implementation_knowledge_base", {})
        tabs["code_patterns"] = {"rows": ib.get("reusable_components", [])}
        tabs["shared_libraries"] = {"items": ib.get("shared_libraries", [])}
        tabs["security_findings"] = {"rows": stage_kb.get("historical_remediation", [])}
        tabs["remediation_history"] = {"rows": stage_kb.get("historical_remediation", [])}
    elif stage_key == "testing":
        tk = stage_kb.get("reusable_test_knowledge", {})
        tabs["test_plans"] = {"rows": tk.get("historical_test_cases", [])}
        tabs["regression_packs"] = {"items": tk.get("historical_regression_suites", [])}
        tabs["vapt_results"] = {"items": tk.get("historical_vapt_scenarios", [])}
        tabs["uat_results"] = {"items": tk.get("historical_uat_packs", [])}
        tabs["ai_validation"] = {"items": tk.get("historical_ai_validation_packs", [])}
        tabs["reusable_packs"] = {"rows": stage_kb.get("test_packs", [])}
    return tabs
