"""Enterprise governance knowledge base — mock data for control lineage & reuse."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from modules.shared.utils.demo_data_standards import BANKING_APPLICATIONS, BANKING_OWNERS, between, pick, seed

ANCHOR = __import__("datetime").date(2026, 5, 28)

_KB_APPS = [
    "Net Banking", "Mobile Banking", "UPI Gateway", "CRM", "Treasury",
    "Trade Finance", "Payments", "Core Banking", "Cards", "Data Lake", "Fraud Monitoring",
]

_REUSE_PATTERNS = [
    "Zero Trust API Gateway", "Input Validation Library", "Immutable Audit Log Pipeline",
    "OAuth2/OIDC Federation", "RAG Data-Flow Security", "HSM Token Vault Integration",
    "Prompt Injection Test Suite", "DR Failover Blueprint", "Micro-segmentation Mesh",
]

_REGULATORY_MAP = [
    "RBI Master Direction — IT Governance", "PCI DSS v4.0 Req 8.3", "NPCI UPI Security Circular",
    "RBI Cyber Security Framework", "DPSC Baseline v2025", "ISO 27001 A.9.4",
]

_ROOT_CAUSES = [
    "Incomplete evidence lifecycle documentation", "Stale SAST scan beyond 90-day window",
    "Missing compensating control for legacy integration", "Repeat gap — design not propagated to dev",
    "Third-party API without rate limiting", "AI prompt guardrail not deployed to production",
]

_COMPENSATING = [
    "Enhanced monitoring with 24×7 SOC alerting", "Manual weekly access review until automation live",
    "WAF rule set compensating for missing input validation on legacy endpoint",
    "Temporary network segmentation pending micro-segmentation rollout",
]


def _apps_for_control(control_id: str, count: int = 11) -> list[str]:
    s = seed("kbapps", control_id)
    n = min(count, len(_KB_APPS))
    ordered = list(_KB_APPS)
    start = between(s, 0, max(len(ordered) - n, 0))
    return ordered[start:start + n]


def build_control_knowledge_repository(
    control: dict, release: dict, stage_key: str, framework: str,
) -> dict[str, Any]:
    cid = control["control_id"]
    s = seed("kbctrl", cid, release["id"])
    apps = _apps_for_control(cid)
    implementing = apps[:between(s >> 2, 6, 9)]
    failed = apps[between(s >> 4, 7, 9):between(s >> 4, 7, 9) + between(s >> 6, 1, 3)]
    closed_obs = apps[between(s >> 8, 3, 6):between(s >> 8, 3, 6) + between(s >> 10, 2, 4)]
    closed_n = between(s >> 12, 28, 38)
    open_n = between(s >> 14, 1, 5)

    def _reuse_rows(kind: str, n: int) -> list[dict]:
        rows = []
        for i in range(n):
            rs = seed("kbr", cid, kind, i)
            app = pick(rs, apps)
            rows.append({
                "reference_id": f"{kind[:3].upper()}-REU-{cid}-{i+1:02d}",
                "application": app,
                "release": pick(rs >> 2, ["REL-2025-Q4-NB", "REL-2025-Q3-MB", "REL-2026-Q1-PAY", release["id"], "REL-2025-Q2-CRM"]),
                "status": pick(rs >> 4, ["Approved", "Reused", "Closed", "Active"]),
                "owner": pick(rs >> 6, BANKING_OWNERS),
                "closure_date": (ANCHOR - timedelta(days=between(rs >> 8, 30, 800))).strftime("%Y-%m-%d"),
                "summary": pick(rs >> 10, [
                    f"Prior {framework} implementation validated for {app}",
                    "Reuse approved — scope delta documented",
                    "Pattern adopted from enterprise reference architecture",
                ]),
            })
        return rows

    return {
        "profile": {
            "control_id": cid,
            "control_name": control.get("control_description", "")[:72],
            "control_category": pick(s >> 16, ["Access Control", "Data Protection", "Logging & Monitoring", "Secure Development", "AI Governance"]),
            "risk_rating": pick(s >> 18, ["Critical", "High", "High", "Medium"]),
            "control_owner": control.get("owner", pick(s, BANKING_OWNERS)),
            "control_objective": f"Ensure {control.get('control_description', 'control')[:80]} is implemented, evidenced, and auditable across digital channels.",
            "control_description": control.get("control_description", ""),
            "regulatory_mapping": ", ".join(pick(seed("kbreg", cid, i), _REGULATORY_MAP) for i in range(3)),
            "framework_mapping": f"{framework} · {pick(s >> 22, ['PCI DSS', 'AppSec', 'DPSC', 'AI Governance', 'VAPT'])}",
        },
        "summary": {
            "total_applications": len(apps),
            "closed_observations": closed_n,
            "open_observations": open_n,
            "apps_using": apps,
            "apps_implementing": implementing,
            "apps_failed": failed or [apps[-1]],
            "apps_closed_observations": closed_obs,
        },
        "tabs": {
            "requirement_reuse": {"label": "Requirement Reuse", "rows": _reuse_rows("REQ", between(s >> 24, 4, 7))},
            "design_reuse": {"label": "Design Reuse", "rows": _reuse_rows("DSG", between(s >> 26, 4, 6))},
            "development_reuse": {"label": "Development Reuse", "rows": _reuse_rows("DEV", between(s >> 28, 4, 7))},
            "testing_reuse": {"label": "Testing Reuse", "rows": _reuse_rows("TST", between(s >> 30, 4, 6))},
            "audit_reuse": {"label": "Audit Reuse", "rows": _reuse_rows("AUD", between(s >> 32, 3, 5))},
            "evidence_reuse": {"label": "Evidence Reuse", "rows": _reuse_rows("EVD", between(s >> 34, 5, 8))},
        },
    }


def SDLC_FRAMEWORKS_EXTRA() -> str:
    return pick(seed("fwextra"), ["PCI DSS", "AppSec", "DPSC", "AI Governance", "VAPT"])


def build_audit_observation_kb(control: dict, history: dict, framework: str) -> dict[str, Any]:
    cid = control["control_id"]
    s = seed("kbobs", cid)
    apps = _apps_for_control(cid, 8)

    def _obs_rows(source: str, n: int, status: str) -> list[dict]:
        rows = []
        for i in range(n):
            os = seed("kbob", cid, source, i)
            rows.append({
                "observation_id": f"OBS-{pick(os, ['2023', '2024', '2025', '2026'])}-{between(os >> 2, 100, 999)}",
                "application": pick(os >> 4, apps),
                "audit_year": pick(os >> 6, ["FY2023", "FY2024", "FY2025", "Q1-FY2026"]),
                "severity": pick(os >> 8, ["Critical", "High", "Medium", "Low"]),
                "closure_status": status,
                "summary": pick(os >> 10, [
                    f"{framework} control gap — evidence lifecycle incomplete",
                    "Repeat observation — design not propagated to implementation",
                    "Compensating control accepted pending remediation",
                ]),
            })
        return rows

    open_obs = _obs_rows("open", between(s >> 2, 2, 4), "Open")
    closed_obs = _obs_rows("closed", between(s >> 4, 5, 8), "Closed")
    repeat_obs = _obs_rows("repeat", between(s >> 6, 2, 4), "Closed — Repeat")

    closure_packages = []
    for i, obs in enumerate(closed_obs[:4]):
        cs = seed("kbclp", cid, i)
        closure_packages.append({
            "observation_id": obs["observation_id"],
            "evidence_used": pick(cs, ["VAPT closure report", "SAST scan + CAB minutes", "Architecture sign-off pack", "DR drill attestation"]),
            "owner": pick(cs >> 2, BANKING_OWNERS),
            "approver": pick(cs >> 4, ["Internal Audit", "Compliance Head", "CIO Office"]),
            "closure_comments": pick(cs >> 6, [
                "Evidence validated in ECS repository; observation closed.",
                "Management response accepted; 90-day monitoring period.",
                "Repeat finding — root cause addressed via design pattern reuse.",
            ]),
        })

    return {
        "open_observations": open_obs,
        "closed_observations": closed_obs,
        "repeat_observations": repeat_obs,
        "root_causes": [{"cause": pick(seed("kbrc", cid, i), _ROOT_CAUSES), "frequency": between(seed("kbrcf", cid, i), 1, 6)} for i in range(4)],
        "compensating_controls": [{"control": pick(seed("kbcomp", cid, i), _COMPENSATING), "application": pick(seed("kbcompa", cid, i), apps)} for i in range(3)],
        "closure_packages": closure_packages,
    }


def build_knowledge_graph(control: dict, release: dict, framework: str, stage_key: str) -> dict[str, Any]:
    cid = control["control_id"]
    app = control.get("application", release["application"])
    nodes = [
        {"id": f"fw:{framework}", "label": framework, "type": "framework", "drill_metric": "framework", "drill_id": framework},
        {"id": f"ctrl:{cid}", "label": cid, "type": "control", "drill_metric": "control", "drill_id": cid},
        {"id": f"app:{app}", "label": app, "type": "application", "drill_metric": "", "drill_id": ""},
        {"id": "st:requirement", "label": "Requirement", "type": "stage", "drill_metric": "lifecycle_step", "drill_id": f"{cid}::requirement"},
        {"id": "st:design", "label": "Design", "type": "stage", "drill_metric": "lifecycle_step", "drill_id": f"{cid}::design"},
        {"id": "st:development", "label": "Development", "type": "stage", "drill_metric": "lifecycle_step", "drill_id": f"{cid}::development"},
        {"id": "st:testing", "label": "Testing", "type": "stage", "drill_metric": "lifecycle_step", "drill_id": f"{cid}::testing"},
        {"id": "st:go-live", "label": "Go-Live", "type": "stage", "drill_metric": "lifecycle_step", "drill_id": f"{cid}::go-live"},
        {"id": "st:audit", "label": "Audit", "type": "stage", "drill_metric": "lifecycle_step", "drill_id": f"{cid}::audit"},
        {"id": f"evd:{cid}-1", "label": "Evidence Pack", "type": "evidence", "drill_metric": "evidence", "drill_id": f"EVD-{stage_key[:3].upper()}-001"},
        {"id": f"obs:{cid}", "label": "Audit Observation", "type": "observation", "drill_metric": "history_observation", "drill_id": f"H-OBS-{cid}-01"},
        {"id": "cls:closure", "label": "Closure", "type": "closure", "drill_metric": "history_closure", "drill_id": f"H-CLS-{cid}-01"},
    ]
    edges = [
        ("fw:" + framework, f"ctrl:{cid}"),
        (f"ctrl:{cid}", f"app:{app}"),
        (f"ctrl:{cid}", "st:requirement"),
        ("st:requirement", "st:design"),
        ("st:design", "st:development"),
        ("st:development", "st:testing"),
        ("st:testing", "st:go-live"),
        ("st:go-live", "st:audit"),
        (f"ctrl:{cid}", f"evd:{cid}-1"),
        ("st:audit", f"obs:{cid}"),
        (f"obs:{cid}", "cls:closure"),
    ]
    return {"nodes": nodes, "edges": [{"from": a, "to": b} for a, b in edges], "control_id": cid}


def enrich_lifecycle_step_detail(
    step: dict, control: dict, release: dict, stage_key: str, framework: str,
) -> dict[str, Any]:
    sk = step.get("stage", "requirement")
    s = seed("lcstep", control["control_id"], sk)
    app = control.get("application", release["application"])
    return {
        **step,
        "documents": [
            {"doc_id": f"DOC-{sk[:3].upper()}-{between(seed('lcd', s, i), 1, 99):02d}", "title": pick(seed("lcdt", s, i), [
                f"{sk.title()} governance artifact — {app}", f"Signed {framework} checklist", f"CAB approval excerpt",
            ]), "status": pick(seed("lcds", s, i), ["Approved", "In Review"])}
            for i in range(between(s >> 2, 2, 4))
        ],
        "evidence": [
            {"evidence_id": f"EVD-LC-{sk[:3].upper()}-{i+1}", "title": pick(seed("lce", s, i), ["Scan report", "Approval email", "Screenshot", "CAB minutes"]),
             "status": pick(seed("lces", s, i), ["Approved", "Pending"])}
            for i in range(between(s >> 4, 2, 5))
        ],
        "approvals": [
            {"approver": pick(seed("lca", s, i), ["AppSec CoE", "Internal Audit", "CAB Chair", "Enterprise Architecture"]),
             "date": (ANCHOR - timedelta(days=between(seed("lcad", s, i), 1, 60))).strftime("%Y-%m-%d"),
             "status": pick(seed("lcas", s, i), ["Approved", "Conditional"])}
            for i in range(between(s >> 6, 1, 3))
        ],
        "observations": [
            {"obs_id": f"OBS-LC-{between(seed('lco', s, i), 100, 999)}", "severity": pick(seed("lcosev", s, i), ["High", "Medium"]),
             "status": pick(seed("lcost", s, i), ["Open", "Closed"])}
            for i in range(between(s >> 8, 0, 2))
        ],
        "exceptions": [
            {"exception_id": f"EXC-LC-{between(seed('lcx', s, i), 10, 99)}", "summary": "Temporary waiver — hypercare monitoring",
             "status": pick(seed("lcxs", s, i), ["Active", "Expired"])}
            for i in range(between(s >> 10, 0, 2))
        ],
    }


def build_knowledge_reuse_scores(release_id: str) -> dict[str, Any]:
    s = seed("reusekpi", release_id)
    breakdown = {
        "requirement": round(between(s, 68, 86) + (s % 7) / 10, 1),
        "design": round(between(s >> 2, 62, 82) + ((s >> 2) % 7) / 10, 1),
        "code": round(between(s >> 4, 58, 78) + ((s >> 4) % 7) / 10, 1),
        "test": round(between(s >> 6, 70, 88) + ((s >> 6) % 7) / 10, 1),
        "audit": round(between(s >> 8, 72, 90) + ((s >> 8) % 7) / 10, 1),
        "evidence": round(between(s >> 10, 65, 85) + ((s >> 10) % 7) / 10, 1),
    }
    overall = round(sum(breakdown.values()) / len(breakdown), 1)
    reused = between(s >> 12, 142, 218)
    required = between(s >> 14, 185, 265)
    return {
        "overall_pct": overall,
        "formula": f"{reused} historical assets reused / {required} total assets required",
        "reused_count": reused,
        "required_count": required,
        "breakdown": breakdown,
    }


def build_cross_app_analytics(release_id: str) -> dict[str, Any]:
    s = seed("crossapp", release_id)

    def _ctrl_rank(prefix: str, n: int, field: str) -> list[dict]:
        rows = []
        for i in range(n):
            rs = seed("car", release_id, prefix, i)
            cid = f"{pick(rs, ['APPSEC', 'PCI', 'DPSC', 'AI-GOV', 'VAPT'])}-{between(rs >> 2, 1, 99):02d}"
            rows.append({
                "control_id": cid,
                "application_count": between(rs >> 4, 4, 11),
                "framework": pick(rs >> 6, ["AppSec", "PCI DSS", "DPSC", "AI Governance"]),
                field: between(rs >> 8, 3, 34) if field != "reuse_count" else between(rs >> 8, 8, 42),
                "top_application": pick(rs >> 10, _KB_APPS),
            })
        return rows

    return {
        "top_reused_controls": _ctrl_rank("reuse", 8, "reuse_count"),
        "top_failed_controls": _ctrl_rank("fail", 8, "failure_count"),
        "common_findings": [
            {"finding": pick(seed("cf", release_id, i), [
                "Incomplete MFA on privileged API", "Stale SAST evidence beyond 90 days",
                "Missing AI prompt guardrail in production", "DR failover test not documented",
                "Session timeout non-compliance on mobile channel",
            ]), "occurrences": between(seed("cff", release_id, i), 4, 18), "framework": pick(seed("cffw", release_id, i), ["AppSec", "PCI DSS", "AI Governance"])}
            for i in range(6)
        ],
        "highest_reuse_apps": [
            {"application": app, "reuse_score": round(between(seed("hra", release_id, app), 72, 96) + (seed("hra", release_id, app) % 9) / 10, 1),
             "controls_reused": between(seed("hrac", release_id, app), 12, 48)}
            for app in _KB_APPS[:6]
        ],
        "highest_exception_apps": [
            {"application": app, "exceptions": between(seed("hea", release_id, app), 2, 14),
             "open": between(seed("heao", release_id, app), 1, 5)}
            for app in _KB_APPS[:6]
        ],
        "highest_maturity_apps": sorted([
            {"application": app, "maturity_score": round(between(seed("hma", release_id, app), 68, 97) + (seed("hma", release_id, app) % 9) / 10, 1),
             "governance_tier": pick(seed("hmat", release_id, app), ["Leading", "Managed", "Defined", "Optimizing"])}
            for app in _KB_APPS[:8]
        ], key=lambda x: x["maturity_score"], reverse=True)[:6],
    }


def build_requirement_knowledge(doc: dict, release: dict, app: str, fw: str, s: int) -> dict[str, Any]:
    hist_rows = []
    for i in range(between(s >> 2, 4, 6)):
        hs = seed("reqhist", s, i)
        hist_rows.append({
            "requirement_id": f"REQ-HIST-{between(hs, 100, 999)}",
            "application": pick(hs >> 2, _KB_APPS),
            "release": pick(hs >> 4, ["REL-2025-Q4-NB", "REL-2025-Q3-MB", "REL-2026-Q1-PAY"]),
            "status": pick(hs >> 6, ["Closed", "Approved", "Reused"]),
            "owner": pick(hs >> 8, BANKING_OWNERS),
            "closure_date": (ANCHOR - timedelta(days=between(hs >> 10, 60, 700))).strftime("%Y-%m-%d"),
        })
    return {
        "historical_requirement_references": hist_rows,
        "recommended_language": (
            f"The {app} release shall implement {fw} control requirements with measurable acceptance criteria, "
            f"owner accountability, and ECS evidence repository linkage within 30 days of requirement sign-off."
        ),
        "previous_approved_text": (
            f"FY2025 Net Banking release — requirement approved verbatim: authentication controls for tier-1 APIs "
            f"must enforce MFA, session binding, and immutable audit logging per RBI Master Direction."
        ),
        "control_interpretation": f"Compliance interprets this as mandatory for all tier-1 {app} endpoints handling customer PII or payment initiation.",
        "regulatory_explanation": pick(s >> 4, _REGULATORY_MAP),
        "audit_explanation": "Internal audit will sample 10% of requirements for traceability to control ID and evidence pack completeness.",
        "control_intent": "Prevent unauthorized access and ensure auditable governance across the SDLC lifecycle.",
        "business_risk": "Regulatory finding, customer data breach, release certification delay, and repeat audit observation.",
        "reuse_action": "Reuse this Requirement",
    }


def build_design_knowledge(release: dict, app: str, fw: str, s: int) -> dict[str, Any]:
    approved = []
    for i, dapp in enumerate(["Net Banking", "Mobile Banking", "CRM", "Data Lake", "Payments"]):
        ds = seed("dsgkb", s, dapp)
        approved.append({
            "application": dapp,
            "release": pick(ds >> 2, ["REL-2025-Q4-NB", "REL-2025-Q3-MB", "REL-2026-Q1-PAY"]),
            "approval_date": (ANCHOR - timedelta(days=between(ds >> 4, 90, 600))).strftime("%Y-%m-%d"),
            "architect": pick(ds >> 6, ["Enterprise Architecture", "A. Sharma", "R. Mehta"]),
            "reviewer": pick(ds >> 8, ["AppSec CoE", "Internal Audit", "Compliance Head"]),
            "status": "Approved",
            "title": pick(ds >> 10, ["Zero-trust API gateway", "RAG security design", "HSM integration", "DR topology"]),
        })
    patterns = []
    for i, pat in enumerate(_REUSE_PATTERNS[:5]):
        ps = seed("dsgpat", s, pat)
        used = pick(ps, [["Mobile Banking", "UPI Gateway", "Net Banking"], ["Net Banking", "CRM", "Mobile Banking"], ["Payments", "Core Banking"]])
        patterns.append({
            "pattern": pat,
            "used_in": used if isinstance(used, list) else [used],
            "reference_architecture": "Available" if between(ps >> 2, 0, 1) else "Available",
            "diagram": pick(ps >> 4, ["Available", "Available", "Pending"]),
            "review_comments": pick(ps >> 6, ["Available", "Available"]),
        })
    return {
        "historical_design_knowledge_base": approved,
        "reusable_design_patterns": patterns,
        "architecture_patterns": ["Event-driven audit pipeline", "Multi-region active-passive DR", "API gateway zero-trust mesh"],
        "reference_architectures": [f"{a} — approved {fw} reference" for a in _DESIGN_APPS()],
        "security_architecture_examples": ["OAuth2/OIDC federation", "Micro-segmentation for payment switch", "AI inference guardrail layer"],
    }


def _DESIGN_APPS() -> list[str]:
    return ["Net Banking", "Mobile Banking", "CRM", "Data Lake", "Payments"]


def build_development_knowledge(release: dict, app: str, fw: str, s: int) -> dict[str, Any]:
    components = [
        {"component": "Input Validation Library", "technology": "Java / Spring", "repository": "gitlab.bank.com/platform/input-guard",
         "owner": "Platform Engineering", "controls": ["APPSEC-012", "APPSEC-019", "APPSEC-027"],
         "used_by": ["Net Banking", "CRM", "Mobile Banking"]},
        {"component": "Audit Log SDK", "technology": "Python / Node", "repository": "gitlab.bank.com/platform/audit-sdk",
         "owner": "Core Platform", "controls": ["APPSEC-031", "DPSC-008"], "used_by": ["Payments", "Core Banking", "UPI Gateway"]},
        {"component": "Secrets Manager Client", "technology": "Multi-lang", "repository": "gitlab.bank.com/security/secrets-client",
         "owner": "AppSec CoE", "controls": ["APPSEC-005", "PCI-003"], "used_by": ["Net Banking", "Cards", "Treasury"]},
    ]
    return {
        "implementation_knowledge_base": {
            "reusable_components": components,
            "shared_libraries": [c["component"] for c in components],
            "internal_frameworks": ["ECS Secure Dev Framework v2026", "AI Guardrail SDK"],
            "sdks": ["audit-sdk", "input-guard", "secrets-client", "token-vault-client"],
            "common_services": ["Identity Service", "Evidence Repository API", "Governance Policy Engine"],
            "microservices": ["auth-gateway", "audit-collector", "compliance-reporter"],
            "security_modules": ["WAF rule pack", "SAST gate plugin", "Dependency scanner"],
        },
        "reusable_code_pattern": "Decorator-based input validation with centralized policy enforcement and ECS evidence hook.",
        "secure_coding_examples": ["Parameterized SQL — JDBC template", "Output encoding — React CSP headers", "AI prompt sanitization — guardrail middleware"],
        "static_analysis_results": f"Last SAST run: {between(s >> 2, 0, 3)} Critical, {between(s >> 4, 2, 8)} High — all tracked in Jira.",
        "historical_remediation": [
            {"issue": "SQL injection in merchant API", "application": "UPI Gateway", "closure": "2025-08-14", "pattern": "Input Validation Library adoption"},
            {"issue": "Hardcoded secret in config", "application": "CRM", "closure": "2025-11-02", "pattern": "Secrets Manager Client migration"},
        ],
        "known_good_implementations": [
            {"application": "Net Banking", "control": "APPSEC-012", "repository": "netbank-api", "status": "Auditor accepted"},
            {"application": "Mobile Banking", "control": "APPSEC-019", "repository": "mobile-auth-svc", "status": "Reused in Q2 release"},
        ],
    }


def build_testing_knowledge(release: dict, app: str, fw: str, s: int) -> dict[str, Any]:
    packs = [
        {"pack_name": "Prompt Injection Tests", "used_in": ["AI Ops Assistant", "AI Governance", "Customer Support AI", "Fraud AI"],
         "pass_rate": "97%", "known_failures": 4, "last_execution": (ANCHOR - timedelta(days=7)).strftime("%Y-%m-%d")},
        {"pack_name": "OWASP ASVS L2 Security Suite", "used_in": ["Net Banking", "Mobile Banking", "UPI Gateway"],
         "pass_rate": "94%", "known_failures": 6, "last_execution": (ANCHOR - timedelta(days=3)).strftime("%Y-%m-%d")},
        {"pack_name": "PCI DSS Regression Pack", "used_in": ["Cards", "Payments", "Core Banking"],
         "pass_rate": "99%", "known_failures": 1, "last_execution": (ANCHOR - timedelta(days=14)).strftime("%Y-%m-%d")},
    ]
    test_cases = [
        {"test_case_id": f"TC-{between(seed('tkb', s, i), 1000, 9999)}", "control_id": f"APPSEC-{between(seed('tkbc', s, i), 1, 99):02d}",
         "application": pick(seed("tkba", s, i), _KB_APPS), "pass_rate": f"{between(seed('tkbp', s, i), 88, 100)}%",
         "last_execution": (ANCHOR - timedelta(days=between(seed("tkbd", s, i), 1, 45))).strftime("%Y-%m-%d")}
        for i in range(6)
    ]
    return {
        "reusable_test_knowledge": {
            "historical_test_cases": test_cases,
            "historical_vapt_scenarios": ["Authenticated API fuzzing", "Session fixation", "Privilege escalation via JWT"],
            "historical_uat_packs": ["Net Banking UAT v4.1", "Mobile onboarding UAT", "Payments switch UAT"],
            "historical_ai_validation_packs": ["Prompt injection battery", "Hallucination guardrail test", "PII leakage red-team"],
            "historical_regression_suites": ["Core regression — 847 cases", "Security regression — 124 cases"],
        },
        "test_packs": packs,
        "reuse_action": "Reuse Test Pack",
    }


def build_golive_knowledge(release: dict, app: str, s: int) -> dict[str, Any]:
    rows = []
    for i in range(6):
        gs = seed("glkb", release["id"], i)
        rows.append({
            "application": pick(gs, _KB_APPS),
            "release": pick(gs >> 2, ["REL-2025-Q4-NB", "REL-2025-Q3-MB", "REL-2025-Q2-PAY", release["name"]]),
            "go_live_date": (ANCHOR - timedelta(days=between(gs >> 4, 30, 500))).strftime("%Y-%m-%d"),
            "approval_authority": pick(gs >> 6, ["CAB Chair", "CIO Office", "Audit Committee"]),
            "result": pick(gs >> 8, ["Successful", "Successful with hypercare", "Rollback — DR issue resolved"]),
            "artifact": pick(gs >> 10, ["CAB approval package", "Rollback plan", "DR validation report", "Closure evidence pack"]),
        })
    return {"historical_go_live_repository": rows}


def build_document_viewer_tabs(
    artifact: dict, stage_key: str, doc: dict, release: dict, app: str, fw: str, s: int,
) -> dict[str, Any]:
    hist = artifact.get("historical_references") or artifact.get("historical_approved_references") or []
    evidence = artifact.get("required_evidence") or []
    ctrl_rows = []
    for sec in artifact.get("sections", []):
        if sec.get("type") == "table" and "control" in sec.get("title", "").lower():
            ctrl_rows.extend(sec.get("rows", []))

    stage_kb: dict[str, Any] = {}
    if stage_key == "requirement":
        stage_kb = build_requirement_knowledge(doc, release, app, fw, s)
    elif stage_key == "design":
        stage_kb = build_design_knowledge(release, app, fw, s)
    elif stage_key == "development":
        stage_kb = build_development_knowledge(release, app, fw, s)
    elif stage_key == "testing":
        stage_kb = build_testing_knowledge(release, app, fw, s)
    elif stage_key == "go-live":
        stage_kb = build_golive_knowledge(release, app, s)

    return {
        "overview": {
            "executive_summary": artifact.get("executive_summary", ""),
            "sections": artifact.get("sections", [])[:4],
            "stage_knowledge": stage_kb,
        },
        "control_mapping": {
            "rows": ctrl_rows or [
                {"control_id": f"{fw[:3].upper()}-023", "framework": fw, "description": doc.get("category", ""), "status": "Mapped"},
            ],
        },
        "historical_reuse": {"rows": hist, "stage_section": stage_kb},
        "related_applications": {
            "rows": [{"application": a, "tier": pick(seed("relapp", s, a), ["Tier-1", "Tier-2"]), "status": pick(seed("relapps", s, a), ["Active", "Implementing", "Closed obs"])}
                     for a in release.get("impacted_applications", [app]) + _KB_APPS[:4]][:8],
        },
        "related_observations": {
            "rows": [{"observation_id": h.get("observation_id", ""), "application": h.get("application"), "audit_year": h.get("audit_year"),
                      "severity": pick(seed("relobs", s, i), ["High", "Medium"]), "closure_status": "Closed"}
                     for i, h in enumerate(hist)],
        },
        "related_evidence": {"rows": evidence},
        "closure_packages": {
            "rows": [{"observation_id": h.get("observation_id"), "evidence_used": pick(seed("clsevd", s, i), evidence[0]["title"] if evidence else "Scan report"),
                      "owner": h.get("control_owner"), "approver": h.get("approval_authority"), "comments": h.get("summary", "")}
                     for i, h in enumerate(hist[:4])],
        },
        "lessons_learned": {
            "items": [
                "Reuse approved design patterns when scope is unchanged — reduces audit findings by 40%.",
                "Link evidence to control ID at development gate — accelerates auditor sampling.",
                "Cite historical closure references in CAB package — improves first-pass approval rate.",
                pick(seed("lesson", s), _ROOT_CAUSES) + " — address via enterprise reference implementation.",
            ],
        },
    }
