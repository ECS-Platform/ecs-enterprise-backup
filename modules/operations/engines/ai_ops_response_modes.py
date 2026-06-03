"""Context-aware AI Ops Assistant response mode renderers — one investigation, eight perspectives."""

from __future__ import annotations

from modules.shared.services.chatbot_nav import action_link, framework_url, link_html, mvp_url

MODE_IDS = (
    "business", "technical", "executive", "audit",
    "compliance", "evidence", "incident", "root_cause",
)

_SCENARIO_KPIS: dict[str, dict] = {
    "net_banking": {
        "business": {
            "customers_affected": "1.2M",
            "transactions_delayed": "145,000",
            "business_severity": "High",
            "revenue_impact": "₹2.4 Cr estimated",
            "user_impact": "Login delays · session timeouts · delayed confirmations",
            "services_affected": ["Retail Internet Banking", "Bill Pay", "Fund Transfer", "Account Statement"],
        },
        "technical": {
            "failing_components": ["Nginx cluster (NETBANK-EDGE-01)", "CBS Oracle cluster", "Auth middleware tier", "Redis cache tier"],
            "servers": ["NETBANK-APP-03", "NETBANK-APP-04", "CBS-DB-PRIMARY", "CBS-DB-STANDBY"],
            "api_failures": ["Login API 503 burst", "Session validate timeout", "Balance inquiry latency"],
            "api_latency_sec": 3.8,
            "error_rate_pct": 27,
            "infra_signals": ["DB cluster failover detected", "Tripwire sudo policy drift", "Prisma IAM finding on cache tier"],
            "dependency_failures": ["CBS replication lag", "Identity federation latency", "Backup sync delayed"],
        },
        "executive": {
            "current_status": "DEGRADED — stabilization in progress",
            "strategic_impact": "Moderate retail channel disruption; no CDE breach indicated",
            "executive_risk": "Medium — customer experience and SLA governance exposure",
            "escalations": ["P1 ServiceNow INC0041287", "Digital Channels war room", "CIO notification sent"],
            "decisions_required": ["Approve failover extension window", "Authorize customer advisory broadcast"],
            "regulatory_risk": "Low",
            "executive_attention": "Required",
        },
        "audit": {
            "controls_impacted": 3,
            "open_observations": 2,
            "failed_controls": ["ITPP-DR-04 DR Drill Conducted", "DB-ENC-02 TDE Review", "ITPP-INC-01 Incident Review Record"],
            "audit_implications": "Incident closure evidence required before Q2 mock audit sign-off",
            "evidence_gaps": ["Incident review record", "Failover validation attestation", "Timeline export to Audit Prep"],
        },
        "compliance": {
            "frameworks": [
                {"name": "PCI DSS", "controls": "10.2 Logging · 10.6 Review", "status": "Monitoring — no CDE breach", "violation_risk": "Low if closed within SLA"},
                {"name": "ISO 27001", "controls": "A.16 Incident Management", "status": "Partial — timeline evidence pending", "violation_risk": "Medium"},
                {"name": "RBI Cyber Security", "controls": "IS Policy §4.2 Classification", "status": "Review — severity HIGH", "violation_risk": "Medium"},
                {"name": "DPDP", "controls": "Data breach notification", "status": "Not triggered — no compromise", "violation_risk": "Low"},
                {"name": "NIST CSF", "controls": "RS.RP Response Planning", "status": "Active response", "violation_risk": "Low"},
                {"name": "SWIFT CSP", "controls": "CSP 6.4 Logging", "status": "Not in scope for this incident", "violation_risk": "None"},
            ],
        },
        "evidence": {
            "available": 14,
            "missing": 3,
            "expired": 2,
            "avg_age_days": 18,
            "quality_score": "72%",
            "required_uploads": ["ServiceNow timeline export", "Failover validation report", "Incident review sign-off"],
            "repositories": ["SharePoint Audit Library", "ServiceNow GRC", "Splunk incident pack"],
        },
        "incident": {
            "primary_ticket": "INC0041287",
            "owner": "Infrastructure Lead",
            "war_room": "Digital Ops Bridge — Room B",
            "next_actions": ["Complete DB failover validation", "Upload incident timeline to Audit Prep", "Issue customer advisory"],
        },
        "root_cause": {
            "root_cause": "Database failover misconfiguration during peak login window",
            "contributing_factors": ["Tripwire baseline drift on auth middleware", "Delayed backup sync affecting recovery validation", "Prisma IAM exposure on cache tier"],
            "trigger_event": "Storage latency spike on CBS primary cluster",
            "affected_systems": ["CBS Oracle cluster", "Net Banking app tier", "Authentication middleware", "Mobile Banking session APIs"],
            "permanent_fix": "Update cluster failover policy and validate replication consistency",
            "preventive_actions": ["Automated failover health checks", "Close Tripwire drift within 24h SLA", "ITPP DR drill evidence refresh"],
        },
    },
}


