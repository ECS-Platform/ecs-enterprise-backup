"""Reusable ECS Governance framework — navigation, data enrichment, reuse, control 360."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from urllib.parse import urlencode

from app.demo_data_standards import BANKING_APPLICATIONS, between, pick, seed
from app.ecs_sdlc_stage_dashboard import STAGE_KEY_TO_SLUG, sdlc_stage_path

ANCHOR = date(2026, 5, 28)

STAGE_KEYS = ("requirement", "design", "development", "testing", "go-live")

STAGE_LABELS = {
    "requirement": "Requirement Governance",
    "design": "Design Governance",
    "development": "Development Governance",
    "testing": "Testing Governance",
    "go-live": "Go-Live Governance",
}

METRIC_TAB_MAP: dict[str, str] = {
    "framework": "framework-coverage",
    "framework_coverage_drill": "framework-coverage",
    "controls": "control-coverage",
    "control": "control-coverage",
    "control_coverage_drill": "control-coverage",
    "evidence": "evidence-coverage",
    "evidence_coverage_drill": "evidence-coverage",
    "gaps": "open-gaps",
    "gaps_drill": "open-gaps",
    "readiness_breakdown": "readiness",
    "status_timeline": "status",
    "approvals_drill": "approvals",
    "historical_lineage": "knowledge-reuse",
    "control_reuse_repo": "knowledge-reuse",
    "design_reuse_repo": "knowledge-reuse",
    "code_reuse_repo": "knowledge-reuse",
    "test_pack_reuse_repo": "knowledge-reuse",
    "documents": "knowledge-reuse",
    "document": "knowledge-reuse",
    "audit": "audit-trail",
    "knowledge_reuse": "knowledge-reuse",
    "readiness": "readiness",
    "reuse_modal": "knowledge-reuse",
}

REUSE_TYPES = ("requirement", "design", "testing", "control")

BANKING_APPS = [
    "Net Banking", "Mobile Banking", "UPI", "CRM", "Data Lake",
    "Treasury", "Cards", "AI Assistant", "Customer Service Copilot",
]

DOMAINS = ["Retail Digital", "Wholesale Banking", "Payments", "Risk & Compliance", "AI CoE"]


def build_stage_workspace_url(
    stage_key: str,
    release_id: str,
    *,
    tab: str = "",
    metric: str = "",
    application_id: str = "",
    framework_id: str = "",
    document_id: str = "",
    control_id: str = "",
    role: str = "",
    user: str = "",
) -> str:
    """Canonical stage workspace URL preserving navigation context."""
    tab = tab or METRIC_TAB_MAP.get(metric, "overview")
    params: dict[str, str] = {"release": release_id}
    if tab and tab != "overview":
        params["tab"] = tab
    if application_id:
        params["applicationId"] = application_id
    if framework_id:
        params["frameworkId"] = framework_id
    if document_id:
        params["documentId"] = document_id
    if control_id:
        params["controlId"] = control_id
    if role:
        params["role"] = role
    if user:
        params["user"] = user
    return f"{sdlc_stage_path(stage_key)}?{urlencode(params)}"


def build_navigation_context(
    stage_key: str,
    release: dict,
    *,
    metric: str = "",
    tab: str = "",
    application_id: str = "",
    framework_id: str = "",
    document_id: str = "",
    control_id: str = "",
) -> dict[str, Any]:
    tab = tab or METRIC_TAB_MAP.get(metric, "overview")
    return {
        "releaseId": release["id"],
        "stageId": stage_key,
        "stageLabel": STAGE_LABELS.get(stage_key, stage_key),
        "applicationId": application_id or release.get("application", ""),
        "frameworkId": framework_id,
        "selectedDocument": document_id,
        "selectedControl": control_id,
        "tab": tab,
        "stage_link": build_stage_workspace_url(
            stage_key, release["id"], tab=tab,
            application_id=application_id, framework_id=framework_id,
            document_id=document_id, control_id=control_id,
        ),
    }


def recalculate_framework_coverage(fw_rows: list[dict]) -> tuple[float, float, float]:
    """Return (framework_coverage_pct, control_coverage_pct, evidence_coverage_pct)."""
    if not fw_rows:
        return 0.0, 0.0, 0.0
    fw_scores: list[float] = []
    all_controls: list[dict] = []
    all_evidence: list[dict] = []
    for row in fw_rows:
        controls = row.get("control_records", [])
        evidence = row.get("evidence_records", [])
        all_controls.extend(controls)
        all_evidence.extend(evidence)
        total = max(len(controls), 1)
        covered = sum(1 for c in controls if c.get("status") == "Covered")
        mapped = sum(1 for c in controls if c.get("mapped_requirement") or c.get("control_id"))
        ev_attached = sum(c.get("evidence_count", 0) for c in controls)
        ev_approved = sum(1 for e in evidence if e.get("status") == "Approved")
        ev_total = max(len(evidence), 1)
        ctrl_pct = covered / total * 100
        map_pct = mapped / total * 100
        ev_pct = ev_approved / ev_total * 100
        attach_pct = min(ev_attached / max(total * 2, 1) * 100, 100)
        fw_scores.append(round(ctrl_pct * 0.35 + map_pct * 0.25 + ev_pct * 0.25 + attach_pct * 0.15, 1))
    ctrl_cov = round(sum(1 for c in all_controls if c.get("status") == "Covered") / max(len(all_controls), 1) * 100, 1)
    ev_cov = round(sum(1 for e in all_evidence if e.get("status") == "Approved") / max(len(all_evidence), 1) * 100, 1)
    fw_cov = round(sum(fw_scores) / len(fw_scores), 1)
    return fw_cov, ctrl_cov, ev_cov


def enrich_framework_control_row(control: dict, release: dict, framework: str, stage_key: str) -> dict[str, Any]:
    s = seed("fwctrl", control.get("control_id", ""), release.get("id", ""), stage_key)
    apps = BANKING_APPS[:between(s >> 2, 4, 9)]
    return {
        **control,
        "control_name": control.get("control_description", "")[:48],
        "control_objective": pick(s >> 4, [
            "Protect customer data in transit and at rest",
            "Ensure privileged access is logged and reviewed",
            "Validate AI outputs against policy guardrails",
            "Maintain segregation of duties for payment flows",
        ]),
        "requirement_source": f"REQ-{release['id'].split('-')[-1]}-{between(s, 101, 299)}",
        "design_source": f"DSG-{between(s >> 6, 10, 99):03d}",
        "development_source": f"DEV-{control.get('control_id', 'CTRL')}-IMPL",
        "testing_source": f"TC-{between(s >> 8, 1000, 9999)}",
        "evidence_count": control.get("evidence_count", between(s >> 10, 1, 6)),
        "observations": control.get("findings_count", 0) + between(s >> 12, 0, 3),
        "exceptions": control.get("exceptions_count", 0),
        "audit_findings": between(s >> 14, 0, 2),
        "applications_using": apps,
        "reuse_count": between(s >> 16, 3, 24),
        "mapped_requirement": f"REQ-{release['id'].split('-')[-1]}-{between(s, 101, 299)}",
        "last_review": (ANCHOR - timedelta(days=between(s >> 18, 7, 90))).strftime("%Y-%m-%d"),
    }


def build_control_360(control: dict, release: dict, stage_key: str, framework: str = "") -> dict[str, Any]:
    s = seed("c360", control.get("control_id", ""), release.get("id", ""))
    fw = framework or control.get("framework", "AppSec")
    enriched = enrich_framework_control_row(control, release, fw, stage_key)
    return {
        "profile": enriched,
        "lineage": {
            "requirement": enriched["requirement_source"],
            "design": enriched["design_source"],
            "development": enriched["development_source"],
            "testing": enriched["testing_source"],
            "evidence_ids": [f"EVD-{control.get('control_id', 'X')}-{i+1:02d}" for i in range(enriched["evidence_count"])],
        },
        "applications": enriched["applications_using"],
        "observation_history": [
            {"obs_id": f"OBS-{between(seed('o', s, i), 100, 999)}", "application": pick(seed("oa", s, i), BANKING_APPS),
             "severity": pick(seed("os", s, i), ["High", "Medium", "Low"]), "status": pick(seed("ost", s, i), ["Closed", "Open"]),
             "date": (ANCHOR - timedelta(days=between(seed("od", s, i), 30, 900))).strftime("%Y-%m-%d")}
            for i in range(between(s >> 4, 2, 5))
        ],
        "reuse_score": round(between(s >> 6, 62, 96) + (s % 7) / 10, 1),
        "approval_history": [
            {"authority": pick(seed("ap", s, i), ["AppSec CoE", "Compliance Head", "Internal Audit", "CAB Chair"]),
             "date": (ANCHOR - timedelta(days=between(seed("apd", s, i), 7, 180))).strftime("%Y-%m-%d"),
             "status": "Approved"}
            for i in range(3)
        ],
    }


def build_reuse_modal_payload(
    reuse_type: str,
    source: dict,
    release: dict,
    stage_key: str = "requirement",
) -> dict[str, Any]:
    s = seed("reuse", reuse_type, source.get("doc_id") or source.get("control_id", ""), release.get("id", ""))
    label = {"requirement": "Requirement", "design": "Design", "testing": "Test Pack", "control": "Control"}.get(reuse_type, "Artifact")
    return {
        "reuse_type": reuse_type,
        "source_id": source.get("doc_id") or source.get("control_id") or source.get("title", ""),
        "source_title": source.get("title") or source.get("control_id") or label,
        "target_applications": BANKING_APPS,
        "target_releases": [release["name"], "REL-2025-Q4-NB", "REL-2025-Q3-MB", "REL-2026-Q1-PAY"],
        "target_controls": [f"APPSEC-{between(seed('tc', s, i), 1, 99):02d}" for i in range(10)],
        "target_frameworks": ["PCI DSS", "DPSC", "AppSec", "VAPT", "AI Governance"],
        "target_domains": DOMAINS,
        "clone_options": [
            {"id": "clone", "label": "Clone", "description": "Copy artifact metadata only"},
            {"id": "clone_mapping", "label": "Clone With Mapping", "description": "Include control-to-framework mappings"},
            {"id": "clone_evidence", "label": "Clone With Evidence", "description": "Attach approved evidence references"},
            {"id": "clone_approval", "label": "Clone With Approval Trail", "description": "Preserve approval chain and audit comments"},
        ],
        "impact_analysis": {
            "applications_affected": between(s >> 2, 2, 6),
            "controls_remapped": between(s >> 4, 4, 18),
            "evidence_reused": between(s >> 6, 3, 12),
            "estimated_effort_days": between(s >> 8, 2, 10),
            "risk_delta": pick(s >> 10, ["Low", "Low", "Medium"]),
        },
        "preview_package_id": f"PKG-{reuse_type.upper()[:3]}-{release['id'].split('-')[-1]}-{between(s >> 12, 100, 999)}",
    }


def build_stage_knowledge_base(stage_key: str, release: dict, detail: dict) -> dict[str, Any]:
    s = seed("stkb", stage_key, release["id"])
    return {
        "approved_designs": [
            {"id": f"DSG-{i+1:03d}", "title": pick(seed("ad", s, i), ["Zero Trust API Gateway", "RAG Security Pipeline", "Event-Driven Audit Bus"]),
             "application": pick(seed("ada", s, i), BANKING_APPS), "status": "Approved"}
            for i in range(8)
        ],
        "approved_controls": [
            {"control_id": f"APPSEC-{between(seed('ac', s, i), 1, 99):02d}", "framework": pick(seed("acf", s, i), ["PCI DSS", "AppSec", "DPSC"]),
             "applications": between(seed("aca", s, i), 2, 6)}
            for i in range(10)
        ],
        "reusable_patterns": [
            {"pattern": pick(seed("rp", s, i), ["Input Validation Library", "Audit Log SDK", "MFA Enforcement Module", "Prompt Guard Middleware"]),
             "used_in": ", ".join(BANKING_APPS[:between(seed("rpu", s, i), 2, 5)]), "reuse_count": between(seed("rpc", s, i), 3, 18)}
            for i in range(8)
        ],
        "lessons_learned": [
            "Reuse approved design patterns when scope unchanged — reduces audit findings by 40%.",
            "Link evidence to control ID at development gate — accelerates auditor sampling.",
            "Cite historical closure references in CAB package — improves first-pass approval.",
            pick(seed("ll", s), ["Incomplete VAPT scope", "Stale DR evidence", "Missing AI model approval"]) + " — address via enterprise reference implementation.",
        ],
        "audit_learnings": [
            {"finding": "Repeat observation on session timeout", "root_cause": "Config drift across regions", "fix": "Centralized policy template"},
            {"finding": "Evidence staleness > 90 days", "root_cause": "Manual collection process", "fix": "Automated ECS scheduler pull"},
        ],
        "vapt_learnings": [
            {"scenario": "Prompt injection on AI Assistant", "result": "Closed", "retest": "2026-04-12"},
            {"scenario": "IDOR on Net Banking API", "result": "Remediated", "retest": "2026-03-28"},
        ],
        "control_libraries": [
            {"library": "Platform Security SDK", "controls": 24, "apps": 6},
            {"library": "Payment Controls Pack", "controls": 18, "apps": 4},
        ],
        "reusable_test_packs": [
            {"pack": "PCI Regression Pack", "pass_rate": "99%", "apps": 4},
            {"pack": "Prompt Injection Tests", "pass_rate": "97%", "apps": 3},
            {"pack": "UAT Sign-off Template", "pass_rate": "100%", "apps": 5},
        ],
        "stage_artifacts": len(detail.get("documents", [])),
        "historical_depth_years": 5,
    }


def enrich_audit_trail_rows(rows: list[dict], stage_key: str, release: dict) -> list[dict]:
    enriched = []
    for i, row in enumerate(rows):
        s = seed("auden", stage_key, release["id"], i)
        enriched.append({
            **row,
            "date": row.get("timestamp", row.get("date", "")),
            "user": row.get("actor", row.get("user", "")),
            "role": pick(s >> 2, ["App Owner", "Auditor", "Compliance", "AppSec CoE", "CIO", "Model Risk"]),
            "application": pick(s >> 4, BANKING_APPS),
            "stage": STAGE_LABELS.get(stage_key, stage_key),
            "control": f"CTRL-{between(s >> 6, 1, 99):02d}",
            "evidence": f"EVD-{between(s >> 8, 100, 999)}",
            "result": pick(s >> 10, ["Approved", "Submitted", "Closed", "Remediated", "Accepted"]),
        })
    return enriched


def extend_stage_document_tabs(tabs: dict[str, Any], stage_key: str, stage_kb: dict[str, Any], doc: dict, release: dict, s: int) -> dict[str, Any]:
    """Stage-specific document viewer tabs beyond the base set."""
    from app.ecs_demo_remediation import extend_document_tabs

    tabs = extend_document_tabs(tabs, stage_key, stage_kb, doc, release, s)
    hist = tabs.get("historical_reuse", {}).get("rows", [])
    tabs["audit_history"] = {
        "rows": [
            {"date": (ANCHOR - timedelta(days=between(seed("dah", s, i), 30, 800))).strftime("%Y-%m-%d"),
             "user": pick(seed("dau", s, i), ["S. Nair (Auditor)", "R. Mehta", "AppSec CoE"]),
             "action": pick(seed("daa", s, i), ["Evidence Approved", "Control Mapping", "Observation Closed"]),
             "application": pick(seed("dap", s, i), BANKING_APPS), "result": "Approved"}
            for i in range(min(12, max(len(hist), 6)))
        ],
    }
    tabs["reusable_controls"] = {"rows": stage_kb.get("approved_controls", [])[:8]}
    if stage_key == "requirement":
        tabs["overview"]["control_objective"] = pick(s >> 2, [
            "Ensure security and compliance controls are defined before design begins.",
            "Map regulatory obligations to testable requirements across impacted applications.",
        ])
        tabs["overview"]["control_interpretation"] = pick(s >> 4, [
            "Applies to all tier-1 retail channels including Net Banking and Mobile Banking.",
            "Includes AI-assisted flows where customer PII may be processed.",
        ])
    elif stage_key == "design":
        for key, label in [
            ("architecture_patterns", "Architecture Patterns"),
            ("reference_designs", "Reference Designs"),
            ("historical_implementations", "Historical Implementations"),
            ("reusable_components", "Reusable Design Components"),
            ("applications_using", "Applications Using Design"),
            ("approval_history", "Approval History"),
            ("audit_findings", "Audit Findings"),
            ("knowledge_base", "Knowledge Base"),
        ]:
            if key == "architecture_patterns":
                tabs[key] = {"rows": stage_kb.get("reusable_patterns", [])}
            elif key == "reference_designs":
                tabs[key] = {"rows": stage_kb.get("approved_designs", [])}
            elif key == "knowledge_base":
                tabs[key] = {"items": stage_kb.get("lessons_learned", [])}
            else:
                tabs[key] = {"rows": hist[:6] if hist else stage_kb.get("approved_designs", [])[:4]}
    elif stage_key == "development":
        for key in ("reference_implementations", "control_libraries", "shared_components", "secure_coding_refs",
                    "cicd_evidence", "sast_results", "dast_results", "dependency_analysis", "deployment_history", "tech_knowledge_base"):
            tabs[key] = {"rows": stage_kb.get("control_libraries", []) if "library" in key else stage_kb.get("reusable_patterns", [])[:6]}
    elif stage_key == "testing":
        for key in ("reusable_test_packs", "regression_packs", "historical_executions", "related_applications",
                    "vapt_results", "uat_results", "ai_validation_results", "defect_leakage", "production_defects"):
            tabs[key] = {"rows": stage_kb.get("reusable_test_packs", [])}
    return tabs
