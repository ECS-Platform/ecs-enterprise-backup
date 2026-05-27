"""Enterprise Operations & Governance Intelligence — outage summarization layer."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from app.chatbot_context_engine import execute_quick_action, render_quick_action_html
from app.chatbot_engine import get_context, record_exchange, set_chat_structured, update_chat_context

OUTAGE_FOLLOW_UPS = [
    ("Show impacted applications", "show_impacted_applications"),
    ("Show related incidents", "show_related_incidents"),
    ("Show open high-risk observations", "show_open_high_risk_observations"),
    ("Show active TD exceptions", "show_active_td_exceptions"),
    ("Show DR readiness", "show_dr_readiness"),
    ("Show affected business units", "show_affected_business_units"),
    ("Show SLA breach risk", "show_sla_breach_risk"),
]

APPLICATION_ALIASES = {
    "net banking": "net_banking",
    "internet banking": "net_banking",
    "mobile banking": "mobile_banking",
    "mobile app": "mobile_banking",
    "upi": "upi",
    "upi transactions": "upi",
    "payments": "payments",
    "payment api": "payments",
    "payment apis": "payments",
    "treasury": "treasury",
    "loan system": "loan_system",
    "loan": "loan_system",
}

OUTAGE_SCENARIOS: dict[str, dict] = {
    "net_banking": {
        "application": "Net Banking",
        "status": "DEGRADED",
        "severity": "HIGH",
        "customer_impact": "Login failures and transaction delays observed across retail internet banking channels.",
        "impact_level": "MODERATE",
        "data_compromise": "NOT DETECTED",
        "eta": "45–60 minutes",
        "business_units": ["Retail Banking", "Digital Channels"],
        "impacted_apps": ["Net Banking", "Mobile Banking APIs", "UPI Gateway"],
        "correlated_signals": [
            "ServiceNow P1 INC0041287 — login degradation",
            "DB cluster failover instability — CBS_ORACLE_CLUSTER",
            "Tripwire sudo policy drift — NETBANKING_PROD",
            "Prisma IAM finding — exposed Redis cache tier",
        ],
        "governance_observations": [
            "DB Baselining — Transparent Data Encryption review pending",
            "ITPP — DR Drill Conducted overdue",
            "ServiceNow P1 incident unresolved (42m)",
            "TD exception EXC-2026-014 active on failover cluster",
        ],
        "technical_causes": [
            "DB cluster failover instability during peak login window",
            "Unresolved Tripwire baseline drift on authentication middleware",
            "Delayed backup synchronization affecting recovery validation",
            "Elevated Prisma cloud IAM vulnerabilities on cache tier",
        ],
        "timeline": [
            ("2026-05-24 08:12 UTC", "SOC alert — elevated login failure rate"),
            ("2026-05-24 08:18 UTC", "ServiceNow P1 INC0041287 opened"),
            ("2026-05-24 08:25 UTC", "DB failover initiated — partial instability"),
            ("2026-05-24 08:40 UTC", "Governance correlation — Tripwire drift linked"),
            ("2026-05-24 08:55 UTC", "Stabilization in progress — ETA issued"),
        ],
        "recommended_actions": [
            "Validate DB replication and failover consistency",
            "Review open P1 ServiceNow incidents",
            "Trigger ITPP DR readiness verification",
            "Review unresolved Prisma IAM findings",
        ],
    },
    "mobile_banking": {
        "application": "Mobile Banking",
        "status": "DEGRADED",
        "severity": "HIGH",
        "customer_impact": "Mobile app login timeouts and delayed balance refresh reported.",
        "impact_level": "MODERATE",
        "data_compromise": "NOT DETECTED",
        "eta": "30–45 minutes",
        "business_units": ["Digital Banking", "Retail Banking"],
        "impacted_apps": ["Mobile Banking", "Net Banking session APIs"],
        "correlated_signals": [
            "API gateway latency spike — MOBILE_BANKING_API",
            "SonarQube high-severity API auth finding",
            "Jira SEC-2201 remediation in progress",
            "Expired TLS certificate warning — edge gateway",
        ],
        "governance_observations": [
            "AppSec — API Security Testing observation open",
            "VAPT — Mobile pen test high finding pending closure",
            "Nginx Baselining — TLS hardening drift detected",
        ],
        "technical_causes": [
            "API gateway overload during morning peak",
            "Certificate expiry window on mobile API edge",
            "SonarQube API auth bypass pattern correlated",
            "Session token validation latency elevated",
        ],
        "timeline": [
            ("2026-05-24 07:50 UTC", "APM governance signal — API latency breach"),
            ("2026-05-24 08:00 UTC", "Customer complaint cluster detected"),
            ("2026-05-24 08:10 UTC", "Certificate validation alert — edge tier"),
            ("2026-05-24 08:22 UTC", "Cross-tool correlation with AppSec backlog"),
        ],
        "recommended_actions": [
            "Validate API gateway throttle and certificate chain",
            "Expedite Jira SEC-2201 remediation review",
            "Review AppSec scan closure evidence",
        ],
    },
    "upi": {
        "application": "UPI",
        "status": "DEGRADED",
        "severity": "CRITICAL",
        "customer_impact": "UPI transaction failures and NPCI switch timeouts reported.",
        "impact_level": "HIGH",
        "data_compromise": "NOT DETECTED",
        "eta": "60–90 minutes",
        "business_units": ["Digital Payments", "Retail Banking"],
        "impacted_apps": ["UPI", "Payments", "Net Banking fund transfer"],
        "correlated_signals": [
            "ServiceNow P1 — UPI switch timeout cluster",
            "Prisma CSPM — misconfigured cloud storage exposure",
            "DPSC observation — API rate limit breach",
            "Jira CLOUD-551 IAM remediation backlog",
        ],
        "governance_observations": [
            "DPSC — UPI Channel Encryption control under review",
            "CSITE — Privileged access anomaly on UPI cluster",
            "TD exception on temporary firewall rule — EXC-2026-041",
        ],
        "technical_causes": [
            "UPI switch timeout under transaction surge",
            "Cloud misconfiguration flagged by Prisma CSPM",
            "API rate limiting threshold exceeded",
            "IAM over-privileged service account on UPI workloads",
        ],
        "timeline": [
            ("2026-05-24 09:05 UTC", "NPCI timeout alerts correlated"),
            ("2026-05-24 09:12 UTC", "ServiceNow P1 opened — payments ops engaged"),
            ("2026-05-24 09:20 UTC", "Prisma finding linked to UPI cluster"),
            ("2026-05-24 09:35 UTC", "Governance escalation to Digital Payments head"),
        ],
        "recommended_actions": [
            "Validate UPI switch health and NPCI connectivity",
            "Review Prisma CSPM critical findings",
            "Confirm DPSC encryption controls in production path",
        ],
    },
    "payments": {
        "application": "Payments",
        "status": "DEGRADED",
        "severity": "HIGH",
        "customer_impact": "Payment API delays and intermittent gateway timeouts affecting merchant transactions.",
        "impact_level": "MODERATE",
        "data_compromise": "NOT DETECTED",
        "eta": "45–75 minutes",
        "business_units": ["Payments", "Cards & Acquiring"],
        "impacted_apps": ["Payments", "Card Payment Gateway", "Net Banking bill pay"],
        "correlated_signals": [
            "API gateway overload — CARD_PAYMENT_GATEWAY",
            "PCI DSS TLS exception EXC-2026-014 active",
            "ServiceNow change CHG003892 post-review pending",
            "Backup failure monitoring alert — offsite sync delayed",
        ],
        "governance_observations": [
            "PCI DSS — Encryption in Transit observation pending",
            "ITPP — Backup Failure Monitoring alert open",
            "VAPT — Payment gateway pen test remediation tracker",
        ],
        "technical_causes": [
            "Payment API gateway capacity saturation",
            "Legacy TLS dependency under active TD exception",
            "Delayed offsite backup sync affecting recovery posture",
        ],
        "timeline": [
            ("2026-05-24 08:30 UTC", "Gateway latency SLA breach"),
            ("2026-05-24 08:45 UTC", "Merchant timeout complaints correlated"),
            ("2026-05-24 09:00 UTC", "Governance link to PCI TD exception"),
        ],
        "recommended_actions": [
            "Scale API gateway capacity and validate WAF rules",
            "Review PCI TD exception renewal timeline",
            "Confirm backup sync completion",
        ],
    },
    "login_generic": {
        "application": "Digital Banking (Multi-channel)",
        "status": "DEGRADED",
        "severity": "HIGH",
        "customer_impact": "Customers unable to login across internet and mobile banking channels.",
        "impact_level": "HIGH",
        "data_compromise": "NOT DETECTED",
        "eta": "45–60 minutes",
        "business_units": ["Retail Banking", "Digital Banking"],
        "impacted_apps": ["Net Banking", "Mobile Banking", "UPI SSO"],
        "correlated_signals": [
            "Identity provider latency — auth federation tier",
            "ServiceNow incident cluster — login failures",
            "Tripwire drift — authentication middleware",
        ],
        "governance_observations": [
            "AppSec — Session Management Security pending",
            "CSITE — SOC login anomaly use-case triggered",
            "ITPP — Incident SLA breach on P1 cluster",
        ],
        "technical_causes": [
            "Authentication federation latency spike",
            "Session validation service degradation",
            "Correlated config drift on auth middleware",
        ],
        "timeline": [
            ("2026-05-24 08:00 UTC", "Login failure rate exceeded threshold"),
            ("2026-05-24 08:15 UTC", "Multi-channel impact confirmed"),
        ],
        "recommended_actions": [
            "Validate identity provider and session tier health",
            "Review CSITE SOC correlation rules",
            "Escalate ITPP incident SLA governance review",
        ],
    },
}


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _detect_application(ql: str) -> str | None:
    if any(p in ql for p in ("unable to login", "cannot login", "can't login", "login fail")):
        return "login_generic"
    for alias, key in sorted(APPLICATION_ALIASES.items(), key=lambda x: -len(x[0])):
        if alias in ql:
            return key
    if "internet banking" in ql or "netbank" in ql:
        return "net_banking"
    if "slow" in ql and "bank" in ql:
        return "net_banking"
    return None


def _is_outage_intent(ql: str) -> bool:
    outage_verbs = ("down", "degraded", "outage", "failing", "failure", "slow", "delayed", "delay", "unavailable", "not working", "issue", "problem", "impact")
    outage_questions = ("why is", "why are", "what is wrong", "what happened", "is.* down", "customer impact", "data safe", "recovery timeline", "expected recovery", "impacted application")
    if any(v in ql for v in outage_verbs):
        return True
    if any(re.search(p, ql) for p in outage_questions if ".*" in p):
        return True
    return any(p in ql for p in (
        "why is", "why are", "customer impact", "data safe", "data compromise",
        "recovery timeline", "expected recovery", "impacted application", "which applications",
        "unable to login", "cannot login", "payment api", "transactions failing",
    ))


def _parse_mode_command(q: str) -> tuple[str, str] | None:
    m = re.match(r"@outage-mode:([a-z_]+):(business|technical|customer)", q.strip(), re.I)
    if m:
        return m.group(1), m.group(2).lower()
    m2 = re.match(r"@outage-follow:([a-z_]+):([a-z_]+)", q.strip(), re.I)
    if m2:
        return m2.group(1), f"follow_{m2.group(2)}"
    m3 = re.match(r"@chat-action:([a-z_]+)(?::([a-z_]+))?", q.strip(), re.I)
    if m3:
        scenario = m3.group(2) or ""
        return scenario, f"follow_{m3.group(1)}"
    return None


def _severity_class(sev: str) -> str:
    return {"CRITICAL": "danger", "HIGH": "warning", "MEDIUM": "info", "LOW": "secondary"}.get(sev, "secondary")


def _build_summary_html(scenario: dict, scenario_key: str, role: str) -> str:
    sev = scenario["severity"]
    badge = _severity_class(sev)
    signals = "".join(f'<li class="small">{s}</li>' for s in scenario["correlated_signals"])
    modes = (
        f'<button type="button" class="btn btn-sm btn-outline-primary ecs-outage-mode-btn" '
        f'data-q="@outage-mode:{scenario_key}:business">Business Summary</button> '
        f'<button type="button" class="btn btn-sm btn-outline-dark ecs-outage-mode-btn" '
        f'data-q="@outage-mode:{scenario_key}:technical">Technical Summary</button> '
        f'<button type="button" class="btn btn-sm btn-outline-success ecs-outage-mode-btn" '
        f'data-q="@outage-mode:{scenario_key}:customer">Customer-Friendly Summary</button>'
    )
    timeline = "".join(
        f'<div class="ecs-ops-timeline-item"><small class="text-muted">{t}</small><br>{e}</div>'
        for t, e in scenario.get("timeline", [])[:4]
    )
    follow_btns = "".join(
        f'<button type="button" class="btn btn-outline-primary btn-sm ecs-chat-quick-action me-1 mb-1" '
        f'data-action="{key}" data-scenario="{scenario_key}">{label}</button>'
        for label, key in OUTAGE_FOLLOW_UPS[:4]
    )
    return f"""
