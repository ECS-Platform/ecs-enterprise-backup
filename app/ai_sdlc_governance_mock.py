"""AI & SDLC Governance — deterministic mock data for leadership demo.

Self-contained mock engine with enterprise-scale, traceable datasets per
ECS Enterprise Demo Quality Standard.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.demo_data_standards import (
    BANKING_APPLICATIONS,
    BANKING_OWNERS,
    between,
    expand_catalog,
    generate_audit_trail,
    generate_monthly_trend,
    pick,
    seed,
)

ANCHOR = date(2026, 5, 28)

AI_APPLICATIONS = [
    {
        "id": "AI-APP-001", "name": "Net Banking AI Assistant", "application": "Net Banking",
        "owner": "R. Mehta", "business_unit": "Retail Digital", "model": "GPT-4o Enterprise (Azure)",
        "use_case": "Account enquiry, transaction help, product FAQ", "users_daily": 12400,
        "risk_tier": "Critical", "compliance_score": 88, "policy_compliance": 92,
        "model_status": "Approved", "prompts_active": 34, "hallucinations_30d": 0,
        "unsafe_blocked_30d": 0, "tokens_mtd": 2840000, "last_review": "2026-05-22",
    },
    {
        "id": "AI-APP-002", "name": "Mobile Banking Copilot", "application": "Mobile Banking",
        "owner": "A. Sharma", "business_unit": "Retail Digital", "model": "Claude 3.5 Sonnet (Bedrock)",
        "use_case": "In-app support, fraud explainability, onboarding guidance", "users_daily": 18600,
        "risk_tier": "Critical", "compliance_score": 84, "policy_compliance": 89,
        "model_status": "Approved", "prompts_active": 41, "hallucinations_30d": 0,
        "unsafe_blocked_30d": 0, "tokens_mtd": 3920000, "last_review": "2026-05-20",
    },
    {
        "id": "AI-APP-003", "name": "Payments Operations Assistant", "application": "Payments",
        "owner": "K. Reddy", "business_unit": "Digital Payments", "model": "GPT-4o Mini (Internal)",
        "use_case": "Settlement queries, NPCI reconciliation, ops runbooks", "users_daily": 890,
        "risk_tier": "High", "compliance_score": 91, "policy_compliance": 94,
        "model_status": "Approved", "prompts_active": 22, "hallucinations_30d": 0,
        "unsafe_blocked_30d": 0, "tokens_mtd": 680000, "last_review": "2026-05-24",
    },
    {
        "id": "AI-APP-004", "name": "Treasury Analytics Assistant", "application": "Treasury",
        "owner": "S. Banerjee", "business_unit": "Wholesale Banking", "model": "FinGPT-Treasury v2 (Private)",
        "use_case": "FX exposure summaries, liquidity scenario analysis", "users_daily": 145,
        "risk_tier": "High", "compliance_score": 79, "policy_compliance": 86,
        "model_status": "Conditional Approval", "prompts_active": 18, "hallucinations_30d": 0,
        "unsafe_blocked_30d": 0, "tokens_mtd": 420000, "last_review": "2026-05-18",
    },
    {
        "id": "AI-APP-005", "name": "Customer Service Copilot", "application": "Customer Onboarding",
        "owner": "M. D'Souza", "business_unit": "Retail Banking", "model": "GPT-4o Enterprise (Azure)",
        "use_case": "Call-centre agent assist, KYC guidance, complaint drafting", "users_daily": 2100,
        "risk_tier": "High", "compliance_score": 86, "policy_compliance": 90,
        "model_status": "Approved", "prompts_active": 29, "hallucinations_30d": 0,
        "unsafe_blocked_30d": 0, "tokens_mtd": 1560000, "last_review": "2026-05-21",
    },
]

_EXTRA_AI_NAMES = [
    ("AI-APP-006", "Trade Finance Document AI", "Trade Finance", "Letter of credit extraction, SWIFT parsing"),
    ("AI-APP-007", "Cards Dispute Resolution Bot", "Cards", "Chargeback drafting, merchant dispute triage"),
    ("AI-APP-008", "Wealth Advisory Copilot", "Wealth Management", "Portfolio summary, suitability checks"),
    ("AI-APP-009", "Loan Origination Assistant", "Loan Origination", "Income doc summarisation, policy Q&A"),
    ("AI-APP-010", "Fraud Alert Explainer", "Fraud Monitoring", "Alert narrative, false-positive guidance"),
    ("AI-APP-011", "Core Banking Ops Guide", "Core Banking", "Batch job runbooks, reconciliation help"),
    ("AI-APP-012", "ATM Incident Assistant", "ATM Switch", "Cash-out incident triage, SLA tracking"),
    ("AI-APP-013", "UPI Merchant Support AI", "UPI Gateway", "Merchant onboarding FAQ, settlement queries"),
    ("AI-APP-014", "CRM Relationship Coach", "CRM", "Relationship manager briefings, next-best-action"),
    ("AI-APP-015", "Data Lake Query Copilot", "Data Lake", "Natural language SQL, lineage explanation"),
    ("AI-APP-016", "Regulatory Reporting Assistant", "Treasury", "RBI return drafting, validation checks"),
    ("AI-APP-017", "Branch Staff Knowledge Bot", "Net Banking", "Product policy, procedure lookup"),
    ("AI-APP-018", "Compliance Policy Navigator", "Core Banking", "Policy search, control mapping hints"),
]

_MODELS_POOL = [
    "GPT-4o Enterprise (Azure)", "Claude 3.5 Sonnet (Bedrock)", "GPT-4o Mini (Internal)",
    "FinGPT-Treasury v2 (Private)", "Llama 3.1 70B (Private)", "Gemini 1.5 Pro (GCP)",
    "Embeddings-small-v3", "CodeLlama-Secure v2",
]

SDLC_FRAMEWORKS = [
    "PCI DSS", "DPSC", "AppSec", "VAPT", "OS Baselining",
    "DB Baselining", "Middleware Baselining", "Nginx Baselining",
    "ITPP", "AI Governance",
]

SDLC_STAGES = [
    {"key": "requirement", "label": "Requirement Governance", "icon": "📋", "order": 1},
    {"key": "design", "label": "Design Governance", "icon": "🏗", "order": 2},
    {"key": "development", "label": "Development Governance", "icon": "⚙", "order": 3},
    {"key": "testing", "label": "Testing Governance", "icon": "🧪", "order": 4},
    {"key": "go-live", "label": "Go-Live Governance", "icon": "🚀", "order": 5},
]

RELEASES = [
    {"id": "REL-2026-Q2-NB", "name": "Net Banking Q2 Release", "application": "Net Banking", "owner": "R. Mehta", "target_date": "2026-06-15"},
    {"id": "REL-2026-Q2-MB", "name": "Mobile Banking 4.2", "application": "Mobile Banking", "owner": "A. Sharma", "target_date": "2026-06-22"},
    {"id": "REL-2026-Q2-PAY", "name": "Payments Switch Upgrade", "application": "Payments", "owner": "K. Reddy", "target_date": "2026-07-05"},
    {"id": "REL-2026-Q3-TF", "name": "Trade Finance OCR Rollout", "application": "Trade Finance", "owner": "T. Kapoor", "target_date": "2026-08-12"},
    {"id": "REL-2026-Q3-UPI", "name": "UPI Gateway Hardening", "application": "UPI Gateway", "owner": "H. Singh", "target_date": "2026-09-01"},
]

_PROMPT_SNIPPETS = [
    "Summarise failed login attempts for customer segment",
    "Draft RBI-compliant response for payment dispute",
    "Explain FX hedging policy for treasury desk",
    "Generate onboarding checklist for NRI account",
    "List PCI controls applicable to card token vault",
    "Parse SWIFT MT700 fields for trade finance LC",
    "Draft chargeback rebuttal for merchant dispute",
    "Summarise portfolio risk for HNI client review",
    "Explain fraud alert FRM-8842 root cause hypothesis",
    "Generate ATM cash-out incident timeline for ops",
]

_POLICY_NAMES = [
    "No PII in prompts without redaction",
    "Approved models only in production",
    "Human review for credit decisions",
    "Prompt versioning before deployment",
    "Hallucination threshold < 0.5 for customer-facing",
    "Token budget per application enforced",
    "AI output logging retained 7 years",
    "Bias testing for customer-facing models",
    "Red-team review for new prompt templates",
    "Data residency — India region only",
    "No training on customer PII without consent",
    "Escalation path for model drift alerts",
]


def _risk_label(score: int) -> str:
    if score >= 80:
        return "Critical"
    if score >= 65:
        return "High"
    if score >= 45:
        return "Medium"
    return "Low"


def _ensure_ai_applications() -> list[dict]:
    apps = list(AI_APPLICATIONS)
    for i, (aid, name, app, use_case) in enumerate(_EXTRA_AI_NAMES):
        s = seed("aiapp", aid)
        apps.append({
            "id": aid, "name": name, "application": app,
            "owner": pick(s, BANKING_OWNERS), "business_unit": pick(s >> 2, ["Retail Digital", "Wholesale Banking", "Digital Payments", "IT Platform"]),
            "model": pick(s >> 4, _MODELS_POOL),
            "use_case": use_case, "users_daily": between(s >> 6, 120, 8500),
            "risk_tier": pick(s >> 8, ["Critical", "High", "High", "Medium"]),
            "compliance_score": between(s >> 10, 72, 96),
            "policy_compliance": between(s >> 12, 78, 98),
            "model_status": pick(s >> 14, ["Approved", "Approved", "Conditional Approval", "Pending"]),
            "prompts_active": between(s >> 16, 8, 42),
            "hallucinations_30d": 0, "unsafe_blocked_30d": 0,
            "tokens_mtd": between(s >> 18, 180000, 4200000),
            "last_review": (ANCHOR - timedelta(days=between(s >> 20, 1, 45))).strftime("%Y-%m-%d"),
        })
    return apps


def _generate_all_prompts(apps: list[dict]) -> list[dict]:
    prompts: list[dict] = []
    for app in apps:
        for j in range(8):
            s = seed("prm", app["id"], j)
            risk = round(0.12 + (s % 75) / 100, 2)
            prompts.append({
                "prompt_id": f"PRM-{app['id'][-3:]}-{j+1:02d}",
                "application": app["name"],
                "application_id": app["id"],
                "user": f"{app['owner'].split()[0].lower()}.ops@bank.com",
                "team": app["business_unit"],
                "model": app["model"],
                "prompt_snippet": pick(s, _PROMPT_SNIPPETS),
                "risk_score": risk,
                "hallucination_flag": risk > 0.42,
                "unsafe_flag": risk > 0.68,
                "review_status": "Quarantined" if risk > 0.68 else "Flagged" if risk > 0.42 else "Approved",
                "timestamp": (ANCHOR - timedelta(days=between(s >> 3, 0, 90))).strftime("%Y-%m-%d %H:%M"),
            })
    return prompts


def _sync_app_counters(apps: list[dict], prompts: list[dict]) -> None:
    for app in apps:
        app_prompts = [p for p in prompts if p["application_id"] == app["id"]]
        app["hallucinations_30d"] = sum(1 for p in app_prompts if p["hallucination_flag"])
        app["unsafe_blocked_30d"] = sum(1 for p in app_prompts if p["unsafe_flag"])


def _generate_token_events(apps: list[dict]) -> list[dict]:
    events: list[dict] = []
    for app in apps:
        s = seed("tok_evt", app["id"])
        daily_avg = max(app["tokens_mtd"] // 28, 1000)
        for d in range(28):
            day = ANCHOR - timedelta(days=27 - d)
            tokens = between(seed("tokd", app["id"], d), int(daily_avg * 0.7), int(daily_avg * 1.3))
            events.append({
                "date": day.strftime("%Y-%m-%d"),
                "month_key": day.strftime("%Y-%m"),
                "application": app["name"],
                "application_id": app["id"],
                "tokens": tokens,
                "cost_usd": round(tokens / 1000 * 0.012, 2),
            })
    return events


def _generate_heatmap_drill(apps: list[dict]) -> dict[str, Any]:
    dimensions = ["Data Privacy", "Model Risk", "Prompt Safety", "Bias & Fairness", "Audit Trail", "Human-in-Loop"]
    rows = []
    cells_index: dict[str, dict] = {}
    for app in apps:
        row = {"application": app["name"], "application_id": app["id"], "cells": []}
        for dim in dimensions:
            s = seed(app["id"], dim)
            score = between(s, 55, 98)
            cell = {
                "dimension": dim, "score": score,
                "tone": "green" if score >= 85 else "amber" if score >= 70 else "red",
                "risk": _risk_label(100 - score),
                "application": app["name"], "application_id": app["id"],
                "controls_reviewed": between(s >> 2, 8, 24),
                "open_findings": between(s >> 4, 0, 5),
                "last_assessed": (ANCHOR - timedelta(days=between(s >> 6, 1, 60))).strftime("%Y-%m-%d"),
            }
            row["cells"].append(cell)
            cells_index[f"{app['id']}::{dim}"] = cell
        rows.append(row)
    return {"dimensions": dimensions, "rows": rows, "cells_index": cells_index}


def build_ai_posture() -> dict[str, Any]:
    apps = _ensure_ai_applications()
    all_prompts = _generate_all_prompts(apps)
    _sync_app_counters(apps, all_prompts)

    total_tokens = sum(a["tokens_mtd"] for a in apps)
    avg_compliance = round(sum(a["compliance_score"] for a in apps) / len(apps), 1)
    avg_policy = round(sum(a["policy_compliance"] for a in apps) / len(apps), 1)
    hallucinations = [p for p in all_prompts if p["hallucination_flag"]]
    unsafe = [p for p in all_prompts if p["unsafe_flag"]]
    approved_models = sum(1 for a in apps if a["model_status"] == "Approved")

    heatmap = _generate_heatmap_drill(apps)
    token_events = _generate_token_events(apps)

    token_by_app = [{"application": a["name"], "application_id": a["id"], "tokens": a["tokens_mtd"],
                     "cost_usd": round(a["tokens_mtd"] / 1000 * 0.012, 0)} for a in apps]
    token_by_team: dict[str, dict] = {}
    for a in apps:
        t = token_by_team.setdefault(a["business_unit"], {"team": a["business_unit"], "tokens": 0, "cost_usd": 0})
        t["tokens"] += a["tokens_mtd"]
        t["cost_usd"] = round(t["tokens"] / 1000 * 0.012, 0)

    monthly_trend = generate_monthly_trend(
        12, ANCHOR, prefix="ai_tok_m",
        value_fn=lambda s, _i: between(s, 7200000, 11800000),
    )
    for pt in monthly_trend:
        mk = pt["month_key"]
        pt["tokens"] = pt["value"]
        pt["events"] = [e for e in token_events if e["month_key"] == mk or mk == ANCHOR.strftime("%Y-%m")][:40]
        if not pt["events"]:
            pt["events"] = [e for e in token_events if e["month_key"] <= mk][:20]

    policies = []
    for i, name in enumerate(_POLICY_NAMES):
        s = seed("pol", i)
        violations = between(s, 0, 8)
        policies.append({
            "policy": name,
            "compliance_pct": between(s >> 2, 82, 100),
            "violations": violations,
            "owner": pick(s >> 4, ["AI CoE", "Model Risk", "Compliance", "AppSec CoE", "FinOps"]),
            "violation_records": [
                {"id": f"POL-V-{i+1:03d}-{v+1:02d}", "application": pick(seed("pv", i, v), apps)["name"],
                 "detail": f"Policy breach sample #{v+1}", "status": pick(seed("pvs", i, v), ["Open", "Remediated", "Accepted"])}
                for v in range(violations)
            ],
        })

    model_approvals = [
        {"model": a["model"], "application": a["name"], "application_id": a["id"],
         "status": a["model_status"],
         "approved_by": "Model Risk Board" if a["model_status"] == "Approved" else "Pending CIO",
         "expiry": "2026-12-31" if a["model_status"] == "Approved" else "—",
         "risk_tier": a["risk_tier"]}
        for a in apps
    ]

    audit_trail = generate_audit_trail(
        85, ANCHOR, years_back=3,
        detail_builder=lambda i, action, actor: (
            f"{pick(seed('ad', i), apps)['name']} — {pick(seed('adf', i), SDLC_FRAMEWORKS)} — {action}"
        ),
    )

    return {
        "summary": {
            "ai_applications": len(apps),
            "avg_compliance_score": avg_compliance,
            "avg_policy_compliance": avg_policy,
            "prompts_audited_30d": len(all_prompts),
            "hallucination_alerts": len(hallucinations),
            "unsafe_blocked": len(unsafe),
            "total_tokens_mtd": total_tokens,
            "total_cost_usd": round(total_tokens / 1000 * 0.012, 0),
            "models_approved": approved_models,
            "models_conditional": len(apps) - approved_models,
        },
        "kpis": [
            {"label": "AI Applications", "value": len(apps), "hint": "Production AI assistants", "tone": "primary", "drill": "inventory"},
            {"label": "AI Compliance Score", "value": f"{avg_compliance}%", "hint": "Weighted posture average", "tone": "success", "drill": "compliance"},
            {"label": "Policy Compliance", "value": f"{avg_policy}%", "hint": f"{len(policies)} AI policies tracked", "tone": "info", "drill": "policies"},
            {"label": "Hallucination Alerts", "value": len(hallucinations), "hint": "Flagged in audit sample", "tone": "warning", "drill": "hallucinations"},
            {"label": "Unsafe Blocked", "value": len(unsafe), "hint": "Auto-quarantined", "tone": "danger", "drill": "unsafe"},
            {"label": "Tokens MTD", "value": f"{total_tokens/1_000_000:.1f}M", "hint": f"${round(total_tokens/1000*0.012,0):,.0f} estimated", "tone": "teal", "drill": "tokens"},
            {"label": "Models Approved", "value": f"{approved_models}/{len(apps)}", "hint": "Production clearance", "tone": "success", "drill": "models"},
            {"label": "Prompts Audited", "value": len(all_prompts), "hint": "Full audit log", "tone": "navy", "drill": "prompts"},
        ],
        "applications": apps,
        "risk_heatmap": {"dimensions": heatmap["dimensions"], "rows": heatmap["rows"]},
        "_heatmap_index": heatmap["cells_index"],
        "prompt_audit": all_prompts,
        "hallucinations": hallucinations,
        "unsafe_prompts": unsafe,
        "token_usage": {
            "by_application": token_by_app,
            "by_team": list(token_by_team.values()),
            "daily_trend": [
                {"day": (ANCHOR - timedelta(days=6 - i)).strftime("%d %b"), "day_key": (ANCHOR - timedelta(days=6 - i)).strftime("%Y-%m-%d"),
                 "tokens": between(seed("tok7", i), 800000, 1200000),
                 "events": [e for e in token_events if e["date"] == (ANCHOR - timedelta(days=6 - i)).strftime("%Y-%m-%d")]}
                for i in range(7)
            ],
            "monthly_trend": monthly_trend,
            "events": token_events,
        },
        "policies": policies,
        "model_approvals": model_approvals,
        "audit_trail": audit_trail,
    }


def _stage_summary(stage_key: str, release: dict) -> dict[str, Any]:
    s = seed(stage_key, release["id"])
    fw_coverage = between(s, 72, 98)
    ctrl_coverage = between(s >> 2, 68, 95)
    checklist = between(s >> 4, 55, 92)
    gaps = between(s >> 6, 4, 22)
    readiness = round((fw_coverage + ctrl_coverage + checklist) / 3, 1)
    return {
        "framework_coverage_pct": fw_coverage,
        "control_coverage_pct": ctrl_coverage,
        "checklist_completion_pct": checklist,
        "open_gaps": gaps,
        "owner": release["owner"],
        "due_date": release["target_date"],
        "approval_status": pick(s, ["In Review", "Approved", "Pending Evidence", "Escalated"]),
        "evidence_status": pick(s >> 8, ["72% collected", "85% collected", "58% collected", "Complete"]),
        "risk_rating": _risk_label(100 - readiness),
        "readiness_score": readiness,
        "gap_records": [
            {"gap_id": f"GAP-{release['id'][-2:]}-{stage_key[:3].upper()}-{g+1:03d}",
             "framework": pick(seed("gap", stage_key, release["id"], g), SDLC_FRAMEWORKS),
             "control": f"CTRL-{between(seed('gc', g), 100, 999)}",
             "description": pick(seed("gd", g), ["Missing SAST evidence", "DR test overdue", "Consent log gap", "TLS cipher non-compliance", "Prompt guardrail not deployed"]),
             "owner": pick(seed("go", g), BANKING_OWNERS), "due": release["target_date"],
             "severity": pick(seed("gs", g), ["High", "Medium", "Low"])}
            for g in range(gaps)
        ],
    }


def build_sdlc_gates(release_id: str = "") -> dict[str, Any]:
    release = next((r for r in RELEASES if r["id"] == release_id), RELEASES[0]) if release_id else RELEASES[0]
    stages = []
    for st in SDLC_STAGES:
        summary = _stage_summary(st["key"], release)
        stages.append({**st, **summary, "release_id": release["id"]})

    overall = round(sum(s["readiness_score"] for s in stages) / len(stages), 1)
    total_gaps = sum(s["open_gaps"] for s in stages)
    all_gaps = []
    for s in stages:
        all_gaps.extend(s.get("gap_records", []))

    return {
        "release": release,
        "releases": RELEASES,
        "frameworks": SDLC_FRAMEWORKS,
        "stages": stages,
        "all_gaps": all_gaps,
        "summary": {
            "overall_readiness": overall,
            "total_gaps": total_gaps,
            "frameworks_in_scope": len(SDLC_FRAMEWORKS),
            "releases_active": len(RELEASES),
        },
        "kpis": [
            {"label": "Overall Readiness", "value": f"{overall}%", "tone": "success" if overall >= 80 else "warning", "drill": "readiness"},
            {"label": "Active Releases", "value": len(RELEASES), "tone": "primary", "drill": "releases"},
            {"label": "Frameworks in Scope", "value": len(SDLC_FRAMEWORKS), "tone": "info", "drill": "frameworks"},
            {"label": "Open Gaps (All Stages)", "value": total_gaps, "tone": "danger", "drill": "gaps"},
            {"label": "Stages Complete", "value": sum(1 for s in stages if s["checklist_completion_pct"] >= 90), "tone": "teal", "drill": "stages_complete"},
        ],
    }


def _stage_requirements(release: dict, count: int = 24) -> list[dict]:
    titles = [
        "Multi-factor authentication for privileged admin API",
        "AI copilot must not expose raw PAN/CVV in responses",
        "Database encryption at rest for customer PII",
        "DR failover RTO ≤ 4 hours for tier-1 apps",
        "API rate limiting for UPI merchant endpoints",
        "Session timeout ≤ 15 minutes for net banking",
        "Immutable audit logs for privileged DB access",
        "WAF rules for OWASP Top 10 on internet banking",
        "Consent capture for AI-assisted onboarding",
        "Segregation of duties for treasury deal booking",
    ]
    rows = []
    for i in range(count):
        s = seed("req", release["id"], i)
        rows.append({
            "req_id": f"REQ-{release['id'].split('-')[-1]}-{101+i}",
            "title": pick(s, titles) + (f" (variant {i+1})" if i >= len(titles) else ""),
            "interpretation": f"Maps to {pick(s>>2, SDLC_FRAMEWORKS)}, {pick(s>>4, SDLC_FRAMEWORKS)}",
            "controls_generated": between(s >> 6, 2, 6),
            "owner_ack": pick(s >> 8, ["Acknowledged", "Pending", "Acknowledged"]),
            "applicability": pick(s >> 10, [release["application"], "All AI assistants", "Net Banking, Mobile Banking"]),
            "owner": pick(s >> 12, BANKING_OWNERS),
            "status": pick(s >> 14, ["Approved", "In Review", "Approved"]),
        })
    return rows


def _stage_designs(release: dict, count: int = 22) -> list[dict]:
    rows = []
    for i in range(count):
        s = seed("dsg", release["id"], i)
        rows.append({
            "design_id": f"DSG-2026-{14+i:03d}",
            "title": f"{release['application']} — {pick(s, ['Architecture', 'Security', 'API', 'Data', 'AI RAG'])} design #{i+1}",
            "architecture_review": pick(s >> 2, ["Approved", "Pending", "Approved"]),
            "security_review": pick(s >> 4, ["Approved", "Pending", "Conditional"]),
            "compliance_review": pick(s >> 6, ["Approved", "Conditional", "Pending"]),
            "reviewer": pick(s >> 8, ["Enterprise Architecture", "AppSec CoE", "A. Sharma", "AI CoE"]),
            "submitted": (ANCHOR - timedelta(days=between(s >> 10, 1, 45))).strftime("%Y-%m-%d"),
            "status": pick(s >> 12, ["Approved", "In Review", "Pending Security"]),
        })
    return rows


def _stage_development(release: dict, count: int = 24) -> list[dict]:
    items = [
        ("Secure coding — OWASP Top 10 training completion", "AppSec AS-C-02"),
        ("SAST pipeline integration (SonarQube)", "AppSec AS-C-05"),
        ("Secrets scanning in CI/CD", "AppSec AS-C-07"),
        ("AI prompt injection guardrails", "AI Governance AG-08"),
        ("OS hardening baseline (CIS L2)", "OS Baselining OS-11"),
        ("DB TDE enablement verification", "DB Baselining DBB-03"),
        ("Nginx TLS 1.3 configuration", "Nginx Baselining NGX-02"),
        ("Middleware patch compliance", "Middleware Baselining MW-07"),
    ]
    rows = []
    for i in range(count):
        s = seed("dev", release["id"], i)
        item, ctrl = pick(s, items)
        pct = between(s >> 2, 55, 100)
        rows.append({
            "item": item if i < len(items) else f"{item} — track {i+1}",
            "progress_pct": pct,
            "control": ctrl,
            "owner": pick(s >> 4, BANKING_OWNERS + ["DevOps Lead", "Infra Team", "AI CoE"]),
            "status": "Complete" if pct >= 95 else "In Progress" if pct >= 70 else "At Risk",
        })
    return rows


def _stage_testing(release: dict, count: int = 28) -> list[dict]:
    types = ["VAPT", "AppSec", "Compliance", "AI Governance", "DB Baselining", "Regression"]
    rows = []
    for i in range(count):
        s = seed("tst", release["id"], i)
        ttype = pick(s, types)
        defects = between(s >> 2, 0, 5)
        status = "Passed" if defects == 0 and ttype != "AppSec" else pick(s >> 4, ["Passed", "Failed", "In Progress", "Pending"])
        rows.append({
            "test_id": f"TC-{ttype[:4].upper()}-{400+i}",
            "name": f"{ttype} — {release['application']} scope item {i+1}",
            "type": ttype,
            "status": status,
            "defects": defects,
            "owner": pick(s >> 6, ["EY VAPT", "AppSec CoE", "Internal Audit", "Model Risk", "DBA Team"]),
            "due": (ANCHOR + timedelta(days=between(s >> 8, 1, 30))).strftime("%Y-%m-%d"),
            "defect_records": [
                {"defect_id": f"DEF-{400+i}-{d+1}", "severity": pick(seed("def", i, d), ["Critical", "High", "Medium"]),
                 "summary": pick(seed("defs", i, d), ["SQL injection vector", "Missing MFA on admin API", "Weak cipher suite", "Prompt injection bypass"])}
                for d in range(defects)
            ],
        })
    return rows


def build_sdlc_stage_detail(stage_key: str, release_id: str = "") -> dict[str, Any]:
    release = next((r for r in RELEASES if r["id"] == release_id), RELEASES[0])
    stage_meta = next((s for s in SDLC_STAGES if s["key"] == stage_key), SDLC_STAGES[0])
    summary = _stage_summary(stage_key, release)

    fw_rows = []
    for fw in SDLC_FRAMEWORKS:
        s = seed(stage_key, release["id"], fw)
        gaps = between(s >> 6, 1, 8)
        fw_rows.append({
            "framework": fw,
            "controls_total": between(s, 12, 48),
            "controls_covered": between(s >> 2, 8, 45),
            "checklist_pct": between(s >> 4, 60, 98),
            "gaps": gaps,
            "owner": release["owner"],
            "due_date": release["target_date"],
            "evidence_status": pick(s, ["Collected", "Partial", "Pending", "Approved"]),
            "risk": _risk_label(between(s >> 8, 20, 75)),
            "gap_records": summary["gap_records"][:gaps],
        })

    detail: dict[str, Any] = {
        "stage": stage_meta,
        "release": release,
        "summary": summary,
        "framework_rows": fw_rows,
        "audit_trail": generate_audit_trail(
            32, ANCHOR, years_back=3,
            detail_builder=lambda i, action, _actor: f"{release['name']} — {stage_meta['label']} — {action}",
        ),
    }

    if stage_key == "requirement":
        detail["requirements"] = _stage_requirements(release)
    elif stage_key == "design":
        detail["designs"] = _stage_designs(release)
    elif stage_key == "development":
        detail["development"] = _stage_development(release)
    elif stage_key == "testing":
        detail["testing"] = _stage_testing(release)
    elif stage_key == "go-live":
        obs_count = between(seed(release["id"], "obs"), 8, 18)
        detail["go_live"] = {
            "readiness_score": summary["readiness_score"],
            "open_observations": obs_count,
            "exceptions_pending": between(seed(release["id"], "exc"), 2, 8),
            "residual_risk_acceptance": "CIO sign-off required for High items",
            "final_approval": pick(seed(release["id"], "fin"), ["Pending Audit Committee", "Approved", "Conditional"]),
            "observation_records": [
                {"obs_id": f"OBS-{release['id'][-2:]}-{o+1:03d}", "framework": pick(seed("obf", o), SDLC_FRAMEWORKS),
                 "summary": pick(seed("obs", o), ["VAPT finding open", "Evidence stale >90d", "Exception expiring", "Control not tested"]),
                 "severity": pick(seed("obse", o), ["High", "Medium", "Low"]), "owner": pick(seed("obo", o), BANKING_OWNERS)}
                for o in range(obs_count)
            ],
            "checklist": [
                {"item": "All critical VAPT findings closed", "status": "Complete", "owner": "AppSec CoE"},
                {"item": "Evidence pack submitted to auditor", "status": "In Progress", "owner": release["owner"]},
                {"item": "AI Governance model approval current", "status": "Complete", "owner": "Model Risk"},
                {"item": "DR drill evidence within 90 days", "status": "Complete", "owner": "ITPP Owner"},
                {"item": "CAB emergency change window confirmed", "status": "Pending", "owner": "Change Manager"},
            ] + [
                {"item": f"Go-live gate item {i+6}", "status": pick(seed("gl", i), ["Complete", "In Progress", "Pending"]),
                 "owner": pick(seed("glo", i), BANKING_OWNERS)}
                for i in range(14)
            ],
        }

    return detail


def build_ai_registry() -> dict[str, Any]:
    apps = _ensure_ai_applications()
    models = []
    for i, app in enumerate(apps):
        s = seed("mdl", app["id"])
        models.append({
            "model_id": f"MDL-{i+1:03d}",
            "name": app["model"],
            "provider": pick(s, ["Microsoft Azure OpenAI", "AWS Bedrock", "Internal LLM Gateway", "Internal MLOps", "GCP Vertex"]),
            "version": f"{between(s>>2,1,3)}.{between(s>>4,0,9)}.{between(s>>6,0,20)}",
            "risk_tier": app["risk_tier"],
            "status": "Approved" if app["model_status"] == "Approved" else app["model_status"].replace(" Approval", ""),
            "approved_by": "Model Risk Board" if app["model_status"] == "Approved" else "Pending",
            "approved_date": (ANCHOR - timedelta(days=between(s>>8, 30, 180))).strftime("%Y-%m-%d"),
            "expiry": "2026-12-31" if app["model_status"] == "Approved" else "2026-08-31",
            "applications": [app["name"]],
            "owner": app["owner"],
        })

    models = expand_catalog(models, 20, lambda n: {
        "model_id": f"MDL-{n+1:03d}", "name": pick(seed("mx", n), _MODELS_POOL),
        "provider": "Internal MLOps", "version": "1.0.0", "risk_tier": "Medium",
        "status": pick(seed("ms", n), ["Approved", "Pending", "Conditional"]),
        "approved_by": "AI CoE", "approved_date": "2026-02-01", "expiry": "2026-12-31",
        "applications": [pick(seed("ma", n), apps)["name"]], "owner": pick(seed("mo", n), BANKING_OWNERS),
    })

    prompts = []
    for app in apps:
        for v in range(1, 4):
            prompts.append({
                "prompt_id": f"PR-{app['id'][-3:]}-v{v}",
                "name": f"{app['name']} — System Prompt v{v}.0",
                "application": app["name"], "application_id": app["id"],
                "version": f"v{v}.0",
                "status": "Approved" if v < 3 else pick(seed("ps", app["id"], v), ["Pending Review", "In Review"]),
                "owner": app["owner"],
                "approved_by": "Model Risk" if v < 3 else "—",
                "last_updated": (ANCHOR - timedelta(days=v * 18)).strftime("%Y-%m-%d"),
                "use_case": app["use_case"],
            })

    version_history = []
    for app in apps:
        for v in range(1, 5):
            version_history.append({
                "prompt_id": f"PR-{app['id'][-3:]}-v{v}",
                "version": f"v{v}.0",
                "changed_by": app["owner"],
                "change": pick(seed("pvc", app["id"], v), ["PII redaction rules tightened", "RBI consent language added", "Fraud template update", "NPCI reconciliation prompt"]),
                "date": (ANCHOR - timedelta(days=v * 22)).strftime("%Y-%m-%d"),
                "status": pick(seed("pvs", app["id"], v), ["Approved", "Pending Review"]),
            })

    use_cases = expand_catalog([
        {"id": "UC-001", "name": "Customer-facing FAQ & support", "applications": 3, "risk": "High", "owner": "Retail Digital", "status": "Active", "model_count": 2},
        {"id": "UC-002", "name": "Operations & reconciliation assist", "applications": 1, "risk": "High", "owner": "Digital Payments", "status": "Active", "model_count": 1},
        {"id": "UC-003", "name": "Treasury analytics & FX scenarios", "applications": 1, "risk": "Critical", "owner": "Wholesale Banking", "status": "Conditional", "model_count": 1},
    ], 20, lambda n: {
        "id": f"UC-{n+1:03d}",
        "name": pick(seed("ucn", n), ["Internal code Q&A", "Document extraction", "Agent assist", "Regulatory drafting", "Risk summarisation"]),
        "applications": between(seed("uca", n), 1, 4), "risk": pick(seed("ucr", n), ["High", "Medium", "Critical"]),
        "owner": pick(seed("uco", n), BANKING_OWNERS), "status": pick(seed("ucs", n), ["Active", "Pilot", "Conditional"]),
        "model_count": between(seed("ucm", n), 1, 3),
    })

    owners = expand_catalog([
        {"name": o, "role": "App Owner", "applications": [pick(seed("own", i), apps)["name"]], "models": between(seed("om", i), 1, 3), "prompts": between(seed("op", i), 2, 8)}
        for i, o in enumerate(BANKING_OWNERS[:8])
    ], 18, lambda n: {
        "name": pick(seed("own2", n), BANKING_OWNERS), "role": pick(seed("or", n), ["App Owner", "AI Governance", "Approver"]),
        "applications": [pick(seed("oa", n), apps)["name"]], "models": between(seed("om2", n), 1, 4), "prompts": between(seed("op2", n), 1, 12),
    })

    model_workflow = [
        {"step": 1, "stage": "Submitted", "actor": "App Owner", "date": "2026-04-15", "status": "Complete"},
        {"step": 2, "stage": "Security Review", "actor": "AppSec CoE", "date": "2026-04-18", "status": "Complete"},
        {"step": 3, "stage": "Model Risk Assessment", "actor": "Model Risk Board", "date": "2026-04-22", "status": "Complete"},
        {"step": 4, "stage": "Compliance Sign-off", "actor": "Compliance Head", "date": "2026-04-25", "status": "Conditional"},
        {"step": 5, "stage": "CIO Approval", "actor": "CIO", "date": "—", "status": "Pending"},
    ]
    prompt_workflow = [
        {"step": 1, "stage": "Draft", "actor": "App Owner", "status": "Complete"},
        {"step": 2, "stage": "AI CoE Review", "actor": "AI CoE", "status": "Complete"},
        {"step": 3, "stage": "Red-team Test", "actor": "Model Risk", "status": "In Progress"},
        {"step": 4, "stage": "Production Deploy", "actor": "DevOps", "status": "Pending"},
    ]

    pending_prompts = sum(1 for p in prompts if p["status"] != "Approved")
    approved_models = sum(1 for m in models if m["status"] == "Approved")

    return {
        "summary": {
            "models_total": len(models),
            "models_approved": approved_models,
            "prompts_total": len(prompts),
            "prompts_pending": pending_prompts,
            "use_cases": len(use_cases),
            "owners": len(owners),
        },
        "kpis": [
            {"label": "Models in Registry", "value": len(models), "tone": "primary", "drill": "models"},
            {"label": "Approved Models", "value": approved_models, "tone": "success", "drill": "models_approved"},
            {"label": "Prompt Templates", "value": len(prompts), "tone": "info", "drill": "prompts"},
            {"label": "Pending Approval", "value": pending_prompts, "tone": "warning", "drill": "prompts_pending"},
            {"label": "AI Use Cases", "value": len(use_cases), "tone": "teal", "drill": "use_cases"},
            {"label": "Registered Owners", "value": len(owners), "tone": "navy", "drill": "owners"},
        ],
        "models": models,
        "prompts": prompts,
        "prompt_version_history": version_history,
        "model_approval_workflow": model_workflow,
        "prompt_approval_workflow": prompt_workflow,
        "owners": owners,
        "use_cases": use_cases,
    }


def drill_posture(metric: str, item_id: str = "") -> dict[str, Any]:
    posture = build_ai_posture()
    if metric == "application":
        app = next((a for a in posture["applications"] if a["id"] == item_id or a["name"] == item_id), posture["applications"][0])
        return {
            "type": "application", "title": app["name"], "data": app,
            "related_prompts": [p for p in posture["prompt_audit"] if p["application_id"] == app["id"]],
            "link": "/mvp/ai-registry",
        }
    if metric == "inventory":
        return {"type": "list", "title": f"AI Application Inventory ({len(posture['applications'])})", "rows": posture["applications"]}
    if metric in ("hallucinations", "unsafe", "prompts"):
        key = "hallucinations" if metric == "hallucinations" else "unsafe_prompts" if metric == "unsafe" else "prompt_audit"
        rows = posture[key]
        if item_id:
            row = next((r for r in rows if r["prompt_id"] == item_id), rows[0] if rows else {})
            return {"type": "prompt", "title": row.get("prompt_id", "Prompt"), "data": row}
        return {"type": "list", "title": f"{metric.replace('_', ' ').title()} ({len(rows)})", "rows": rows}
    if metric == "policies":
        if item_id:
            pol = next((p for p in posture["policies"] if p["policy"] == item_id or p["policy"].startswith(item_id)), posture["policies"][0])
            return {"type": "list", "title": pol["policy"], "rows": pol.get("violation_records", [])}
        return {"type": "list", "title": f"AI Policy Compliance ({len(posture['policies'])})", "rows": posture["policies"]}
    if metric == "models":
        return {"type": "list", "title": f"Model Approval Status ({len(posture['model_approvals'])})", "rows": posture["model_approvals"]}
    if metric == "tokens":
        if item_id:
            if len(item_id) == 7 and "-" in item_id:  # YYYY-MM month
                events = [e for e in posture["token_usage"]["events"] if e["month_key"] == item_id]
                return {"type": "list", "title": f"Token events — {item_id} ({len(events)})", "rows": events}
            if len(item_id) == 10:  # YYYY-MM-DD day
                events = [e for e in posture["token_usage"]["events"] if e["date"] == item_id]
                return {"type": "list", "title": f"Token events — {item_id} ({len(events)})", "rows": events}
        return {"type": "tokens", "title": "Token Usage Analytics", "data": posture["token_usage"]}
    if metric == "compliance" or metric == "heatmap_cell":
        idx = posture.get("_heatmap_index", {})
        if item_id and item_id in idx:
            cell = idx[item_id]
            return {"type": "heatmap_cell", "title": f"{cell['application']} — {cell['dimension']}", "data": cell}
        return {"type": "heatmap", "title": "AI Risk Heatmap", "data": posture["risk_heatmap"]}
    if metric == "audit":
        return {"type": "list", "title": f"Audit Trail ({len(posture['audit_trail'])})", "rows": posture["audit_trail"]}
    return {"type": "summary", "title": "AI Governance Posture", "data": posture["summary"], "rows": posture["applications"]}


def drill_registry(section: str, item_id: str = "") -> dict[str, Any]:
    reg = build_ai_registry()
    mapping = {
        "models": ("models", "model_id", "Model"),
        "models_approved": ("models", "model_id", "Approved Model"),
        "prompts": ("prompts", "prompt_id", "Prompt"),
        "prompts_pending": ("prompts", "prompt_id", "Pending Prompt"),
        "use_cases": ("use_cases", "id", "Use Case"),
        "owners": ("owners", "name", "Owner"),
        "version_history": ("prompt_version_history", "prompt_id", "Prompt Version"),
    }
    if section in mapping:
        key, id_field, label = mapping[section]
        rows = reg[key]
        if section == "models_approved":
            rows = [r for r in rows if r["status"] == "Approved"]
        elif section == "prompts_pending":
            rows = [r for r in rows if r["status"] != "Approved"]
        if item_id:
            row = next((r for r in rows if str(r.get(id_field)) == item_id), rows[0] if rows else {})
            return {
                "type": section, "title": f"{label}: {row.get(id_field, item_id)}", "data": row,
                "workflow": reg["model_approval_workflow"] if "model" in section else reg["prompt_approval_workflow"],
            }
        return {"type": "list", "title": f"{label} Registry ({len(rows)})", "rows": rows}
    if section == "version_history":
        rows = reg["prompt_version_history"]
        if item_id:
            row = next((r for r in rows if r["prompt_id"] == item_id), rows[0])
            return {"type": "version", "title": f"Version: {row['prompt_id']}", "data": row}
        return {"type": "list", "title": f"Prompt Version History ({len(rows)})", "rows": rows}
    return {"type": "summary", "title": "AI Registry", "data": reg["summary"]}


def drill_sdlc(metric: str, release_id: str = "", stage_key: str = "", item_id: str = "") -> dict[str, Any]:
    gates = build_sdlc_gates(release_id)
    if metric == "gaps":
        rows = gates["all_gaps"]
        if item_id:
            row = next((r for r in rows if r["gap_id"] == item_id), rows[0] if rows else {})
            return {"type": "gap", "title": row.get("gap_id", "Gap"), "data": row}
        return {"type": "list", "title": f"Open SDLC Gaps ({len(rows)})", "rows": rows}
    if metric == "releases":
        return {"type": "list", "title": f"Active Releases ({len(gates['releases'])})", "rows": gates["releases"]}
    if metric == "frameworks":
        return {"type": "list", "title": f"Frameworks in Scope ({len(gates['frameworks'])})", "rows": [{"framework": f} for f in gates["frameworks"]]}
    if metric == "stages_complete":
        rows = [s for s in gates["stages"] if s["checklist_completion_pct"] >= 90]
        return {"type": "list", "title": f"Stages ≥90% Complete ({len(rows)})", "rows": rows}
    if metric == "readiness":
        return {"type": "list", "title": "Stage Readiness", "rows": gates["stages"]}
    if stage_key:
        detail = build_sdlc_stage_detail(stage_key, release_id)
        if metric == "framework" and item_id:
            row = next((r for r in detail["framework_rows"] if r["framework"] == item_id), detail["framework_rows"][0])
            return {"type": "framework", "title": f"{row['framework']} — {detail['release']['name']}", "data": row, "rows": row.get("gap_records", [])}
        if metric == "requirements":
            return {"type": "list", "title": f"Requirements ({len(detail.get('requirements', []))})", "rows": detail.get("requirements", [])}
        if metric == "observations":
            gl = detail.get("go_live", {})
            rows = gl.get("observation_records", [])
            return {"type": "list", "title": f"Open Observations ({len(rows)})", "rows": rows}
        return {"type": "stage", "title": detail["stage"]["label"], "data": detail["summary"], "rows": detail.get("requirements") or detail.get("designs") or detail.get("development") or detail.get("testing") or []}
    return {"type": "summary", "title": "SDLC Compliance Gates", "data": gates["summary"], "rows": gates["stages"]}
