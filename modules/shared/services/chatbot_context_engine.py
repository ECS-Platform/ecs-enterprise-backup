"""Chatbot contextual mock data — quick actions, role filtering, framework/application scope."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

from modules.shared.services.ecs_state import BANKING_APPLICATIONS
from modules.frameworks.engines.framework_catalog import FRAMEWORK_CATALOG

APPLICATIONS = BANKING_APPLICATIONS + ["Mobile Banking", "Internet Banking", "Card Platform", "Retail Banking"]
FRAMEWORKS = list(FRAMEWORK_CATALOG.keys())
OWNERS = ["R. Mehta", "A. Sharma", "K. Reddy", "P. Nair", "S. Banerjee", "V. Rao"]
CONNECTORS = ["ServiceNow", "Jira", "Prisma CSPM", "Tripwire", "SonarQube", "Splunk SIEM", "SharePoint"]
IMPACT_TYPES = [
    "stale evidence", "failed controls", "remediation overdue", "failed sync",
    "unsupported OS", "expired exception", "missing evidence", "SLA breach",
]
SEVERITIES = ["Critical", "High", "Medium", "Low"]
STATUSES = ["Open", "In Progress", "Pending Review", "Escalated", "Monitoring"]

ROLE_APP_SCOPE = {
    "owner": ["Net Banking", "Mobile Banking", "Payments"],
    "auditor": APPLICATIONS,
    "cio": APPLICATIONS,
    "vertical_head": ["Net Banking", "Mobile Banking", "UPI", "Payments", "Treasury"],
    "compliance_head": APPLICATIONS,
    "compliance_officer": APPLICATIONS,
    "functional_head": ["Treasury", "Loan System", "Payments"],
    "admin": APPLICATIONS,
    "enterprise_admin": APPLICATIONS,
}


def _seed(key: str, lo: int, hi: int) -> int:
    h = int(hashlib.md5(key.encode()).hexdigest()[:8], 16)
    return lo + (h % (hi - lo + 1))


def _ts(offset_hours: int = 0) -> str:
    from datetime import timedelta
    dt = datetime.now(timezone.utc) - timedelta(hours=offset_hours)
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def parse_query_context(query: str, existing: dict | None = None) -> dict:
    """Extract framework/application/module from natural language."""
    ctx = dict(existing or {})
    ql = query.lower()
    for alias, fw in {
        "pci dss": "PCI DSS", "pci": "PCI DSS", "appsec": "AppSec", "vapt": "VAPT",
        "dpsc": "DPSC", "csite": "CSITE", "itpp": "ITPP", "os baselining": "OS Baselining",
        "db baselining": "DB Baselining", "nginx": "Nginx Baselining",
    }.items():
        if alias in ql:
            ctx["framework"] = fw
            break
    for app in sorted(APPLICATIONS, key=len, reverse=True):
        if app.lower() in ql:
            ctx["application"] = app
            break
    if any(w in ql for w in ("gap", "gaps", "pending", "missing", "completeness")):
        ctx["module"] = "Governance"
    elif any(w in ql for w in ("outage", "down", "degraded", "failing", "incident")):
        ctx["module"] = "Operations"
    elif any(w in ql for w in ("audit", "readiness", "submission")):
        ctx["module"] = "Audit Prep"
    if any(w in ql for w in ("critical", "high risk", "high-risk")):
        ctx["severity"] = "High"
    elif "medium" in ql:
        ctx["severity"] = "Medium"
    ctx.setdefault("framework", ctx.get("framework") or "PCI DSS")
    ctx.setdefault("application", ctx.get("application") or "Net Banking")
    ctx.setdefault("module", ctx.get("module") or "Governance")
    ctx.setdefault("severity", ctx.get("severity") or "High")
    return ctx


def _scoped_apps(ctx: dict, role: str) -> list[str]:
    allowed = ROLE_APP_SCOPE.get(role.replace("compliance_officer", "compliance_head"), APPLICATIONS)
    app = ctx.get("application")
    if app and app in allowed:
        return [app] + [a for a in allowed if a != app][:4]
    fw = ctx.get("framework", "PCI DSS")
    apps = []
    for a in allowed:
        if _seed(f"{fw}-{a}", 0, 9) > 2 or a == app:
            apps.append(a)
    return apps[:6] or allowed[:4]


def generate_impacted_applications(ctx: dict, role: str) -> list[dict]:
    rows = []
    for i, app in enumerate(_scoped_apps(ctx, role)):
        fw = ctx.get("framework") if i == 0 else FRAMEWORKS[_seed(app + str(i), 0, len(FRAMEWORKS) - 1)]
        impact = IMPACT_TYPES[_seed(f"imp-{app}-{fw}", 0, len(IMPACT_TYPES) - 1)]
        sev = SEVERITIES[min(3, _seed(f"sev-{app}", 0, 3))]
        rows.append({
            "application": app,
            "framework": fw,
            "impact_type": impact,
            "severity": sev,
            "open_observations": _seed(f"obs-{app}", 1, 18),
            "status": STATUSES[_seed(f"st-{app}", 0, len(STATUSES) - 1)],
        })
    return rows


def generate_related_incidents(ctx: dict, role: str) -> list[dict]:
    rows = []
    apps = _scoped_apps(ctx, role)
    templates = [
        ("failed ServiceNow sync", "ServiceNow", "Open"),
        ("Prisma CSPM timeout", "Prisma CSPM", "Investigating"),
        ("Jira remediation failure", "Jira", "In Progress"),
        ("expired firewall evidence pull", "SharePoint", "Open"),
        ("CAB approval delay", "ServiceNow", "Pending"),
        ("Tripwire baseline drift alert", "Tripwire", "Escalated"),
        ("SonarQube gate failure", "SonarQube", "Open"),
        ("Splunk correlation rule miss", "Splunk SIEM", "Monitoring"),
    ]
    for i, (desc, conn, status) in enumerate(templates[:8]):
        app = apps[i % len(apps)]
        rows.append({
            "incident_id": f"INC-2026-{_seed(f'inc-{app}-{i}', 1000, 9999)}",
            "application": app,
            "connector": conn,
            "severity": SEVERITIES[min(3, _seed(f"inc-sev-{i}", 0, 3))],
            "status": status,
            "created": _ts(_seed(f"inc-ts-{i}", 1, 72)),
            "summary": desc,
        })
    return rows


def generate_high_risk_observations(ctx: dict, role: str) -> list[dict]:
    rows = []
    fw = ctx.get("framework", "PCI DSS")
    apps = _scoped_apps(ctx, role)
    templates = [
        ("PCI DSS MFA enforcement gap", "PCI DSS", "Missing MFA evidence for admin console"),
        ("VAPT critical SSRF finding", "VAPT", "External pen test — SSRF on payment API"),
        ("AppSec SAST critical vulnerability", "AppSec", "SonarQube critical in auth module"),
        ("stale evidence — firewall export", "PCI DSS", "Firewall rule export older than 90 days"),
        ("unsupported OS on middleware", "OS Baselining", "RHEL 7 host outside support window"),
        ("DB hardening — TDE review pending", "DB Baselining", "Oracle TDE attestation expired"),
        ("DPSC API encryption control gap", "DPSC", "UPI channel TLS cipher non-compliance"),
        ("CSITE privileged access anomaly", "CSITE", "SOC use-case triggered on admin tier"),
    ]
    min_sev = ctx.get("severity", "High")
    sev_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    min_rank = sev_order.get(min_sev, 1)
    for i, (title, obs_fw, detail) in enumerate(templates):
        sev = SEVERITIES[min(3, _seed(f"obs-sev-{i}", 0, 2))]
        if sev_order.get(sev, 9) > min_rank + 1:
            continue
        app = apps[i % len(apps)]
        if fw != "Enterprise-wide" and obs_fw != fw and i % 3 != 0:
            continue
        rows.append({
            "observation_id": f"OBS-2026-{_seed(f'obs-{i}', 100, 999)}",
            "framework": obs_fw,
            "application": app,
            "severity": sev,
            "aging_days": f"{_seed(f'age-{i}', 3, 45)}d",
            "owner": OWNERS[i % len(OWNERS)],
            "status": STATUSES[_seed(f"obs-st-{i}", 0, 2)],
            "summary": title,
            "detail": detail,
        })
    return rows[:12] or [{
        "observation_id": "OBS-2026-001", "framework": fw, "application": apps[0],
        "severity": "High", "aging_days": "12d", "owner": OWNERS[0], "status": "Open",
        "summary": f"{fw} control gap", "detail": "Evidence refresh required",
    }]


def generate_td_exceptions(ctx: dict, role: str) -> list[dict]:
    rows = []
    apps = _scoped_apps(ctx, role)
    fw = ctx.get("framework", "PCI DSS")
    templates = [
        ("firewall waiver — legacy TLS", "PCI DSS", "EXC-2026-014", "K. Reddy (CISO)"),
        ("unsupported cipher suite approval", "PCI DSS", "EXC-2026-021", "Compliance Head"),
        ("delayed remediation — pen test finding", "VAPT", "EXC-2026-033", "CIO / CISO"),
        ("temporary MFA bypass — batch job", "AppSec", "EXC-2026-028", "App Owner"),
        ("OS extended support exception", "OS Baselining", "EXC-2026-041", "Infrastructure Ops"),
        ("DB encryption TD — non-prod parity", "DB Baselining", "EXC-2026-052", "DB Owner"),
    ]
    for i, (desc, exc_fw, eid, approver) in enumerate(templates):
        app = apps[i % len(apps)]
        if fw not in ("Enterprise-wide", exc_fw) and i % 2 != 0:
            continue
        rows.append({
            "exception_id": eid,
            "application": app,
            "framework": exc_fw,
            "expiry": f"2026-0{6 + (i % 3)}-{(i % 20) + 5:02d}",
            "risk": SEVERITIES[min(2, _seed(f"exc-{i}", 0, 2))],
            "approver": approver,
            "status": "Active" if i % 4 != 3 else "Due Renewal",
            "description": desc,
        })
    return rows


FOLLOW_UP_ACTIONS = [
    ("Show impacted applications", "show_impacted_applications"),
    ("Show related incidents", "show_related_incidents"),
    ("Show open high-risk observations", "show_open_high_risk_observations"),
    ("Show active TD exceptions", "show_active_td_exceptions"),
]

CONTEXTUAL_ACTIONS = [
    ("View Evidence", "view_evidence"),
    ("Open Observation", "open_observation"),
    ("Review Connector", "review_connector"),
    ("Raise Exception", "raise_exception"),
    ("Trigger Remediation", "trigger_remediation"),
    ("Notify Owner", "notify_owner"),
]

OWNER_CHAT_ACTIONS = CONTEXTUAL_ACTIONS + [
    ("Upload Missing Evidence", "upload_missing"),
]

AUDITOR_CHAT_ACTIONS = [
    ("Review Evidence Queue", "view_evidence"),
    ("Open Observations", "open_observation"),
    ("Assign Owner", "assign_owner"),
    ("Request Re-upload", "request_reupload"),
    ("Escalate Observation", "escalate_observation"),
    ("Approve / Reject Queue", "evidence_approval"),
]


def _table_html(headers: list[str], rows: list[dict], keys: list[str], link_keys: dict | None = None, role: str = "owner", user: str = "User") -> str:
    from modules.shared.services.chatbot_nav import framework_url, link_html, mvp_url

    if not rows:
        return '<p class="small text-muted mb-0">No records in current scope — broaden filters or change framework/application.</p>'
    th = "".join(f"<th>{h}</th>" for h in headers)
    link_keys = link_keys or {}
    body = ""
    for r in rows[:10]:
        cells = []
        for k in keys:
            val = r.get(k, "—")
            if k in link_keys:
                lk = link_keys[k]
                if lk == "observation":
                    url = mvp_url("search", role, user, framework=r.get("framework", ""), application=r.get("application", ""), observation_id=str(val))
                elif lk == "exception":
                    url = mvp_url("exceptions", role, user, framework=r.get("framework", ""), highlight=str(val))
                elif lk == "framework":
                    url = framework_url(str(val), role, user)
                elif lk == "incident":
                    url = mvp_url("integrations_hub", role, user, highlight=str(val))
                else:
                    url = mvp_url("evidence_health", role, user, framework=r.get("framework", ""), application=r.get("application", ""), highlight=str(val))
                cells.append(f'<td class="small">{link_html(str(val), url)}</td>')
            else:
                cells.append(f'<td class="small">{val}</td>')
        body += "<tr>" + "".join(cells) + "</tr>"
    return (
        f'<div class="table-responsive ecs-chat-table-wrap"><table class="table table-sm table-bordered mb-0 ecs-chat-data-table">'
        f"<thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>"
    )


def render_quick_action_html(action: str, ctx: dict, role: str, scenario_key: str = "", user: str = "User") -> str:
    """Render executive compact table/card for a quick action."""
    from modules.shared.services.chatbot_nav import action_link
    titles = {
        "show_impacted_applications": "Impacted Applications",
        "show_related_incidents": "Related Incidents",
        "show_open_high_risk_observations": "Open High-Risk Observations",
        "show_active_td_exceptions": "Active TD Exceptions",
    }
    title = titles.get(action, action.replace("_", " ").title())
    scope = f"{ctx.get('framework', 'Enterprise')} · {ctx.get('application', 'All apps')} · {role.replace('_', ' ').title()}"

    if action == "show_impacted_applications":
        rows = generate_impacted_applications(ctx, role)
        table = _table_html(
            ["Application", "Framework", "Impact Type", "Severity", "Open Obs.", "Status"],
            rows, ["application", "framework", "impact_type", "severity", "open_observations", "status"],
            link_keys={"application": "evidence", "framework": "framework"}, role=role, user=user,
        )
    elif action == "show_related_incidents":
        rows = generate_related_incidents(ctx, role)
        table = _table_html(
            ["Incident ID", "Application", "Connector", "Severity", "Status", "Created"],
            rows, ["incident_id", "application", "connector", "severity", "status", "created"],
            link_keys={"incident_id": "incident"}, role=role, user=user,
        )
    elif action == "show_open_high_risk_observations":
        rows = generate_high_risk_observations(ctx, role)
        table = _table_html(
            ["Observation ID", "Framework", "Application", "Severity", "Aging", "Owner", "Status"],
            rows, ["observation_id", "framework", "application", "severity", "aging_days", "owner", "status"],
            link_keys={"observation_id": "observation", "framework": "framework"}, role=role, user=user,
        )
    elif action == "show_active_td_exceptions":
        rows = generate_td_exceptions(ctx, role)
        table = _table_html(
            ["Exception ID", "Application", "Framework", "Expiry", "Risk", "Approver", "Status"],
            rows, ["exception_id", "application", "framework", "expiry", "risk", "approver", "status"],
            link_keys={"exception_id": "exception", "framework": "framework"}, role=role, user=user,
        )
    elif action in ("view_evidence", "open_observation", "review_connector", "raise_exception", "trigger_remediation", "notify_owner"):
        from modules.shared.services.chatbot_nav import action_link, link_html
        url = action_link(action, role, user, ctx)
        labels = {
            "view_evidence": "Evidence Health",
            "open_observation": "Observation Search",
            "review_connector": "Integrations Hub",
            "raise_exception": "Exceptions / TD",
            "trigger_remediation": "Audit Prep Gaps",
            "notify_owner": "Onboarding / Owners",
        }
        return (
            f'<div class="ecs-chat-action-result chart-card p-2 mb-2">'
            f'<h6 class="chart-card-title mb-1">{labels.get(action, action.replace("_", " ").title())}</h6>'
            f'<p class="small mb-2">Opening {scope} with role context preserved.</p>'
            f'{link_html("Open " + labels.get(action, "module"), url, "btn btn-primary btn-sm")}'
            f'</div>'
        )
    else:
        return f'<div class="ecs-chat-action-result"><p class="small">Action {action} queued for {scope}.</p></div>'

    follow_btns = "".join(
        f'<a href="{action_link(key, role, user, ctx)}" class="btn btn-outline-secondary btn-sm me-1 mb-1">{label}</a>'
        for label, key in CONTEXTUAL_ACTIONS[:4]
    )
    quick_row = "".join(
        f'<button type="button" class="btn btn-outline-primary btn-sm ecs-chat-quick-action me-1 mb-1" '
        f'data-action="{key}" data-scenario="{scenario_key}">{label}</button>'
        for label, key in FOLLOW_UP_ACTIONS if key != action
    )
    count = len(rows) if action.startswith("show_") else 0
    exec_summary = ""
    if role == "cio":
        exec_summary = (
            f'<div class="ecs-chat-exec-summary small mb-2 p-2 bg-light rounded">'
            f'<strong>Enterprise view:</strong> {count} correlated records across '
            f'{len(_scoped_apps(ctx, role))} applications · {ctx.get("framework", "Multi-framework")} scope.</div>'
        )
    elif role == "owner":
        exec_summary = (
            f'<div class="ecs-chat-exec-summary small mb-2 p-2 bg-light rounded">'
            f'<strong>App Owner view:</strong> scoped to your owned applications only.</div>'
        )
    elif role in ("compliance_head", "compliance_officer"):
        exec_summary = (
            f'<div class="ecs-chat-exec-summary small mb-2 p-2 bg-light rounded">'
            f'<strong>Compliance view:</strong> regulator-facing gaps and active TD exceptions.</div>'
        )
    return f"""
