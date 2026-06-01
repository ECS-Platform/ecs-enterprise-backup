"""ECS AI Ops Assistant — banking governance copilot workspace and summary modes."""

from __future__ import annotations

from modules.shared.services.chatbot_nav import action_link, framework_url, link_html, mvp_url

SUMMARY_MODES: list[tuple[str, str, str]] = [
    ("business", "Business Summary", "outline-primary"),
    ("technical", "Technical Summary", "outline-dark"),
    ("executive", "Executive Summary", "outline-info"),
    ("audit", "Audit Summary", "outline-warning"),
    ("compliance", "Compliance Summary", "outline-danger"),
    ("evidence", "Evidence Summary", "outline-success"),
    ("incident", "Incident Summary", "outline-secondary"),
    ("root_cause", "Root Cause Analysis", "outline-dark"),
]

SAMPLE_QUERY_GROUPS: list[dict] = [
    {
        "category": "Incidents & Operations",
        "queries": [
            "Why is Net Banking down?",
            "Why are UPI transactions failing?",
            "Show related incidents for Mobile Banking",
            "What is the recovery timeline for Payments API?",
        ],
    },
    {
        "category": "Audit & Evidence",
        "queries": [
            "How many evidences await my approval?",
            "Show rejected observations for PCI DSS",
            "Which controls are missing evidence for Net Banking?",
            "Show expiring evidences this quarter",
        ],
    },
    {
        "category": "Compliance & Frameworks",
        "queries": [
            "What is PCI DSS?",
            "What is DPSC compliance status for UPI?",
            "Show high-risk controls for RBI Cyber Security",
            "Framework coverage for AppSec and VAPT",
        ],
    },
    {
        "category": "Governance & Risk",
        "queries": [
            "What is enterprise maturity?",
            "Show open high-risk observations",
            "Show active TD exceptions",
            "Show DR readiness for ITPP",
        ],
    },
]


def build_assistant_view(role: str, user: str = "User") -> dict:
    from modules.operations.engines.operations_intelligence import OUTAGE_SCENARIOS
    from modules.shared.utils.demo_data_standards import ensure_drill_rows

    scenarios = list(OUTAGE_SCENARIOS.values())
    incident_rows = []
    for key, s in OUTAGE_SCENARIOS.items():
        inc_id = s["correlated_signals"][0].split("—")[0].strip() if s.get("correlated_signals") else "INC-OPEN"
        incident_rows.append({
            "incident_id": inc_id,
            "application": s["application"],
            "framework": "ITPP" if "banking" in s["application"].lower() else "Enterprise-wide",
            "owner": "Digital Ops Lead" if "Mobile" in s["application"] else "Infrastructure Lead",
            "severity": s["severity"],
            "status": s["status"],
            "eta": s["eta"],
            "scenario_key": key,
        })
    default_references = [
        {"label": "Audit Prep", "url": mvp_url("audit_prep", role, user, tab="gaps")},
        {"label": "Evidence Health", "url": mvp_url("evidence_health", role, user)},
        {"label": "Correlation", "url": mvp_url("correlation", role, user)},
        {"label": "Risk Register", "url": mvp_url("risk_register", role, user)},
        {"label": "Governance Analytics", "url": mvp_url("governance_analytics", role, user)},
        {"label": "PCI DSS", "url": framework_url("PCI DSS", role, user)},
        {"label": "VAPT", "url": framework_url("VAPT", role, user)},
        {"label": "Scheduler", "url": mvp_url("scheduler", role, user)},
    ]
    return {
        "kpis": [
            {"label": "Active Incidents", "value": len(scenarios), "tone": "danger", "drill": "active_incidents"},
            {"label": "Open Findings", "value": sum(len(s.get("governance_observations", [])) for s in scenarios), "tone": "warning", "drill": "open_findings"},
            {"label": "Frameworks Linked", "value": 15, "tone": "success", "drill": "frameworks_linked"},
            {"label": "Evidence Gaps", "value": sum(len(s.get("governance_observations", [])) for s in scenarios) + 4, "tone": "info", "drill": "evidence_gaps"},
        ],
        "sample_queries": SAMPLE_QUERY_GROUPS,
        "summary_modes": [{"id": m[0], "label": m[1], "btn": m[2]} for m in SUMMARY_MODES],
        "scenarios": [
            {"key": k, "application": v["application"], "severity": v["severity"], "status": v["status"]}
            for k, v in OUTAGE_SCENARIOS.items()
        ],
        "incident_rows": ensure_drill_rows(incident_rows, 25, metric="incidents"),
        "default_references": default_references,
        "role": role,
    }


