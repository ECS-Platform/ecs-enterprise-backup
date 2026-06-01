"""SDLC stage workspace dashboards — slug routes and stage-specific artifact sections."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from modules.shared.utils.demo_data_standards import BANKING_OWNERS, between, pick, seed

ANCHOR = date(2026, 5, 28)

# URL slug → internal stage key
STAGE_SLUG_TO_KEY: dict[str, str] = {
    "requirements": "requirement",
    "design": "design",
    "development": "development",
    "testing": "testing",
    "golive": "go-live",
}

STAGE_KEY_TO_SLUG: dict[str, str] = {v: k for k, v in STAGE_SLUG_TO_KEY.items()}

STAGE_DASHBOARD_SECTIONS: dict[str, list[dict[str, str]]] = {
    "requirement": [
        {"id": "brd-repository", "label": "BRD Repository", "data_key": "brd_repository"},
        {"id": "frd-repository", "label": "FRD Repository", "data_key": "frd_repository"},
        {"id": "user-stories", "label": "User Stories", "data_key": "user_stories"},
        {"id": "acceptance-criteria", "label": "Acceptance Criteria", "data_key": "acceptance_criteria"},
        {"id": "traceability-matrix", "label": "Requirement Traceability Matrix", "data_key": "traceability_matrix"},
        {"id": "review-evidence", "label": "Review Evidence", "data_key": "review_evidence"},
        {"id": "audit-trail", "label": "Audit Trail", "data_key": "audit_trail"},
    ],
    "design": [
        {"id": "solution-architecture", "label": "Solution Architecture", "data_key": "solution_architecture"},
        {"id": "technical-architecture", "label": "Technical Architecture", "data_key": "technical_architecture"},
        {"id": "hld", "label": "HLD", "data_key": "hld"},
        {"id": "lld", "label": "LLD", "data_key": "lld"},
        {"id": "api-specifications", "label": "API Specifications", "data_key": "api_specifications"},
        {"id": "design-reviews", "label": "Design Reviews", "data_key": "design_reviews"},
        {"id": "design-evidence", "label": "Design Evidence", "data_key": "design_evidence"},
        {"id": "audit-trail", "label": "Audit Trail", "data_key": "audit_trail"},
    ],
    "development": [
        {"id": "code-repositories", "label": "Code Repositories", "data_key": "code_repositories"},
        {"id": "secure-coding", "label": "Secure Coding Controls", "data_key": "secure_coding"},
        {"id": "sast-findings", "label": "SAST Findings", "data_key": "sast_findings"},
        {"id": "code-reviews", "label": "Code Reviews", "data_key": "code_reviews"},
        {"id": "branch-controls", "label": "Branch Controls", "data_key": "branch_controls"},
        {"id": "vulnerabilities", "label": "Vulnerabilities", "data_key": "vulnerabilities"},
        {"id": "exceptions", "label": "Exceptions", "data_key": "exceptions"},
        {"id": "audit-trail", "label": "Audit Trail", "data_key": "audit_trail"},
    ],
    "testing": [
        {"id": "test-cases", "label": "Test Cases", "data_key": "test_cases"},
        {"id": "test-execution", "label": "Test Execution", "data_key": "test_execution"},
        {"id": "sit-results", "label": "SIT Results", "data_key": "sit_results"},
        {"id": "uat-results", "label": "UAT Results", "data_key": "uat_results"},
        {"id": "security-testing", "label": "Security Testing", "data_key": "security_testing"},
        {"id": "performance-testing", "label": "Performance Testing", "data_key": "performance_testing"},
        {"id": "defects", "label": "Defects", "data_key": "defects"},
        {"id": "evidence-repository", "label": "Evidence Repository", "data_key": "evidence_repository"},
    ],
    "go-live": [
        {"id": "cab-approvals", "label": "CAB Approvals", "data_key": "cab_approvals"},
        {"id": "deployment-checklist", "label": "Deployment Checklist", "data_key": "deployment_checklist"},
        {"id": "rollback-plan", "label": "Rollback Plan", "data_key": "rollback_plan"},
        {"id": "production-validation", "label": "Production Validation", "data_key": "production_validation"},
        {"id": "hypercare", "label": "Hypercare", "data_key": "hypercare"},
        {"id": "closure-report", "label": "Closure Report", "data_key": "closure_report"},
        {"id": "audit-trail", "label": "Audit Trail", "data_key": "audit_trail"},
    ],
}


def sdlc_stage_path(stage_key: str) -> str:
    slug = STAGE_KEY_TO_SLUG.get(stage_key, stage_key)
    return f"/sdlc/{slug}"


def resolve_stage_key(slug_or_key: str) -> str | None:
    if slug_or_key in STAGE_SLUG_TO_KEY:
        return STAGE_SLUG_TO_KEY[slug_or_key]
    if slug_or_key in STAGE_KEY_TO_SLUG:
        return slug_or_key
    return None


def _audit_rows(detail: dict) -> list[dict]:
    return [
        {
            "timestamp": e.get("timestamp", e.get("date", "")),
            "user": e.get("user", e.get("actor", "")),
            "action": e.get("action", ""),
            "detail": e.get("detail", ""),
        }
        for e in detail.get("audit_trail", [])
    ]


def build_stage_dashboard(stage_key: str, detail: dict, release: dict) -> dict[str, Any]:
    """Build stage-specific artifact sections for the workspace dashboard."""
    release_id = release.get("id", "")
    app = release.get("application", "Net Banking")
    apps = detail.get("summary", {}).get("applications_impacted", [app])
    sections: dict[str, list[dict]] = {}
    requirements = detail.get("requirements", [])
    designs = detail.get("designs", [])
    development = detail.get("development", [])
    testing = detail.get("testing", [])
    go_live = detail.get("go_live", {})
    all_evidence = [e for r in detail.get("framework_rows", []) for e in r.get("evidence_records", [])]

    if stage_key == "requirement":
        sections["brd_repository"] = [
            {"doc_id": r["req_id"], "title": r["title"], "application": r["application"],
             "owner": r["owner"], "status": r["status"], "controls": r["controls_generated"]}
            for r in requirements[:12]
        ]
        sections["frd_repository"] = [
            {"doc_id": f"FRD-{r['req_id'].split('-')[-1]}", "title": f"Functional spec — {r['title'][:48]}",
             "application": r["application"], "owner": r["owner"], "status": r["status"]}
            for r in requirements[6:18]
        ]
        sections["user_stories"] = [
            {"story_id": f"US-{release_id.split('-')[-1]}-{i+1:03d}",
             "title": pick(seed("us", i, release_id), [
                 "As a customer I can view masked account balances",
                 "As an agent I can escalate fraud alerts with audit trail",
                 "As compliance I can export AI prompt logs for review",
             ]),
             "application": pick(seed("usa", i), apps), "points": between(seed("usp", i), 3, 13),
             "status": pick(seed("uss", i), ["Done", "In Progress", "Approved"])}
            for i in range(20)
        ]
        sections["acceptance_criteria"] = [
            {"ac_id": f"AC-{release_id.split('-')[-1]}-{i+1:03d}",
             "requirement": requirements[i % len(requirements)]["req_id"] if requirements else f"REQ-{i}",
             "criterion": pick(seed("ac", i), [
                 "All PII fields masked in API responses",
                 "MFA enforced for privileged admin actions",
                 "Audit log entry within 5 seconds of event",
             ]),
             "status": pick(seed("acs", i), ["Verified", "Pending", "Approved"])}
            for i in range(18)
        ]
        sections["traceability_matrix"] = [
            {"requirement": r["req_id"], "control": c["control_id"], "framework": c["framework"],
             "application": c["application"], "status": c["status"]}
            for r in requirements[:10]
            for c in r.get("control_records", [])[:2]
        ]
        sections["review_evidence"] = [
            {"evidence_id": e["evidence_id"], "title": e["title"], "control": e["control_id"],
             "status": e["status"], "collected": e["collected_date"]}
            for e in all_evidence[:25]
        ]
        sections["audit_trail"] = _audit_rows(detail)

    elif stage_key == "design":
        sections["solution_architecture"] = [
            {"doc_id": d["design_id"], "title": d["title"], "application": d["application"],
             "reviewer": d["reviewer"], "status": d["status"]}
            for d in designs[:8]
        ]
        sections["technical_architecture"] = [
            {"doc_id": f"TECH-{d['design_id'].split('-')[-1]}", "title": f"Technical view — {d['application']}",
             "owner": d["owner"], "submitted": d["submitted"], "status": d["security_review"]}
            for d in designs[4:14]
        ]
        sections["hld"] = [
            {"hld_id": f"HLD-{release_id.split('-')[-1]}-{i+1:03d}",
             "component": pick(seed("hld", i), ["API Gateway", "Auth Service", "Payment Switch", "Data Lake Ingest"]),
             "application": pick(seed("hlda", i), apps), "version": f"v{between(seed('hldv', i), 1, 3)}.0",
             "status": pick(seed("hlds", i), ["Approved", "In Review"])}
            for i in range(15)
        ]
        sections["lld"] = [
            {"lld_id": f"LLD-{release_id.split('-')[-1]}-{i+1:03d}",
             "module": pick(seed("lld", i), ["Session Manager", "Token Vault", "Prompt Filter", "Audit Bus"]),
             "application": pick(seed("llda", i), apps), "owner": pick(seed("lldo", i), BANKING_OWNERS),
             "status": pick(seed("llds", i), ["Approved", "Draft"])}
            for i in range(16)
        ]
        sections["api_specifications"] = [
            {"api_id": f"API-{release_id.split('-')[-1]}-{i+1:03d}",
             "endpoint": pick(seed("api", i), ["/v2/accounts", "/v1/payments", "/v3/ai/completions", "/v1/fraud/score"]),
             "application": pick(seed("apia", i), apps), "version": "OpenAPI 3.1",
             "status": pick(seed("apis", i), ["Published", "Review"])}
            for i in range(14)
        ]
        sections["design_reviews"] = [
            {"review_id": d["design_id"], "title": d["title"], "architecture": d["architecture_review"],
             "security": d["security_review"], "compliance": d["compliance_review"], "owner": d["owner"]}
            for d in designs
        ]
        sections["design_evidence"] = [
            {"evidence_id": e["evidence_id"], "title": e["title"], "framework": e["framework"],
             "status": e["status"], "owner": e["owner"]}
            for e in all_evidence[:22]
        ]
        sections["audit_trail"] = _audit_rows(detail)

    elif stage_key == "development":
        sections["code_repositories"] = [
            {"repo": pick(seed("repo", i), [
                "gitlab.bank.com/retail/net-banking", "gitlab.bank.com/platform/audit-sdk",
                "gitlab.bank.com/payments/upi-gateway", "gitlab.bank.com/ai/prompt-guard",
            ]),
             "application": pick(seed("repoa", i), apps), "branch_policy": "Protected main",
             "last_commit": (ANCHOR - timedelta(days=between(seed("repod", i), 1, 14))).strftime("%Y-%m-%d")}
            for i in range(12)
        ]
        sections["secure_coding"] = [
            {"control": d["control_id"], "item": d["item"], "application": d["application"],
             "progress_pct": d["progress_pct"], "status": d["status"]}
            for d in development[:16]
        ]
        sections["sast_findings"] = [
            {"finding_id": f"SAST-{release_id.split('-')[-1]}-{i+1:03d}",
             "severity": pick(seed("sastsev", i), ["Critical", "High", "Medium", "Low"]),
             "rule": pick(seed("sastr", i), ["SQL Injection", "Hardcoded Secret", "Weak Crypto", "XSS"]),
             "application": pick(seed("sasta", i), apps), "status": pick(seed("sasts", i), ["Open", "Fixed", "Accepted"])}
            for i in range(22)
        ]
        sections["code_reviews"] = [
            {"review_id": f"CR-{release_id.split('-')[-1]}-{i+1:03d}",
             "author": pick(seed("cra", i), BANKING_OWNERS), "reviewer": pick(seed("crr", i), BANKING_OWNERS),
             "repo": pick(seed("crrepo", i), ["net-banking", "mobile-api", "upi-core"]),
             "status": pick(seed("crs", i), ["Approved", "Changes Requested"])}
            for i in range(18)
        ]
        sections["branch_controls"] = [
            {"branch": pick(seed("br", i), ["main", "release/2026-q2", "hotfix/pci-patch"]),
             "application": pick(seed("bra", i), apps), "protection": "Required reviews: 2",
             "status": "Enforced"}
            for i in range(10)
        ]
        sections["vulnerabilities"] = [
            {"vuln_id": f"VUL-{release_id.split('-')[-1]}-{i+1:03d}",
             "severity": pick(seed("vsev", i), ["Critical", "High", "Medium"]),
             "component": pick(seed("vcomp", i), ["Spring Boot", "Log4j", "OpenSSL", "nginx"]),
             "status": pick(seed("vst", i), ["Remediated", "In Progress", "Open"])}
            for i in range(20)
        ]
        sections["exceptions"] = [
            {"exception_id": f"DEV-EX-{i+1:03d}", "summary": pick(seed("dex", i), [
                "Temporary SAST waiver for legacy module", "Extended patch window for vendor dependency",
             ]), "application": pick(seed("dexa", i), apps), "expiry": release.get("target_date", ""),
             "status": pick(seed("dexs", i), ["Approved", "Pending"])}
            for i in range(8)
        ]
        sections["audit_trail"] = _audit_rows(detail)

    elif stage_key == "testing":
        sections["test_cases"] = [
            {"test_id": t["test_id"], "name": t["name"], "application": t["application"],
             "type": t["type"], "status": t["status"], "owner": t["owner"]}
            for t in testing
        ]
        sections["test_execution"] = [
            {"run_id": f"RUN-{release_id.split('-')[-1]}-{i+1:03d}",
             "suite": pick(seed("run", i), ["Regression", "Smoke", "Security", "Performance"]),
             "passed": between(seed("runp", i), 120, 480), "failed": between(seed("runf", i), 0, 12),
             "date": (ANCHOR - timedelta(days=between(seed("rund", i), 1, 30))).strftime("%Y-%m-%d")}
            for i in range(15)
        ]
        sections["sit_results"] = [
            {"test_id": t["test_id"], "application": t["application"], "result": t["status"],
             "defects": t["defects"], "executed": t["due"]}
            for t in testing[:18]
        ]
        sections["uat_results"] = [
            {"test_id": t["test_id"], "application": t["application"], "sign_off": t["owner"],
             "business_owner": t["owner"], "status": t["status"]}
            for t in testing[6:20]
        ]
        sections["security_testing"] = [
            {"test_id": f"SEC-{release_id.split('-')[-1]}-{i+1:03d}",
             "type": pick(seed("sec", i), ["DAST", "Pen Test", "Prompt Injection", "API Fuzzing"]),
             "findings": between(seed("secf", i), 0, 8), "status": pick(seed("secs", i), ["Pass", "Conditional", "Fail"])}
            for i in range(12)
        ]
        sections["performance_testing"] = [
            {"test_id": f"PERF-{release_id.split('-')[-1]}-{i+1:03d}",
             "scenario": pick(seed("perf", i), ["Peak login", "Payment burst", "AI inference load"]),
             "tps": between(seed("perft", i), 800, 4200), "status": pick(seed("perfs", i), ["Pass", "Tuned"])}
            for i in range(10)
        ]
        sections["defects"] = [
            {"defect_id": d["defect_id"], "test_id": t["test_id"], "severity": d["severity"],
             "summary": d["summary"], "status": pick(seed("dfst", t["test_id"], d["defect_id"]), ["Open", "Fixed", "Verified"]),
             "application": d["application"]}
            for t in testing
            for d in t.get("defect_records", [])
        ]
        sections["evidence_repository"] = [
            {"evidence_id": e["evidence_id"], "title": e["title"], "control": e["control_id"],
             "status": e["status"], "collected": e["collected_date"]}
            for e in all_evidence[:28]
        ]

    elif stage_key == "go-live":
        checklist = go_live.get("checklist", [])
        sections["cab_approvals"] = [
            {"cab_id": f"CAB-{release_id.split('-')[-1]}-{i+1:03d}",
             "authority": pick(seed("cab", i), ["CAB Chair", "CIO Office", "Audit Committee"]),
             "decision": pick(seed("cabd", i), ["Approved", "Conditional", "Pending"]),
             "date": (ANCHOR - timedelta(days=between(seed("cabdt", i), 3, 21))).strftime("%Y-%m-%d")}
            for i in range(6)
        ]
        sections["deployment_checklist"] = [
            {"item_id": c["item_id"], "item": c["item"], "application": c["application"],
             "owner": c["owner"], "status": c["status"]}
            for c in checklist
        ]
        sections["rollback_plan"] = [
            {"plan_id": f"RB-{release_id.split('-')[-1]}", "application": app, "rto": "30 min",
             "last_drill": (ANCHOR - timedelta(days=45)).strftime("%Y-%m-%d"), "status": "Validated"},
            {"plan_id": f"RB-{release_id.split('-')[-1]}-B", "application": pick(seed("rba", 1), apps),
             "rto": "45 min", "last_drill": (ANCHOR - timedelta(days=62)).strftime("%Y-%m-%d"), "status": "Validated"},
        ]
        sections["production_validation"] = [
            {"check_id": f"PV-{release_id.split('-')[-1]}-{i+1:03d}",
             "check": pick(seed("pv", i), ["Health endpoints green", "Smoke tests pass", "Monitoring alerts configured"]),
             "application": pick(seed("pva", i), apps), "status": pick(seed("pvs", i), ["Pass", "In Progress"])}
            for i in range(12)
        ]
        sections["hypercare"] = [
            {"ticket_id": f"HC-{release_id.split('-')[-1]}-{i+1:03d}",
             "issue": pick(seed("hc", i), ["Latency spike on auth", "Intermittent timeout on UPI", "Log volume alert"]),
             "severity": pick(seed("hcsev", i), ["High", "Medium", "Low"]),
             "status": pick(seed("hcs", i), ["Resolved", "Monitoring", "Open"])}
            for i in range(10)
        ]
        sections["closure_report"] = [
            {"report_id": f"CLR-{release_id.split('-')[-1]}", "release": release["name"],
             "go_live_date": release.get("target_date", ""), "status": go_live.get("final_approval", "Pending"),
             "observations": go_live.get("open_observations", 0), "exceptions": go_live.get("exceptions_pending", 0)},
        ]
        sections["audit_trail"] = _audit_rows(detail)

    tabs = STAGE_DASHBOARD_SECTIONS.get(stage_key, [])
    return {"tabs": tabs, "sections": sections, "stage_key": stage_key, "slug": STAGE_KEY_TO_SLUG.get(stage_key, stage_key)}
