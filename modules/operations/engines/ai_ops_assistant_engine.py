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


def build_summary_mode_buttons(scenario_key: str, active_mode: str = "") -> str:
    buttons = []
    for mode_id, label, btn_class in SUMMARY_MODES:
        active = " active" if mode_id == active_mode else ""
        buttons.append(
            f'<button type="button" class="btn btn-sm btn-{btn_class} ecs-outage-mode-btn me-1 mb-1{active}" '
            f'data-scenario-key="{scenario_key}" data-mode-id="{mode_id}" '
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
    from modules.operations.engines.ai_ops_response_modes import render_response_mode

    body = render_response_mode(scenario, mode, scenario_key, role, user)
    app = scenario["application"]
    back = (
        f'<button type="button" class="btn btn-sm btn-link ecs-outage-mode-reset p-0" '
        f'data-scenario-key="{scenario_key}">← Show all modes</button>'
    )
    return body + f'<div class="mt-2">{back}</div>'
