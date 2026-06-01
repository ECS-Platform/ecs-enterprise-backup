"""Rich governance document artifacts for AI & SDLC Governance demo viewer."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from modules.ai_sdlc.engines.ai_sdlc_knowledge_repository import (
    build_design_knowledge,
    build_development_knowledge,
    build_document_viewer_tabs,
    build_golive_knowledge,
    build_requirement_knowledge,
    build_testing_knowledge,
)
from modules.shared.utils.demo_data_standards import BANKING_APPLICATIONS, BANKING_OWNERS, between, pick, seed
from modules.enterprise_grc.engines.ecs_demo_remediation import extend_document_tabs
from modules.enterprise_grc.engines.ecs_governance_framework import extend_stage_document_tabs

ANCHOR = date(2026, 5, 28)

_DESIGN_APPS = ["Net Banking", "Mobile Banking", "CRM", "Data Lake", "Payments"]

_EVIDENCE_TYPES = [
    "Screenshot", "Architecture Diagram", "Configuration Export", "Scan Report",
    "Approval Email", "CAB Minutes", "Test Report", "Deployment Log",
]

_REQ_CATEGORIES = {
    "Control objective": "control_objective",
    "Regulatory expectation": "regulatory_expectation",
    "Audit requirement document": "audit_requirement",
    "Generated checklist": "generated_checklist",
    "Similar controls from previous audits": "similar_controls",
    "Reference implementations": "reference_implementations",
}

_DESIGN_CATEGORIES = {
    "Design submission template": "design_submission",
    "Sample approved designs from historical observations": "historical_designs",
    "Design review comments": "review_comments",
    "Design approval workflow": "approval_workflow",
}

_DEV_CATEGORIES = {
    "Development implementation plan": "implementation_plan",
    "Coding standards": "coding_standards",
    "Secure coding checklist": "secure_coding_checklist",
    "Developer evidence repository": "dev_evidence_repo",
}

_TEST_CATEGORIES = {
    "Test strategy": "test_strategy",
    "Test case inventory": "test_inventory",
    "Test execution results": "test_execution",
    "Defect mapping": "defect_mapping",
    "Evidence repository": "test_evidence_repo",
}

_GOLIVE_CATEGORIES = {
    "Go-live checklist": "go_live_checklist",
    "Risk assessment": "risk_assessment",
    "Approval records": "approval_records",
    "Closure evidence": "closure_evidence",
}


def _evidence_examples(s: int, stage_key: str, app: str, fw: str, count: int | None = None) -> list[dict]:
    n = count or between(s >> 2, 5, 8)
    rows = []
    for i in range(n):
        es = seed("docevd", stage_key, s, i)
        rows.append({
            "evidence_id": f"EVD-DOC-{stage_key[:3].upper()}-{between(es, 1000, 9999)}",
            "evidence_type": pick(es >> 2, _EVIDENCE_TYPES),
            "title": pick(es >> 4, [
                f"{fw} attestation — {app}",
                f"SAST scan report — {app} release branch",
                f"Architecture diagram — {app} tier-1 path",
                f"CAB approval email — production window",
                f"VAPT executive summary — signed",
                f"Deployment log — blue/green cutover",
            ]),
            "submitted_by": pick(es >> 6, BANKING_OWNERS + ["AppSec CoE", "Internal Audit"]),
            "review_status": pick(es >> 8, ["Reviewed", "In Review", "Approved"]),
            "approval_status": pick(es >> 10, ["Approved", "Approved", "Pending", "Conditional"]),
            "application": app,
        })
    return rows


def _historical_references(s: int, stage_key: str, app: str, fw: str) -> list[dict]:
    other = [a for a in BANKING_APPLICATIONS if a != app]
    rows = []
    for i in range(between(s >> 12, 3, 5)):
        hs = seed("dochist", stage_key, s, i)
        rows.append({
            "observation_id": f"OBS-HIST-{pick(hs, ['2023', '2024', '2025'])}-{between(hs >> 2, 100, 999)}",
            "audit_year": pick(hs >> 4, ["FY2023", "FY2024", "FY2025", "Q1-FY2026"]),
            "application": pick(hs >> 6, other + [app]),
            "closure_date": (ANCHOR - timedelta(days=between(hs >> 8, 60, 900))).strftime("%Y-%m-%d"),
            "control_owner": pick(hs >> 10, BANKING_OWNERS),
            "approval_authority": pick(hs >> 12, ["Internal Audit", "Compliance Head", "CAB Chair", "CIO Office"]),
            "summary": pick(hs >> 14, [
                f"Prior {fw} control validated — reuse approved for similar scope",
                "Observation closed with compensating control evidence on file",
                "Management response accepted; pattern reused in current release",
            ]),
        })
    return rows


def _approval_comments(s: int, stage_key: str) -> list[dict]:
    return [
        {
            "reviewer": pick(seed("docap", stage_key, s, i), ["V. Desai (Compliance)", "AppSec CoE", "Internal Audit", "Enterprise Architecture", "CIO Office"]),
            "date": (ANCHOR - timedelta(days=between(seed("docapd", stage_key, s, i), 1, 45))).strftime("%Y-%m-%d"),
            "comment": pick(seed("docapc", stage_key, s, i), [
                "Scope aligns with release impacted applications. Proceed with evidence collection.",
                "Conditional approval — retest required for tier-1 authentication path.",
                "Approved for reuse; ensure historical closure references are cited in evidence pack.",
                "Risk acceptance documented; monitor hypercare period for 14 days post go-live.",
            ]),
            "status": pick(seed("docaps", stage_key, s, i), ["Approved", "Conditional", "Approved"]),
        }
        for i in range(3)
    ]


def _table_section(title: str, columns: list[dict], rows: list[dict]) -> dict:
    return {"title": title, "type": "table", "columns": columns, "rows": rows}


def _prose_section(title: str, content: str) -> dict:
    return {"title": title, "type": "prose", "content": content}


def _build_requirement_artifact(category: str, release: dict, app: str, fw: str, s: int) -> dict[str, Any]:
    apps = release.get("impacted_applications", [app])
    cat_focus = {
        "Control objective": "Defines measurable control objectives and success criteria for audit traceability.",
        "Regulatory expectation": "Maps RBI Master Direction, NPCI, and PCI DSS obligations to release scope.",
        "Audit requirement document": "Internal audit checklist with evidence frequency and owner accountability.",
        "Generated checklist": "Auto-generated SDLC gate checklist synced from ECS every 4 hours.",
        "Similar controls from previous audits": "Cross-reference of validated controls from FY2023–FY2025 audits.",
        "Reference implementations": "Approved reference patterns from Enterprise Architecture repository.",
    }
    focus = cat_focus.get(category, category)
    ctrl_rows = [
        {"control_id": f"{fw[:3].upper()}-{between(seed('dc', s, i), 1, 99):02d}", "framework": fw,
         "description": pick(seed("dcd", s, i), ["MFA for privileged API", "PII encryption at rest", "Immutable audit logging", "Session timeout enforcement"]),
         "owner": pick(seed("dco", s, i), BANKING_OWNERS), "status": pick(seed("dcs", s, i), ["Required", "Mapped", "Approved"])}
        for i in range(between(s >> 4, 4, 8))
    ]
    risk_rows = [
        {"risk_id": f"RSK-REQ-{i+1}", "description": pick(seed("drsk", s, i), ["Unauthorized API access", "Data leakage via AI copilot", "Regulatory non-compliance on consent", "DR RTO breach"]),
         "severity": pick(seed("drsev", s, i), ["High", "Medium", "Critical"]), "mitigation": "Mapped to control objective"}
        for i in range(3)
    ]
    sections = [
        _prose_section("Executive Summary", (
            f"This requirement artifact defines governance expectations for {release['name']} "
            f"covering {app} under {fw}. It establishes auditable control objectives aligned to "
            f"RBI Master Direction, PCI DSS v4.0, and internal ADD policy."
        )),
        _prose_section("Requirement Summary", (
            f"{category} — {focus} Applies to {app} under {fw} framework for {release['name']}. "
            f"Release owner: {release['owner']}."
        )),
        _prose_section("Audit Requirement", (
            f"Internal audit requires traceability from business requirement to control ID for {fw}. "
            f"Evidence must be collected within 30 days of requirement sign-off. "
            f"Auditor workspace: ECS Evidence Repository — folder REQ-{release['id'].split('-')[-1]}."
        )),
        _prose_section("Risk Description", (
            f"Failure to implement stated requirements for {app} exposes the bank to regulatory "
            f"findings, customer data breach, and delayed release certification. Residual risk "
            f"requires CIO acceptance if any High items remain open at design gate."
        )),
        _prose_section("Business Justification", (
            f"{app} release enables Q2 digital channel enhancements with projected 12% transaction "
            f"volume increase. Governance investment prevents repeat FY2024 audit observations "
            f"on authentication and logging controls."
        )),
        _prose_section("Implementation Guidance", (
            "Map each requirement to ECS control registry. Upload signed requirement spec, "
            "traceability matrix, and owner acknowledgement to governance repository. "
            "Reference similar controls from prior audits where scope is unchanged."
        )),
        _prose_section("Control Owner Responsibilities", (
            "App owner validates applicability across impacted applications. Compliance reviews "
            "regulatory mapping. Internal audit samples 10% of requirements for traceability quality."
        )),
        _table_section("Impacted Applications", [{"key": "application", "label": "Application"}, {"key": "tier", "label": "Tier"}, {"key": "owner", "label": "Owner"}],
            [{"application": a, "tier": pick(seed("dtier", s, a), ["Tier-1", "Tier-1", "Tier-2"]), "owner": pick(seed("down", s, a), BANKING_OWNERS)} for a in apps]),
        _table_section("Control Mapping", [{"key": "control_id", "label": "Control ID"}, {"key": "framework", "label": "Framework"}, {"key": "description", "label": "Description"}, {"key": "owner", "label": "Owner"}, {"key": "status", "label": "Status"}], ctrl_rows),
        _table_section("Risk Register", [{"key": "risk_id", "label": "Risk ID"}, {"key": "description", "label": "Description"}, {"key": "severity", "label": "Severity"}, {"key": "mitigation", "label": "Mitigation"}], risk_rows),
        _table_section("Evidence Checklist", [{"key": "item", "label": "Evidence Item"}, {"key": "mandatory", "label": "Mandatory"}, {"key": "owner", "label": "Owner"}],
            [{"item": pick(seed("deci", s, i), ["Signed requirement spec", "Traceability matrix", "Owner acknowledgement", "Regulatory mapping sheet", "Risk assessment"]),
              "mandatory": "Yes", "owner": pick(seed("deco", s, i), BANKING_OWNERS)} for i in range(5)]),
        _prose_section("Previous Accepted Implementations", (
            f"Net Banking Q4 2025 — {fw} control pack reused with delta analysis. "
            f"Mobile Banking 4.1 — consent capture pattern approved by Internal Audit. "
            f"Payments Switch — NPCI mapping accepted with minor scope amendment."
        )),
    ]
    if category == "Similar controls from previous audits":
        sections.append(_prose_section("Historical Closure References", (
            "OBS-2024-118 closed 2024-11-12 — MFA control reused. "
            "OBS-2023-044 closed 2023-09-30 — logging control pattern accepted."
        )))
    req_kb = build_requirement_knowledge({"category": category}, release, app, fw, s)
    sections.append(_table_section(
        "Historical Requirement References",
        [{"key": "requirement_id", "label": "Requirement ID"}, {"key": "application", "label": "Application"},
         {"key": "release", "label": "Release"}, {"key": "status", "label": "Status"},
         {"key": "owner", "label": "Owner"}, {"key": "closure_date", "label": "Closure Date"}],
        req_kb["historical_requirement_references"],
    ))
    sections.extend([
        _prose_section("Recommended Requirement Language", req_kb["recommended_language"]),
        _prose_section("Previous Approved Requirement Text", req_kb["previous_approved_text"]),
        _prose_section("Control Interpretation Guidance", req_kb["control_interpretation"]),
        _prose_section("Regulatory Explanation", req_kb["regulatory_explanation"]),
        _prose_section("Audit Explanation", req_kb["audit_explanation"]),
        _prose_section("Control Intent", req_kb["control_intent"]),
        _prose_section("Business Risk if Not Implemented", req_kb["business_risk"]),
    ])
    return {
        "executive_summary": sections[0]["content"],
        "sections": sections,
        "required_evidence": _evidence_examples(s, "requirement", app, fw),
        "historical_references": _historical_references(s, "requirement", app, fw),
        "approval_comments": _approval_comments(s, "requirement"),
        "sample_approved_evidence": _evidence_examples(s >> 1, "requirement", app, fw, 3),
    }


def _build_design_artifact(category: str, release: dict, app: str, fw: str, s: int) -> dict[str, Any]:
    hist_app = pick(s >> 3, _DESIGN_APPS)
    cat_focus = {
        "Design submission template": "Standard v3.2 template — context diagram, data classification, threat model mandatory.",
        "Sample approved designs from historical observations": "Archive of designs approved under prior audit remediations.",
        "Design review comments": "Consolidated AppSec CoE and Enterprise Architecture review thread.",
        "Design approval workflow": "Submit → Architecture → Security → Compliance → CIO. SLA 5 days per stage.",
    }
    focus = cat_focus.get(category, category)
    sections = [
        _prose_section("Executive Summary", (
            f"Design governance artifact — {category}. {focus} Solution covers {app} for {release['name']}."
        )),
        _prose_section("Solution Overview", (
            f"{app} solution introduces API gateway hardening, RAG pipeline for customer FAQ, "
            f"and HSM integration for card token path. Deployment model: active-active across "
            f"DC1/DC2 with 4-hour RTO."
        )),
        _prose_section("Architecture Summary", (
            "Three-tier architecture: CDN → API Gateway (WAF) → Microservices mesh. "
            "Identity via OAuth2/OIDC federation. Async audit events to immutable log pipeline."
        )),
        _prose_section("Security Architecture", (
            "Defense-in-depth: mTLS between services, secrets in HashiCorp Vault, "
            "prompt injection filter on AI inference path. AppSec threat model reviewed STRIDE."
        )),
        _prose_section("Data Classification", (
            "Customer PII: Restricted. Transaction metadata: Confidential. "
            "Aggregated analytics: Internal. AI training data: Prohibited without consent."
        )),
        _prose_section("Threat Model Summary", (
            "Top threats: prompt injection, IDOR on account APIs, SSRF via webhook callbacks. "
            "Mitigations mapped to AppSec AS-C controls. Red-team review scheduled pre-VAPT."
        )),
        _prose_section("Design Assumptions", (
            "Existing SSO federation remains authoritative. No new internet-facing endpoints without CAB. "
            "AI model inference stays in India region per data residency policy."
        )),
        _table_section("Control Mapping Matrix", [{"key": "control_id", "label": "Control"}, {"key": "design_element", "label": "Design Element"}, {"key": "status", "label": "Status"}],
            [{"control_id": f"AS-C-{between(seed('dsgc', s, i), 1, 20):02d}", "design_element": pick(seed("dsge", s, i), ["API gateway WAF", "HSM key rotation", "Audit log pipeline", "Zero-trust segmentation"]),
              "status": pick(seed("dsgs", s, i), ["Approved", "In Review"])} for i in range(6)]),
        _table_section("Design Review Comments", [{"key": "reviewer", "label": "Reviewer"}, {"key": "comment", "label": "Comment"}, {"key": "status", "label": "Status"}],
            [{"reviewer": pick(seed("drc", s, i), ["Enterprise Architecture", "AppSec CoE", "Compliance"]),
              "comment": pick(seed("drcc", s, i), ["Approve data-flow diagram", "Resolve STRIDE item #4", "Add NPCI reference"]),
              "status": pick(seed("drcs", s, i), ["Resolved", "Open", "Resolved"])} for i in range(5)]),
        _table_section("Historical Approved Designs", [{"key": "design_ref", "label": "Reference"}, {"key": "application", "label": "Application"}, {"key": "observation", "label": "Prior Observation"}, {"key": "status", "label": "Status"}],
            [{"design_ref": f"DSG-{2024 + i}-APPROVED", "application": pick(seed("dha", s, i), _DESIGN_APPS),
              "observation": f"OBS-202{4+i}-0{14+i} — remediated", "status": "Approved for reuse"}
             for i in range(4)]),
    ]
    if category == "Sample approved designs from historical observations":
        sections.append(_prose_section("Historical Observation Examples", (
            f"{hist_app} — OBS-2025-014: Threat model gap closed with approved zero-trust design. "
            f"Net Banking — OBS-2024-087: API rate limiting design accepted by AppSec CoE. "
            f"CRM — OBS-2024-033: Data residency architecture approved by Compliance."
        )))
    dsg_kb = build_design_knowledge(release, app, fw, s)
    sections.append(_table_section(
        "Historical Design Knowledge Base",
        [{"key": "application", "label": "Application"}, {"key": "release", "label": "Release"},
         {"key": "approval_date", "label": "Approval Date"}, {"key": "architect", "label": "Architect"},
         {"key": "reviewer", "label": "Reviewer"}, {"key": "status", "label": "Status"}],
        dsg_kb["historical_design_knowledge_base"],
    ))
    sections.append(_table_section(
        "Reusable Design Patterns",
        [{"key": "pattern", "label": "Pattern"}, {"key": "used_in", "label": "Used In"},
         {"key": "reference_architecture", "label": "Reference Arch"}, {"key": "diagram", "label": "Diagram"},
         {"key": "review_comments", "label": "Review Comments"}],
        [{"pattern": p["pattern"], "used_in": ", ".join(p["used_in"]), **{k: p[k] for k in ("reference_architecture", "diagram", "review_comments")}}
          for p in dsg_kb["reusable_design_patterns"]],
    ))
    return {
        "executive_summary": sections[0]["content"],
        "sections": sections,
        "required_evidence": _evidence_examples(s, "design", app, fw),
        "historical_references": _historical_references(s, "design", app, fw),
        "approval_comments": _approval_comments(s, "design"),
    }


def _build_development_artifact(category: str, release: dict, app: str, fw: str, s: int) -> dict[str, Any]:
    cat_titles = {
        "Development implementation plan": "Sprint-level plan with CI/CD gate criteria and evidence schedule.",
        "Coding standards": "Bank standards v2026.1 — Java, Python, TypeScript + AI/LLM addendum.",
        "Secure coding checklist": "42-item developer self-assessment before merge to release branch.",
        "Developer evidence repository": "Index of SAST reports, coverage, secrets scans, code review approvals.",
    }
    task_rows = [
        {"task": pick(seed("devt", s, i), ["Integrate SAST gate in CI", "Enable secrets scanning", "Implement parameterized queries", "Deploy prompt guardrail", "OS hardening validation"]),
         "owner": pick(seed("devto", s, i), ["DevOps Lead", "Platform Engineering", "App Owner"]),
         "status": pick(seed("devts", s, i), ["Complete", "In Progress", "Complete"]),
         "evidence": pick(seed("devte", s, i), ["SonarQube report", "GitLeaks log", "Code review PR-4421"])}
        for i in range(6)
    ]
    sections = [
        _prose_section("Executive Summary", (
            f"Development artifact — {category}. {cat_titles.get(category, '')} Target: {app}."
        )),
        _prose_section("Control Implementation Approach", (
            "Shift-left model: SAST/DAST gates block merge on Critical findings. "
            "Secrets scanning on every commit. AI guardrails deployed as middleware filter."
        )),
        _prose_section("Secure Coding Checklist", (
            "42-item checklist: input validation, output encoding, authZ checks, "
            "no hardcoded secrets, dependency CVE triage, LLM prompt sanitization."
        )),
        _prose_section("Vulnerability Remediation Plan", (
            "Critical: 0 open. High: 2 in remediation (SQL parameterization, TLS cipher). "
            "Target closure: 5 business days before release candidate tag."
        )),
        _prose_section("Open-Source Dependency Assessment", (
            "SBOM generated via Syft. 3 medium CVEs with vendor patches scheduled. "
            "No prohibited licenses detected in release branch."
        )),
        _prose_section("Static Code Scan Summary", (
            f"SonarQube scan — {app}: 0 Blocker, 2 Critical (in remediation), 18 Major. "
            "Quality gate: PASSED with waiver for legacy module (approved)."
        )),
        _prose_section("AI Model Guardrail Implementation", (
            "Prompt injection filter deployed. PII redaction rules in system prompt v2.3. "
            "Output logging to immutable audit stream — 7-year retention."
        )),
        _table_section("Development Tasks", [{"key": "task", "label": "Task"}, {"key": "owner", "label": "Owner"}, {"key": "status", "label": "Status"}, {"key": "evidence", "label": "Evidence Produced"}], task_rows),
        _prose_section("Historical Successful Implementations", (
            "Mobile Banking 4.1 — SAST gate pattern reused. Payments Switch — secrets scanning "
            "pipeline copied with 2-day adaptation. Net Banking — guardrail middleware reference impl."
        )),
    ]
    dev_kb = build_development_knowledge(release, app, fw, s)
    ib = dev_kb["implementation_knowledge_base"]
    sections.append(_table_section(
        "Implementation Knowledge Base — Reusable Components",
        [{"key": "component", "label": "Component"}, {"key": "technology", "label": "Technology Stack"},
         {"key": "repository", "label": "Repository"}, {"key": "owner", "label": "Owner"},
         {"key": "controls", "label": "Control Coverage"}, {"key": "used_by", "label": "Used By"}],
        [{"component": c["component"], "technology": c["technology"], "repository": c["repository"],
          "owner": c["owner"], "controls": ", ".join(c["controls"]), "used_by": ", ".join(c["used_by"])}
         for c in ib["reusable_components"]],
    ))
    sections.extend([
        _prose_section("Reusable Code Pattern", dev_kb["reusable_code_pattern"]),
        _prose_section("Secure Coding Examples", " · ".join(dev_kb["secure_coding_examples"])),
        _prose_section("Static Analysis Results", dev_kb["static_analysis_results"]),
    ])
    sections.append(_table_section(
        "Known Good Implementations",
        [{"key": "application", "label": "Application"}, {"key": "control", "label": "Control"},
         {"key": "repository", "label": "Repository"}, {"key": "status", "label": "Status"}],
        dev_kb["known_good_implementations"],
    ))
    return {
        "executive_summary": sections[0]["content"],
        "sections": sections,
        "required_evidence": _evidence_examples(s, "development", app, fw),
        "historical_references": _historical_references(s, "development", app, fw),
        "approval_comments": _approval_comments(s, "development"),
    }


def _build_testing_artifact(category: str, release: dict, app: str, fw: str, s: int) -> dict[str, Any]:
    passed = between(s >> 4, 780, 840)
    failed = between(s >> 6, 8, 28)
    cat_titles = {
        "Test strategy": "Risk-based strategy — functional, security, compliance, performance.",
        "Test case inventory": "847 cases mapped to control objectives — 92% automated.",
        "Test execution results": "Latest run results with pass/fail and defect linkage.",
        "Defect mapping": "Defect-to-control matrix with remediation targets.",
        "Evidence repository": "Centralized test evidence — scans, logs, sign-offs.",
    }
    sections = [
        _prose_section("Executive Summary", (
            f"Testing artifact — {category}. {cat_titles.get(category, '')} Application: {app}."
        )),
        _prose_section("Test Objectives", (
            "Validate OWASP ASVS Level 2 controls, NPCI compliance scenarios, "
            "AI prompt injection resistance, and regression of tier-1 payment flows."
        )),
        _prose_section("Security Test Plan", (
            "EY VAPT scope: authenticated/unauthenticated API fuzzing, privilege escalation, "
            "business logic flaws. AppSec CoE: SAST/DAST correlation review."
        )),
        _prose_section("Pass/Fail Summary", (
            f"Total executed: {passed + failed}. Passed: {passed}. Failed: {failed}. Blocked: 12. "
            f"Critical open: {between(s >> 8, 0, 2)}. Target: zero Critical before go-live gate."
        )),
        _prose_section("VAPT Report Summary", (
            "External scan completed 2026-05-18. 1 Critical (remediated), 4 High (2 open), "
            "12 Medium accepted with compensating controls. Re-test scheduled."
        )),
        _prose_section("AI Model Validation Report", (
            "Prompt red-team: 847 adversarial prompts. 3 bypass attempts blocked. "
            "Hallucination rate within policy threshold. Model Risk sign-off conditional."
        )),
        _prose_section("UAT Sign-Off Package", (
            "Business UAT: 98% pass rate. Outstanding items tracked in Jira release board. "
            "Product owner sign-off pending 2 cosmetic defects."
        )),
        _table_section("Test Cases Sample", [{"key": "test_id", "label": "Test ID"}, {"key": "objective", "label": "Objective"}, {"key": "result", "label": "Result"}],
            [{"test_id": f"TC-{app[:3].upper()}-{400+i}", "objective": pick(seed("tstobj", s, i), ["OWASP injection", "MFA bypass", "Rate limit", "Prompt injection"]),
              "result": pick(seed("tstr", s, i), ["Pass", "Pass", "Fail", "Pass"])} for i in range(6)]),
        _table_section("Open Findings", [{"key": "finding_id", "label": "Finding"}, {"key": "severity", "label": "Severity"}, {"key": "status", "label": "Status"}],
            [{"finding_id": f"FND-{i+1}", "severity": pick(seed("fsev", s, i), ["High", "Medium"]),
              "status": pick(seed("fsts", s, i), ["Open", "In Remediation", "Accepted"])} for i in range(4)]),
        _prose_section("Historical Findings Closure Examples", (
            "FY2024 VAPT Critical — SQL injection closed with parameterized queries. "
            "FY2025 AI red-team — prompt bypass patched in guardrail v2.1."
        )),
    ]
    tst_kb = build_testing_knowledge(release, app, fw, s)
    sections.append(_table_section(
        "Reusable Test Knowledge — Historical Test Cases",
        [{"key": "test_case_id", "label": "Test Case ID"}, {"key": "control_id", "label": "Control ID"},
         {"key": "application", "label": "Application"}, {"key": "pass_rate", "label": "Pass Rate"},
         {"key": "last_execution", "label": "Last Execution"}],
        tst_kb["reusable_test_knowledge"]["historical_test_cases"],
    ))
    sections.append(_table_section(
        "Reusable Test Packs",
        [{"key": "pack_name", "label": "Test Pack"}, {"key": "used_in", "label": "Used In"},
         {"key": "pass_rate", "label": "Pass Rate"}, {"key": "known_failures", "label": "Known Failures"},
         {"key": "last_execution", "label": "Last Execution"}],
        [{"pack_name": p["pack_name"], "used_in": ", ".join(p["used_in"]), "pass_rate": p["pass_rate"],
          "known_failures": p["known_failures"], "last_execution": p["last_execution"]} for p in tst_kb["test_packs"]],
    ))
    return {
        "executive_summary": sections[0]["content"],
        "sections": sections,
        "required_evidence": _evidence_examples(s, "testing", app, fw),
        "historical_references": _historical_references(s, "testing", app, fw),
        "approval_comments": _approval_comments(s, "testing"),
        "linked_evidence": _evidence_examples(s >> 1, "testing", app, fw, 4),
    }


def _build_golive_artifact(category: str, release: dict, app: str, fw: str, s: int) -> dict[str, Any]:
    cat_titles = {
        "Go-live checklist": "19-item production readiness checklist across infra, security, ops.",
        "Risk assessment": "Residual risk register with CIO acceptance for High items.",
        "Approval records": "CAB, Audit Committee, and Change Manager sign-offs.",
        "Closure evidence": "Final auditor evidence pack — VAPT, DR, AI approval, runbooks.",
    }
    sections = [
        _prose_section("Executive Summary", (
            f"Go-live artifact — {category}. {cat_titles.get(category, '')} Release: {release['name']}."
        )),
        _prose_section("Go-Live Criteria", (
            "All Critical VAPT findings closed. Evidence pack submitted to auditor. "
            "CAB approval obtained. DR drill within 90 days. AI model approval current."
        )),
        _prose_section("CAB Approval Package", (
            f"CAB-2026-042 — Production window 2026-06-14 02:00–06:00 IST. "
            f"Change type: Standard. Rollback plan attached. Emergency contacts confirmed."
        )),
        _prose_section("Production Readiness Checklist", (
            "19 items: monitoring dashboards, runbooks, L1/L2 handover, license checks, "
            "NPCI certification, fraud rules updated, rollback tested in staging."
        )),
        _prose_section("Rollback Plan", (
            "Blue/green deployment with instant traffic switch. Database migration reversible "
            "via snapshot restore. RTO: 30 minutes. Last drill: 2026-05-10 — successful."
        )),
        _prose_section("DR Validation Report", (
            "Tier-1 failover drill completed. RTO achieved: 3h 42m (target ≤ 4h). "
            "Evidence uploaded to ITPP repository. Auditor attestation pending."
        )),
        _prose_section("Risk Acceptance", (
            "2 Medium residual risks accepted by CIO with 90-day remediation plan. "
            "0 High items open. Exception register entry EXC-GL-003 expires 2026-08-01."
        )),
        _prose_section("Hypercare Support Plan", (
            "14-day hypercare: war room 24×7, AppSec on-call, enhanced monitoring thresholds, "
            "daily stand-down with release manager and ops lead."
        )),
        _table_section("Approval Chain", [{"key": "role", "label": "Role"}, {"key": "name", "label": "Approver"}, {"key": "date", "label": "Date"}, {"key": "status", "label": "Status"}],
            [{"role": r, "name": pick(seed("glap", s, r), BANKING_OWNERS + ["CAB Chair", "CIO"]),
              "date": (ANCHOR - timedelta(days=between(seed("glapd", s, r), 1, 20))).strftime("%Y-%m-%d"),
              "status": pick(seed("glaps", s, r), ["Approved", "Approved", "Pending"])}
             for r in ["App Owner", "AppSec CoE", "Compliance", "Internal Audit", "CAB Chair", "CIO"]]),
        _prose_section("Final Evidence Package", (
            "VAPT closure letter, DR drill attestation, AI model approval, ops runbook sign-off, "
            "CAB minutes, compliance sign-off email — archived in ECS Evidence Repository."
        )),
    ]
    gl_kb = build_golive_knowledge(release, app, s)
    sections.append(_table_section(
        "Historical Go-Live Repository",
        [{"key": "application", "label": "Application"}, {"key": "release", "label": "Release"},
         {"key": "go_live_date", "label": "Go Live Date"}, {"key": "approval_authority", "label": "Approval Authority"},
         {"key": "result", "label": "Result"}, {"key": "artifact", "label": "Artifact"}],
        gl_kb["historical_go_live_repository"],
    ))
    return {
        "executive_summary": sections[0]["content"],
        "sections": sections,
        "required_evidence": _evidence_examples(s, "go-live", app, fw),
        "historical_references": _historical_references(s, "go-live", app, fw),
        "approval_comments": _approval_comments(s, "go-live"),
        "exception_approvals": [
            {"exception_id": f"EXC-GL-{between(seed('glex', s, i), 1, 99):03d}", "summary": "Temporary WAF exception — legacy API",
             "expiry": (ANCHOR + timedelta(days=60)).strftime("%Y-%m-%d"), "status": "Approved"}
            for i in range(2)
        ],
    }


def build_document_artifact(stage_key: str, category: str, release: dict, app: str, fw: str, s: int) -> dict[str, Any]:
    builders = {
        "requirement": _build_requirement_artifact,
        "design": _build_design_artifact,
        "development": _build_development_artifact,
        "testing": _build_testing_artifact,
        "go-live": _build_golive_artifact,
    }
    builder = builders.get(stage_key, _build_requirement_artifact)
    artifact = builder(category, release, app, fw, s)
    artifact["historical_approved_references"] = artifact.get("historical_references", [])
    doc_stub = {"category": category, "title": f"{release['name']} — {category}", "doc_id": f"DOC-{release['id'].split('-')[-1]}-{between(s, 100, 999)}"}
    tabs = build_document_viewer_tabs(artifact, stage_key, doc_stub, release, app, fw, s)
    stage_kb = tabs.get("overview", {}).get("stage_knowledge", {})
    tabs = extend_document_tabs(tabs, stage_key, stage_kb, doc_stub, release, s)
    artifact["viewer_tabs"] = extend_stage_document_tabs(tabs, stage_key, stage_kb, doc_stub, release, s)
    artifact["reuse_modal"] = {
        "reuse_type": stage_key if stage_key in ("requirement", "design", "testing") else "requirement",
        "drill_metric": "reuse_modal",
        "drill_id": f"{stage_key}::{doc_stub['doc_id']}",
    }
    if stage_key == "requirement":
        artifact["reuse_action"] = "Reuse this Requirement"
    elif stage_key == "testing":
        artifact["reuse_action"] = "Reuse Test Pack"
    return artifact