<div class="ecs-ops-intel-card border rounded p-2 mb-1">
<div class="d-flex justify-content-between align-items-start mb-2">
<div><span class="badge bg-{badge} ecs-ops-severity">{sev}</span>
<span class="badge bg-secondary ms-1">{scenario['status']}</span></div>
<small class="text-muted">Operations Intelligence</small></div>
<h6 class="mb-1">{scenario['application']}</h6>
<p class="small mb-2"><strong>Customer Impact:</strong> {scenario['customer_impact']}</p>
<div class="small mb-2"><strong>Data compromise:</strong> <span class="text-success">{scenario['data_compromise']}</span>
· <strong>ETA:</strong> <span class="badge bg-info text-dark">{scenario['eta']}</span></div>
<div class="mb-2"><small class="text-muted d-block">Correlated governance signals:</small><ul class="mb-0 ps-3 ecs-paginated-list">{signals}</ul></div>
<div class="ecs-ops-mode-select mb-2 p-2 bg-light rounded"><small class="text-muted d-block mb-1">Select response mode (expand for detail):</small>{modes}</div>
<details class="ecs-ops-timeline small mb-2"><summary>Operations timeline</summary>{timeline}</details>
<div class="ecs-ops-followups"><small class="text-muted d-block">Suggested follow-ups:</small>{follow_btns}</div>
</div>"""


def _build_mode_html(scenario: dict, mode: str, scenario_key: str) -> str:
    if mode == "business":
        body = f"""