def build_summary_mode_buttons(scenario_key: str) -> str:
    buttons = []
    for mode_id, label, btn_class in SUMMARY_MODES:
        buttons.append(
            f'<button type="button" class="btn btn-sm btn-{btn_class} ecs-outage-mode-btn me-1 mb-1" '
            f'data-q="@outage-mode:{scenario_key}:{mode_id}">{label}</button>'
        )
    return "".join(buttons)


def _ctx(scenario: dict, role: str) -> dict:
    return {
        "framework": "Enterprise-wide",
        "application": scenario.get("application", ""),
        "module": "Operations",
        "severity": scenario.get("severity", "HIGH"),
        "user_role": role,
    }


def _drill_row(links: list[str]) -> str:
    if not links:
        return ""
    return (
        '<div class="ecs-ops-drilldowns mt-2 pt-2 border-top">'
        '<small class="text-muted d-block mb-1">Drilldowns:</small>'
        + " ".join(links)
        + "</div>"
    )


def build_summary_mode_html(scenario: dict, mode: str, scenario_key: str, role: str, user: str = "User") -> str:
    ctx = _ctx(scenario, role)
    app = scenario["application"]
    drills = [
        mvp_url("correlation", role, user, application=app),
        mvp_url("audit_prep", role, user, application=app, tab="gaps"),
        mvp_url("evidence_health", role, user, application=app),
        mvp_url("risk_register", role, user),
    ]
    drill_links = [
        link_html("Cross-Tool Correlation", drills[0], "btn btn-outline-primary btn-sm me-1 mb-1"),
        link_html("Audit Prep Gaps", drills[1], "btn btn-outline-warning btn-sm me-1 mb-1"),
        link_html("Evidence Health", drills[2], "btn btn-outline-success btn-sm me-1 mb-1"),
        link_html("Risk Register", drills[3], "btn btn-outline-danger btn-sm me-1 mb-1"),
    ]

    if mode == "business":
        body = f"""
<details open class="ecs-ops-detail-wrap mb-2"><summary class="fw-semibold text-primary">Business Summary</summary>
<div class="ecs-ops-detail ecs-ops-business border-start border-4 border-primary ps-2 mt-2">
<p><strong>{app}</strong> is experiencing service disruption affecting retail and digital banking channels.</p>
<p><strong>Customer impact:</strong> {scenario['customer_impact']}</p>
<ul><li>Delayed logins and session timeouts on internet and mobile channels</li>
<li>Intermittent transaction confirmation delays</li>
<li>Call-centre volume elevated — estimated 12% above baseline</li></ul>
<p><strong>Impact level:</strong> {scenario['impact_level']} · <strong>Data compromise:</strong> {scenario['data_compromise']}</p>
<p><strong>Business units:</strong> {', '.join(scenario['business_units'])}</p>
<p><strong>Estimated recovery:</strong> {scenario['eta']}</p>
<p class="mb-0"><em>Advisory: Infrastructure stabilization and transaction queue restoration in progress.</em></p>
</div></details>"""

    elif mode == "technical":
        obs = "".join(f"<li>{o}</li>" for o in scenario["governance_observations"])
        causes = "".join(f"<li>{c}</li>" for c in scenario["technical_causes"])
        actions = "".join(f"<li>{a}</li>" for a in scenario["recommended_actions"])
        body = f"""
<details open class="ecs-ops-detail-wrap mb-2"><summary class="fw-semibold">Technical Summary</summary>
<div class="ecs-ops-detail ecs-ops-technical border-start border-4 border-dark ps-2 mt-2">
<p><strong>Probable correlated causes:</strong></p><ul class="ecs-paginated-list">{causes}</ul>
<p><strong>Related governance observations:</strong></p><ul class="ecs-paginated-list">{obs}</ul>
<p><strong>Impacted applications:</strong> {', '.join(scenario['impacted_apps'])}</p>
<p><strong>Recommended actions:</strong></p><ul class="ecs-paginated-list">{actions}</ul>
</div></details>"""

    elif mode == "executive":
        body = f"""
<details open class="ecs-ops-detail-wrap mb-2"><summary class="fw-semibold text-info">Executive Summary</summary>
<div class="ecs-ops-detail border-start border-4 border-info ps-2 mt-2">
<p><strong>Status:</strong> {scenario['status']} · <strong>Severity:</strong> {scenario['severity']}</p>
<p>CIO briefing — {app} degradation with moderate customer impact. No confirmed data compromise.</p>
<ul>
<li><strong>Regulatory exposure:</strong> RBI Cyber incident reporting threshold under review; PCI DSS logging controls unaffected</li>
<li><strong>Audit year FY2026:</strong> 3 linked open observations may require auditor notification if outage exceeds 4 hours</li>
<li><strong>Recovery ETA:</strong> {scenario['eta']}</li>
<li><strong>Escalation:</strong> P1 ServiceNow incident active; DR validation triggered under ITPP</li>
</ul>
<p class="mb-0"><em>Board talking point: Service restoration prioritized; compensating monitoring active.</em></p>
</div></details>"""
        drill_links.append(link_html("CIO Dashboard", mvp_url("enterprise", role, user), "btn btn-outline-info btn-sm me-1 mb-1"))

    elif mode == "audit":
        obs = scenario["governance_observations"][:4]
        obs_lis = "".join(f"<li>{o}</li>" for o in obs)
        body = f"""
<details open class="ecs-ops-detail-wrap mb-2"><summary class="fw-semibold text-warning">Audit Summary</summary>
<div class="ecs-ops-detail border-start border-4 border-warning ps-2 mt-2">
<p>Internal audit and external assurance impact for <strong>{app}</strong>:</p>
<ul class="ecs-paginated-list">{obs_lis}</ul>
<p><strong>Audit observations at risk:</strong> DB Baselining TDE review, ITPP DR drill overdue, VAPT closure evidence pending.</p>
<p><strong>Auditor actions:</strong> Request incident timeline evidence; validate compensating controls for failover cluster TD EXC-2026-014.</p>
<p class="mb-0">Mock audit readiness score may drop 4–6 points until incident closure evidence uploaded.</p>
</div></details>"""
        drill_links.insert(0, link_html("Audit Prep Queue", drills[1], "btn btn-outline-warning btn-sm me-1 mb-1"))

    elif mode == "compliance":
        fw_links = [
            link_html("PCI DSS", framework_url("PCI DSS", role, user), "btn btn-outline-danger btn-sm me-1 mb-1"),
            link_html("DPSC", framework_url("DPSC", role, user), "btn btn-outline-danger btn-sm me-1 mb-1"),
            link_html("RBI Cyber Security", framework_url("RBI Cyber Security", role, user), "btn btn-outline-danger btn-sm me-1 mb-1"),
            link_html("ITPP", framework_url("ITPP", role, user), "btn btn-outline-danger btn-sm me-1 mb-1"),
        ]
        body = f"""
<details open class="ecs-ops-detail-wrap mb-2"><summary class="fw-semibold text-danger">Compliance Summary</summary>
<div class="ecs-ops-detail border-start border-4 border-danger ps-2 mt-2">
<p><strong>Framework impact for {app}:</strong></p>
<ul>
<li><strong>PCI DSS:</strong> Logging and monitoring controls — no CDE breach indicated; incident evidence required for Q2 attestation</li>
<li><strong>DPSC:</strong> Payment channel availability SLA breach risk — NPCI reporting review if duration exceeds threshold</li>
<li><strong>RBI Cyber Security:</strong> Incident classification under IS policy §4.2 — severity {scenario['severity']}</li>
<li><strong>ITPP:</strong> DR and incident management controls engaged — failover validation pending</li>
</ul>
<p><strong>Framework drilldowns:</strong></p><div>{''.join(fw_links)}</div>
</div></details>"""

    elif mode == "evidence":
        ev_drills = [
            link_html("Evidence Health", drills[2], "btn btn-outline-success btn-sm me-1 mb-1"),
            link_html("Evidence Reuse", mvp_url("reuse", role, user), "btn btn-outline-success btn-sm me-1 mb-1"),
            link_html("Completeness Gaps", mvp_url("completeness", role, user, application=app), "btn btn-outline-success btn-sm me-1 mb-1"),
            action_link("upload_missing", role, user, ctx),
        ]
        body = f"""
<details open class="ecs-ops-detail-wrap mb-2"><summary class="fw-semibold text-success">Evidence Summary</summary>
<div class="ecs-ops-detail border-start border-4 border-success ps-2 mt-2">
<p>Evidence posture linked to <strong>{app}</strong> incident:</p>
<ul>
<li>Incident timeline artefacts — ServiceNow export pending upload to Audit Prep</li>
<li>DB Baselining — TDE attestation stale &gt; 90 days on CBS cluster</li>
<li>ITPP — DR drill evidence overdue; blocks clean audit opinion on availability controls</li>
<li>Tripwire baseline drift report — required for root-cause closure pack</li>
</ul>
<p><strong>Owners:</strong> App Owner (Net Banking), Infrastructure Lead, Compliance Officer</p>
<div>{''.join(ev_drills)}</div>
</div></details>"""

    elif mode == "incident":
        timeline = "".join(
            f'<div class="ecs-ops-timeline-item"><small class="text-muted">{t}</small><br>{e}</div>'
            for t, e in scenario.get("timeline", [])[:5]
        )
        inc_id = scenario["correlated_signals"][0].split("—")[0].strip() if scenario.get("correlated_signals") else "INC-OPEN"
        body = f"""
<details open class="ecs-ops-detail-wrap mb-2"><summary class="fw-semibold">Incident Summary</summary>
<div class="ecs-ops-detail border-start border-4 border-secondary ps-2 mt-2">
<p><strong>Primary ticket:</strong> {inc_id}</p>
<p><strong>Status:</strong> {scenario['status']} · <strong>Severity:</strong> {scenario['severity']} · <strong>ETA:</strong> {scenario['eta']}</p>
<p><strong>Correlated signals:</strong></p><ul class="small ecs-paginated-list">
{''.join(f'<li>{s}</li>' for s in scenario['correlated_signals'][:5])}</ul>
<p><strong>Operations timeline:</strong></p>{timeline}
</div></details>"""
        drill_links.insert(0, link_html("Integrations Hub", mvp_url("integrations_hub", role, user), "btn btn-outline-secondary btn-sm me-1 mb-1"))

    elif mode == "root_cause":
        causes = scenario["technical_causes"]
        rca = "".join(
            f"<li><strong>Level {i+1}:</strong> {c}</li>"
            for i, c in enumerate(causes[:4])
        )
        body = f"""
<details open class="ecs-ops-detail-wrap mb-2"><summary class="fw-semibold text-dark">Root Cause Analysis</summary>
<div class="ecs-ops-detail border-start border-4 border-dark ps-2 mt-2">
<p>5-Whys style RCA for <strong>{app}</strong>:</p>
<ol class="ecs-paginated-list">{rca}</ol>
<p><strong>Contributing governance gaps:</strong></p>
<ul class="ecs-paginated-list">{''.join(f'<li>{o}</li>' for o in scenario['governance_observations'][:3])}</ul>
<p><strong>Corrective actions:</strong></p>
<ul class="ecs-paginated-list">{''.join(f'<li>{a}</li>' for a in scenario['recommended_actions'][:4])}</ul>
<p class="mb-0"><em>Permanent fix requires DB failover hardening + Tripwire drift closure + ITPP DR validation.</em></p>
</div></details>"""
        drill_links.insert(0, link_html("Correlation Chain", drills[0], "btn btn-outline-dark btn-sm me-1 mb-1"))

    else:
        body = f'<p class="small text-muted">Summary mode "{mode}" is not configured.</p>'

    back = (
        f'<button type="button" class="btn btn-sm btn-link ecs-outage-mode-btn p-0" '
        f'data-q="Why is {app} down?">← Back to incident overview</button>'
    )
    return body + _drill_row(drill_links) + f'<div class="mt-2">{back}</div>'