def _scale_kpis(scenario_key: str, scenario: dict) -> dict:
    """Derive mode KPIs from scenario; use rich net_banking template as baseline."""
    base = _SCENARIO_KPIS.get("net_banking", {})
    if scenario_key == "net_banking":
        return base
    app = scenario["application"]
    sev = scenario["severity"]
    return {
        "business": {
            **base["business"],
            "customers_affected": "850K" if sev == "CRITICAL" else "620K",
            "transactions_delayed": "98,000" if "UPI" in app else "72,000",
            "services_affected": scenario.get("impacted_apps", [app])[:4],
        },
        "technical": {
            **base["technical"],
            "failing_components": scenario.get("technical_causes", [])[:4],
            "api_latency_sec": 4.2 if sev == "CRITICAL" else 2.9,
            "error_rate_pct": 31 if sev == "CRITICAL" else 19,
            "infra_signals": scenario.get("correlated_signals", [])[:4],
        },
        "executive": {
            **base["executive"],
            "current_status": f"{scenario['status']} — {app}",
            "regulatory_risk": "Medium" if sev == "CRITICAL" else "Low",
        },
        "audit": {
            **base["audit"],
            "failed_controls": scenario.get("governance_observations", [])[:3],
            "open_observations": len(scenario.get("governance_observations", [])),
        },
        "compliance": base["compliance"],
        "evidence": {**base["evidence"], "missing": len(scenario.get("governance_observations", []))},
        "incident": {
            **base["incident"],
            "primary_ticket": scenario["correlated_signals"][0].split("—")[0].strip() if scenario.get("correlated_signals") else "INC-OPEN",
            "next_actions": scenario.get("recommended_actions", [])[:3],
        },
        "root_cause": {
            **base["root_cause"],
            "root_cause": scenario.get("technical_causes", ["Under investigation"])[0],
            "contributing_factors": scenario.get("technical_causes", [])[1:4],
            "preventive_actions": scenario.get("recommended_actions", [])[:3],
            "affected_systems": scenario.get("impacted_apps", [app]),
        },
    }


def build_investigation_object(scenario: dict, scenario_key: str) -> dict[str, object]:
    """Single investigation object consumed by all response mode renderers."""
    kpis = _scale_kpis(scenario_key, scenario)
    inc_id = scenario["correlated_signals"][0].split("—")[0].strip() if scenario.get("correlated_signals") else "INC-OPEN"
    return {
        "scenario_key": scenario_key,
        "application": scenario["application"],
        "status": scenario["status"],
        "severity": scenario["severity"],
        "eta": scenario["eta"],
        "customer_impact": scenario["customer_impact"],
        "data_compromise": scenario["data_compromise"],
        "incident_id": inc_id,
        "timeline": scenario.get("timeline", []),
        "correlated_signals": scenario.get("correlated_signals", []),
        "business_units": scenario.get("business_units", []),
        "impacted_apps": scenario.get("impacted_apps", []),
        "governance_observations": scenario.get("governance_observations", []),
        "technical_causes": scenario.get("technical_causes", []),
        "recommended_actions": scenario.get("recommended_actions", []),
        "mode_kpis": kpis,
    }


def _kpi_grid(items: list[tuple[str, str]]) -> str:
    cards = "".join(
        f'<div class="ecs-sched-card"><strong>{val}</strong><span>{lbl}</span></div>'
        for lbl, val in items
    )
    return f'<div class="ecs-sched-summary mb-2">{cards}</div>'


