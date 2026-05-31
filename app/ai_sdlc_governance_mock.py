"""AI & SDLC Governance — deterministic mock data for leadership demo.

Self-contained mock engine with enterprise-scale, traceable datasets per
ECS Enterprise Demo Quality Standard.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.ai_sdlc_document_artifacts import build_document_artifact
from app.ai_sdlc_knowledge_repository import (
    build_audit_observation_kb,
    build_control_knowledge_repository,
    build_cross_app_analytics,
    build_knowledge_graph,
    build_knowledge_reuse_scores,
    enrich_lifecycle_step_detail,
)
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
from app.ecs_demo_remediation import (
    build_ai_analytics_trends,
    build_registry_audit_trail,
    build_stage_card_drill,
    enrich_framework_drill,
)
from app.ecs_ai_governance_drilldowns import (
    AI_COMPLIANCE_FORMULA,
    POLICY_COMPLIANCE_FORMULA,
    build_ai_compliance_breakdown,
    build_ai_governance_knowledge_base,
    build_ecs_control_compliance,
    build_evidence_collection_analytics,
    build_policy_compliance_drill,
    enrich_registry_relationships,
)
from app.ecs_sdlc_stage_dashboard import STAGE_KEY_TO_SLUG, build_stage_dashboard, resolve_stage_key, sdlc_stage_path
from app.ecs_governance_drilldowns import (
    build_approvals_drill,
    build_control_coverage_drill,
    build_control_reuse_repository,
    build_code_reuse_repository,
    build_design_reuse_repository,
    build_evidence_coverage_drill,
    build_framework_coverage_drill,
    build_gaps_drill,
    build_historical_lineage,
    build_readiness_breakdown,
    build_status_explanation,
    build_status_timeline,
    build_test_pack_reuse_repository,
    coverage_formulas,
    enrich_audit_trail_full,
)
from app.ecs_governance_framework import (
    METRIC_TAB_MAP,
    build_control_360,
    build_navigation_context,
    build_reuse_modal_payload,
    build_stage_knowledge_base,
    build_stage_workspace_url,
    enrich_audit_trail_rows,
    enrich_framework_control_row,
    recalculate_framework_coverage,
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
    {
        "id": "REL-2026-Q2-NB", "name": "Net Banking Q2 Release", "application": "Net Banking",
        "impacted_applications": ["Net Banking", "Mobile Banking", "CRM", "Data Lake"],
        "owner": "R. Mehta", "target_date": "2026-06-15",
    },
    {
        "id": "REL-2026-Q2-MB", "name": "Mobile Banking 4.2", "application": "Mobile Banking",
        "impacted_applications": ["Mobile Banking", "Net Banking", "UPI Gateway", "Fraud Monitoring"],
        "owner": "A. Sharma", "target_date": "2026-06-22",
    },
    {
        "id": "REL-2026-Q2-PAY", "name": "Payments Switch Upgrade", "application": "Payments",
        "impacted_applications": ["Payments", "UPI Gateway", "Core Banking", "Cards"],
        "owner": "K. Reddy", "target_date": "2026-07-05",
    },
    {
        "id": "REL-2026-Q3-TF", "name": "Trade Finance OCR Rollout", "application": "Trade Finance",
        "impacted_applications": ["Trade Finance", "Core Banking", "CRM", "Wealth Management", "Data Lake"],
        "owner": "T. Kapoor", "target_date": "2026-08-12",
    },
    {
        "id": "REL-2026-Q3-UPI", "name": "UPI Gateway Hardening", "application": "UPI Gateway",
        "impacted_applications": ["UPI Gateway", "Payments", "Mobile Banking", "Fraud Monitoring"],
        "owner": "H. Singh", "target_date": "2026-09-01",
    },
]

_STAGE_OWNERS: dict[str, list[str]] = {
    "requirement": ["V. Desai", "S. Nair", "P. Nair", "R. Khanna", "Compliance Head", "Regulatory Affairs"],
    "design": ["T. Kapoor", "L. Menon", "Enterprise Architecture", "AppSec CoE Lead", "Solution Architect"],
    "development": ["DevOps Lead", "Infra Team", "J. Patel", "H. Singh", "Platform Engineering", "SRE Lead"],
    "testing": ["EY VAPT", "AppSec CoE", "Internal Audit", "Model Risk", "DBA Team", "QA Lead"],
    "go-live": ["Change Manager", "CIO Office", "Audit Committee Sec", "Release Manager", "S. Banerjee", "CAB Chair"],
}

_FW_PREFIX: dict[str, str] = {
    "PCI DSS": "PCI", "DPSC": "DPSC", "AppSec": "AS-C", "VAPT": "VAPT",
    "OS Baselining": "OS", "DB Baselining": "DBB", "Middleware Baselining": "MW",
    "Nginx Baselining": "NGX", "ITPP": "ITPP", "AI Governance": "AG",
}

_STAGE_GAP_TEXT: dict[str, list[str]] = {
    "requirement": [
        "Requirement traceability matrix incomplete for tier-1 control",
        "Regulatory expectation not mapped to PCI control family",
        "Business owner sign-off missing on AI consent requirement",
        "Audit requirement document version mismatch",
        "Similar-control reuse not validated against current scope",
    ],
    "design": [
        "Threat model not updated for new API surface",
        "Architecture review comment unresolved — data residency",
        "Security design pattern deviates from approved template",
        "Design approval workflow step skipped for middleware layer",
        "Historical observation reference not incorporated in design",
    ],
    "development": [
        "SAST quality gate bypassed on feature branch",
        "Secrets scanning alert not remediated before merge",
        "Secure coding checklist item marked complete without evidence",
        "Developer evidence repository link broken for AppSec control",
        "Coding standards exception not recorded in governance tool",
    ],
    "testing": [
        "VAPT re-test pending for critical finding closure",
        "Test execution result not linked to control objective",
        "Defect mapping incomplete for regression suite",
        "Compliance test case inventory gap for NPCI scope",
        "Evidence repository upload missing for penetration test",
    ],
    "go-live": [
        "Go-live checklist item pending CAB sign-off",
        "Risk assessment not refreshed within 30-day window",
        "Approval record missing for production cutover window",
        "Closure evidence stale — DR drill report >90 days",
        "Exception register entry expiring before release date",
    ],
}

_STAGE_CONTROL_DESC: dict[str, list[str]] = {
    "requirement": [
        "Document and approve business security requirements",
        "Map regulatory obligations to control objectives",
        "Maintain requirement-to-control traceability matrix",
        "Validate applicability across impacted applications",
        "Obtain business owner acknowledgement on scope",
    ],
    "design": [
        "Complete solution architecture security review",
        "Validate threat model against STRIDE categories",
        "Approve data-flow diagram for PII handling",
        "Confirm design patterns meet baselining standards",
        "Record architecture decision records (ADR) for deviations",
    ],
    "development": [
        "Enforce SAST/DAST gates in CI/CD pipeline",
        "Verify secrets scanning on every commit",
        "Complete secure coding training for release team",
        "Implement control-specific code annotations",
        "Upload developer evidence to governance repository",
    ],
    "testing": [
        "Execute VAPT scope per approved test strategy",
        "Run compliance validation test suite",
        "Map test cases to control objectives",
        "Track defect remediation to control closure",
        "Collect test execution evidence for auditor",
    ],
    "go-live": [
        "Complete go-live readiness checklist",
        "Obtain CAB approval for production deployment",
        "Validate rollback plan and runbook sign-off",
        "Confirm residual risk acceptance for open items",
        "Archive closure evidence pack for audit trail",
    ],
}

_STAGE_DOC_CATEGORIES: dict[str, list[str]] = {
    "requirement": [
        "Control objective", "Regulatory expectation", "Audit requirement document",
        "Generated checklist", "Similar controls from previous audits", "Reference implementations",
    ],
    "design": [
        "Design submission template", "Sample approved designs from historical observations",
        "Design review comments", "Design approval workflow",
    ],
    "development": [
        "Development implementation plan", "Coding standards", "Secure coding checklist",
        "Developer evidence repository",
    ],
    "testing": [
        "Test strategy", "Test case inventory", "Test execution results",
        "Defect mapping", "Evidence repository",
    ],
    "go-live": [
        "Go-live checklist", "Risk assessment", "Approval records", "Closure evidence",
    ],
}

_STAGE_DETAIL_CACHE: dict[tuple[str, str], dict[str, Any]] = {}
_STAGE_DETAIL_CACHE.clear()  # bust cache on governance framework upgrade


def _release_apps(release: dict) -> list[str]:
    return release.get("impacted_applications") or [release["application"]]


def _stage_owner(stage_key: str, s: int) -> str:
    return pick(s, _STAGE_OWNERS.get(stage_key, BANKING_OWNERS))


def _generate_control_records(stage_key: str, release: dict, framework: str, count: int) -> list[dict]:
    apps = _release_apps(release)
    prefix = _FW_PREFIX.get(framework, "CTRL")
    descs = _STAGE_CONTROL_DESC[stage_key]
    records = []
    for i in range(count):
        s = seed("ctrl", stage_key, release["id"], framework, i)
        status = pick(s >> 2, ["Covered", "Covered", "Partial", "Not Covered"])
        ev_count = between(s >> 4, 1, 5) if status != "Not Covered" else between(s >> 4, 0, 1)
        findings = 0 if status == "Covered" else between(s >> 6, 1, 3)
        exceptions = between(s >> 8, 0, 2) if status != "Covered" else 0
        records.append({
            "control_id": f"{prefix}-{between(s, 1, 99):02d}",
            "control_description": pick(s >> 10, descs),
            "application": pick(s >> 12, apps),
            "framework": framework,
            "owner": _stage_owner(stage_key, s >> 14),
            "status": status,
            "evidence_count": ev_count,
            "findings_count": findings,
            "exceptions_count": exceptions,
        })
    return [_enrich_control(r, release, stage_key, framework) for r in records]


def _generate_evidence_records(
    stage_key: str, release: dict, framework: str, controls: list[dict],
) -> list[dict]:
    records = []
    idx = 0
    for ctrl in controls:
        for e in range(ctrl["evidence_count"]):
            s = seed("evd", stage_key, release["id"], framework, ctrl["control_id"], e)
            status = pick(s, ["Approved", "Approved", "Pending", "Stale"])
            records.append({
                "evidence_id": f"EVD-{stage_key[:3].upper()}-{release['id'].split('-')[-1]}-{idx+1:04d}",
                "title": pick(s >> 2, [
                    f"{framework} control attestation — {ctrl['control_id']}",
                    f"Scan report — {ctrl['application']}",
                    f"Approval email — {framework}",
                    f"Screenshot — compliance dashboard",
                    f"Signed checklist — {stage_key} gate",
                ]),
                "application": ctrl["application"],
                "framework": framework,
                "control_id": ctrl["control_id"],
                "type": pick(s >> 4, ["Document", "Scan Report", "Approval", "Screenshot", "Log Export"]),
                "status": status,
                "collected_date": (ANCHOR - timedelta(days=between(s >> 6, 1, 120))).strftime("%Y-%m-%d"),
                "owner": ctrl["owner"],
                "file_format": pick(s >> 8, ["PDF", "XLSX", "PNG", "JSON", "DOCX"]),
                "size_kb": between(s >> 10, 48, 4200),
                "retention_years": 7,
                "auditor_visible": pick(s >> 12, [True, True, False]),
                "summary": f"Supporting evidence for {ctrl['control_description'][:60]}…",
                "source_system": pick(s >> 14, ["ECS Evidence Repo", "SharePoint", "Jira", "SonarQube", "ServiceNow"]),
            })
            idx += 1
    return records


def _generate_gap_records(stage_key: str, release: dict, framework: str, count: int) -> list[dict]:
    apps = _release_apps(release)
    texts = _STAGE_GAP_TEXT[stage_key]
    records = []
    for g in range(count):
        s = seed("gap", stage_key, release["id"], framework, g)
        prefix = _FW_PREFIX.get(framework, "CTRL")
        records.append({
            "gap_id": f"GAP-{release['id'].split('-')[-1]}-{stage_key[:3].upper()}-{framework[:3].upper()}-{g+1:03d}",
            "framework": framework,
            "control": f"{prefix}-{between(s, 1, 99):02d}",
            "description": pick(s >> 2, texts),
            "application": pick(s >> 4, apps),
            "owner": _stage_owner(stage_key, s >> 6),
            "due": release["target_date"],
            "severity": pick(s >> 8, ["High", "Medium", "Low"]),
            "stage": stage_key,
        })
    return records


def _generate_framework_rows(stage_key: str, release: dict) -> list[dict]:
    apps = _release_apps(release)
    rows = []
    for fw in SDLC_FRAMEWORKS:
        s = seed("fwrow", stage_key, release["id"], fw)
        ctrl_count = between(s, 14, 28)
        controls = _generate_control_records(stage_key, release, fw, ctrl_count)
        evidence = _generate_evidence_records(stage_key, release, fw, controls)
        gap_count = between(s >> 6, 5, 7)
        gaps = _generate_gap_records(stage_key, release, fw, gap_count)
        fw_apps = [apps[i % len(apps)] for i in range(between(s >> 8, 2, min(5, len(apps))))]
        fw_apps = list(dict.fromkeys([release["application"]] + fw_apps))[:5]
        covered = sum(1 for c in controls if c["status"] == "Covered")
        ev_collected = sum(1 for e in evidence if e["status"] == "Approved")
        history_rollup = _rollup_framework_history(controls)
        enriched_controls = [enrich_framework_control_row(c, release, fw, stage_key) for c in controls]
        rows.append({
            "framework": fw,
            "applications_impacted": fw_apps,
            "controls_total": len(controls),
            "controls_covered": covered,
            "control_records": enriched_controls,
            "history_rollup": history_rollup,
            "checklist_pct": round(covered / max(len(controls), 1) * 100, 1),
            "gaps": len(gaps),
            "gap_records": gaps,
            "evidence_collected": ev_collected,
            "evidence_total": len(evidence),
            "evidence_pct": round(ev_collected / max(len(evidence), 1) * 100, 1),
            "evidence_status": f"{ev_collected}/{len(evidence)}",
            "evidence_records": evidence,
            "owner": _stage_owner(stage_key, s >> 10),
            "due_date": release["target_date"],
            "risk": _risk_label(between(s >> 12, 20, 75)),
        })
    return rows


def _derive_stage_summary(stage_key: str, release: dict, fw_rows: list[dict], extra: dict | None = None) -> dict[str, Any]:
    extra = extra or {}
    all_controls = [c for r in fw_rows for c in r["control_records"]]
    all_evidence = [e for r in fw_rows for e in r["evidence_records"]]
    all_gaps = [g for r in fw_rows for g in r["gap_records"]]
    fw_coverage, ctrl_coverage, ev_coverage = recalculate_framework_coverage(fw_rows)
    ev_collected = sum(1 for e in all_evidence if e["status"] == "Approved")
    checklist_pct = extra.get("checklist_completion_pct", round(ev_collected / max(len(all_evidence), 1) * 100, 1))
    readiness = round((fw_coverage + ctrl_coverage + ev_coverage) / 3, 1)
    s = seed("sum", stage_key, release["id"])
    return {
        "applications_impacted": _release_apps(release),
        "framework_coverage_pct": fw_coverage,
        "control_coverage_pct": ctrl_coverage,
        "evidence_coverage_pct": ev_coverage,
        "checklist_completion_pct": checklist_pct,
        "open_gaps": len(all_gaps),
        "gap_records": all_gaps,
        "owner": release["owner"],
        "due_date": release["target_date"],
        "approval_status": pick(s, ["In Review", "Approved", "Pending Evidence", "Escalated"]),
        "evidence_collected": ev_collected,
        "evidence_total": len(all_evidence),
        "evidence_status": f"{ev_collected}/{len(all_evidence)} collected",
        "risk_rating": _risk_label(max(0, 100 - readiness)),
        "readiness_score": readiness,
        "stage_key": stage_key,
        "status": pick(s >> 2, ["On Track", "At Risk", "Approved", "In Review"]),
    }


_LIFECYCLE_STAGE_KEYS = [
    ("requirement", "Requirement"),
    ("design", "Design"),
    ("development", "Development"),
    ("testing", "Testing"),
    ("go-live", "Go-Live"),
    ("audit", "Audit"),
    ("closure", "Closure"),
]

_AUDIT_CYCLES = ["FY2023", "FY2024", "FY2025", "Q1-FY2026", "Q2-FY2026"]

_HISTORY_KEYS = (
    "previous_observations",
    "previously_approved_designs",
    "previously_accepted_evidence",
    "similar_controls",
    "historical_closure_comments",
)


def _other_banking_apps(release: dict, count: int = 8) -> list[str]:
    scope = set(_release_apps(release))
    pool = [a for a in BANKING_APPLICATIONS if a not in scope]
    return pool[:count] if pool else BANKING_APPLICATIONS[:count]


def _generate_control_lifecycle(control: dict, release: dict, stage_key: str) -> list[dict]:
    trace = []
    base_offset = between(seed("lcbase", control["control_id"], release["id"]), 95, 200)
    for i, (sk, label) in enumerate(_LIFECYCLE_STAGE_KEYS):
        s = seed("lc", control["control_id"], sk, release["id"])
        submitted = ANCHOR - timedelta(days=max(base_offset - i * 14, 7))
        approved = submitted + timedelta(days=between(s >> 2, 1, 10))
        if i <= 3:
            status = pick(s >> 4, ["Complete", "Approved", "Complete"])
        elif i == 4:
            status = pick(s >> 4, ["Complete", "In Progress", "Approved"])
        elif i == 5:
            status = pick(s >> 6, ["In Progress", "Complete", "Approved"])
        else:
            status = pick(s >> 6, ["Approved", "Pending", "In Progress"])
        ev_count = control["evidence_count"] if sk in ("audit", "closure") else between(s >> 8, 0, 2)
        trace.append({
            "stage": sk,
            "stage_label": label,
            "owner": _stage_owner(sk, s >> 10),
            "reviewer": pick(s >> 12, ["Internal Audit", "AppSec CoE", "Compliance Head", "CAB Chair", "Model Risk", "Enterprise Architecture"]),
            "status": status,
            "submission_date": submitted.strftime("%Y-%m-%d"),
            "approval_date": approved.strftime("%Y-%m-%d") if status in ("Complete", "Approved") else "—",
            "evidence_count": ev_count,
            "comments": pick(s >> 14, [
                "Scope validated against release impacted applications.",
                "Reviewer confirmed mapping to framework control family.",
                "Conditional approval — retest required before go-live.",
                "Evidence pack complete; forwarded to auditor workspace.",
                "Closure comment: residual risk accepted by CIO office.",
            ]),
            "application": control["application"],
        })
    return trace


def _generate_control_history(control: dict, release: dict, stage_key: str, framework: str) -> dict[str, list]:
    other_apps = _other_banking_apps(release, 10)
    cid = control["control_id"]
    obs, designs, evidence, similar, closures = [], [], [], [], []
    for i in range(between(seed("hobs", cid), 4, 7)):
        s = seed("hobs", cid, i)
        obs.append({
            "obs_id": f"H-OBS-{cid}-{i+1:02d}",
            "application": pick(s, other_apps),
            "audit_cycle": pick(s >> 2, _AUDIT_CYCLES),
            "summary": pick(s >> 4, [
                f"Prior audit: {framework} control gap — evidence stale",
                f"FY2024 observation: {control['control_description'][:50]}",
                "Repeat finding: incomplete lifecycle documentation",
                "Auditor note: reuse prior remediation pattern",
            ]),
            "severity": pick(s >> 6, ["High", "Medium", "Low"]),
            "raised_date": (ANCHOR - timedelta(days=between(s >> 8, 120, 900))).strftime("%Y-%m-%d"),
            "status": pick(s >> 10, ["Closed", "Accepted", "Open"]),
        })
    for i in range(between(seed("hdsg", cid), 3, 6)):
        s = seed("hdsg", cid, i)
        designs.append({
            "design_id": f"H-DSG-{cid}-{i+1:02d}",
            "application": pick(s, other_apps),
            "title": pick(s >> 2, [
                f"Approved {framework} reference architecture",
                "Historical zero-trust API design — reuse eligible",
                "Prior release security design — AppSec signed",
            ]),
            "approved_date": (ANCHOR - timedelta(days=between(s >> 4, 90, 800))).strftime("%Y-%m-%d"),
            "approver": pick(s >> 6, ["Enterprise Architecture", "AppSec CoE", "AI CoE"]),
            "framework": framework,
            "reuse_notes": "Approved for reuse where scope unchanged.",
        })
    for i in range(between(seed("hevd", cid), 4, 7)):
        s = seed("hevd", cid, i)
        evidence.append({
            "evidence_id": f"H-EVD-{cid}-{i+1:02d}",
            "application": pick(s, other_apps),
            "title": pick(s >> 2, [
                f"Accepted {framework} attestation — prior cycle",
                "VAPT closure report — accepted by auditor",
                "Signed compliance checklist — reuse approved",
            ]),
            "accepted_date": (ANCHOR - timedelta(days=between(s >> 4, 60, 750))).strftime("%Y-%m-%d"),
            "accepted_by": pick(s >> 6, ["Internal Audit", "KPMG — PCI Audit", "EY VAPT"]),
            "audit_cycle": pick(s >> 8, _AUDIT_CYCLES),
            "reuse_eligible": pick(s >> 10, [True, True, False]),
        })
    for i in range(between(seed("hsim", cid), 4, 7)):
        s = seed("hsim", cid, i)
        app = pick(s, other_apps)
        similar.append({
            "control_id": f"{_FW_PREFIX.get(framework, 'CTRL')}-{between(s >> 2, 1, 99):02d}",
            "application": app,
            "framework": framework,
            "description": control["control_description"],
            "status": pick(s >> 4, ["Covered", "Partial", "Covered"]),
            "last_validated": (ANCHOR - timedelta(days=between(s >> 6, 30, 400))).strftime("%Y-%m-%d"),
            "evidence_count": between(s >> 8, 1, 5),
        })
    for i in range(between(seed("hcls", cid), 3, 6)):
        s = seed("hcls", cid, i)
        closures.append({
            "comment_id": f"H-CLS-{cid}-{i+1:02d}",
            "audit_cycle": pick(s, _AUDIT_CYCLES),
            "application": pick(s >> 2, other_apps),
            "closed_by": pick(s >> 4, ["Internal Audit", "Compliance Head", "CAB Chair"]),
            "closed_date": (ANCHOR - timedelta(days=between(s >> 6, 45, 700))).strftime("%Y-%m-%d"),
            "comment": pick(s >> 8, [
                "Finding closed — evidence validated in ECS repository.",
                "Management response accepted; similar control deployed.",
                "Closure approved with 90-day monitoring period.",
            ]),
            "linked_control_id": cid,
        })
    return {
        "previous_observations": obs,
        "previously_approved_designs": designs,
        "previously_accepted_evidence": evidence,
        "similar_controls": similar,
        "historical_closure_comments": closures,
    }


def _enrich_control(control: dict, release: dict, stage_key: str, framework: str) -> dict:
    control["lifecycle_trace"] = _generate_control_lifecycle(control, release, stage_key)
    control["history"] = _generate_control_history(control, release, stage_key, framework)
    return control


def _rollup_framework_history(controls: list[dict]) -> dict[str, list]:
    rolled: dict[str, list] = {k: [] for k in _HISTORY_KEYS}
    for c in controls:
        hist = c.get("history", {})
        for k in _HISTORY_KEYS:
            rolled[k].extend(hist.get(k, []))
    return {k: v[:30] for k, v in rolled.items()}


def build_sdlc_executive(release_id: str = "", gates: dict[str, Any] | None = None) -> dict[str, Any]:
    release = next((r for r in RELEASES if r["id"] == release_id), RELEASES[0])
    if gates is None:
        stages = []
        release_total_gaps = 0
        for st in SDLC_STAGES:
            detail = build_sdlc_stage_detail(st["key"], release["id"])
            summary = detail["summary"]
            stages.append({**st, **summary, "release_id": release["id"]})
            release_total_gaps += summary["open_gaps"]
    else:
        stages = gates["stages"]
        release_total_gaps = gates["summary"]["total_gaps"]

    exec_apps = list(dict.fromkeys(_release_apps(release) + BANKING_APPLICATIONS))[:12]

    heatmap_rows = []
    gap_by_app: dict[str, dict] = {}
    fw_matrix_rows = []

    for app in exec_apps:
        cells = []
        total_gaps = 0
        high_gaps = 0
        stages_hit: set[str] = set()
        for st in SDLC_STAGES:
            detail = build_sdlc_stage_detail(st["key"], release["id"])
            app_gaps = [g for g in detail["summary"]["gap_records"] if g.get("application") == app]
            total_gaps += len(app_gaps)
            high_gaps += sum(1 for g in app_gaps if g.get("severity") == "High")
            if app_gaps:
                stages_hit.add(st["key"])
            readiness = round(max(35, detail["summary"]["readiness_score"] - len(app_gaps) * 2.5), 1)
            cells.append({
                "stage": st["key"],
                "stage_label": st["label"],
                "readiness_score": readiness,
                "gaps": len(app_gaps),
                "tone": "green" if readiness >= 85 else "amber" if readiness >= 70 else "red",
            })
        heatmap_rows.append({"application": app, "cells": cells})
        gap_by_app[app] = {
            "application": app,
            "total_gaps": total_gaps,
            "high_gaps": high_gaps,
            "stages_affected": len(stages_hit),
            "owner": pick(seed("gao", app), BANKING_OWNERS),
        }

    gap_ranking = sorted(gap_by_app.values(), key=lambda x: x["total_gaps"], reverse=True)

    for app in exec_apps:
        fw_cells = []
        for fw in SDLC_FRAMEWORKS:
            covered = total = 0
            for st in SDLC_STAGES:
                detail = build_sdlc_stage_detail(st["key"], release["id"])
                fw_row = next((r for r in detail["framework_rows"] if r["framework"] == fw), None)
                if not fw_row:
                    continue
                app_ctrls = [c for c in fw_row["control_records"] if c["application"] == app]
                total += len(app_ctrls)
                covered += sum(1 for c in app_ctrls if c["status"] == "Covered")
            pct = round(covered / max(total, 1) * 100, 1) if total else between(seed("fwapp", app, fw), 55, 92)
            fw_cells.append({
                "framework": fw,
                "compliance_pct": pct,
                "controls_covered": covered,
                "controls_total": total,
            })
        fw_matrix_rows.append({"application": app, "cells": fw_cells})

    stage_completion = [{
        "stage": st["key"],
        "label": st["label"],
        "completion_pct": st["checklist_completion_pct"],
        "readiness_score": st["readiness_score"],
        "open_gaps": st["open_gaps"],
        "evidence_collected": st.get("evidence_collected", 0),
        "evidence_total": st.get("evidence_total", 0),
    } for st in stages]

    go_live = build_sdlc_stage_detail("go-live", release["id"]).get("go_live", {})
    exceptions = go_live.get("exception_records", [])
    for exc in exceptions:
        exc["stage"] = "go-live"

    analytics = build_cross_app_analytics(release["id"])
    reuse = build_knowledge_reuse_scores(release["id"])

    return {
        "readiness_heatmap": {"dimensions": [st["label"] for st in SDLC_STAGES], "rows": heatmap_rows},
        "gap_applications": gap_ranking,
        "framework_by_application": {"frameworks": SDLC_FRAMEWORKS, "rows": fw_matrix_rows},
        "stage_completion": stage_completion,
        "exceptions_dashboard": exceptions,
        "cross_app_analytics": analytics,
        "knowledge_reuse": reuse,
        "widgets": [
            {"label": "Release Readiness Heatmap", "value": f"{len(exec_apps)} apps", "tone": "primary", "drill": "exec_readiness_heatmap", "hint": "Apps × stages"},
            {"label": "Highest SDLC Gaps", "value": gap_ranking[0]["total_gaps"] if gap_ranking else 0, "tone": "danger", "drill": "exec_gap_applications", "hint": "Top applications"},
            {"label": "Framework by Application", "value": len(SDLC_FRAMEWORKS), "tone": "info", "drill": "exec_framework_by_app", "hint": "Compliance matrix"},
            {"label": "Stage Completion", "value": f"{sum(1 for s in stage_completion if s['completion_pct'] >= 90)}/5", "tone": "success", "drill": "exec_stage_completion", "hint": "Pipeline status"},
            {"label": "Open Exceptions", "value": len(exceptions), "tone": "warning", "drill": "exec_exceptions", "hint": "Go-live register"},
        ],
        "analytics_widgets": [
            {"label": "Top Reused Controls", "value": analytics["top_reused_controls"][0]["control_id"] if analytics["top_reused_controls"] else "—", "tone": "teal", "drill": "exec_top_reused", "hint": "Enterprise reuse"},
            {"label": "Top Failed Controls", "value": analytics["top_failed_controls"][0]["control_id"] if analytics["top_failed_controls"] else "—", "tone": "danger", "drill": "exec_top_failed", "hint": "Repeat failures"},
            {"label": "Common Audit Findings", "value": len(analytics["common_findings"]), "tone": "warning", "drill": "exec_common_findings", "hint": "Cross-app patterns"},
            {"label": "Highest Control Reuse", "value": analytics["highest_reuse_apps"][0]["application"] if analytics["highest_reuse_apps"] else "—", "tone": "success", "drill": "exec_reuse_by_app", "hint": "Leading apps"},
            {"label": "Highest Exceptions", "value": analytics["highest_exception_apps"][0]["application"] if analytics["highest_exception_apps"] else "—", "tone": "danger", "drill": "exec_exceptions_by_app", "hint": "Exception hotspots"},
            {"label": "Governance Maturity", "value": f"{analytics['highest_maturity_apps'][0]['maturity_score']}%" if analytics["highest_maturity_apps"] else "—", "tone": "navy", "drill": "exec_governance_maturity", "hint": "Maturity leaders"},
        ],
        "summary": {
            "applications_tracked": len(exec_apps),
            "total_exceptions": len(exceptions),
            "total_gaps": release_total_gaps,
        },
    }


def _control_drill_payload(row: dict, release: dict | None = None, stage_key: str = "") -> dict[str, Any]:
    rel = release or RELEASES[0]
    sk = stage_key or "requirement"
    fw = row.get("framework", "AppSec")
    history = row.get("history", {})
    return {
        "lifecycle_trace": row.get("lifecycle_trace", []),
        "history": history,
        "knowledge_repository": build_control_knowledge_repository(row, rel, sk, fw),
        "audit_knowledge": build_audit_observation_kb(row, history, fw),
        "knowledge_graph": build_knowledge_graph(row, rel, fw, sk),
        "control_360": build_control_360(row, rel, sk, fw),
    }


def _framework_history_payload(row: dict) -> dict[str, Any]:
    return {"history": row.get("history_rollup", _rollup_framework_history(row.get("control_records", [])))}

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

    analytics = build_ai_analytics_trends()
    monthly_trend = analytics["monthly_trends"]
    for pt in monthly_trend:
        mk = pt["month_key"]
        pt["value"] = pt["tokens"]
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
                {"id": f"POL-V-{i+1:03d}-{v+1:02d}",
                 "application": (vapp := pick(seed("pv", i, v), apps))["name"],
                 "application_id": vapp["id"],
                 "detail": pick(seed("pvd", i, v), [
                     f"Unredacted PII in prompt log — {vapp['name']}",
                     f"Unapproved model invocation detected — {vapp['application']}",
                     f"Missing human review for credit-adjacent output — {vapp['name']}",
                     f"Prompt deployed without versioning — {vapp['application']}",
                     f"Hallucination threshold exceeded in customer-facing response",
                 ]),
                 "status": pick(seed("pvs", i, v), ["Open", "Remediated", "Accepted"])}
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

    posture_payload = {
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
        "applications": apps,
        "risk_heatmap": {"dimensions": heatmap["dimensions"], "rows": heatmap["rows"]},
        "_heatmap_index": heatmap["cells_index"],
        "prompt_audit": all_prompts,
        "hallucinations": hallucinations,
        "unsafe_prompts": unsafe,
        "token_usage": {
            "by_application": analytics["by_application"] or token_by_app,
            "by_team": list(token_by_team.values()),
            "daily_trend": [
                {"day": (ANCHOR - timedelta(days=6 - i)).strftime("%d %b"), "day_key": (ANCHOR - timedelta(days=6 - i)).strftime("%Y-%m-%d"),
                 "tokens": max(sum(e["tokens"] for e in token_events if e["date"] == (ANCHOR - timedelta(days=6 - i)).strftime("%Y-%m-%d")), between(seed("dtk", i), 420_000, 1_850_000)),
                 "events": [e for e in token_events if e["date"] == (ANCHOR - timedelta(days=6 - i)).strftime("%Y-%m-%d")]}
                for i in range(7)
            ],
            "monthly_trend": monthly_trend,
            "events": token_events,
            "analytics": analytics,
        },
        "policies": policies,
        "model_approvals": model_approvals,
        "audit_trail": audit_trail,
    }
    compliance_breakdown = build_ai_compliance_breakdown(posture_payload)
    posture_payload["summary"]["avg_compliance_score"] = compliance_breakdown["current_score"]
    posture_payload["compliance_breakdown"] = compliance_breakdown
    posture_payload["policy_compliance_explainer"] = build_policy_compliance_drill(posture_payload)
    posture_payload["summary"]["avg_policy_compliance"] = posture_payload["policy_compliance_explainer"]["aggregate_pct"]
    posture_payload["coverage_formulas"] = {
        **coverage_formulas(),
        "ai_compliance": AI_COMPLIANCE_FORMULA,
        "policy_compliance": POLICY_COMPLIANCE_FORMULA,
    }
    posture_payload["kpis"] = [
        {"label": "AI Applications", "value": len(apps), "hint": "Production AI assistants", "tone": "primary", "drill": "inventory"},
        {"label": "AI Compliance Score", "value": f"{compliance_breakdown['current_score']}%", "hint": "Weighted governance dimensions", "tone": "success", "drill": "compliance"},
        {"label": "Policy Compliance", "value": f"{posture_payload['policy_compliance_explainer']['aggregate_pct']}%", "hint": f"{len(policies)} AI policies tracked", "tone": "info", "drill": "policies"},
        {"label": "Hallucination Alerts", "value": len(hallucinations), "hint": "Flagged in audit sample", "tone": "warning", "drill": "hallucinations"},
        {"label": "Unsafe Blocked", "value": len(unsafe), "hint": "Auto-quarantined", "tone": "danger", "drill": "unsafe"},
        {"label": "Tokens MTD", "value": f"{total_tokens/1_000_000:.1f}M", "hint": f"${round(total_tokens/1000*0.012,0):,.0f} estimated", "tone": "teal", "drill": "tokens"},
        {"label": "Models Approved", "value": f"{approved_models}/{len(apps)}", "hint": "Production clearance", "tone": "success", "drill": "models"},
        {"label": "Prompts Audited", "value": len(all_prompts), "hint": "Full audit log", "tone": "navy", "drill": "prompts"},
    ]
    posture_payload["knowledge_base"] = build_ai_governance_knowledge_base(posture_payload)
    posture_payload["control_compliance"] = build_ecs_control_compliance()
    posture_payload["evidence_collection_analytics"] = build_evidence_collection_analytics()
    return posture_payload


def build_sdlc_gates(release_id: str = "") -> dict[str, Any]:
    release = next((r for r in RELEASES if r["id"] == release_id), RELEASES[0]) if release_id else RELEASES[0]
    stages = []
    all_gaps = []
    for st in SDLC_STAGES:
        detail = build_sdlc_stage_detail(st["key"], release["id"])
        summary = detail["summary"]
        stages.append({
            **st,
            **summary,
            "release_id": release["id"],
            "slug": STAGE_KEY_TO_SLUG.get(st["key"], st["key"]),
            "path": sdlc_stage_path(st["key"]),
        })
        all_gaps.extend(summary.get("gap_records", []))

    overall = round(sum(s["readiness_score"] for s in stages) / len(stages), 1)
    total_gaps = len(all_gaps)

    gates_payload = {
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
            "applications_impacted": _release_apps(release),
        },
        "kpis": [
            {"label": "Overall Readiness", "value": f"{overall}%", "tone": "success" if overall >= 80 else "warning", "drill": "readiness"},
            {"label": "Active Releases", "value": len(RELEASES), "tone": "primary", "drill": "releases"},
            {"label": "Frameworks in Scope", "value": len(SDLC_FRAMEWORKS), "tone": "info", "drill": "frameworks"},
            {"label": "Open Gaps (All Stages)", "value": total_gaps, "tone": "danger", "drill": "gaps"},
            {"label": "Stages Complete", "value": sum(1 for s in stages if s["checklist_completion_pct"] >= 90), "tone": "teal", "drill": "stages_complete"},
        ],
    }
    gates_payload["executive"] = build_sdlc_executive(release["id"], gates_payload)
    reuse = gates_payload["executive"]["knowledge_reuse"]
    gates_payload["knowledge_reuse"] = reuse
    gates_payload["kpis"].append({
        "label": "Knowledge Reuse %",
        "value": f"{reuse['overall_pct']}%",
        "tone": "success" if reuse["overall_pct"] >= 75 else "warning",
        "drill": "knowledge_reuse",
    })
    gates_payload["coverage_formulas"] = coverage_formulas()
    return gates_payload


def _stage_requirements(release: dict, stage_key: str = "requirement", count: int = 24) -> list[dict]:
    apps = _release_apps(release)
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
        "NPCI UPI mandate compliance for merchant onboarding",
        "RBI cyber security framework mapping for digital channels",
    ]
    rows = []
    for i in range(count):
        s = seed("req", release["id"], stage_key, i)
        ctrl_n = between(s >> 6, 2, 6)
        app = pick(s >> 10, apps)
        controls = _generate_control_records(stage_key, release, pick(s >> 2, SDLC_FRAMEWORKS), ctrl_n)
        rows.append({
            "req_id": f"REQ-{release['id'].split('-')[-1]}-{101+i}",
            "title": titles[i % len(titles)],
            "interpretation": f"Maps to {pick(s>>2, SDLC_FRAMEWORKS)}, {pick(s>>4, SDLC_FRAMEWORKS)}",
            "controls_generated": len(controls),
            "control_records": controls,
            "owner_ack": pick(s >> 8, ["Acknowledged", "Pending", "Acknowledged"]),
            "application": app,
            "applicability": app,
            "owner": _stage_owner(stage_key, s >> 12),
            "status": pick(s >> 14, ["Approved", "In Review", "Approved"]),
        })
    return rows


def _stage_designs(release: dict, stage_key: str = "design", count: int = 22) -> list[dict]:
    apps = _release_apps(release)
    design_types = [
        "Zero-trust API gateway architecture", "RAG data-flow security design",
        "HSM integration for card token vault", "Micro-segmentation for payment switch",
        "AI inference pipeline threat model", "Multi-region DR topology",
        "OAuth2/OIDC federation design", "Event-driven audit log pipeline",
    ]
    rows = []
    for i in range(count):
        s = seed("dsg", release["id"], stage_key, i)
        app = pick(s >> 16, apps)
        rows.append({
            "design_id": f"DSG-{release['id'].split('-')[-1]}-{14+i:03d}",
            "title": f"{app} — {design_types[i % len(design_types)]}",
            "application": app,
            "architecture_review": pick(s >> 2, ["Approved", "Pending", "Approved"]),
            "security_review": pick(s >> 4, ["Approved", "Pending", "Conditional"]),
            "compliance_review": pick(s >> 6, ["Approved", "Conditional", "Pending"]),
            "reviewer": pick(s >> 8, ["Enterprise Architecture", "AppSec CoE", "A. Sharma", "AI CoE"]),
            "submitted": (ANCHOR - timedelta(days=between(s >> 10, 1, 45))).strftime("%Y-%m-%d"),
            "status": pick(s >> 12, ["Approved", "In Review", "Pending Security"]),
            "owner": _stage_owner(stage_key, s >> 14),
        })
    return rows


def _stage_development(release: dict, stage_key: str = "development", count: int = 24) -> list[dict]:
    apps = _release_apps(release)
    items = [
        ("Implement parameterized queries for all JDBC access", "AppSec AS-C-03"),
        ("Integrate SonarQube SAST gate — block on Critical", "AppSec AS-C-05"),
        ("Enable GitLeaks secrets scanning in CI pipeline", "AppSec AS-C-07"),
        ("Deploy LLM prompt injection filter middleware", "AI Governance AG-08"),
        ("Apply CIS Level 2 hardening to RHEL app servers", "OS Baselining OS-11"),
        ("Verify Oracle TDE encryption on customer schema", "DB Baselining DBB-03"),
        ("Configure Nginx TLS 1.3 with approved cipher suites", "Nginx Baselining NGX-02"),
        ("Patch WebLogic to approved middleware baseline", "Middleware Baselining MW-07"),
        ("Implement PCI DSS log retention for card data path", "PCI DSS PCI-10"),
        ("Configure DPSC data classification tags in pipeline", "DPSC DPSC-04"),
        ("Automate VAPT scan trigger on release candidate build", "VAPT VAPT-02"),
        ("Enable ITPP change record linkage in deployment job", "ITPP ITPP-06"),
    ]
    rows = []
    for i in range(count):
        s = seed("dev", release["id"], stage_key, i)
        item, ctrl = items[i % len(items)]
        pct = between(s >> 2, 55, 100)
        app = pick(s >> 18, apps)
        rows.append({
            "item_id": f"DEV-{release['id'].split('-')[-1]}-{i+1:03d}",
            "item": item,
            "progress_pct": pct,
            "control_id": ctrl,
            "control": ctrl,
            "application": app,
            "owner": _stage_owner(stage_key, s >> 4),
            "status": "Complete" if pct >= 95 else "In Progress" if pct >= 70 else "At Risk",
        })
    return rows


def _stage_testing(release: dict, stage_key: str = "testing", count: int = 28) -> list[dict]:
    apps = _release_apps(release)
    test_names = [
        "OWASP ZAP dynamic scan — authenticated session", "PCI ASV external vulnerability scan",
        "Prompt injection red-team exercise", "NPCI UPI compliance regression suite",
        "DR failover simulation — tier-1 payment path", "Load test — 10K TPS UPI peak",
        "SAST false-positive validation review", "API fuzzing — OAuth token endpoints",
        "Database encryption verification audit", "Middleware patch compliance scan",
    ]
    types = ["VAPT", "AppSec", "Compliance", "AI Governance", "DB Baselining", "Regression"]
    rows = []
    for i in range(count):
        s = seed("tst", release["id"], stage_key, i)
        ttype = types[i % len(types)]
        defects = between(s >> 2, 0, 4)
        app = pick(s >> 20, apps)
        status = "Passed" if defects == 0 and i % 5 != 0 else pick(s >> 4, ["Passed", "Failed", "In Progress", "Pending"])
        rows.append({
            "test_id": f"TC-{release['id'].split('-')[-1]}-{400+i}",
            "name": f"{test_names[i % len(test_names)]} — {app}",
            "application": app,
            "type": ttype,
            "status": status,
            "defects": defects,
            "owner": _stage_owner(stage_key, s >> 6),
            "due": (ANCHOR + timedelta(days=between(s >> 8, 1, 30))).strftime("%Y-%m-%d"),
            "defect_records": [
                {"defect_id": f"DEF-{release['id'].split('-')[-1]}-{400+i}-{d+1}",
                 "application": app,
                 "severity": pick(seed("def", stage_key, i, d), ["Critical", "High", "Medium"]),
                 "summary": pick(seed("defs", stage_key, i, d), [
                     "SQL injection in merchant API parameter", "Missing MFA on batch admin endpoint",
                     "TLS 1.2 cipher fallback enabled", "Prompt injection via URL-encoded payload",
                     "Session fixation on mobile login flow",
                 ])}
                for d in range(defects)
            ],
        })
    return rows


def _stage_local_readiness_score(summary: dict) -> float:
    return round(
        (summary.get("framework_coverage_pct", 0)
         + summary.get("control_coverage_pct", 0)
         + summary.get("evidence_coverage_pct", summary.get("checklist_completion_pct", 0))) / 3,
        1,
    )


def _release_stage_readiness_scores(
    release_id: str, current_stage_key: str, current_summary: dict,
) -> list[dict[str, Any]]:
    """Per-stage governance scores used for release readiness average."""
    scores: list[dict[str, Any]] = []
    for st in SDLC_STAGES[:5]:
        if st["key"] == current_stage_key:
            score = _stage_local_readiness_score(current_summary)
        else:
            ck = (release_id, st["key"])
            cached = _STAGE_DETAIL_CACHE.get(ck)
            if cached:
                score = _stage_local_readiness_score(cached["summary"])
            else:
                release = next((r for r in RELEASES if r["id"] == release_id), RELEASES[0])
                fw_rows = _generate_framework_rows(st["key"], release)
                sm = _derive_stage_summary(st["key"], release, fw_rows)
                score = _stage_local_readiness_score(sm)
        scores.append({"key": st["key"], "label": st["label"], "readiness_score": score})
    return scores


def _stage_documents(stage_key: str, release: dict) -> list[dict]:
    apps = _release_apps(release)
    categories = _STAGE_DOC_CATEGORIES[stage_key]
    doc_type_map = {
        "requirement": "Requirement Document",
        "design": "Design Document",
        "development": "Development Plan",
        "testing": "Test Plan",
        "go-live": "Release Readiness Pack",
    }
    previews = {
        "Control objective": "This document defines the control objectives for {app} aligned to {fw} requirements, including measurable success criteria and owner accountability.",
        "Regulatory expectation": "Regulatory mapping for {app}: RBI Master Direction on IT Governance, NPCI circular references, and PCI DSS v4.0 applicability matrix for the release scope.",
        "Audit requirement document": "Internal audit requirement checklist derived from FY2025 observations. Each line item maps to evidence type, collection frequency, and responsible owner.",
        "Generated checklist": "Auto-generated SDLC gate checklist with {n} items. Completion status synced from ECS governance module every 4 hours.",
        "Similar controls from previous audits": "Cross-reference of controls validated in Net Banking Q4 2025 audit. Reuse approved where scope unchanged; delta analysis for new features.",
        "Reference implementations": "Approved reference architecture patterns from Enterprise Architecture repository. Includes sample configs for Nginx, middleware, and API gateway.",
        "Design submission template": "Standard template v3.2 for solution design submissions. Mandatory sections: context diagram, data classification, threat model summary.",
        "Sample approved designs from historical observations": "Archive of three designs approved under OBS-2025-014 remediation. Annotated with auditor comments and closure evidence links.",
        "Design review comments": "Consolidated review thread from AppSec CoE and Enterprise Architecture. 12 open comments, 28 resolved.",
        "Design approval workflow": "Workflow definition: Submit → Architecture Review → Security Review → Compliance → CIO sign-off. SLA: 5 business days per stage.",
        "Development implementation plan": "Sprint-level implementation plan covering 6 sprints. Secure coding milestones, CI/CD gate criteria, and evidence upload schedule.",
        "Coding standards": "Bank coding standards v2026.1 — Java, Python, TypeScript. Includes AI/LLM-specific secure coding addendum.",
        "Secure coding checklist": "Developer self-assessment checklist (42 items). Must be completed before merge to release branch.",
        "Developer evidence repository": "Index of developer-uploaded evidence: SAST reports, unit test coverage, secrets scan results, code review approvals.",
        "Test strategy": "Risk-based test strategy covering functional, security, compliance, and performance dimensions. VAPT scope aligned to OWASP ASVS Level 2.",
        "Test case inventory": "Inventory of 847 test cases mapped to control objectives. 92% automated, 8% manual compliance validation.",
        "Test execution results": "Latest execution run: 812 passed, 23 failed, 12 blocked. Linked to Jira defects and control remediation tracker.",
        "Defect mapping": "Defect-to-control mapping matrix. Each open defect linked to impacted control, severity, and target remediation date.",
        "Evidence repository": "Centralized test evidence: scan reports, execution logs, sign-off emails, screenshots. Retention: 7 years.",
        "Go-live checklist": "Production readiness checklist — 19 items across infrastructure, security, compliance, and operations.",
        "Risk assessment": "Residual risk register for release. 3 High items with CIO acceptance required; 8 Medium with compensating controls documented.",
        "Approval records": "CAB approval #CAB-2026-042, Audit Committee conditional sign-off, Change Manager production window confirmation.",
        "Closure evidence": "Final evidence pack for auditor: VAPT closure report, DR drill attestation, AI model approval letter, ops runbook sign-off.",
    }
    docs = []
    for i, cat in enumerate(categories):
        for j in range(4):
            s = seed("doc", stage_key, release["id"], cat, j)
            app = pick(s, apps)
            fw = pick(s >> 2, SDLC_FRAMEWORKS)
            n = between(s >> 4, 18, 42)
            tmpl = previews.get(cat, f"{cat} documentation for {release['name']}.")
            content = tmpl.format(app=app, fw=fw, n=n)
            artifact = build_document_artifact(stage_key, cat, release, app, fw, s)
            docs.append({
                "doc_id": f"DOC-{stage_key[:3].upper()}-{release['id'].split('-')[-1]}-{i+1:02d}-{j+1}",
                "title": f"{release['name']} — {cat}" + (f" (vol {j+1})" if j else ""),
                "category": cat,
                "doc_type": doc_type_map[stage_key],
                "application": app,
                "version": f"{between(s>>6,1,3)}.{between(s>>8,0,9)}",
                "status": pick(s >> 10, ["Approved", "In Review", "Draft"]),
                "owner": _stage_owner(stage_key, s >> 12),
                "submitted": (ANCHOR - timedelta(days=between(s >> 14, 1, 60))).strftime("%Y-%m-%d"),
                "pages": between(s >> 16, 8, 64),
                "content_preview": content,
                "linked_controls": len(artifact.get("sections", [{}])) + between(s >> 18, 2, 8),
                "linked_evidence": len(artifact.get("required_evidence", [])),
                "artifact": artifact,
                "stage_key": stage_key,
            })
    return docs


def build_sdlc_stage_detail(stage_key: str, release_id: str = "") -> dict[str, Any]:
    cache_key = (release_id or RELEASES[0]["id"], stage_key)
    if cache_key in _STAGE_DETAIL_CACHE:
        return _STAGE_DETAIL_CACHE[cache_key]

    release = next((r for r in RELEASES if r["id"] == release_id), RELEASES[0])
    stage_meta = next((s for s in SDLC_STAGES if s["key"] == stage_key), SDLC_STAGES[0])
    stage_meta = {
        **stage_meta,
        "slug": STAGE_KEY_TO_SLUG.get(stage_key, stage_key),
        "path": sdlc_stage_path(stage_key),
    }
    fw_rows = _generate_framework_rows(stage_key, release)
    documents = _stage_documents(stage_key, release)

    extra_summary: dict[str, Any] = {}
    detail: dict[str, Any] = {
        "stage": stage_meta,
        "release": release,
        "framework_rows": fw_rows,
        "documents": documents,
        "audit_trail": generate_audit_trail(
            55, ANCHOR, years_back=5,
            detail_builder=lambda i, action, _actor: (
                f"{release['name']} — {stage_meta['label']} — "
                f"{pick(seed('aud', stage_key, i), _release_apps(release))} — {action}"
            ),
        ),
    }

    if stage_key == "requirement":
        detail["requirements"] = _stage_requirements(release, stage_key)
    elif stage_key == "design":
        detail["designs"] = _stage_designs(release, stage_key)
    elif stage_key == "development":
        detail["development"] = _stage_development(release, stage_key)
    elif stage_key == "testing":
        detail["testing"] = _stage_testing(release, stage_key)
    elif stage_key == "go-live":
        obs_count = between(seed(release["id"], stage_key, "obs"), 10, 16)
        exc_count = between(seed(release["id"], stage_key, "exc"), 3, 9)
        checklist_items = [
            {"item_id": f"GL-{release['id'].split('-')[-1]}-001", "item": "All critical VAPT findings closed or accepted", "application": release["application"], "status": "Complete", "owner": "AppSec CoE"},
            {"item_id": f"GL-{release['id'].split('-')[-1]}-002", "item": "Evidence pack submitted to external auditor", "application": release["application"], "status": "In Progress", "owner": release["owner"]},
            {"item_id": f"GL-{release['id'].split('-')[-1]}-003", "item": "AI Governance model approval current", "application": pick(seed("gl", 0), _release_apps(release)), "status": "Complete", "owner": "Model Risk"},
            {"item_id": f"GL-{release['id'].split('-')[-1]}-004", "item": "DR drill evidence within 90-day window", "application": pick(seed("gl", 1), _release_apps(release)), "status": "Complete", "owner": "ITPP Owner"},
            {"item_id": f"GL-{release['id'].split('-')[-1]}-005", "item": "CAB emergency change window confirmed", "application": release["application"], "status": "Pending", "owner": "Change Manager"},
            {"item_id": f"GL-{release['id'].split('-')[-1]}-006", "item": "Production rollback runbook signed off", "application": release["application"], "status": "Complete", "owner": "Release Manager"},
            {"item_id": f"GL-{release['id'].split('-')[-1]}-007", "item": "Monitoring dashboards configured for new endpoints", "application": pick(seed("gl", 2), _release_apps(release)), "status": "Complete", "owner": "SRE Lead"},
            {"item_id": f"GL-{release['id'].split('-')[-1]}-008", "item": "NPCI certification letter on file", "application": "UPI Gateway" if "UPI" in _release_apps(release) else release["application"], "status": "In Progress", "owner": "Compliance Head"},
            {"item_id": f"GL-{release['id'].split('-')[-1]}-009", "item": "Ops handover completed with L1/L2 runbooks", "application": release["application"], "status": "Complete", "owner": "Platform Engineering"},
            {"item_id": f"GL-{release['id'].split('-')[-1]}-010", "item": "Penetration test closure letter received", "application": pick(seed("gl", 3), _release_apps(release)), "status": "Pending", "owner": "EY VAPT"},
            {"item_id": f"GL-{release['id'].split('-')[-1]}-011", "item": "Database migration scripts validated in staging", "application": pick(seed("gl", 4), _release_apps(release)), "status": "Complete", "owner": "DBA Team"},
            {"item_id": f"GL-{release['id'].split('-')[-1]}-012", "item": "Customer communication plan approved", "application": release["application"], "status": "Complete", "owner": "Retail Digital"},
            {"item_id": f"GL-{release['id'].split('-')[-1]}-013", "item": "Fraud monitoring rules updated for new flows", "application": "Fraud Monitoring" if "Fraud Monitoring" in _release_apps(release) else release["application"], "status": "In Progress", "owner": "Fraud Ops"},
            {"item_id": f"GL-{release['id'].split('-')[-1]}-014", "item": "License and certificate expiry check passed", "application": release["application"], "status": "Complete", "owner": "Infra Team"},
            {"item_id": f"GL-{release['id'].split('-')[-1]}-015", "item": "CIO residual risk acceptance documented", "application": release["application"], "status": "Pending", "owner": "CIO Office"},
        ]
        complete = sum(1 for c in checklist_items if c["status"] == "Complete")
        extra_summary["checklist_completion_pct"] = round(complete / len(checklist_items) * 100, 1)
        detail["go_live"] = {
            "open_observations": obs_count,
            "exceptions_pending": exc_count,
            "residual_risk_acceptance": "CIO sign-off required for High residual risk items",
            "final_approval": pick(seed(release["id"], stage_key, "fin"), ["Pending Audit Committee", "Approved", "Conditional"]),
            "observation_records": [
                {"obs_id": f"OBS-{release['id'].split('-')[-1]}-GL-{o+1:03d}",
                 "application": pick(seed("obapp", stage_key, o), _release_apps(release)),
                 "framework": pick(seed("obf", stage_key, o), SDLC_FRAMEWORKS),
                 "summary": pick(seed("obs", stage_key, o), _STAGE_GAP_TEXT["go-live"]),
                 "severity": pick(seed("obse", stage_key, o), ["High", "Medium", "Low"]),
                 "owner": _stage_owner(stage_key, seed("obo", stage_key, o))}
                for o in range(obs_count)
            ],
            "exception_records": [
                {"exception_id": f"EXC-{release['id'].split('-')[-1]}-GL-{x+1:03d}",
                 "application": pick(seed("exapp", stage_key, x), _release_apps(release)),
                 "framework": pick(seed("exfw", stage_key, x), SDLC_FRAMEWORKS),
                 "summary": pick(seed("exs", stage_key, x), [
                     "Temporary WAF rule exception for legacy API", "Extended DR RTO acceptance",
                     "AI model conditional approval — monitoring period", "Middleware patch deferral — vendor dependency",
                 ]),
                 "expiry": (ANCHOR + timedelta(days=between(seed("exd", stage_key, x), 14, 90))).strftime("%Y-%m-%d"),
                 "owner": _stage_owner(stage_key, seed("exo", stage_key, x)),
                 "status": pick(seed("exst", stage_key, x), ["Pending Approval", "Approved", "Expiring Soon"])}
                for x in range(exc_count)
            ],
            "checklist": checklist_items,
        }

    summary = _derive_stage_summary(stage_key, release, fw_rows, extra_summary)
    stage_score_rows = _release_stage_readiness_scores(release["id"], stage_key, summary)
    release_readiness = round(
        sum(r["readiness_score"] for r in stage_score_rows) / max(len(stage_score_rows), 1), 1,
    )
    summary["readiness_score"] = release_readiness
    summary["target_readiness"] = 90.0
    summary["readiness_gap"] = round(max(90.0 - release_readiness, 0), 1)
    if stage_key == "go-live":
        detail["go_live"]["readiness_score"] = release_readiness
    detail["summary"] = summary
    detail["coverage_formulas"] = coverage_formulas()
    detail["readiness_breakdown"] = build_readiness_breakdown(
        stage_key, detail, release, gates_stages=stage_score_rows,
    )
    detail["framework_coverage_explainer"] = build_framework_coverage_drill(detail, release)
    detail["control_coverage_explainer"] = build_control_coverage_drill(detail)
    detail["evidence_coverage_explainer"] = build_evidence_coverage_drill(detail)
    detail["status_workspace"] = {
        **build_status_timeline(stage_key, detail, release),
        "explanation": build_status_explanation(summary["status"], summary),
        "current_status": summary["status"],
        "approval_status": summary["approval_status"],
    }
    detail["approvals_workspace"] = build_approvals_drill(stage_key, release)
    detail["knowledge_reuse"] = build_knowledge_reuse_scores(release["id"])
    detail["knowledge_base"] = build_stage_knowledge_base(stage_key, release, detail)
    detail["audit_trail"] = enrich_audit_trail_full(
        enrich_audit_trail_rows(detail["audit_trail"], stage_key, release), stage_key
    )
    detail["stage_dashboard"] = build_stage_dashboard(stage_key, detail, release)

    _STAGE_DETAIL_CACHE[cache_key] = detail
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
                "model": app["model"],
                "version": f"v{v}.0",
                "status": "Approved" if v < 3 else pick(seed("ps", app["id"], v), ["Pending Review", "In Review"]),
                "owner": app["owner"],
                "approved_by": "Model Risk" if v < 3 else "—",
                "last_updated": (ANCHOR - timedelta(days=v * 18)).strftime("%Y-%m-%d"),
                "use_case": app["use_case"],
                "risk_score": round(between(seed("prsk", app["id"], v), 12, 68) / 100, 2),
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

    registry_payload = {
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
        "audit_trail": build_registry_audit_trail(),
    }
    return enrich_registry_relationships(registry_payload, apps)


def drill_posture(metric: str, item_id: str = "") -> dict[str, Any]:
    posture = build_ai_posture()
    if metric == "application":
        app = next((a for a in posture["applications"] if a["id"] == item_id or a["name"] == item_id), posture["applications"][0])
        app_prompts = [p for p in posture["prompt_audit"] if p["application_id"] == app["id"]]
        app_audit = [e for e in posture["audit_trail"] if app["name"] in e.get("detail", "")][:30]
        related_model = next((m for m in posture["model_approvals"] if m.get("application_id") == app["id"]), {})
        evidence_rows = [
            {"evidence_id": f"EVD-AI-{app['id'][-3:]}-{n+1:02d}",
             "title": pick(seed("aiev", app["id"], n), [
                 f"Model approval letter — {app['model']}",
                 f"Prompt safety attestation — {app['name']}",
                 f"Bias test results — {app['use_case'][:40]}",
                 f"Token budget compliance report",
                 f"Human-in-loop review checklist",
             ]),
             "status": pick(seed("aievs", app["id"], n), ["Approved", "Approved", "Pending"]),
             "collected_date": (ANCHOR - timedelta(days=between(seed("aied", app["id"], n), 3, 90))).strftime("%Y-%m-%d")}
            for n in range(6)
        ]
        return {
            "type": "application",
            "title": app["name"],
            "data": {
                **app,
                "compliance": app["compliance_score"],
                "hallucinations": app["hallucinations_30d"],
                "unsafe_prompts": app["unsafe_blocked_30d"],
            },
            "related_prompts": app_prompts,
            "related_model": related_model,
            "evidence_rows": evidence_rows,
            "audit_history": app_audit,
            "link": "/mvp/ai-registry",
        }
    if metric == "inventory":
        return {
            "type": "list", "list_kind": "posture_inventory",
            "title": f"AI Application Inventory ({len(posture['applications'])})",
            "rows": posture["applications"],
        }
    if metric in ("hallucinations", "unsafe", "prompts"):
        key = "hallucinations" if metric == "hallucinations" else "unsafe_prompts" if metric == "unsafe" else "prompt_audit"
        rows = posture[key]
        if item_id:
            row = next((r for r in rows if r["prompt_id"] == item_id), rows[0] if rows else {})
            return {"type": "prompt", "title": row.get("prompt_id", "Prompt"), "data": row}
        return {
            "type": "list", "list_kind": f"posture_{metric}",
            "title": f"{metric.replace('_', ' ').title()} ({len(rows)})",
            "rows": rows,
        }
    if metric == "controls":
        controls = posture.get("control_compliance") or build_ecs_control_compliance()
        if item_id:
            ctrl = next(
                (c for c in controls if c["control_id"] == item_id or c["control_id"].startswith(item_id)),
                controls[0] if controls else {},
            )
            return {
                "type": "control_violations",
                "title": f"{ctrl.get('control_id', '')} | {ctrl.get('control_name', '')}",
                "data": {
                    "framework": ctrl.get("framework"),
                    "control_id": ctrl.get("control_id"),
                    "control_name": ctrl.get("control_name"),
                    "compliance_pct": ctrl.get("compliance_pct"),
                    "violations": ctrl.get("violations"),
                    "control_owner": ctrl.get("control_owner"),
                },
                "rows": ctrl.get("violation_records", []),
            }
        return {
            "type": "control_compliance_drill",
            "title": "ECS Control Compliance",
            "data": {"total_controls": len(controls), "rows": controls},
            "rows": controls,
        }
    if metric == "policies":
        if item_id:
            pol = next((p for p in posture["policies"] if p["policy"] == item_id or p["policy"].startswith(item_id)), posture["policies"][0])
            return {
                "type": "policy_violations",
                "title": pol["policy"],
                "data": {
                    "policy": pol["policy"],
                    "compliance_pct": pol["compliance_pct"],
                    "violations": pol["violations"],
                    "owner": pol.get("owner", "AI CoE"),
                },
                "rows": pol.get("violation_records", []),
            }
        return {
            "type": "policy_compliance_drill",
            "title": "Policy Compliance",
            "data": posture.get("policy_compliance_explainer") or build_policy_compliance_drill(posture),
        }
    if metric == "models":
        return {
            "type": "list", "list_kind": "posture_models",
            "title": f"Model Approval Status ({len(posture['model_approvals'])})",
            "rows": posture["model_approvals"],
        }
    if metric == "tokens":
        if item_id:
            if len(item_id) == 7 and "-" in item_id:
                events = [e for e in posture["token_usage"]["events"] if e["month_key"] == item_id]
                return {"type": "list", "list_kind": "posture_tokens", "title": f"Token events — {item_id} ({len(events)})", "rows": events}
            if len(item_id) == 10:
                events = [e for e in posture["token_usage"]["events"] if e["date"] == item_id]
                return {"type": "list", "list_kind": "posture_tokens", "title": f"Token events — {item_id} ({len(events)})", "rows": events}
        return {"type": "tokens", "title": "Token Usage Analytics", "data": posture["token_usage"]}
    if metric == "compliance":
        return {
            "type": "compliance_breakdown",
            "title": "AI Compliance Score",
            "data": posture.get("compliance_breakdown") or build_ai_compliance_breakdown(posture),
        }
    if metric == "heatmap_cell":
        idx = posture.get("_heatmap_index", {})
        if item_id and item_id in idx:
            cell = idx[item_id]
            return {"type": "heatmap_cell", "title": f"{cell['application']} — {cell['dimension']}", "data": cell}
        return {"type": "heatmap", "title": "AI Risk Heatmap", "data": posture["risk_heatmap"]}
    if metric == "audit":
        return {"type": "list", "list_kind": "posture_audit", "title": f"Audit Trail ({len(posture['audit_trail'])})", "rows": posture["audit_trail"]}
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
            if "model" in section:
                related_prompts = [p for p in reg["prompts"] if p.get("model") == row.get("name")]
                return {
                    "type": "registry_model",
                    "title": f"Model: {row.get('name', item_id)}",
                    "data": row,
                    "related_prompts": related_prompts,
                    "workflow": reg["model_approval_workflow"],
                }
            if section in ("prompts", "prompts_pending"):
                related_model = next((m for m in reg["models"] if m.get("model_id") == row.get("model_id") or m.get("name") == row.get("model")), {})
                return {
                    "type": "registry_prompt",
                    "title": f"Prompt: {row.get('name', item_id)}",
                    "data": row,
                    "related_model": related_model,
                    "workflow": reg["prompt_approval_workflow"],
                }
            return {
                "type": section, "title": f"{label}: {row.get(id_field, item_id)}", "data": row,
                "workflow": reg["model_approval_workflow"] if "model" in section else reg["prompt_approval_workflow"],
            }
        return {"type": "list", "list_kind": f"registry_{section}", "title": f"{label} Registry ({len(rows)})", "rows": rows}
    if section == "version_history":
        rows = reg["prompt_version_history"]
        if item_id:
            row = next((r for r in rows if r["prompt_id"] == item_id), rows[0])
            return {"type": "version", "title": f"Version: {row['prompt_id']}", "data": row}
        return {"type": "list", "title": f"Prompt Version History ({len(rows)})", "rows": rows}
    if section == "audit":
        rows = reg.get("audit_trail", [])
        return {"type": "list", "title": f"Registry Audit Trail ({len(rows)})", "rows": rows}
    return {"type": "summary", "title": "AI Registry", "data": reg["summary"]}


def _sdlc_app_banner(release: dict, applications: list[str] | None = None) -> dict[str, Any]:
    apps = applications or _release_apps(release)
    return {
        "release": release["name"],
        "primary_application": release["application"],
        "applications_impacted": apps,
    }


def _all_stage_controls(detail: dict) -> list[dict]:
    return [c for r in detail.get("framework_rows", []) for c in r.get("control_records", [])]


def _all_stage_evidence(detail: dict) -> list[dict]:
    return [e for r in detail.get("framework_rows", []) for e in r.get("evidence_records", [])]


def _history_drill(metric: str, history: dict, item_id: str, release: dict, stage_key: str) -> dict[str, Any] | None:
    mapping = {
        "history_observation": ("previous_observations", "obs_id", "Audit Observation"),
        "history_design": ("previously_approved_designs", "design_id", "Approved Design"),
        "history_evidence": ("previously_accepted_evidence", "evidence_id", "Accepted Evidence"),
        "history_similar": ("similar_controls", "control_id", "Similar Control"),
        "history_closure": ("historical_closure_comments", "comment_id", "Closure Comment"),
    }
    if metric not in mapping:
        return None
    key, id_field, label = mapping[metric]
    rows = history.get(key, [])
    if item_id:
        row = next((r for r in rows if str(r.get(id_field)) == item_id), rows[0] if rows else {})
        return {"type": metric, "title": f"{label}: {row.get(id_field, item_id)} — {row.get('application', '')}", "data": row}
    return {"type": "list", "title": f"{label} ({len(rows)})", "rows": rows}


def drill_sdlc(
    metric: str, release_id: str = "", stage_key: str = "", item_id: str = "",
    page: int = 1, severity: str = "", search: str = "",
) -> dict[str, Any]:
    gates = build_sdlc_gates(release_id)
    release = gates["release"]

    def _with_apps(payload: dict[str, Any], apps: list[str] | None = None) -> dict[str, Any]:
        payload["applications"] = _sdlc_app_banner(release, apps)
        sk = stage_key or payload.get("stage_key", "")
        tab = METRIC_TAB_MAP.get(metric, "overview")
        nav = build_navigation_context(
            sk, release, metric=metric, tab=tab,
            framework_id=str(item_id) if metric == "framework" and item_id else "",
            document_id=str(item_id) if metric in ("document", "documents") and item_id else "",
            control_id=str(item_id) if metric == "control" and item_id else "",
        ) if sk else {}
        payload["stage_link"] = nav.get("stage_link") or (
            build_stage_workspace_url(sk, release["id"], tab=tab) if sk else ""
        )
        payload["navigation_context"] = nav
        payload["release_id"] = release["id"]
        payload["stage_key"] = sk
        return payload

    _HIST_ID_FIELDS = {
        "previous_observations": "obs_id",
        "previously_approved_designs": "design_id",
        "previously_accepted_evidence": "evidence_id",
        "similar_controls": "control_id",
        "historical_closure_comments": "comment_id",
    }

    if metric.startswith("history_"):
        detail = build_sdlc_stage_detail(stage_key, release_id) if stage_key else None
        history: dict[str, list] = {k: [] for k in _HISTORY_KEYS}
        if detail:
            if item_id in SDLC_FRAMEWORKS:
                fw_row = next((r for r in detail["framework_rows"] if r["framework"] == item_id), None)
                if fw_row:
                    history = fw_row.get("history_rollup", {})
            elif item_id:
                hist_key = next((k for m, k in [
                    ("history_observation", "previous_observations"),
                    ("history_design", "previously_approved_designs"),
                    ("history_evidence", "previously_accepted_evidence"),
                    ("history_similar", "similar_controls"),
                    ("history_closure", "historical_closure_comments"),
                ] if m == metric), None)
                id_field = _HIST_ID_FIELDS.get(hist_key or "", "obs_id")
                for c in _all_stage_controls(detail):
                    h = c.get("history", {})
                    if hist_key and any(str(r.get(id_field)) == item_id for r in h.get(hist_key, [])):
                        history = h
                        break
            else:
                for c in _all_stage_controls(detail):
                    h = c.get("history", {})
                    for hk in _HISTORY_KEYS:
                        history[hk].extend(h.get(hk, []))
        payload = _history_drill(metric, history, item_id if item_id not in SDLC_FRAMEWORKS else "", release, stage_key)
        return _with_apps(payload or {"type": "list", "title": "Historical Knowledge", "rows": []})

    if metric == "lifecycle_step" and item_id:
        detail = build_sdlc_stage_detail(stage_key, release_id) if stage_key else None
        ctrl_id, step_key = item_id.split("::") if "::" in item_id else (item_id, "")
        ctrl, sk_used, fw = None, stage_key, "AppSec"
        if detail:
            ctrl = next((c for c in _all_stage_controls(detail) if c["control_id"] == ctrl_id), None)
            sk_used = stage_key
        if not ctrl:
            for st in SDLC_STAGES:
                det = build_sdlc_stage_detail(st["key"], release_id)
                match = next((c for c in _all_stage_controls(det) if c["control_id"] == ctrl_id), None)
                if match:
                    ctrl, detail, sk_used = match, det, st["key"]
                    break
        if ctrl:
            step = next(
                (s for s in ctrl.get("lifecycle_trace", []) if s["stage"] == step_key or s["stage_label"] == step_key),
                ctrl.get("lifecycle_trace", [{}])[0],
            )
            enriched = enrich_lifecycle_step_detail(step, ctrl, release, sk_used, ctrl.get("framework", fw))
            return _with_apps({
                "type": "lifecycle_step",
                "title": f"{ctrl_id} — {enriched.get('stage_label', step_key)}",
                "data": enriched,
                "control_id": ctrl_id,
            }, _release_apps(release))
        return _with_apps({"type": "lifecycle_step", "title": "Lifecycle Step", "data": {}})

    if metric == "knowledge_reuse":
        ex = gates.get("executive") or build_sdlc_executive(release["id"], gates)
        reuse = ex.get("knowledge_reuse") or build_knowledge_reuse_scores(release["id"])
        dim = item_id or ""
        if dim and dim in reuse.get("breakdown", {}):
            return _with_apps({
                "type": "knowledge_reuse_dim",
                "title": f"{dim.title()} Reuse — {reuse['breakdown'][dim]}%",
                "data": {"dimension": dim, "pct": reuse["breakdown"][dim], "formula": reuse["formula"]},
            })
        return _with_apps({"type": "knowledge_reuse", "title": f"Knowledge Reuse — {reuse['overall_pct']}%", "data": reuse})

    if metric == "control_graph" and item_id:
        for st in SDLC_STAGES:
            det = build_sdlc_stage_detail(st["key"], release_id)
            match = next((c for c in _all_stage_controls(det) if c["control_id"] == item_id), None)
            if match:
                graph = build_knowledge_graph(match, release, match.get("framework", "AppSec"), st["key"])
                return _with_apps({"type": "knowledge_graph", "title": f"Control Relationship Graph — {item_id}", "graph": graph, "control_id": item_id}, _release_apps(release))
        return _with_apps({"type": "knowledge_graph", "title": "Control Relationship Graph", "graph": {"nodes": [], "edges": []}})

    _EXEC_ANALYTICS = {
        "exec_top_reused": ("top_reused_controls", "Top Reused Controls", [
            {"key": "control_id", "label": "Control ID"}, {"key": "reuse_count", "label": "Reuse Count"},
            {"key": "application_count", "label": "Applications"}, {"key": "framework", "label": "Framework"},
            {"key": "top_application", "label": "Top Application"},
        ]),
        "exec_top_failed": ("top_failed_controls", "Top Failed Controls", [
            {"key": "control_id", "label": "Control ID"}, {"key": "failure_count", "label": "Failures"},
            {"key": "application_count", "label": "Applications"}, {"key": "framework", "label": "Framework"},
        ]),
        "exec_common_findings": ("common_findings", "Most Common Audit Findings", [
            {"key": "finding", "label": "Finding"}, {"key": "occurrences", "label": "Occurrences"}, {"key": "framework", "label": "Framework"},
        ]),
        "exec_reuse_by_app": ("highest_reuse_apps", "Applications with Highest Control Reuse", [
            {"key": "application", "label": "Application"}, {"key": "reuse_score", "label": "Reuse Score"},
            {"key": "controls_reused", "label": "Controls Reused"},
        ]),
        "exec_exceptions_by_app": ("highest_exception_apps", "Applications with Highest Exceptions", [
            {"key": "application", "label": "Application"}, {"key": "exceptions", "label": "Exceptions"}, {"key": "open", "label": "Open"},
        ]),
        "exec_governance_maturity": ("highest_maturity_apps", "Governance Maturity Leaders", [
            {"key": "application", "label": "Application"}, {"key": "maturity_score", "label": "Maturity %"},
            {"key": "governance_tier", "label": "Tier"},
        ]),
    }
    if metric in _EXEC_ANALYTICS:
        ex = gates.get("executive") or build_sdlc_executive(release["id"], gates)
        analytics = ex.get("cross_app_analytics") or build_cross_app_analytics(release["id"])
        key, title, cols = _EXEC_ANALYTICS[metric]
        rows = analytics.get(key, [])
        if item_id:
            row = next((r for r in rows if str(r.get(list(r.keys())[0])) == item_id or r.get("control_id") == item_id or r.get("application") == item_id), rows[0] if rows else {})
            return _with_apps({"type": "exec_analytics_detail", "title": f"{title} — {item_id}", "data": row, "columns": cols})
        return _with_apps({"type": "exec_analytics", "title": f"{title} ({len(rows)})", "rows": rows, "columns": cols, "metric": metric})

    if metric == "exec_readiness_heatmap":
        ex = gates.get("executive") or build_sdlc_executive(release["id"], gates)
        hm = ex["readiness_heatmap"]
        if item_id and "::" in item_id:
            app, stg = item_id.split("::", 1)
            row = next((r for r in hm["rows"] if r["application"] == app), None)
            cell = next((c for c in row["cells"] if c["stage"] == stg), {}) if row else {}
            return _with_apps({"type": "exec_heatmap_cell", "title": f"{app} — {cell.get('stage_label', stg)}", "data": {**cell, "application": app}, "stage_key": stg})
        flat = [{"application": r["application"], **c, "drill_id": f"{r['application']}::{c['stage']}"} for r in hm["rows"] for c in r["cells"]]
        return _with_apps({"type": "exec_heatmap", "title": f"Release Readiness Heatmap ({len(flat)} cells)", "data": hm, "rows": flat})

    if metric == "exec_gap_applications":
        ex = gates.get("executive") or build_sdlc_executive(release["id"], gates)
        rows = ex["gap_applications"]
        if item_id:
            row = next((r for r in rows if r["application"] == item_id), rows[0] if rows else {})
            return _with_apps({"type": "exec_gap_app", "title": f"Gaps — {row.get('application', item_id)}", "data": row})
        return _with_apps({"type": "exec_ranking", "title": f"Applications with Highest SDLC Gaps ({len(rows)})", "rows": rows})

    if metric == "exec_framework_by_app":
        ex = gates.get("executive") or build_sdlc_executive(release["id"], gates)
        matrix = ex["framework_by_application"]
        if item_id and "::" in item_id:
            app, fw = item_id.split("::", 1)
            row = next((r for r in matrix["rows"] if r["application"] == app), None)
            cell = next((c for c in row["cells"] if c["framework"] == fw), {}) if row else {}
            return _with_apps({"type": "exec_fw_cell", "title": f"{app} — {fw}", "data": {**cell, "application": app}, "stage_key": ""})
        flat = [{"application": r["application"], **c, "drill_id": f"{r['application']}::{c['framework']}"} for r in matrix["rows"] for c in r["cells"]]
        return _with_apps({"type": "exec_matrix", "title": f"Framework Compliance by Application ({len(flat)} cells)", "data": matrix, "rows": flat})

    if metric == "exec_stage_completion":
        ex = gates.get("executive") or build_sdlc_executive(release["id"], gates)
        rows = ex["stage_completion"]
        if item_id:
            row = next((r for r in rows if r["stage"] == item_id), rows[0] if rows else {})
            return _with_apps({"type": "exec_stage", "title": f"{row.get('label', item_id)} — Completion", "data": row, "stage_key": row.get("stage", item_id)})
        return _with_apps({"type": "exec_dashboard", "title": f"Stage Completion Dashboard ({len(rows)})", "rows": rows})

    if metric == "exec_exceptions":
        ex = gates.get("executive") or build_sdlc_executive(release["id"], gates)
        rows = ex["exceptions_dashboard"]
        if item_id:
            row = next((r for r in rows if r.get("exception_id") == item_id), rows[0] if rows else {})
            return _with_apps({"type": "exception", "title": f"{row.get('exception_id', item_id)} — {row.get('application', '')}", "data": row, "stage_key": "go-live"})
        return _with_apps({"type": "exec_exceptions", "title": f"Open Exceptions Dashboard ({len(rows)})", "rows": rows})

    if metric == "gaps":
        rows: list[dict] = []
        if stage_key:
            detail = build_sdlc_stage_detail(stage_key, release_id)
            if item_id in SDLC_FRAMEWORKS:
                fw_row = next((r for r in detail["framework_rows"] if r["framework"] == item_id), None)
                rows = fw_row.get("gap_records", []) if fw_row else []
            else:
                rows = detail["summary"].get("gap_records", [])
        else:
            rows = list(gates["all_gaps"])
        if item_id and item_id not in SDLC_FRAMEWORKS:
            row = next((r for r in rows if r.get("gap_id") == item_id), None)
            if row:
                return _with_apps({"type": "gap", "title": f"{row.get('gap_id', 'Gap')} — {row.get('application', '')}", "data": row})
        return _with_apps({"type": "list", "title": f"Open SDLC Gaps ({len(rows)})", "rows": rows})

    if metric == "releases":
        rows = [{**r, "applications_impacted": _release_apps(r)} for r in gates["releases"]]
        if item_id:
            row = next((r for r in rows if r["id"] == item_id), rows[0])
            return _with_apps({"type": "release", "title": row["name"], "data": row})
        return _with_apps({"type": "list", "title": f"Active Releases ({len(rows)})", "rows": rows})

    if metric == "frameworks":
        rows = [{"framework": f, "applications_impacted": ", ".join(_release_apps(release))} for f in gates["frameworks"]]
        return _with_apps({"type": "list", "title": f"Frameworks in Scope ({len(rows)})", "rows": rows})

    if metric == "stages_complete":
        rows = [s for s in gates["stages"] if s["checklist_completion_pct"] >= 90]
        return _with_apps({"type": "list", "title": f"Stages ≥90% Complete ({len(rows)})", "rows": rows})

    if metric == "readiness_breakdown" or (metric == "readiness" and stage_key):
        detail = build_sdlc_stage_detail(stage_key, release_id)
        data = build_readiness_breakdown(stage_key, detail, release, gates.get("stages"))
        return _with_apps({"type": "readiness_breakdown", "title": f"{detail['stage']['label']} — Readiness Calculation", "data": data})

    if metric == "framework_coverage_drill" and stage_key:
        detail = build_sdlc_stage_detail(stage_key, release_id)
        return _with_apps({"type": "framework_coverage_drill", "title": "Framework Coverage Breakdown", "data": build_framework_coverage_drill(detail, release)})

    if metric == "control_coverage_drill" and stage_key:
        detail = build_sdlc_stage_detail(stage_key, release_id)
        return _with_apps({"type": "control_coverage_drill", "title": "Control Coverage", "data": build_control_coverage_drill(detail)})

    if metric == "evidence_coverage_drill" and stage_key:
        detail = build_sdlc_stage_detail(stage_key, release_id)
        return _with_apps({"type": "evidence_coverage_drill", "title": "Evidence Coverage", "data": build_evidence_coverage_drill(detail)})

    if metric == "gaps_drill" and stage_key:
        detail = build_sdlc_stage_detail(stage_key, release_id)
        pg = page if page > 0 else (int(item_id) if item_id and item_id.isdigit() else 1)
        sev = severity or (item_id if item_id in ("Critical", "High", "Medium", "Low") else "")
        return _with_apps({
            "type": "gaps_drill",
            "title": f"Open Gaps ({detail['summary']['open_gaps']})",
            "data": build_gaps_drill(detail, page=pg, severity=sev, search=search),
        })

    if metric == "status_timeline" and stage_key:
        detail = build_sdlc_stage_detail(stage_key, release_id)
        return _with_apps({"type": "status_timeline", "title": "Lifecycle Status Timeline", "data": build_status_timeline(stage_key, detail, release)})

    if metric == "approvals_drill" and stage_key:
        return _with_apps({"type": "approvals_drill", "title": "Approval Status & History", "data": build_approvals_drill(stage_key, release)})

    if metric == "historical_lineage" and stage_key:
        detail = build_sdlc_stage_detail(stage_key, release_id)
        return _with_apps({"type": "historical_lineage", "title": "Historical Implementation Lineage", "data": build_historical_lineage(stage_key, detail, release)})

    if metric == "control_reuse_repo":
        return _with_apps({"type": "control_reuse_repo", "title": "Reusable Control Repository", "data": build_control_reuse_repository(release)})

    if metric == "design_reuse_repo":
        return _with_apps({"type": "design_reuse_repo", "title": "Reusable Design Patterns", "data": build_design_reuse_repository(release)})

    if metric == "code_reuse_repo":
        return _with_apps({"type": "code_reuse_repo", "title": "Reusable Code Components", "data": build_code_reuse_repository(release)})

    if metric == "test_pack_reuse_repo":
        return _with_apps({"type": "test_pack_reuse_repo", "title": "Reusable Test Packs", "data": build_test_pack_reuse_repository(release)})

    if metric == "readiness":
        if stage_key:
            detail = build_sdlc_stage_detail(stage_key, release_id)
            data = build_readiness_breakdown(stage_key, detail, release, gates.get("stages"))
            return _with_apps({
                "type": "readiness_breakdown",
                "title": f"{detail['stage']['label']} — Readiness Calculation",
                "data": data,
            })
        overall = gates["summary"]["overall_readiness"]
        formulas = coverage_formulas()
        breakdown = [{
            "dimension": st["label"], "stage_key": st["key"], "weight_pct": 20,
            "score": st["readiness_score"], "contribution": round(st["readiness_score"] * 0.2, 1),
        } for st in gates["stages"]]
        return _with_apps({
            "type": "readiness_breakdown",
            "title": "Overall Release Readiness",
            "data": {
                "current_score": overall, "target_score": 90.0,
                "missing_score": round(max(90 - overall, 0), 1),
                "breakdown": breakdown,
                "trend": [{"month": (ANCHOR.replace(day=1) - timedelta(days=30 * i)).strftime("%Y-%m"), "readiness": round(overall - i * 2.1, 1)} for i in range(5, -1, -1)],
                "improvement_actions": [
                    {"action": "Close cross-stage AppSec gaps", "impact_pts": 3.5, "owner": release["owner"]},
                    {"action": "Refresh stale evidence across impacted apps", "impact_pts": 2.4, "owner": "Compliance Head"},
                ],
                "formula": formulas["readiness"],
                "calculation_steps": [f"Overall readiness {overall}% = sum of stage contributions across {len(breakdown)} gates."],
            },
        })

    if metric == "controls":
        detail = build_sdlc_stage_detail(stage_key, release_id) if stage_key else None
        rows = _all_stage_controls(detail) if detail else []
        if stage_key and item_id:
            if item_id.endswith("::covered"):
                fw = item_id.replace("::covered", "")
                rows = [c for r in detail["framework_rows"] if r["framework"] == fw for c in r["control_records"] if c["status"] == "Covered"]
                return _with_apps({"type": "controls", "title": f"{fw} — Covered Controls ({len(rows)})", "rows": rows})
            if any(r["framework"] == item_id for r in detail.get("framework_rows", [])):
                rows = [c for r in detail["framework_rows"] if r["framework"] == item_id for c in r["control_records"]]
                return _with_apps({"type": "controls", "title": f"{item_id} — Controls ({len(rows)})", "rows": rows})
            row = next((c for c in rows if c["control_id"] == item_id), rows[0] if rows else {})
            ev_rows = [e for r in detail["framework_rows"] for e in r["evidence_records"] if e["control_id"] == row.get("control_id")]
            extra = _control_drill_payload(row, release, stage_key or "")
            return _with_apps({
                "type": "control", "title": f"{row.get('control_id', item_id)} — {row.get('application', '')}",
                "data": row, "rows": ev_rows,
                **extra,
            })
        if item_id and not stage_key:
            for st in SDLC_STAGES:
                det = build_sdlc_stage_detail(st["key"], release_id)
                match = next((c for c in _all_stage_controls(det) if c["control_id"] == item_id), None)
                if match:
                    return drill_sdlc("control", release_id, st["key"], item_id)
        return _with_apps({"type": "controls", "title": f"Controls ({len(rows)})", "rows": rows})

    if metric == "control":
        return drill_sdlc("controls", release_id, stage_key, item_id)

    if metric == "evidence":
        detail = build_sdlc_stage_detail(stage_key, release_id) if stage_key else None
        rows = _all_stage_evidence(detail) if detail else []
        if stage_key and item_id:
            if any(r["framework"] == item_id for r in detail.get("framework_rows", [])):
                rows = [e for r in detail["framework_rows"] if r["framework"] == item_id for e in r["evidence_records"]]
                return _with_apps({"type": "evidence_list", "title": f"{item_id} — Evidence ({len(rows)})", "rows": rows})
            row = next((e for e in rows if e["evidence_id"] == item_id), rows[0] if rows else {})
            return _with_apps({"type": "evidence", "title": f"{row.get('evidence_id', item_id)} — {row.get('application', '')}", "data": row})
        if stage_key:
            sm = detail["summary"]
            return _with_apps({"type": "evidence_list", "title": f"Stage Evidence ({sm.get('evidence_collected', 0)}/{sm.get('evidence_total', 0)})", "rows": rows})
        return _with_apps({"type": "evidence_list", "title": f"Evidence ({len(rows)})", "rows": rows})

    if metric == "documents":
        detail = build_sdlc_stage_detail(stage_key, release_id) if stage_key else None
        rows = detail.get("documents", []) if detail else []
        if item_id:
            row = next((d for d in rows if d["doc_id"] == item_id), rows[0] if rows else {})
            return _with_apps({
                "type": "document_viewer",
                "title": row.get("title", item_id),
                "data": row,
                "artifact": row.get("artifact", {}),
                "viewer_tabs": row.get("artifact", {}).get("viewer_tabs"),
            })
        return _with_apps({"type": "documents", "title": f"Governance Documents ({len(rows)})", "rows": rows})

    if metric == "document":
        return drill_sdlc("documents", release_id, stage_key, item_id)

    if metric == "reuse_modal" and item_id:
        detail = build_sdlc_stage_detail(stage_key, release_id) if stage_key else build_sdlc_stage_detail("requirement", release_id)
        reuse_type, source_id = (item_id.split("::", 1) + [""])[:2] if "::" in item_id else ("requirement", item_id)
        doc = next((d for d in detail.get("documents", []) if d["doc_id"] == source_id), detail.get("documents", [{}])[0] if detail.get("documents") else {})
        ctrl = next((c for c in _all_stage_controls(detail) if c["control_id"] == source_id), None)
        source = doc if doc else (ctrl or {"title": source_id, "control_id": source_id})
        return _with_apps({
            "type": "reuse_modal",
            "title": f"Reuse {reuse_type.title()} — {source.get('title', source_id)}",
            "data": build_reuse_modal_payload(reuse_type, source, release, stage_key or "requirement"),
            "stage_key": stage_key or "requirement",
        })

    if metric == "stage_card" and item_id:
        detail = build_sdlc_stage_detail(item_id, release_id)
        return _with_apps({
            "type": "stage_card",
            "title": f"{detail['stage']['label']} Gate — {release['name']}",
            "data": build_stage_card_drill(item_id, detail, release),
            "stage_key": item_id,
        })

    if metric == "framework":
        detail = build_sdlc_stage_detail(stage_key, release_id) if stage_key else None
        if detail and item_id:
            row = next((r for r in detail["framework_rows"] if r["framework"] == item_id), detail["framework_rows"][0])
            hist = row.get("history_rollup", _rollup_framework_history(row.get("control_records", [])))
            enriched = enrich_framework_drill(row, release, detail["summary"])
            return _with_apps({
                "type": "framework",
                "title": f"{row['framework']} — {detail['release']['name']}",
                "data": row,
                "rows": row.get("control_records", []),
                "gap_rows": row.get("gap_records", []),
                "evidence_rows": row.get("evidence_records", []),
                "applications_impacted": row.get("applications_impacted", []),
                "history": hist,
                "framework_summary": enriched["framework_summary"],
                "control_lineage": enriched["control_lineage"],
            })
        if detail:
            return _with_apps({"type": "list", "title": f"Framework Coverage ({len(detail['framework_rows'])})", "rows": detail["framework_rows"]})
        return _with_apps({"type": "list", "title": f"Frameworks ({len(gates['frameworks'])})", "rows": [{"framework": f} for f in gates["frameworks"]]})

    if stage_key:
        detail = build_sdlc_stage_detail(stage_key, release_id)

        if metric == "requirements":
            rows = detail.get("requirements", [])
            if item_id:
                row = next((r for r in rows if r["req_id"] == item_id), rows[0] if rows else {})
                return _with_apps({"type": "requirement", "title": f"{row.get('req_id')} — {row.get('application', '')}", "data": row, "rows": row.get("control_records", [])})
            return _with_apps({"type": "list", "title": f"Requirements ({len(rows)})", "rows": rows})

        if metric == "designs":
            rows = detail.get("designs", [])
            if item_id:
                row = next((r for r in rows if r["design_id"] == item_id), rows[0] if rows else {})
                return _with_apps({"type": "design", "title": f"{row.get('design_id')} — {row.get('application', '')}", "data": row})
            return _with_apps({"type": "list", "title": f"Designs ({len(rows)})", "rows": rows})

        if metric == "development":
            rows = detail.get("development", [])
            if item_id:
                row = next((r for r in rows if r.get("item_id") == item_id or r.get("control_id") == item_id), rows[0] if rows else {})
                return _with_apps({"type": "development", "title": f"{row.get('item_id', item_id)} — {row.get('application', '')}", "data": row})
            return _with_apps({"type": "list", "title": f"Development Items ({len(rows)})", "rows": rows})

        if metric == "testing":
            rows = detail.get("testing", [])
            if item_id:
                row = next((r for r in rows if r["test_id"] == item_id), rows[0] if rows else {})
                return _with_apps({"type": "testing", "title": f"{row.get('test_id')} — {row.get('application', '')}", "data": row, "rows": row.get("defect_records", [])})
            return _with_apps({"type": "list", "title": f"Test Cases ({len(rows)})", "rows": rows})

        if metric == "defects":
            rows = [d for t in detail.get("testing", []) for d in t.get("defect_records", [])]
            if item_id:
                row = next((d for d in rows if d["defect_id"] == item_id), rows[0] if rows else {})
                return _with_apps({"type": "defect", "title": f"{row.get('defect_id')} — {row.get('application', '')}", "data": row})
            return _with_apps({"type": "list", "title": f"Defects ({len(rows)})", "rows": rows})

        if metric == "observations":
            gl = detail.get("go_live", {})
            rows = gl.get("observation_records", [])
            if item_id:
                row = next((r for r in rows if r["obs_id"] == item_id), rows[0] if rows else {})
                return _with_apps({"type": "observation", "title": f"{row.get('obs_id')} — {row.get('application', '')}", "data": row})
            return _with_apps({"type": "list", "title": f"Open Observations ({len(rows)})", "rows": rows})

        if metric == "exceptions":
            gl = detail.get("go_live", {})
            rows = gl.get("exception_records", [])
            if item_id:
                row = next((r for r in rows if r["exception_id"] == item_id), rows[0] if rows else {})
                return _with_apps({"type": "exception", "title": f"{row.get('exception_id')} — {row.get('application', '')}", "data": row})
            return _with_apps({"type": "list", "title": f"Exceptions ({len(rows)})", "rows": rows})

        if metric == "checklist":
            gl = detail.get("go_live", {})
            rows = gl.get("checklist", [])
            if item_id:
                row = next((r for r in rows if r.get("item_id") == item_id), rows[0] if rows else {})
                return _with_apps({"type": "checklist_item", "title": f"{row.get('item', item_id)[:48]} — {row.get('application', '')}", "data": row})
            return _with_apps({"type": "list", "title": f"Go-Live Checklist ({len(rows)})", "rows": rows})

        if metric == "audit":
            rows = detail.get("audit_trail", [])
            return _with_apps({"type": "list", "title": f"Audit Trail ({len(rows)})", "rows": rows})

        return _with_apps({"type": "stage", "title": detail["stage"]["label"], "data": detail["summary"], "rows": detail.get("documents", [])})

    return _with_apps({"type": "summary", "title": "SDLC Compliance Gates", "data": gates["summary"], "rows": gates["stages"]})