<details class="ecs-ops-detail-wrap mb-2"><summary class="fw-semibold text-primary">Business View — click to expand</summary>
<div class="ecs-ops-detail ecs-ops-business border-start border-4 border-primary ps-2 mt-2">
<h6>Business View</h6>
<p>{scenario['application']} is currently experiencing service disruption due to backend infrastructure instability.</p>
<p><strong>Current impact:</strong></p><ul>
<li>delayed logins and session timeouts</li>
<li>delayed transaction confirmations</li>
<li>intermittent payment failures on linked channels</li></ul>
<p><strong>Impact level:</strong> {scenario['impact_level']}<br>
<strong>Customer data compromise:</strong> {scenario['data_compromise']}</p>
<p><strong>Current actions:</strong> infrastructure stabilization, database recovery validation, transaction queue restoration.</p>
<p><strong>Estimated recovery:</strong> {scenario['eta']}</p>
<p class="mb-0"><em>Customer advisory: Teams are actively working on service restoration.</em></p>
</div></details>"""
    elif mode == "technical":
        obs = "".join(f"<li>{o}</li>" for o in scenario["governance_observations"])
        causes = "".join(f"<li>{c}</li>" for c in scenario["technical_causes"])
        apps = ", ".join(scenario["impacted_apps"])
        actions = "".join(f"<li>{a}</li>" for a in scenario["recommended_actions"])
        body = f"""