def _section(title: str, body: str, border: str = "primary") -> str:
    return (
        f'<div class="ecs-ops-mode-section border-start border-4 border-{border} ps-2 mb-2">'
        f'<h6 class="mb-1">{title}</h6>{body}</div>'
    )


def _ctx(inv: dict, role: str) -> dict:
    return {
        "framework": "Enterprise-wide",
        "application": inv["application"],
        "module": "Operations",
        "severity": inv["severity"],
        "user_role": role,
    }


def render_business_summary(inv: dict, role: str, user: str) -> str:
    k = inv["mode_kpis"]["business"]
    services = "".join(f"<li>{s}</li>" for s in k["services_affected"])
    return _section(
        "Business Summary",
        _kpi_grid([
            ("Customers Affected", k["customers_affected"]),
            ("Transactions Delayed", k["transactions_delayed"]),
            ("Business Severity", k["business_severity"]),
            ("ETA", inv["eta"]),
            ("Revenue Impact", k["revenue_impact"]),
            ("User Impact", k["user_impact"][:28] + "…"),
        ])
        + f'<p class="small mb-1"><strong>Audience:</strong> Application Owner · Business Head</p>'
        + f'<p class="small mb-1">{inv["customer_impact"]}</p>'
        + f'<p class="small mb-1"><strong>Services affected:</strong></p><ul class="small mb-0">{services}</ul>'
        + f'<p class="small mb-0 mt-1"><strong>Business units:</strong> {", ".join(inv["business_units"])}</p>',
        "primary",
    )


def render_technical_summary(inv: dict, role: str, user: str) -> str:
    k = inv["mode_kpis"]["technical"]
    components = "".join(f"<li>{c}</li>" for c in k["failing_components"])
    apis = "".join(f"<li>{a}</li>" for a in k["api_failures"])
    signals = "".join(f"<li>{s}</li>" for s in k["infra_signals"])
    deps = "".join(f"<li>{d}</li>" for d in k["dependency_failures"])
    return _section(
        "Technical Summary",
        _kpi_grid([
            ("API Latency", f"{k['api_latency_sec']} sec"),
            ("Error Rate", f"{k['error_rate_pct']}%"),
            ("Failing Components", str(len(k["failing_components"]))),
            ("Servers Impacted", str(len(k["servers"]))),
            ("API Failures", str(len(k["api_failures"]))),
            ("Dependency Failures", str(len(k["dependency_failures"]))),
        ])
        + f'<p class="small mb-1"><strong>Audience:</strong> Operations Team · Platform Team</p>'
        + "<p class=\"small mb-1\"><strong>Failing components:</strong></p>"
        + f'<ul class="small mb-1">{components}</ul>'
        + f'<p class="small mb-1"><strong>Server details:</strong> {", ".join(k["servers"])}</p>'
        + "<p class=\"small mb-1\"><strong>API failures:</strong></p>"
        + f'<ul class="small mb-1">{apis}</ul>'
        + "<p class=\"small mb-1\"><strong>Infrastructure signals:</strong></p>"
        + f'<ul class="small mb-1">{signals}</ul>'
        + "<p class=\"small mb-0\"><strong>Dependency failures:</strong></p>"
        + f'<ul class="small mb-0">{deps}</ul>',
        "dark",
    )


def render_executive_summary(inv: dict, role: str, user: str) -> str:
    k = inv["mode_kpis"]["executive"]
    esc = "".join(f"<li>{e}</li>" for e in k["escalations"])
    dec = "".join(f"<li>{d}</li>" for d in k["decisions_required"])
    return _section(
        "Executive Summary",
        _kpi_grid([
            ("Severity", inv["severity"]),
            ("Executive Attention", k["executive_attention"]),
            ("Regulatory Risk", k["regulatory_risk"]),
            ("ETA", inv["eta"]),
            ("Strategic Impact", "Moderate"),
            ("Data Compromise", inv["data_compromise"]),
        ])
        + f'<p class="small mb-1"><strong>Audience:</strong> CIO · CTO · CISO</p>'
        + f'<p class="small mb-1"><strong>Current status:</strong> {k["current_status"]}</p>'
        + f'<p class="small mb-1"><strong>Strategic impact:</strong> {k["strategic_impact"]}</p>'
        + f'<p class="small mb-1"><strong>Executive risk:</strong> {k["executive_risk"]}</p>'
        + "<p class=\"small mb-1\"><strong>Escalations:</strong></p>"
        + f'<ul class="small mb-1">{esc}</ul>'
        + "<p class=\"small mb-0\"><strong>Decisions required:</strong></p>"
        + f'<ul class="small mb-0">{dec}</ul>',
        "info",
    )


