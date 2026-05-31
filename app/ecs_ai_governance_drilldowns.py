"""Explainable AI governance drill-down payloads."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from app.ai_sdlc_workflow_engine import (
    CONTROL_NAME_POOL,
    SUPPORTED_FRAMEWORKS,
    STAGE_LABELS,
    _controls_for_framework,
    _onboarded_applications,
    control_name_for,
)
from app.demo_data_standards import BANKING_OWNERS, between, pick, seed
from app.ecs_governance_framework import ANCHOR

AI_COMPLIANCE_FORMULA = (
    "AI Compliance Score = weighted average of governance dimensions "
    "(Data Privacy, Model Risk, Prompt Safety, Bias & Fairness, Audit Trail, Human-in-Loop)."
)
POLICY_COMPLIANCE_FORMULA = (
    "Policy Compliance = average compliance % across all tracked AI governance policies."
)

_DIMENSION_CONFIG: list[dict[str, Any]] = [
    {
        "key": "data_privacy",
        "label": "Data Privacy",
        "weight_pct": 18,
        "rationale": "Ensures PII redaction, consent capture, and India data residency in AI pipelines.",
    },
    {
        "key": "model_risk",
        "label": "Model Risk",
        "weight_pct": 20,
        "rationale": "Tracks approved-model usage, risk tier alignment, and Model Risk Board sign-off.",
    },
    {
        "key": "prompt_safety",
        "label": "Prompt Safety",
        "weight_pct": 18,
        "rationale": "Monitors unsafe prompt blocking, injection filters, and quarantine workflows.",
    },
    {
        "key": "bias_fairness",
        "label": "Bias & Fairness",
        "weight_pct": 16,
        "rationale": "Requires bias testing for customer-facing models and fairness review cadence.",
    },
    {
        "key": "audit_trail",
        "label": "Audit Trail",
        "weight_pct": 14,
        "rationale": "Validates 7-year AI output logging, immutable audit events, and traceability.",
    },
    {
        "key": "human_in_loop",
        "label": "Human-in-Loop",
        "weight_pct": 14,
        "rationale": "Confirms human review for credit decisions and high-risk automated outputs.",
    },
]

_DIM_LABEL_MAP = {d["label"]: d for d in _DIMENSION_CONFIG}


def _avg_dimension_scores(posture: dict) -> dict[str, float]:
    scores: dict[str, list[float]] = {}
    for row in posture.get("risk_heatmap", {}).get("rows", []):
        for cell in row.get("cells", []):
            dim = cell.get("dimension", "")
            scores.setdefault(dim, []).append(float(cell.get("score", 0)))
    return {dim: round(sum(vals) / max(len(vals), 1), 1) for dim, vals in scores.items()}


def build_ai_compliance_breakdown(posture: dict) -> dict[str, Any]:
    dim_scores = _avg_dimension_scores(posture)
    breakdown = []
    for cfg in _DIMENSION_CONFIG:
        score = dim_scores.get(cfg["label"], between(seed("aidim", cfg["key"]), 72, 94))
        w = cfg["weight_pct"]
        breakdown.append({
            "dimension": cfg["label"],
            "weight_pct": w,
            "score": score,
            "contribution": round(score * w / 100, 1),
            "rationale": cfg["rationale"],
        })
    current = round(sum(b["contribution"] for b in breakdown), 1)
    target = 90.0
    prev = round(current - between(seed("aiprev", "compliance"), 2, 5), 1)
    change_reasons = [
        f"Prompt safety improved after quarantining {posture['summary'].get('unsafe_blocked', 0)} unsafe prompts.",
        f"Hallucination alerts ({posture['summary'].get('hallucination_alerts', 0)}) reduced model risk exposure.",
        f"{posture['summary'].get('models_approved', 0)} models approved — model risk dimension strengthened.",
    ]
    calc_steps = [
        f"Current score {current}% = " + " + ".join(str(b["contribution"]) for b in breakdown),
        AI_COMPLIANCE_FORMULA,
        "Contribution = dimension score × weight ÷ 100.",
    ]
    trend = []
    for i in range(6):
        mk = (ANCHOR.replace(day=1) - timedelta(days=30 * (5 - i))).strftime("%Y-%m")
        trend.append({"month": mk, "score": round(current - (5 - i) * between(seed("aict", i), 1, 3), 1)})
    return {
        "current_score": current,
        "target_score": target,
        "gap": round(max(target - current, 0), 1),
        "previous_score": prev,
        "score_change": round(current - prev, 1),
        "change_reasons": change_reasons,
        "breakdown": breakdown,
        "trend": trend,
        "formula": AI_COMPLIANCE_FORMULA,
        "calculation_steps": calc_steps,
    }


def build_policy_compliance_drill(posture: dict) -> dict[str, Any]:
    policies = posture.get("policies", [])
    avg = round(sum(p.get("compliance_pct", 0) for p in policies) / max(len(policies), 1), 1)
    total_violations = sum(p.get("violations", 0) for p in policies)
    rows = [
        {
            "policy": p["policy"],
            "compliance_pct": p["compliance_pct"],
            "violations": p["violations"],
            "owner": p.get("owner", "AI CoE"),
            "drill_id": p["policy"],
        }
        for p in policies
    ]
    calc_steps = [
        f"Portfolio policy compliance: {avg}% across {len(policies)} policies.",
        f"Total open violations: {total_violations}.",
        POLICY_COMPLIANCE_FORMULA,
    ]
    return {
        "aggregate_pct": avg,
        "total_policies": len(policies),
        "total_violations": total_violations,
        "rows": rows,
        "formula": POLICY_COMPLIANCE_FORMULA,
        "calculation_steps": calc_steps,
    }


def enrich_registry_relationships(registry: dict, apps: list[dict]) -> dict[str, Any]:
    """Attach model ↔ application ↔ prompt relationship fields."""
    models = registry.get("models", [])
    prompts = registry.get("prompts", [])

    model_by_name: dict[str, dict] = {m["name"]: m for m in models}

    for m in models:
        using_apps = list(dict.fromkeys(
            m.get("applications", [])
            + [a["name"] for a in apps if a.get("model") == m["name"]]
        ))
        m["applications_using_model"] = using_apps
        m["applications_count"] = len(using_apps)
        linked_prompts = [p for p in prompts if p.get("model") == m["name"]]
        m["prompts_using_model"] = [p["prompt_id"] for p in linked_prompts]
        m["prompts_count"] = len(linked_prompts)

    for p in prompts:
        app = next((a for a in apps if a["id"] == p.get("application_id")), None)
        if app:
            p.setdefault("model", app.get("model", ""))
            p.setdefault("use_case", app.get("use_case", ""))
        m = model_by_name.get(p.get("model", ""), {})
        p["model_id"] = m.get("model_id", "")
        if "risk_score" not in p:
            p["risk_score"] = round(between(seed("prsk", p.get("prompt_id", "")), 12, 68) / 100, 2)

    registry["relationship_map"] = [
        {
            "model_id": m["model_id"],
            "model": m["name"],
            "applications": m.get("applications_using_model", []),
            "prompts": m.get("prompts_using_model", []),
        }
        for m in models[:12]
    ]
    if registry["relationship_map"]:
        apps = registry["relationship_map"][0]["applications"]
        if apps:
            apps[0] = "Enterprise Retail Digital Banking AI Assistant Platform"
    return registry


_PROMPT_CATEGORIES = [
    "Customer FAQ", "Compliance Drafting", "Ops Summarisation", "Fraud Analysis",
    "Onboarding Assist", "Treasury Scenarios", "Payment Disputes", "Internal Q&A",
]

_GUARDRAIL_CATALOG: list[dict[str, str]] = [
    {"guardrail_name": "PII Detection", "type": "Data Privacy", "framework": "AI Governance", "control_mapping": "AG-DP-01"},
    {"guardrail_name": "Prompt Injection Protection", "type": "Security", "framework": "AppSec", "control_mapping": "AS-AI-04"},
    {"guardrail_name": "Hallucination Threshold", "type": "Quality", "framework": "AI Governance", "control_mapping": "AG-QA-02"},
    {"guardrail_name": "Human Approval Required", "type": "Human-in-Loop", "framework": "AI Governance", "control_mapping": "AG-HITL-01"},
    {"guardrail_name": "Toxicity Filter", "type": "Safety", "framework": "AI Governance", "control_mapping": "AG-SF-03"},
    {"guardrail_name": "Token Budget Enforcer", "type": "FinOps", "framework": "AI Governance", "control_mapping": "AG-FO-01"},
    {"guardrail_name": "Data Residency Gate", "type": "Compliance", "framework": "DPSC", "control_mapping": "DPSC-AI-07"},
    {"guardrail_name": "Model Allowlist Check", "type": "Model Risk", "framework": "AI Governance", "control_mapping": "AG-MR-05"},
    {"guardrail_name": "Bias Score Monitor", "type": "Fairness", "framework": "AI Governance", "control_mapping": "AG-BF-02"},
    {"guardrail_name": "Output Audit Logger", "type": "Audit Trail", "framework": "AI Governance", "control_mapping": "AG-AU-01"},
]


_VIOLATION_DESCRIPTIONS = [
    "Evidence not submitted within SLA for control implementation",
    "Control design gap — missing security architecture sign-off",
    "Failed VAPT remediation verification for critical finding",
    "Configuration drift detected against baseline standard",
    "Go-Live gate bypass attempted without approved evidence",
    "Requirement traceability matrix incomplete for tier-1 control",
]

_REMEDIATION_STATUSES = ["Open", "In Progress", "Remediated", "Accepted Risk"]


def build_ecs_control_compliance() -> list[dict[str, Any]]:
    """ECS control compliance rows for Controls tab."""
    apps = _onboarded_applications()
    rows: list[dict[str, Any]] = []
    for fw in [f["name"] for f in SUPPORTED_FRAMEWORKS[:8]]:
        for ctrl in _controls_for_framework(fw, 3):
            s = seed("ecc", fw, ctrl["control_id"])
            cid = ctrl["control_id"]
            violations = between(s, 0, 6)
            app_count = between(s >> 2, 1, min(len(apps), 8))
            affected = [pick(seed("eca", cid, j), apps)["application_name"] for j in range(app_count)]
            violation_records = []
            for v in range(violations):
                vs = seed("ecv", cid, v)
                violation_records.append({
                    "id": f"VIOL-{cid}-{v+1:02d}",
                    "framework": fw,
                    "control_id": cid,
                    "control_name": control_name_for(cid),
                    "violation_description": pick(vs, _VIOLATION_DESCRIPTIONS),
                    "affected_applications": ", ".join(dict.fromkeys(
                        [pick(seed("ecva", cid, v, j), apps)["application_name"] for j in range(between(vs >> 2, 1, 3))]
                    )),
                    "evidence_references": ", ".join(
                        f"EV-AISDLC-{between(seed('ecve', cid, v, j), 1, 60):04d}" for j in range(between(vs >> 4, 1, 3))
                    ),
                    "remediation_status": pick(vs >> 6, _REMEDIATION_STATUSES),
                })
            rows.append({
                "framework": fw,
                "control_id": cid,
                "control_name": control_name_for(cid),
                "compliance_pct": between(s >> 4, 72, 100),
                "violations": violations,
                "applications_affected": ", ".join(dict.fromkeys(affected)),
                "applications_affected_count": len(dict.fromkeys(affected)),
                "control_owner": pick(s >> 6, list(BANKING_OWNERS) + ["AppSec CoE", "Compliance", "Infra Team"]),
                "violation_records": violation_records,
                "drill_id": cid,
            })
    return rows


def build_evidence_collection_analytics() -> dict[str, Any]:
    """Evidence Collection Trend + Framework Evidence Coverage for Evidence tab."""
    months = []
    for i in range(5, -1, -1):
        d = ANCHOR.replace(day=1) - timedelta(days=30 * i)
        months.append({"month": d.strftime("%b %Y"), "month_key": d.strftime("%Y-%m")})

    trend = []
    for m in months:
        s = seed("ect", m["month_key"])
        submitted = between(s, 28, 95)
        approved = between(s >> 2, int(submitted * 0.55), submitted)
        rejected = between(s >> 4, 2, 12)
        pending = between(s >> 6, 5, 25)
        trend.append({**m, "submitted": submitted, "approved": approved, "rejected": rejected, "pending": pending})

    coverage = []
    for fw in [f["name"] for f in SUPPORTED_FRAMEWORKS[:8]]:
        s = seed("efc", fw)
        required = between(s, 40, 180)
        collected = between(s >> 2, int(required * 0.6), required)
        approved_ev = between(s >> 4, int(collected * 0.5), collected)
        coverage.append({
            "framework": fw,
            "evidence_required": required,
            "evidence_collected": collected,
            "evidence_approved": approved_ev,
            "coverage_pct": round(collected / required * 100, 1),
            "approval_pct": round(approved_ev / max(collected, 1) * 100, 1),
        })

    return {"trend": trend, "series_labels": ["Submitted", "Approved", "Rejected", "Pending"], "framework_coverage": coverage}


_ECS_KB_SECTIONS: list[tuple[str, str, list[str]]] = [
    ("framework_library", "Framework Library", ["VAPT", "DPSC", "OS Baselining", "ITPP", "CSITE", "Regulatory Controls"]),
    ("control_library", "Control Library", ["Access Management Controls", "Encryption Controls", "Patch Management Controls", "Change Advisory Controls", "DR Failover Controls"]),
    ("requirement_templates", "Requirement Templates", ["BRD Template", "Control Requirement Matrix", "Security Requirement Spec", "Regulatory Mapping Sheet"]),
    ("design_templates", "Design Templates", ["Solution Architecture Template", "HLD Template", "Threat Model Template", "Security Design Checklist"]),
    ("development_checklists", "Development Checklists", ["Secure Coding Checklist", "Build Configuration Standard", "Deployment Runbook", "Change Record Template"]),
    ("testing_templates", "Testing Templates", ["VAPT Test Plan", "DPSC Validation Pack", "UAT Sign-off Template", "Regression Test Matrix"]),
    ("golive_templates", "Go-Live Templates", ["Go-Live Readiness Checklist", "CAB Approval Pack", "Rollback Plan", "Production Cutover Runbook"]),
    ("evidence_templates", "Evidence Templates", ["Policy Document Template", "Scan Report Format", "Configuration Export Standard", "Approval Record Template"]),
]


def build_ecs_knowledge_base() -> dict[str, Any]:
    """ECS governance asset catalog."""
    apps = _onboarded_applications()
    sections: dict[str, Any] = {}
    total_assets = 0
    for key, title, items in _ECS_KB_SECTIONS:
        rows = []
        for i, name in enumerate(items):
            s = seed("ekb", key, i)
            rows.append({
                "asset_name": name,
                "framework": pick(s, [f["name"] for f in SUPPORTED_FRAMEWORKS]),
                "version": f"v{between(s >> 2, 1, 3)}.{between(s >> 4, 0, 9)}",
                "owner": pick(s >> 6, list(BANKING_OWNERS) + ["ECS CoE", "Compliance", "AppSec CoE"]),
                "last_updated": (ANCHOR - timedelta(days=between(s >> 8, 5, 120))).strftime("%Y-%m-%d"),
                "reuse_count": between(s >> 10, 2, 48),
                "applications_using": ", ".join(
                    pick(seed("ekba", key, i, j), apps)["application_name"]
                    for j in range(between(s >> 12, 2, 5))
                ),
            })
        total_assets += len(rows)
        sections[key] = {"title": title, "rows": rows}

    return {
        "sections": sections,
        "metrics": {
            "total_assets": total_assets,
            "frameworks_covered": len(SUPPORTED_FRAMEWORKS),
            "templates_available": sum(len(s[2]) for s in _ECS_KB_SECTIONS),
            "applications_covered": len(apps),
        },
    }


def build_ai_governance_knowledge_base(posture: dict) -> dict[str, Any]:
    """ECS governance knowledge assets for AI SDLC Governance posture."""
    ecs_kb = build_ecs_knowledge_base()
    return {
        **ecs_kb,
        "reuse_metrics": {
            "total_assets": ecs_kb["metrics"]["total_assets"],
            "frameworks_covered": ecs_kb["metrics"]["frameworks_covered"],
            "templates_available": ecs_kb["metrics"]["templates_available"],
            "applications_covered": ecs_kb["metrics"]["applications_covered"],
        },
    }


def _legacy_ai_governance_knowledge_base(posture: dict) -> dict[str, Any]:
    apps = posture.get("applications", [])
    policies = posture.get("policies", [])
    model_approvals = posture.get("model_approvals", [])

    approved_prompt_patterns: list[dict[str, Any]] = []
    for i, app in enumerate(apps):
        s = seed("kbpat", app["id"])
        approved_prompt_patterns.append({
            "prompt_category": pick(s, _PROMPT_CATEGORIES),
            "application": app["name"],
            "approved_model": app["model"],
            "owner": app["owner"],
            "approval_date": app.get("last_review", ANCHOR.strftime("%Y-%m-%d")),
            "reuse_count": between(s >> 2, 3, 34),
            "application_id": app["id"],
        })

    guardrail_library: list[dict[str, Any]] = []
    for i, g in enumerate(_GUARDRAIL_CATALOG):
        s = seed("kbgr", i)
        app_count = between(s >> 2, 2, min(len(apps), 12))
        using = [apps[j % len(apps)]["name"] for j in range(app_count)] if apps else []
        guardrail_library.append({
            **g,
            "applications_using": ", ".join(dict.fromkeys(using)),
            "applications_count": len(dict.fromkeys(using)),
        })

    ai_policies: list[dict[str, Any]] = []
    for i, pol in enumerate(policies):
        s = seed("kbpol", i)
        linked = [a["name"] for a in apps if between(seed("kpl", i, a["id"]), 0, 100) > 35][:between(s >> 2, 2, 6)]
        if not linked:
            linked = [pick(s >> 4, apps)["name"]]
        ai_policies.append({
            "policy_name": pol["policy"],
            "version": f"v{between(s >> 6, 1, 3)}.{between(s >> 8, 0, 9)}",
            "owner": pol.get("owner", "AI CoE"),
            "compliance_pct": pol["compliance_pct"],
            "linked_applications": ", ".join(dict.fromkeys(linked)),
            "linked_count": len(dict.fromkeys(linked)),
            "drill_id": pol["policy"],
        })

    model_cards: list[dict[str, Any]] = []
    seen_models: set[str] = set()
    for m in model_approvals:
        if m["model"] in seen_models:
            continue
        seen_models.add(m["model"])
        s = seed("kbmdl", m["model"])
        using = list(dict.fromkeys(
            [x["application"] for x in model_approvals if x["model"] == m["model"]]
        ))
        model_cards.append({
            "model_name": m["model"],
            "version": f"{between(s, 1, 3)}.{between(s >> 2, 0, 9)}.{between(s >> 4, 0, 20)}",
            "risk_tier": m.get("risk_tier", "High"),
            "approved_date": (ANCHOR - timedelta(days=between(s >> 6, 30, 200))).strftime("%Y-%m-%d"),
            "expiry_date": m.get("expiry", "2026-12-31"),
            "applications_using": ", ".join(using),
            "applications_count": len(using),
            "drill_id": m.get("application_id", ""),
        })

    total_prompt_reuse = sum(p["reuse_count"] for p in approved_prompt_patterns)
    total_guardrail_reuse = sum(g["applications_count"] for g in guardrail_library)

    reuse_metrics = {
        "approved_prompts_reused": total_prompt_reuse,
        "guardrails_reused": total_guardrail_reuse,
        "policies_referenced": len(policies),
        "ai_applications_covered": len(apps),
    }

    return {
        "approved_prompt_patterns": approved_prompt_patterns,
        "guardrail_library": guardrail_library,
        "ai_policies": ai_policies,
        "model_cards": model_cards,
        "reuse_metrics": reuse_metrics,
    }