<details class="ecs-ops-detail-wrap mb-2"><summary class="fw-semibold">Technical Governance View — click to expand</summary>
<div class="ecs-ops-detail ecs-ops-technical border-start border-4 border-dark ps-2 mt-2">
<h6>Technical Governance View</h6>
<p><strong>Probable correlated causes:</strong></p><ul>{causes}</ul>
<p><strong>Related enterprise observations:</strong></p><ul class="ecs-paginated-list">{obs}</ul>
<p><strong>Applications impacted:</strong> {apps}<br>
<strong>Operational risk:</strong> <span class="badge bg-{_severity_class(scenario['severity'])}">{scenario['severity']}</span></p>
<p><strong>Recommended actions:</strong></p><ul class="ecs-paginated-list">{actions}</ul>
</div></details>"""
    else:
        body = f"""
<details class="ecs-ops-detail-wrap mb-2"><summary class="fw-semibold text-success">Customer Communication View — click to expand</summary>
<div class="ecs-ops-detail ecs-ops-customer border-start border-4 border-success ps-2 mt-2">
<h6>Customer Communication View</h6>
<p>Some customers may currently experience delays while accessing {scenario['application']} services.</p>
<p>Our teams are actively working to restore normal operations as quickly as possible.</p>
<p>At present:</p><ul>
<li>some login delays may occur</li>
<li>certain transactions may take longer than usual</li></ul>
<p><strong>No customer data compromise has been identified.</strong></p>
<p class="mb-0"><em>We regret the inconvenience and appreciate your patience.</em></p>
</div></details>"""
    back = (
        f'<button type="button" class="btn btn-sm btn-link ecs-outage-mode-btn p-0" '
        f'data-q="Why is {scenario["application"]} down?">← Back to outage summary</button>'
    )
    return body + f'<div class="mt-2">{back}</div>'


def _build_follow_up_html(scenario: dict, follow_key: str, role: str, scenario_key: str) -> str:
    ctx = {
        "framework": "Enterprise-wide",
        "application": scenario.get("application", "Net Banking"),
        "module": "Operations",
        "severity": scenario.get("severity", "HIGH").title(),
        "active_outage": scenario_key,
    }
    if follow_key in (
        "show_impacted_applications", "show_related_incidents",
        "show_open_high_risk_observations", "show_active_td_exceptions",
    ):
        return render_quick_action_html(follow_key, ctx, role, scenario_key)
    mapping = {
        "show_dr_readiness": ("DR Readiness", ["ITPP DR validation linked — review DR drill status", f"ETA recovery: {scenario['eta']}"]),
        "show_affected_business_units": ("Affected Business Units", scenario["business_units"]),
        "show_sla_breach_risk": ("SLA Breach Risk", ["P1 incident SLA governance review active", "ITPP incident SLA controls under escalation"]),
    }
    title, items = mapping.get(follow_key, ("Details", scenario["impacted_apps"]))
    lis = "".join(f"<li>{i}</li>" for i in items)
    return f'<div class="ecs-ops-followup"><h6>{title}</h6><ul class="small ecs-paginated-list">{lis or "<li>No items in scope.</li>"}</ul></div>'


def _plain_summary(scenario: dict) -> str:
    return (
        f"[Operations Intelligence Alert]\n\n"
        f"Application: {scenario['application']}\n"
        f"Status: {scenario['status']} · Severity: {scenario['severity']}\n\n"
        f"Customer Impact: {scenario['customer_impact']}\n"
        f"Data compromise: {scenario['data_compromise']} · ETA: {scenario['eta']}\n\n"
        f"Correlated signals:\n"
        + "\n".join(f"  • {s}" for s in scenario["correlated_signals"])
        + "\n\nSelect a response mode using the buttons below:\n"
        "  [Business Summary] [Technical Summary] [Customer-Friendly Summary]"
    )


def try_operations_answer(query: str, role: str = "owner", user: str = "User") -> str | None:
    q = query.strip()
    ql = q.lower()
    ctx = get_context(user, role)

    parsed = _parse_mode_command(q)
    if parsed:
        scenario_key, mode_or_follow = parsed
        scenario = OUTAGE_SCENARIOS.get(scenario_key) if scenario_key else None
        if mode_or_follow.startswith("follow_"):
            follow_key = mode_or_follow.removeprefix("follow_")
            if scenario:
                update_chat_context(user, role, q, application=scenario["application"], module="Operations", severity=scenario["severity"])
                ctx["active_outage"] = scenario_key
                html = _build_summary_html(scenario, scenario_key, role) + _build_follow_up_html(scenario, follow_key, role, scenario_key)
                plain, _ = execute_quick_action(follow_key, user, role, scenario_key)
            else:
                update_chat_context(user, role, q)
                plain, action_html = execute_quick_action(follow_key, user, role, ctx.get("active_outage", ""))
                from app.chatbot_context_engine import render_governance_panel
                html = render_governance_panel(get_context(user, role), role, plain[:120]) + action_html
            set_chat_structured(user, role, html)
            record_exchange(user, role, q, plain)
            return plain
        if not scenario:
            return None
        ctx["active_outage"] = scenario_key
        if mode_or_follow in ("business", "technical", "customer"):
            html = _build_summary_html(scenario, scenario_key, role) + _build_mode_html(scenario, mode_or_follow, scenario_key)
            plain = f"[{mode_or_follow.title()} View] — {scenario['application']}\nSee detailed response in copilot panel."
        else:
            return None
        set_chat_structured(user, role, html)
        record_exchange(user, role, q, plain)
        return plain

    if not _is_outage_intent(ql):
        return None

    scenario_key = _detect_application(ql)
    if not scenario_key and ctx.get("active_outage"):
        scenario_key = ctx["active_outage"]

    if ql.strip() in ("is customer data safe", "is customer data safe?"):
        scenario_key = ctx.get("active_outage") or "net_banking"
        scenario = OUTAGE_SCENARIOS[scenario_key]
        html = _build_summary_html(scenario, scenario_key, role)
        html += f'<div class="alert alert-success small py-2 mb-0"><strong>Customer data compromise:</strong> {scenario["data_compromise"]}. No evidence of data exfiltration in correlated governance signals.</div>'
        plain = f"Customer data compromise: {scenario['data_compromise']} for {scenario['application']}."
        set_chat_structured(user, role, html)
        record_exchange(user, role, q, plain)
        return plain

    if "recovery timeline" in ql or "expected recovery" in ql:
        scenario_key = scenario_key or "net_banking"
        scenario = OUTAGE_SCENARIOS[scenario_key]
        html = _build_summary_html(scenario, scenario_key, role)
        html += f'<div class="badge bg-info text-dark">Estimated recovery: {scenario["eta"]}</div>'
        plain = f"Estimated recovery for {scenario['application']}: {scenario['eta']}"
        set_chat_structured(user, role, html)
        record_exchange(user, role, q, plain)
        return plain

    if "which applications" in ql or "impacted application" in ql:
        scenario_key = scenario_key or "login_generic"
        scenario = OUTAGE_SCENARIOS[scenario_key]
        html = _build_summary_html(scenario, scenario_key, role) + _build_follow_up_html(scenario, "show_impacted_applications", role, scenario_key)
        plain = "Impacted applications: " + ", ".join(scenario["impacted_apps"])
        set_chat_structured(user, role, html)
        record_exchange(user, role, q, plain)
        return plain

    if "customer impact" in ql:
        scenario_key = scenario_key or ctx.get("active_outage") or "net_banking"
        scenario = OUTAGE_SCENARIOS[scenario_key]
        html = _build_summary_html(scenario, scenario_key, role)
        plain = f"Customer impact ({scenario['application']}): {scenario['customer_impact']}"
        set_chat_structured(user, role, html)
        record_exchange(user, role, q, plain)
        return plain

    if not scenario_key:
        return None

    scenario = OUTAGE_SCENARIOS.get(scenario_key)
    if not scenario:
        return None

    ctx["active_outage"] = scenario_key
    update_chat_context(user, role, q, application=scenario["application"], module="Operations", severity=scenario["severity"])
    html = _build_summary_html(scenario, scenario_key, role)
    plain = _plain_summary(scenario)
    set_chat_structured(user, role, html)
    record_exchange(user, role, q, plain)
    return plain