def render_audit_summary(inv: dict, role: str, user: str) -> str:
    k = inv["mode_kpis"]["audit"]
    failed = "".join(f"<li>{c}</li>" for c in k["failed_controls"])
    gaps = "".join(f"<li>{g}</li>" for g in k["evidence_gaps"])
    drill = link_html("Audit Prep Queue", mvp_url("audit_prep", role, user, application=inv["application"], tab="gaps"),
                      "btn btn-outline-warning btn-sm me-1 mb-1")
    return _section(
        "Audit Summary",
        _kpi_grid([
            ("Controls Impacted", str(k["controls_impacted"])),
            ("Open Observations", str(k["open_observations"])),
            ("Evidence Gaps", str(len(k["evidence_gaps"]))),
            ("Audit Readiness Impact", "4–6 pts"),
            ("Failed Controls", str(len(k["failed_controls"]))),
            ("Incident ID", inv["incident_id"]),
        ])
        + f'<p class="small mb-1"><strong>Audience:</strong> Internal Audit</p>'
        + f'<p class="small mb-1"><strong>Audit implications:</strong> {k["audit_implications"]}</p>'
        + "<p class=\"small mb-1\"><strong>Failed controls:</strong></p>"
        + f'<ul class="small mb-1">{failed}</ul>'
        + "<p class=\"small mb-1\"><strong>Evidence missing:</strong></p>"
        + f'<ul class="small mb-1">{gaps}</ul>'
        + f'<div>{drill}</div>',
        "warning",
    )


def render_compliance_summary(inv: dict, role: str, user: str) -> str:
    rows = ""
    for fw in inv["mode_kpis"]["compliance"]["frameworks"]:
        rows += (
            f'<tr><td class="small fw-semibold">{fw["name"]}</td>'
            f'<td class="small">{fw["controls"]}</td>'
            f'<td class="small">{fw["status"]}</td>'
            f'<td class="small">{fw["violation_risk"]}</td></tr>'
        )
    return _section(
        "Compliance Summary",
        f'<p class="small mb-1"><strong>Audience:</strong> Compliance Team · Framework Owners</p>'
        f'<p class="small mb-2"><strong>Framework impact for {inv["application"]}:</strong></p>'
        + '<div class="table-responsive"><table class="table table-sm table-bordered mb-0">'
        + "<thead><tr><th>Framework</th><th>Control References</th><th>Compliance Status</th><th>Potential Violations</th></tr></thead>"
        + f"<tbody>{rows}</tbody></table></div>",
        "danger",
    )


def render_evidence_summary(inv: dict, role: str, user: str) -> str:
    k = inv["mode_kpis"]["evidence"]
    uploads = "".join(f"<li>{u}</li>" for u in k["required_uploads"])
    repos = "".join(f"<li>{r}</li>" for r in k["repositories"])
    ctx = _ctx(inv, role)
    return _section(
        "Evidence Summary",
        _kpi_grid([
            ("Available", str(k["available"])),
            ("Missing", str(k["missing"])),
            ("Expired", str(k["expired"])),
            ("Avg Evidence Age", f"{k['avg_age_days']} days"),
            ("Quality Score", k["quality_score"]),
            ("Required Uploads", str(len(k["required_uploads"]))),
        ])
        + f'<p class="small mb-1"><strong>Audience:</strong> Evidence Owners · App Owners</p>'
        + "<p class=\"small mb-1\"><strong>Required uploads:</strong></p>"
        + f'<ul class="small mb-1">{uploads}</ul>'
        + "<p class=\"small mb-1\"><strong>Linked repositories:</strong></p>"
        + f'<ul class="small mb-1">{repos}</ul>'
        + f'<div>{action_link("upload_missing", role, user, ctx)} '
        + link_html("Evidence Health", mvp_url("evidence_health", role, user, application=inv["application"]),
                    "btn btn-outline-success btn-sm me-1 mb-1") + "</div>",
        "success",
    )