<div class="ecs-chat-action-result chart-card p-2 mb-2">
<div class="d-flex justify-content-between align-items-start mb-1">
<h6 class="mb-0 chart-card-title">{title}</h6>
<span class="badge bg-secondary">{count} rows</span></div>
<p class="ecs-exec-desc-muted mb-2">Scope: {scope}</p>
{exec_summary}
{table}
<div class="mt-2"><small class="text-muted d-block mb-1">Related actions:</small>{quick_row}</div>
<div class="mt-1"><small class="text-muted d-block mb-1">Next steps:</small>{follow_btns}</div>
</div>"""


def render_governance_panel(ctx: dict, role: str, summary: str = "", user: str = "User") -> str:
    """Governance query response with quick action buttons."""
    from modules.shared.services.chatbot_nav import evidence_health_link
    from modules.shared.services.role_permissions import chatbot_actions_for_role

    scope = f"{ctx.get('framework')} · {ctx.get('application')} · {ctx.get('module', 'Governance')}"
    actions = chatbot_actions_for_role(role)
    btns = "".join(
        f'<button type="button" class="btn btn-outline-primary btn-sm ecs-chat-quick-action me-1 mb-1" '
        f'data-action="{key}">{label}</button>'
        for label, key in actions
    )
    eh_link = evidence_health_link(role, user, framework=ctx.get("framework", ""), application=ctx.get("application", ""), label="Evidence Health")
    timeline = "".join(
        f'<div class="ecs-ops-timeline-item"><small class="text-muted">{_ts(i * 4)}</small><br>'
        f'Context captured — {k}: {v}</div>'
        for i, (k, v) in enumerate(ctx.items()) if v and k != "active_outage"
    )
    body = summary or f"Governance intelligence loaded for {scope}."
    return f"""
