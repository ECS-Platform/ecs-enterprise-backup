"""Controlled SDLC document generator — CRD, CDD, CDVD, CTD, CGLD."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from modules.shared.utils.demo_data_standards import BANKING_OWNERS, between, pick, seed

ANCHOR = date(2026, 5, 28)

DOC_TYPES: dict[str, dict[str, str]] = {
    "requirement": {
        "code": "CRD", "label": "Controlled Requirement Document", "short": "Requirement Document",
        "column_label": "Controlled Requirement Document", "link_label": "Open Requirement Document",
    },
    "design": {
        "code": "CDD", "label": "Controlled Design Document", "short": "Design Document",
        "column_label": "Controlled Design Document", "link_label": "Open Design Document",
    },
    "development": {
        "code": "CDVD", "label": "Controlled Development Document", "short": "Development Document",
        "column_label": "Controlled Development Document", "link_label": "Open Development Document",
    },
    "testing": {
        "code": "CTD", "label": "Controlled Testing Document", "short": "Testing Document",
        "column_label": "Controlled Testing Document", "link_label": "Open Testing Document",
    },
    "go-live": {
        "code": "CGLD", "label": "Controlled Go-Live Readiness Document", "short": "Go-Live Document",
        "column_label": "Controlled Go-Live Document", "link_label": "Open Go-Live Document",
    },
}

STAGE_KEYS = tuple(DOC_TYPES.keys())

_APPROVAL_ROLES = [
    "Application Owner", "Solution Architect", "AppSec Lead", "Internal Audit",
    "Compliance Officer", "CAB Chair", "Model Risk", "S. Nair (Auditor)",
]


def document_id(stage_key: str, framework: str, control_id: str, application: str) -> str:
    meta = DOC_TYPES[stage_key]
    fw = framework.replace(" ", "")[:4].upper()
    app = application.replace(" ", "")[:3].upper()
    ctrl = control_id.replace(" ", "-").upper()
    return f"{meta['code']}-{fw}-{ctrl}-{app}"


def _observation_id(framework: str, control_id: str, application: str) -> str:
    fw = framework.replace(" ", "")[:3].upper()
    return f"OBS-{fw}-{control_id.replace('-', '')[:8]}-{pick(seed('obs', framework, control_id, application), ['001', '014', '027'])}"


def _evidence_id(framework: str, control_id: str, application: str, stage_key: str) -> str:
    s = seed("evd", framework, control_id, application, stage_key)
    return f"EVD-{DOC_TYPES[stage_key]['code']}-{between(s, 1000, 9999)}"


def _approval_history(s: int, prefix: str, n: int = 5) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    statuses = ["Draft", "In Review", "Approved", "Needs Rework", "Closed"]
    for i in range(n):
        ps = seed(prefix, "appr", s, i)
        prev = pick(ps, statuses)
        new = pick(ps >> 2, statuses)
        rows.append({
            "user": pick(ps >> 4, BANKING_OWNERS),
            "role": pick(ps >> 6, _APPROVAL_ROLES),
            "timestamp": (ANCHOR - timedelta(days=n - i)).strftime("%Y-%m-%d %H:%M UTC"),
            "previous_status": prev,
            "new_status": new,
            "comments": f"{prefix} gate review — {pick(ps >> 8, ['Scope confirmed', 'Minor rework requested', 'Approved with conditions', 'Signed off'])}",
        })
    return rows


def _section(title: str, body: str) -> dict[str, str]:
    return {"title": title, "body": body}


def generate_crd(application: str, framework: str, domain: str, control_id: str, control_name: str) -> dict[str, Any]:
    s = seed("crd", application, framework, control_id)
    owner = pick(s, BANKING_OWNERS)
    return {
        "document_type": "CRD",
        "document_type_label": DOC_TYPES["requirement"]["label"],
        "document_id": document_id("requirement", framework, control_id, application),
        "application": application,
        "framework": framework,
        "domain": domain,
        "control_id": control_id,
        "control_name": control_name,
        "control_objective": f"Ensure {control_name.lower()} for {application} aligns with {framework} obligations in {domain}.",
        "owner": owner,
        "evidence_id": _evidence_id(framework, control_id, application, "requirement"),
        "observation_id": _observation_id(framework, control_id, application),
        "status": pick(s >> 2, ["Draft", "In Review", "Approved", "Pending App Owner Approval"]),
        "sections": [
            _section("Control Objective", f"Ensure {control_name.lower()} for {application} aligns with {framework} obligations in {domain}."),
            _section("Requirement Interpretation", f"Application team interprets {control_name} as enforceable MFA, session timeout ≤15m, and privileged access review every 90 days."),
            _section("Business Requirement", f"{application} must protect customer sessions and payment initiation with tier-1 availability ({between(s >> 6, 99, 999)/10}%)."),
            _section("Functional Requirement", f"Implement {control_name} with auditable workflows, owner attestation, and integration to SIEM correlation for {domain}."),
            _section("Non Functional Requirement", f"Latency impact < {between(s >> 8, 20, 80)}ms; support 10k TPS peak; DR RPO 15 minutes."),
            _section("Security Requirement", "Encrypt credentials in transit (TLS 1.2+); vault-stored secrets; break-glass procedure documented."),
            _section("Regulatory Requirement", pick(s >> 10, ["RBI Cyber Security Framework §3.2", "PCI DSS 8.3 MFA", "DPSC Authentication baseline v2025"])),
            _section("Stakeholders", f"Owner: {owner}; AppSec: T. Kapoor; Audit: S. Nair; Business: Retail Banking PMO."),
            _section("Acceptance Criteria", "100% privileged users on MFA; zero open Critical observations; auditor sample pass rate ≥95%."),
        ],
        "requirement_approval_history": _approval_history(s, "CRD"),
    }


def generate_cdd(application: str, framework: str, domain: str, control_id: str, control_name: str) -> dict[str, Any]:
    s = seed("cdd", application, framework, control_id)
    return {
        "document_type": "CDD",
        "document_type_label": DOC_TYPES["design"]["label"],
        "document_id": document_id("design", framework, control_id, application),
        "application": application,
        "framework": framework,
        "domain": domain,
        "control_id": control_id,
        "control_name": control_name,
        "owner": pick(s, BANKING_OWNERS),
        "evidence_id": _evidence_id(framework, control_id, application, "design"),
        "observation_id": _observation_id(framework, control_id, application),
        "status": pick(s >> 2, ["In Review", "Approved", "Draft"]),
        "sections": [
            _section("Architecture Impact", f"{application} API tier adopts zero-trust ingress; {domain} control {control_id} spans DMZ and app subnet."),
            _section("Design Approach", pick(s >> 4, ["OAuth2/OIDC federation via corporate IdP", "Service mesh mTLS between microservices", "HSM-backed key wrap for session tokens"])),
            _section("Control Design Pattern", f"Pattern: {control_name} — centralized policy enforcement at API gateway with local enforcement hooks."),
            _section("Data Flow", f"User → WAF → API GW → {application} auth service → policy engine → audit log pipeline → ECS evidence store."),
            _section("Integration Points", "IdP (Azure AD), API Gateway, SIEM (Splunk), ECS evidence repository, ServiceNow change records."),
            _section("Security Design", "TLS 1.3, cert pinning for mobile, rate limiting, geo-fencing for high-risk transactions."),
            _section("AI Governance Design", "Prompt guardrails on copilot-assisted code review; no PII in LLM context for design assistants."),
            _section("Evidence Required", "HLD/LLD diagrams, threat model, design review minutes, AppSec sign-off."),
        ],
        "design_approval_history": _approval_history(s, "CDD"),
    }


def generate_cdvd(application: str, framework: str, domain: str, control_id: str, control_name: str) -> dict[str, Any]:
    s = seed("cdvd", application, framework, control_id)
    return {
        "document_type": "CDVD",
        "document_type_label": DOC_TYPES["development"]["label"],
        "document_id": document_id("development", framework, control_id, application),
        "application": application,
        "framework": framework,
        "domain": domain,
        "control_id": control_id,
        "control_name": control_name,
        "owner": pick(s, BANKING_OWNERS),
        "evidence_id": _evidence_id(framework, control_id, application, "development"),
        "observation_id": _observation_id(framework, control_id, application),
        "status": pick(s >> 2, ["In Development", "Code Review", "Approved"]),
        "sections": [
            _section("Implementation Logic", f"Implement {control_name} via shared auth library v3.2 — middleware validates {control_id} on every authenticated request; fails closed on policy miss."),
            _section("Code Components", f"auth-service, session-manager, policy-enforcer — repos: bank/{application.lower().replace(' ', '-')}-auth"),
            _section("Configuration Items", f"CI-{control_id}: MFA policy JSON, session TTL config, HSM key alias {between(s >> 6, 100, 999)}"),
            _section("API Changes", "POST /v2/session/validate — adds step-up auth header; deprecates legacy cookie-only flow."),
            _section("Guardrails Implemented", "SAST gate in CI; secret scanning; dependency check for auth libraries."),
            _section("Prompt Controls", "Copilot disabled on auth module; manual review required for crypto code."),
            _section("Logging", "Structured JSON logs: user_id hash, session_id, policy_id, decision, latency_ms → SIEM."),
            _section("Monitoring", "Dashboard: failed MFA rate, session anomalies, break-glass usage — PagerDuty Sev2 thresholds."),
            _section("Evidence Generated", "Build logs, merge requests, SAST reports, deployment manifest, config export."),
            _section("Developer Signoff", f"{pick(s >> 8, BANKING_OWNERS)} — Dev Lead, {ANCHOR.strftime('%Y-%m-%d')}"),
        ],
        "developer_signoff_history": _approval_history(s, "CDVD"),
    }


def generate_ctd(application: str, framework: str, domain: str, control_id: str, control_name: str) -> dict[str, Any]:
    s = seed("ctd", application, framework, control_id)
    return {
        "document_type": "CTD",
        "document_type_label": DOC_TYPES["testing"]["label"],
        "document_id": document_id("testing", framework, control_id, application),
        "application": application,
        "framework": framework,
        "domain": domain,
        "control_id": control_id,
        "control_name": control_name,
        "owner": pick(s, BANKING_OWNERS),
        "evidence_id": _evidence_id(framework, control_id, application, "testing"),
        "observation_id": _observation_id(framework, control_id, application),
        "status": pick(s >> 2, ["Testing In Progress", "Retest Required", "Passed"]),
        "sections": [
            _section("Test Strategy", f"Risk-based testing for {control_id} — combine SAST/DAST, manual pen-test samples, and UAT scenarios on {application}."),
            _section("Positive Tests", "Valid MFA enrollment; successful session refresh; privileged access with step-up auth."),
            _section("Negative Tests", "Expired session rejected; invalid OTP lockout; tampered token rejected; break-glass audit trail verified."),
            _section("Security Tests", "TLS downgrade blocked; brute-force throttling; session fixation prevention."),
            _section("AI Safety Tests", "Prompt injection attempts on support bot blocked; no credential echo in LLM responses."),
            _section("Hallucination Tests", "Copilot suggestions validated against secure coding standards — zero unsafe crypto patterns accepted."),
            _section("Bias Tests", "Fraud model fairness review — demographic parity within tolerance for pilot cohort."),
            _section("Performance Tests", f"Auth endpoint sustained {between(s >> 6, 500, 2000)} RPS with p99 < 200ms."),
            _section("Evidence Collected", "Test execution reports, defect logs, retest confirmations, scan exports attached to ECS."),
            _section("Retest Results", pick(s >> 12, ["All Critical/High closed", "1 Medium pending — target fix next sprint", "Retest passed 2026-05-22"])),
        ],
        "testing_approval_history": _approval_history(s, "CTD"),
    }


def generate_cgld(application: str, framework: str, domain: str, control_id: str, control_name: str) -> dict[str, Any]:
    s = seed("cgld", application, framework, control_id)
    return {
        "document_type": "CGLD",
        "document_type_label": DOC_TYPES["go-live"]["label"],
        "document_id": document_id("go-live", framework, control_id, application),
        "application": application,
        "framework": framework,
        "domain": domain,
        "control_id": control_id,
        "control_name": control_name,
        "owner": pick(s, BANKING_OWNERS),
        "evidence_id": _evidence_id(framework, control_id, application, "go-live"),
        "observation_id": _observation_id(framework, control_id, application),
        "status": pick(s >> 2, ["Ready for CAB", "Conditional Go-Live", "Approved"]),
        "sections": [
            _section("Readiness Checklist", f"✓ Requirements approved ✓ Design signed ✓ Dev complete ✓ Testing passed — {control_id}"),
            _section("Evidence Verification", f"All ECS evidence artefacts for {control_id} status Approved or Auditor Accepted."),
            _section("Control Verification", f"{control_name} implementation verified in pre-prod and prod-like environment."),
            _section("Pending Exceptions", f"{between(s >> 4, 0, 2)} time-bound exceptions — compensating monitoring in place."),
            _section("Risk Acceptance", pick(s >> 6, ["None — full compliance", "CIO accepted 1 Medium residual — 30-day remediation plan", "CAB waived low-risk doc gap"])),
            _section("Monitoring Setup", "SOC runbooks updated; dashboards live; on-call briefed for auth anomalies."),
            _section("Rollback Readiness", f"Blue/green deploy with {between(s >> 8, 5, 15)} minute rollback window validated."),
            _section("Production Approval", f"CAB approval ref CAB-{ANCHOR.year}-{between(s >> 10, 100, 999)} — window {ANCHOR.strftime('%Y-%m-%d')} 02:00 IST."),
            _section("Go Live Signoff", pick(s >> 12, ["GO — all gates green", "CONDITIONAL GO — monitor hypercare 14 days", "HOLD — retest required"])),
        ],
        "go_live_signoff_history": _approval_history(s, "CGLD"),
    }


_GENERATORS = {
    "requirement": generate_crd,
    "design": generate_cdd,
    "development": generate_cdvd,
    "testing": generate_ctd,
    "go-live": generate_cgld,
}


def generate_controlled_document(
    stage_key: str,
    application: str,
    framework: str,
    domain: str,
    control_id: str,
    control_name: str = "",
) -> dict[str, Any]:
    stage_key = stage_key.replace("_", "-")
    if stage_key == "requirements":
        stage_key = "requirement"
    if stage_key == "golive":
        stage_key = "go-live"
    gen = _GENERATORS.get(stage_key)
    if not gen:
        return {"ok": False, "error": f"Unknown stage: {stage_key}"}
    from modules.ai_sdlc.engines.ai_sdlc_workflow_engine import control_name_for
    cname = control_name or control_name_for(control_id)
    doc = gen(application, framework, domain, control_id, cname)
    doc["ok"] = True
    doc["stage_key"] = stage_key
    doc["view_label"] = DOC_TYPES[stage_key]["link_label"]
    return doc


def enrich_worklist_row(row: dict[str, Any], stage_key: str) -> dict[str, Any]:
    """Attach document, evidence, observation IDs to a worklist row."""
    app = row.get("application", "")
    fw = row.get("framework", "")
    domain = row.get("domain", "General")
    cid = row.get("control_id") or row.get("control", "")
    cname = row.get("control_name", "")
    doc = generate_controlled_document(stage_key, app, fw, domain, cid, cname)
    row = {**row}
    row["document_id"] = doc["document_id"]
    row["document_type"] = doc["document_type"]
    row["document_view_label"] = DOC_TYPES[stage_key]["link_label"]
    row["document_link_label"] = DOC_TYPES[stage_key]["link_label"]
    row["observation_id"] = doc.get("observation_id") or _observation_id(fw, cid, app)
    row["evidence_id"] = doc.get("evidence_id") or _evidence_id(fw, cid, app, stage_key)
    row["evidence_view_url"] = f"/mvp/ai-sdlc/evidence/view/{row['evidence_id']}"
    row["stage_key"] = stage_key
    return row


def document_counts() -> dict[str, int]:
    """Count generated documents across all worklist controls × stages."""
    from modules.ai_sdlc.engines.ai_sdlc_workflow_engine import _worklist_items
    counts = {meta["code"]: 0 for meta in DOC_TYPES.values()}
    for stage_key in STAGE_KEYS:
        code = DOC_TYPES[stage_key]["code"]
        items = _worklist_items(stage_key, 48)
        counts[code] = len(items)
    counts["total"] = sum(counts.values())
    return counts


def build_control_drill(application: str, framework: str, domain: str, control_id: str, control_name: str = "") -> dict[str, Any]:
    from modules.ai_sdlc.engines.ai_sdlc_workflow_engine import control_name_for
    s = seed("ctrl-drill", application, framework, control_id)
    cname = control_name or control_name_for(control_id)
    return {
        "type": "control",
        "title": f"{control_id} — {cname}",
        "control_id": control_id,
        "control_name": cname,
        "application": application,
        "framework": framework,
        "domain": domain,
        "owner": pick(s, BANKING_OWNERS),
        "status": pick(s >> 2, ["Implemented", "In Progress", "Gap Identified", "Approved"]),
        "evidence_count": between(s >> 4, 2, 12),
        "last_review": (ANCHOR - timedelta(days=between(s >> 6, 1, 45))).strftime("%Y-%m-%d"),
        "control_description": f"{framework} control {control_id} for {domain} on {application}.",
        "implementation_notes": pick(s >> 8, [
            "Control enforced at API gateway with quarterly access review.",
            "Automated scan + manual validation; compensating monitoring for batch jobs.",
        ]),
        "observation_id": _observation_id(framework, control_id, application),
    }


def build_observation_drill(observation_id: str, application: str = "", framework: str = "", control_id: str = "") -> dict[str, Any]:
    s = seed("obs-drill", observation_id, application, control_id)
    return {
        "type": "observation",
        "title": f"Observation {observation_id}",
        "observation_id": observation_id,
        "application": application or pick(s, ["Net Banking", "Mobile Banking", "UPI Gateway"]),
        "framework": framework or pick(s >> 2, ["DPSC", "VAPT", "Internal Audit Controls"]),
        "control_id": control_id or f"DPSC-AUTH-{between(s >> 4, 1, 3):02d}",
        "severity": pick(s >> 6, ["Critical", "High", "Medium", "Low"]),
        "status": pick(s >> 8, ["Open", "In Remediation", "Closed", "Accepted"]),
        "audit_year": pick(s >> 10, ["FY2024", "FY2025", "FY2026"]),
        "finding": pick(s >> 12, [
            "MFA not enforced for privileged admin accounts on payment initiation API.",
            "Session timeout exceeds DPSC baseline for mobile channel.",
            "Insufficient logging correlation for failed authentication events.",
        ]),
        "remediation_plan": "Implement step-up auth, reduce session TTL, export auth logs to SIEM with 90-day retention.",
        "owner": pick(s >> 14, BANKING_OWNERS),
        "target_date": (ANCHOR + timedelta(days=between(s >> 16, 7, 60))).strftime("%Y-%m-%d"),
    }


def build_controlled_evidence_viewer(evidence_id: str) -> dict[str, Any] | None:
    """Synthetic evidence viewer for controlled-document evidence IDs (EVD-*)."""
    if not evidence_id.startswith("EVD-"):
        return None
    from modules.ai_sdlc.engines.ai_sdlc_workflow_engine import control_name_for, _controls_for_framework
    s = seed("evd-view", evidence_id)
    parts = evidence_id.split("-")
    doc_code = parts[1] if len(parts) > 1 else "CRD"
    stage_key = next((k for k, m in DOC_TYPES.items() if m["code"] == doc_code), "requirement")
    app = pick(s, ["Net Banking", "Mobile Banking", "Core Banking", "UPI Gateway"])
    fw = pick(s >> 2, ["DPSC", "VAPT", "ITPP"])
    ctrl = pick(s >> 4, _controls_for_framework(fw))
    cid = ctrl["control_id"]
    return {
        "evidence_id": evidence_id,
        "document_name": f"{doc_code}_Evidence_{evidence_id}.pdf",
        "application": app,
        "framework": fw,
        "domain": ctrl["domain"],
        "control_id": cid,
        "control_name": control_name_for(cid),
        "control_description": f"Evidence artefact supporting {doc_code} for {cid} on {app}.",
        "artifact_type": f"{doc_code} Supporting Evidence",
        "status": pick(s >> 6, ["Approved", "In Review", "Pending"]),
        "owner": pick(s >> 8, BANKING_OWNERS),
        "uploaded_by": pick(s >> 10, BANKING_OWNERS),
        "upload_date": (ANCHOR - timedelta(days=between(s >> 12, 1, 30))).strftime("%Y-%m-%d"),
        "collected_date": (ANCHOR - timedelta(days=between(s >> 14, 1, 30))).strftime("%Y-%m-%d"),
        "stage": DOC_TYPES[stage_key]["short"],
        "files": [{"name": f"{doc_code}_Evidence_{evidence_id}.pdf", "uploaded_at": ANCHOR.strftime("%Y-%m-%d")}],
        "comments": [{"author": pick(s >> 16, BANKING_OWNERS), "text": "Evidence validated against control objective.", "at": _now_str()}],
        "approval_history": _approval_history(s, doc_code, 3),
        "audit_trail": [],
        "approved_by": "Security Reviewer",
        "approval_date": "15-May-2026",
        "finding_status": "Remediated",
        "remediation_date": "22-May-2026",
        "controls_covered": 4,
        "evidence_package": "Complete",
    }


def _now_str() -> str:
    return ANCHOR.strftime("%Y-%m-%d %H:%M UTC")


def render_document_html(doc: dict[str, Any]) -> str:
    """Render document sections as HTML for modal display."""
    parts = [
        f'<div class="mb-2"><span class="badge bg-primary">{doc.get("document_type")}</span> '
        f'<code class="small">{doc.get("document_id")}</code></div>',
        '<dl class="row small mb-3">',
        f'<dt class="col-3">Application</dt><dd class="col-9">{doc.get("application")}</dd>',
        f'<dt class="col-3">Framework</dt><dd class="col-9">{doc.get("framework")}</dd>',
        f'<dt class="col-3">Domain</dt><dd class="col-9">{doc.get("domain")}</dd>',
        f'<dt class="col-3">Control</dt><dd class="col-9">{doc.get("control_id")} — {doc.get("control_name", "")}</dd>',
        f'<dt class="col-3">Owner</dt><dd class="col-9">{doc.get("owner", "—")}</dd>',
        f'<dt class="col-3">Status</dt><dd class="col-9">{doc.get("status", "—")}</dd>',
        f'<dt class="col-3">Evidence</dt><dd class="col-9"><code>{doc.get("evidence_id", "—")}</code></dd>',
        f'<dt class="col-3">Observation</dt><dd class="col-9"><code>{doc.get("observation_id", "—")}</code></dd>',
        "</dl>",
    ]
    for sec in doc.get("sections", []):
        parts.append(f'<h6 class="text-muted small text-uppercase mt-2 mb-1">{sec["title"]}</h6>')
        parts.append(f'<p class="small mb-2">{sec["body"]}</p>')
    hist_key = next((k for k in doc if k.endswith("_history") and isinstance(doc[k], list)), None)
    if hist_key and doc[hist_key]:
        parts.append(f'<h6 class="text-muted small text-uppercase mt-3 mb-1">{hist_key.replace("_", " ").title()}</h6>')
        parts.append('<div class="table-responsive"><table class="table table-sm ecs-compact-table mb-0"><thead><tr>')
        parts.append("<th>User</th><th>Role</th><th>Timestamp</th><th>Previous</th><th>New</th><th>Comments</th></tr></thead><tbody>")
        for h in doc[hist_key]:
            parts.append(
                f"<tr><td>{h.get('user')}</td><td>{h.get('role')}</td><td>{h.get('timestamp')}</td>"
                f"<td>{h.get('previous_status')}</td><td>{h.get('new_status')}</td>"
                f'<td class="ecs-gov-wrap">{h.get("comments", "")}</td></tr>'
            )
        parts.append("</tbody></table></div>")
    return "".join(parts)