def render_incident_summary(inv: dict, role: str, user: str) -> str:
    k = inv["mode_kpis"]["incident"]
    timeline = "".join(
        f'<div class="ecs-ops-timeline-item mb-1"><small class="text-muted">{t}</small><br><span class="small">{e}</span></div>'
        for t, e in inv["timeline"]
    )
    next_act = "".join(f"<li>{a}</li>" for a in k["next_actions"])
    return _section(
        "Incident Summary",
        _kpi_grid([
            ("Primary Ticket", k["primary_ticket"]),
            ("Status", inv["status"]),
            ("Severity", inv["severity"]),
            ("Owner", k["owner"]),
            ("War Room", k["war_room"][:20] + "…"),
            ("ETA", inv["eta"]),
        ])
        + f'<p class="small mb-1"><strong>Audience:</strong> Operations War Room</p>'
        + "<p class=\"small mb-1\"><strong>Chronological timeline:</strong></p>"
        + timeline
        + "<p class=\"small mb-1 mt-2\"><strong>Next actions:</strong></p>"
        + f'<ul class="small mb-0">{next_act}</ul>',
        "secondary",
    )


def render_root_cause_analysis(inv: dict, role: str, user: str) -> str:
    k = inv["mode_kpis"]["root_cause"]
    factors = "".join(f"<li>{f}</li>" for f in k["contributing_factors"])
    systems = "".join(f"<li>{s}</li>" for s in k["affected_systems"])
    preventive = "".join(f"<li>{p}</li>" for p in k["preventive_actions"])
    return _section(
        "Root Cause Analysis",
        _kpi_grid([
            ("Root Cause", "Failover misconfig"),
            ("Trigger Event", "Storage latency"),
            ("Contributing Factors", str(len(k["contributing_factors"]))),
            ("Affected Systems", str(len(k["affected_systems"]))),
            ("Permanent Fix", "Policy update"),
            ("Preventive Actions", str(len(k["preventive_actions"]))),
        ])
        + f'<p class="small mb-1"><strong>Audience:</strong> Problem Management · SRE</p>'
        + f'<p class="small mb-1"><strong>Root cause:</strong> {k["root_cause"]}</p>'
        + f'<p class="small mb-1"><strong>Trigger event:</strong> {k["trigger_event"]}</p>'
        + "<p class=\"small mb-1\"><strong>Contributing factors:</strong></p>"
        + f'<ul class="small mb-1">{factors}</ul>'
        + "<p class=\"small mb-1\"><strong>Affected systems:</strong></p>"
        + f'<ul class="small mb-1">{systems}</ul>'
        + f'<p class="small mb-1"><strong>Permanent fix:</strong> {k["permanent_fix"]}</p>'
        + "<p class=\"small mb-0\"><strong>Preventive actions:</strong></p>"
        + f'<ul class="small mb-0">{preventive}</ul>',
        "dark",
    )


_RENDERERS = {
    "business": render_business_summary,
    "technical": render_technical_summary,
    "executive": render_executive_summary,
    "audit": render_audit_summary,
    "compliance": render_compliance_summary,
    "evidence": render_evidence_summary,
    "incident": render_incident_summary,
    "root_cause": render_root_cause_analysis,
}


def render_response_mode(
    scenario: dict,
    mode: str,
    scenario_key: str,
    role: str,
    user: str = "User",
) -> str:
    """Render a single perspective for the investigation."""
    inv = build_investigation_object(scenario, scenario_key)
    fn = _RENDERERS.get(mode)
    if not fn:
        return f'<p class="small text-muted">Unknown response mode: {mode}</p>'
    return fn(inv, role, user)


def render_all_mode_fingerprints(scenario: dict, scenario_key: str, role: str, user: str = "User") -> dict[str, str]:
    """Return rendered HTML per mode — used for tests."""
    return {m: render_response_mode(scenario, m, scenario_key, role, user) for m in MODE_IDS}