<div class="ecs-ops-intel-card border rounded p-2 mb-1">
<div class="d-flex justify-content-between align-items-start mb-1">
<small class="text-muted">Governance Intelligence · {role.replace('_', ' ').title()}</small>
<span class="badge bg-primary">{ctx.get('severity', 'High')}</span></div>
<p class="small mb-2 ecs-exec-desc">{body}</p>
<details class="ecs-ops-timeline small mb-2"><summary>Operations timeline</summary>{timeline or '<span class="text-muted">Session context active.</span>'}</details>
<div class="ecs-ops-followups"><small class="text-muted d-block">Quick actions:</small>{btns} {eh_link}</div>
</div>"""


def execute_quick_action(action: str, user: str, role: str, scenario_key: str = "") -> tuple[str, str]:
    """Return (plain_text, html) for a quick action."""
    from modules.shared.services.chatbot_engine import get_context
    from modules.shared.services.chatbot_nav import action_link, evidence_health_link

    ctx = get_context(user, role)
    if scenario_key:
        ctx["active_outage"] = scenario_key
    if action in ("view_evidence", "open_observation", "review_connector", "raise_exception", "trigger_remediation", "notify_owner"):
        html = render_quick_action_html(action, ctx, role, scenario_key, user=user)
        plain = f"Navigate to {action.replace('_', ' ')} — link ready in copilot panel."
        return plain, html
    html = render_quick_action_html(action, ctx, role, scenario_key, user=user)
    plain = f"{action.replace('_', ' ').title()} — {len(generate_impacted_applications(ctx, role))} items in scope (see copilot panel)."
    if action == "show_related_incidents":
        plain = f"Related incidents: {len(generate_related_incidents(ctx, role))} correlated events."
    elif action == "show_open_high_risk_observations":
        plain = f"High-risk observations: {len(generate_high_risk_observations(ctx, role))} open items."
    elif action == "show_active_td_exceptions":
        plain = f"Active TD exceptions: {len(generate_td_exceptions(ctx, role))} records."
    return plain, html
