"""Deep drill-down payloads for ECS governance workspaces."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from modules.shared.utils.demo_data_standards import BANKING_OWNERS, between, pick, seed
from modules.enterprise_grc.engines.ecs_governance_framework import ANCHOR, BANKING_APPS, STAGE_LABELS

_FRAMEWORKS = [
    "PCI DSS", "DPSC", "AppSec", "VAPT", "ITPP",
    "Middleware Baseline", "Database Baseline", "AI Governance",
]

READINESS_FORMULA = (
    "Readiness = Σ (Stage Control Score × Weight) where each SDLC stage contributes 20% "
    "(Requirement, Design, Development, Testing, Go-Live)."
)
FRAMEWORK_COVERAGE_FORMULA = (
    "Framework Coverage = Average across in-scope frameworks of "
    "(35% × Controls Covered + 25% × Controls Mapped + 25% × Evidence Approved + 15% × Evidence Attached)."
)
CONTROL_COVERAGE_FORMULA = "Control Coverage = (Controls with status Covered ÷ Total Controls) × 100."
EVIDENCE_COVERAGE_FORMULA = "Evidence Coverage = (Approved Evidence Items ÷ Total Required Evidence Items) × 100."


def coverage_formulas() -> dict[str, str]:
    return {
        "readiness": READINESS_FORMULA,
        "framework_coverage": FRAMEWORK_COVERAGE_FORMULA,
        "control_coverage": CONTROL_COVERAGE_FORMULA,
        "evidence_coverage": EVIDENCE_COVERAGE_FORMULA,
    }


def build_readiness_breakdown(stage_key: str, detail: dict, release: dict, gates_stages: list | None = None) -> dict[str, Any]:
    sm = detail.get("summary", {})
    target = 90.0
    stages = gates_stages or []
    weights = {"requirement": 20, "design": 20, "development": 20, "testing": 20, "go-live": 20}
    breakdown = []
    for st in stages:
        sk = st.get("key") or st.get("stage_key", "")
        label = st.get("label") or STAGE_LABELS.get(sk, sk.title())
        score = st.get("readiness_score", st.get("score", between(seed("rdb", stage_key, sk, release["id"]), 72, 94)))
        w = weights.get(sk, 20)
        breakdown.append({
            "dimension": f"{label} Governance",
            "stage_key": sk,
            "weight_pct": w,
            "score": score,
            "contribution": round(score * w / 100, 1),
        })
    if not breakdown:
        for sk, label in [
            ("requirement", "Requirement"), ("design", "Design"),
            ("development", "Development"), ("testing", "Testing"), ("go-live", "Go-Live"),
        ]:
            s = seed("rdb", stage_key, sk, release["id"])
            score = between(s, 72, 94)
            w = weights[sk]
            breakdown.append({
                "dimension": f"{label} Governance", "stage_key": sk, "weight_pct": w,
                "score": score, "contribution": round(score * w / 100, 1),
            })
    current = round(sum(b["contribution"] for b in breakdown), 1)
    trend = []
    for i in range(6):
        mk = (ANCHOR.replace(day=1) - timedelta(days=30 * (5 - i))).strftime("%Y-%m")
        trend.append({"month": mk, "readiness": round(current - (5 - i) * between(seed("rt", i), 2, 5), 1)})
    actions = [
        {"action": "Close 3 high-severity gaps in AppSec framework", "impact_pts": 4.2, "owner": release["owner"]},
        {"action": "Upload stale DR evidence for Net Banking", "impact_pts": 2.8, "owner": pick(seed("ra", 1), BANKING_OWNERS)},
        {"action": "Complete UAT sign-off for AI validation pack", "impact_pts": 1.9, "owner": "QA Lead"},
    ]
    calc_steps = [
        f"Current score {current}% = " + " + ".join(f"{b['contribution']}" for b in breakdown) + f" (target {target}%)",
        "Readiness Score = average of Requirement, Design, Development, Testing, and Go-Live governance scores (20% weight each).",
        "Stage contribution = stage score × 20 ÷ 100.",
    ]
    return {
        "current_score": current, "target_score": target,
        "missing_score": round(max(target - current, 0), 1),
        "gap": round(max(target - current, 0), 1),
        "breakdown": breakdown,
        "trend": trend,
        "improvement_actions": actions,
        "formula": READINESS_FORMULA,
        "calculation_steps": calc_steps,
    }


def build_framework_coverage_drill(detail: dict, release: dict) -> dict[str, Any]:
    rows = []
    for fw in detail.get("framework_rows", []):
        total = fw.get("controls_total", 0)
        covered = fw.get("controls_covered", 0)
        ev_pct = fw.get("evidence_pct", 0)
        rows.append({
            "framework": fw["framework"],
            "total_controls": total,
            "covered_controls": covered,
            "missing_controls": max(total - covered, 0),
            "evidence_pct": ev_pct,
            "owner": fw.get("owner", release["owner"]),
            "drill_id": fw["framework"],
            "gaps": fw.get("gaps", 0),
        })
    sm = detail.get("summary", {})
    fw_pct = sm.get("framework_coverage_pct", 0)
    return {
        "rows": rows,
        "summary": sm,
        "aggregate_pct": fw_pct,
        "formula": FRAMEWORK_COVERAGE_FORMULA,
        "calculation_steps": [
            f"Aggregate framework coverage: {fw_pct}% across {len(rows)} frameworks.",
            "Per framework: weighted blend of control coverage, mapping, and evidence attachment.",
        ],
    }


def build_control_coverage_drill(detail: dict) -> dict[str, Any]:
    rows = []
    for c in [c for r in detail.get("framework_rows", []) for c in r.get("control_records", [])]:
        rows.append({
            "control_id": c.get("control_id"),
            "control_name": c.get("control_name", c.get("control_description", "")[:48]),
            "application": c.get("application"),
            "owner": c.get("owner"),
            "status": c.get("status"),
            "evidence_count": c.get("evidence_count", 0),
            "framework": c.get("framework"),
            "drill_id": c.get("control_id"),
        })
    covered = sum(1 for r in rows if r.get("status") == "Covered")
    total = len(rows)
    pct = round(covered / max(total, 1) * 100, 1)
    return {
        "rows": rows,
        "total": total,
        "covered": covered,
        "aggregate_pct": pct,
        "formula": CONTROL_COVERAGE_FORMULA,
        "calculation_steps": [
            f"{covered} covered controls ÷ {total} total controls = {pct}%.",
        ],
    }


def build_evidence_coverage_drill(detail: dict) -> dict[str, Any]:
    all_ev = [e for r in detail.get("framework_rows", []) for e in r.get("evidence_records", [])]
    required = len(all_ev)
    submitted = len(all_ev)
    accepted = sum(1 for e in all_ev if e.get("status") == "Approved")
    rejected = sum(1 for e in all_ev if e.get("status") in ("Rejected", "Stale"))
    expired = sum(1 for e in all_ev if e.get("status") == "Stale")
    items = [{
        "evidence_id": e.get("evidence_id"),
        "title": e.get("title"),
        "status": e.get("status"),
        "source": e.get("source_system", "ECS Evidence Repo"),
        "upload_date": e.get("collected_date"),
        "owner": e.get("owner"),
        "audit_reference": f"AUD-REF-{e.get('evidence_id', '')[-4:]}",
        "control_id": e.get("control_id"),
        "framework": e.get("framework"),
        "drill_id": e.get("evidence_id"),
    } for e in all_ev]
    ev_pct = round(accepted / max(required, 1) * 100, 1)
    return {
        "summary": {
            "required": required, "submitted": submitted,
            "accepted": accepted, "rejected": rejected, "expired": expired,
        },
        "rows": items,
        "aggregate_pct": ev_pct,
        "formula": EVIDENCE_COVERAGE_FORMULA,
        "calculation_steps": [
            f"{accepted} approved evidence items ÷ {required} required = {ev_pct}%.",
            f"Submitted: {submitted} · Rejected: {rejected} · Expired: {expired}.",
        ],
    }


def build_gaps_drill(
    detail: dict, page: int = 1, per_page: int = 10, severity: str = "", search: str = "",
) -> dict[str, Any]:
    gaps = detail.get("summary", {}).get("gap_records", [])
    if not gaps:
        gaps = [g for r in detail.get("framework_rows", []) for g in r.get("gap_records", [])]
    all_gaps = list(gaps)
    if severity:
        gaps = [g for g in gaps if g.get("severity", "").lower() == severity.lower()]
    if search:
        q = search.lower()
        gaps = [
            g for g in gaps
            if q in (g.get("gap_id") or "").lower()
            or q in (g.get("framework") or "").lower()
            or q in (g.get("control") or "").lower()
            or q in (g.get("application") or "").lower()
            or q in (g.get("owner") or "").lower()
            or q in (g.get("description") or "").lower()
        ]
    total = len(gaps)
    start = (max(page, 1) - 1) * per_page
    page_rows = gaps[start:start + per_page]
    return {
        "rows": page_rows, "page": max(page, 1), "per_page": per_page,
        "total": total, "total_pages": max(1, (total + per_page - 1) // per_page),
        "severity_filter": severity,
        "search": search,
        "filters": {
            "Critical": sum(1 for g in all_gaps if g.get("severity") == "Critical"),
            "High": sum(1 for g in all_gaps if g.get("severity") == "High"),
            "Medium": sum(1 for g in all_gaps if g.get("severity") == "Medium"),
            "Low": sum(1 for g in all_gaps if g.get("severity") == "Low"),
            "All": len(all_gaps),
        },
    }


def build_status_timeline(stage_key: str, detail: dict, release: dict) -> dict[str, Any]:
    stages = []
    for sk, label in [
        ("requirement", "Requirement"), ("design", "Design"), ("development", "Development"),
        ("testing", "Testing"), ("go-live", "Go-Live"),
    ]:
        s = seed("stl", stage_key, sk, release["id"])
        idx = ["requirement", "design", "development", "testing", "go-live"].index(sk)
        cur_idx = ["requirement", "design", "development", "testing", "go-live"].index(stage_key)
        if idx < cur_idx:
            st = "Completed"
        elif idx == cur_idx:
            st = pick(s, ["In Progress", "Blocked", "Completed"])
        else:
            st = "Not Started"
        stages.append({
            "stage": label, "stage_key": sk,
            "started": (ANCHOR - timedelta(days=between(s, 30, 120))).strftime("%Y-%m-%d") if idx <= cur_idx else "—",
            "completed": (ANCHOR - timedelta(days=between(s >> 2, 7, 45))).strftime("%Y-%m-%d") if idx < cur_idx else "—",
            "status": st,
            "state": pick(s >> 4, ["Started", "Completed", "Blocked", "Escalated"]) if st != "Not Started" else "Pending",
        })
    blockers = [
        {"item": "Pen test closure letter pending", "stage": "Testing", "owner": "AppSec CoE", "severity": "High"},
        {"item": "CIO residual risk sign-off", "stage": "Go-Live", "owner": "CIO Office", "severity": "Medium"},
    ]
    pending = [
        {"action": "Submit evidence pack to external auditor", "due": release.get("target_date"), "owner": release["owner"]},
        {"action": "Complete NPCI certification upload", "due": release.get("target_date"), "owner": "Compliance Head"},
    ]
    return {"timeline": stages, "blockers": blockers, "pending_actions": pending}


def build_status_explanation(status: str, summary: dict) -> dict[str, Any]:
    """Human-readable justification for lifecycle status."""
    gaps = summary.get("open_gaps", 0)
    ctrl = summary.get("control_coverage_pct", 0)
    ev = summary.get("evidence_coverage_pct", summary.get("checklist_completion_pct", 0))
    readiness = summary.get("readiness_score", 0)
    risk = summary.get("risk_rating", "Medium")

    templates: dict[str, dict[str, Any]] = {
        "On Track": {
            "headline": "On Track",
            "summary": "Stage governance metrics meet or exceed target thresholds with manageable open gaps.",
            "reasons": [
                f"Control coverage at {ctrl}% — above 80% threshold for on-track classification.",
                f"Evidence coverage at {ev}% with {summary.get('evidence_status', 'adequate collection')}.",
                f"Release readiness {readiness}% with {gaps} open gaps within acceptable tolerance.",
            ],
            "criteria": ["Control coverage ≥ 80%", "Evidence coverage ≥ 75%", "No Critical blockers unresolved"],
        },
        "At Risk": {
            "headline": "At Risk",
            "summary": "One or more coverage dimensions or gap counts threaten the release target date.",
            "reasons": [
                f"{gaps} open gaps may delay gate sign-off — high-severity items require remediation.",
                f"Control coverage {ctrl}% or evidence coverage {ev}% below on-track threshold.",
                f"Risk rating {risk} driven by incomplete evidence and pending approvals.",
            ],
            "criteria": ["Open gaps > 40 OR control coverage < 80%", "Pending external auditor evidence", "High-severity findings open"],
        },
        "Escalated": {
            "headline": "Escalated",
            "summary": "Issue escalated to leadership due to blocking gaps or approval delays.",
            "reasons": [
                "Compliance or audit sign-off blocked pending evidence samples.",
                f"CIO residual risk acceptance required — {gaps} gaps remain open.",
                "CAB emergency review triggered for go-live readiness exceptions.",
            ],
            "criteria": ["Approval chain stalled > 5 business days", "Critical gap unresolved", "Executive escalation logged"],
        },
        "In Review": {
            "headline": "In Review",
            "summary": "Stage deliverables submitted and under active reviewer assessment.",
            "reasons": [
                f"Evidence pack {summary.get('evidence_status', '')} under compliance review.",
                "AppSec and internal audit sampling in progress.",
                f"Framework coverage {summary.get('framework_coverage_pct', 0)}% validated against scope.",
            ],
            "criteria": ["Submission complete", "Reviewers assigned", "Decision pending"],
        },
        "Approved": {
            "headline": "Approved",
            "summary": "Stage gate approved with documented sign-off and audit trail entry.",
            "reasons": [
                f"All mandatory controls covered at {ctrl}% with evidence accepted.",
                "Approval chain complete through compliance and audit checkpoints.",
                f"Readiness {readiness}% meets release target with residual risk accepted.",
            ],
            "criteria": ["Approval chain complete", "Evidence accepted", "Audit trail recorded"],
        },
    }
    block = templates.get(status, templates["In Review"])
    return {
        **block,
        "status": status,
        "metrics": {
            "readiness_score": readiness,
            "open_gaps": gaps,
            "control_coverage_pct": ctrl,
            "evidence_coverage_pct": ev,
            "risk_rating": risk,
        },
    }


def build_approvals_drill(stage_key: str, release: dict) -> dict[str, Any]:
    chain = [
        {"approver": "R. Mehta", "role": "App Owner", "status": "Approved", "comments": "Scope validated", "decision_date": "2026-05-10"},
        {"approver": "AppSec CoE", "role": "Security Review", "status": "Approved", "comments": "No critical findings", "decision_date": "2026-05-12"},
        {"approver": "V. Desai", "role": "Compliance", "status": "In Review", "comments": "Pending evidence sample", "decision_date": "—"},
        {"approver": "S. Nair", "role": "Internal Audit", "status": "Pending", "comments": "—", "decision_date": "—"},
        {"approver": "CAB Chair", "role": "CAB", "status": "Pending", "comments": "—", "decision_date": "—"},
    ]
    escalations = [
        {"from": "Compliance", "to": "CIO Office", "reason": "High gap count blocking sign-off", "date": "2026-05-18"},
    ]
    return {"approval_chain": chain, "escalations": escalations, "history": chain[:3]}


def build_historical_lineage(stage_key: str, detail: dict, release: dict) -> dict[str, Any]:
    s = seed("hl", stage_key, release["id"])
    impls = []
    for i in range(12):
        impls.append({
            "artifact_type": pick(seed("ht", i), ["Control", "Requirement", "Design", "Code Pattern", "Test Pack"]),
            "artifact_id": f"ART-{between(seed('hi', i), 100, 999)}",
            "application": pick(seed("ha", i), BANKING_APPS),
            "release": pick(seed("hr", i), ["REL-2025-Q4-NB", "REL-2025-Q3-MB", "REL-2024-Q2-PAY"]),
            "owner": pick(seed("ho", i), BANKING_OWNERS),
            "closure_date": (ANCHOR - timedelta(days=between(seed("hd", i), 60, 900))).strftime("%Y-%m-%d"),
            "result": pick(seed("hres", i), ["Closed", "Successful", "Closed with observations"]),
            "drill_id": f"history::{i}",
        })
    return {"implementations": impls, "total": len(impls)}


def build_control_reuse_repository(release: dict) -> dict[str, Any]:
    rows = []
    for i in range(15):
        s = seed("crr", release["id"], i)
        cid = f"APPSEC-{between(s, 1, 99):02d}"
        rows.append({
            "control_id": cid,
            "control_name": pick(s >> 2, ["MFA for privileged access", "Encryption at rest", "API rate limiting", "Session timeout"]),
            "applications_used": ", ".join(BANKING_APPS[:between(s >> 4, 2, 6)]),
            "reuse_score": f"{between(s >> 6, 68, 97)}%",
            "framework_mapping": pick(s >> 8, _FRAMEWORKS),
            "drill_id": cid,
        })
    return {"rows": rows}


def build_design_reuse_repository(release: dict) -> dict[str, Any]:
    rows = [
        {"pattern_name": "Zero Trust API Gateway", "architecture_type": "Microservices", "applications_used": "Net Banking, Mobile Banking, UPI",
         "approvals": 3, "success_rate": "98%", "drill_id": "pattern-zt-api"},
        {"pattern_name": "RAG Security Pipeline", "architecture_type": "AI/ML", "applications_used": "CRM, AI Assistant, CS Copilot",
         "approvals": 2, "success_rate": "96%", "drill_id": "pattern-rag-sec"},
        {"pattern_name": "Event-Driven Audit Bus", "architecture_type": "Integration", "applications_used": "Data Lake, Treasury, Cards",
         "approvals": 4, "success_rate": "99%", "drill_id": "pattern-audit-bus"},
    ]
    return {"rows": rows}


def build_code_reuse_repository(release: dict) -> dict[str, Any]:
    rows = [
        {"component": "Input Validation Library", "category": "Shared Library", "applications_used": 5, "language": "Java", "security_rating": "A"},
        {"component": "Audit Log SDK", "category": "Microservice", "applications_used": 4, "language": "Go", "security_rating": "A"},
        {"component": "Security Middleware", "category": "Middleware", "applications_used": 3, "language": "Java", "security_rating": "A-"},
        {"component": "API Gateway Pattern", "category": "Reference Implementation", "applications_used": 6, "language": "Kotlin", "security_rating": "A"},
    ]
    return {"rows": rows}


def build_test_pack_reuse_repository(release: dict) -> dict[str, Any]:
    rows = [
        {"test_pack": "PCI Regression Pack", "coverage": "PCI DSS 3.2.1", "applications_used": 4, "pass_rate": "99%"},
        {"test_pack": "Prompt Injection Tests", "coverage": "AI Governance", "applications_used": 3, "pass_rate": "97%"},
        {"test_pack": "UAT Sign-off Template", "coverage": "Retail Digital", "applications_used": 5, "pass_rate": "100%"},
    ]
    return {"rows": rows}


def enrich_audit_trail_full(rows: list[dict], stage_key: str) -> list[dict]:
    enriched = []
    for i, row in enumerate(rows):
        s = seed("audf", stage_key, i)
        enriched.append({
            **row,
            "timestamp": row.get("timestamp", row.get("date", "")),
            "user": row.get("actor", row.get("user", "")),
            "object": pick(s >> 2, ["Control Mapping", "Evidence Upload", "Approval", "Exception", "Framework"]),
            "before": pick(s >> 4, ["Draft", "Pending", "In Review", "Submitted"]),
            "after": pick(s >> 6, ["Approved", "Closed", "Accepted", "Remediated"]),
            "application": pick(s >> 8, BANKING_APPS),
            "framework": pick(s >> 10, _FRAMEWORKS),
        })
    return enriched
