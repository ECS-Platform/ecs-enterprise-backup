"""ITPP operational governance — DR, backup, change, incident, capacity, availability."""

from __future__ import annotations

from datetime import datetime, timezone

from app import ecs_state
from app.control_validation_engine import _control_domain, validation_summary
from app.framework_catalog import get_framework_controls
from app.workflow_module import build_owner_work_queue

ITPP_APPLICATIONS = [
    "Net Banking", "Mobile Banking", "UPI", "Cards", "Treasury", "LOS", "CRM",
]

ITPP_LANDING_DOMAINS = [
    "Disaster Recovery",
    "Change Management",
    "Incident Management",
    "Problem Management",
    "Capacity Management",
    "Backup Management",
    "Availability Management",
    "Vendor Governance",
]

ITPP_DOMAIN_LABELS = {
    "Backup Management": "Backup Governance",
    "Availability Management": "Availability Governance",
}

ITPP_DOMAINS = {
    "Disaster Recovery": {
        "icon": "🛡",
        "summary": "DR plan validation, drill execution, failover testing, and critical app coverage.",
        "kpis": ["dr_readiness_pct", "dr_success_rate", "overdue_dr_drills", "critical_app_coverage"],
    },
    "Backup Management": {
        "icon": "💾",
        "summary": "Backup health, retention, encryption, restore testing, and failure monitoring.",
        "kpis": ["backup_success_rate", "failed_backups", "restore_tests_passed", "offsite_backup_pct"],
    },
    "Change Management": {
        "icon": "🔄",
        "summary": "CAB governance, emergency changes, rollback plans, and unauthorized change detection.",
        "kpis": ["failed_changes", "emergency_changes", "unauthorized_changes", "rollback_success_rate"],
    },
    "Incident Management": {
        "icon": "🚨",
        "summary": "P1/P2 tracking, SLA compliance, RCA validation, and major incident reporting.",
        "kpis": ["open_p1_incidents", "sla_breaches", "rca_pending", "major_incidents_qtr"],
    },
    "Problem Management": {
        "icon": "🔍",
        "summary": "Repeat incident detection, KEDB maintenance, and permanent fix tracking.",
        "kpis": ["repeat_incidents", "unresolved_root_causes", "permanent_fix_backlog"],
    },
    "Capacity Management": {
        "icon": "📈",
        "summary": "Utilization monitoring, forecasting, saturation alerts, and scaling reviews.",
        "kpis": ["saturation_alerts", "capacity_plan_current", "peak_load_validated"],
    },
    "Availability Management": {
        "icon": "✅",
        "summary": "Uptime SLAs, HA validation, redundancy configuration, and downtime reporting.",
        "kpis": ["uptime_pct", "ha_tests_passed", "downtime_events_qtr"],
    },
    "Patch Governance": {
        "icon": "🔧",
        "summary": "Patch compliance windows, emergency patching, vulnerability SLAs, and rollback validation.",
        "kpis": ["patch_compliance_pct", "overdue_patches", "emergency_patches", "rollback_success_rate"],
    },
    "Vendor Governance": {
        "icon": "🤝",
        "summary": "Third-party risk reviews, SLA adherence, contract compliance, and vendor audit evidence.",
        "kpis": ["vendor_reviews_due", "sla_breaches", "contract_gaps", "vendor_audit_pct"],
    },
}

DOMAIN_ACTIONS = {
    "Disaster Recovery": [
        ("Upload DR Evidence", "upload_dr"),
        ("View DR Test Results", "view_dr_results"),
        ("Trigger Mock DR Drill", "mock_dr_drill"),
        ("Escalate Failed DR", "escalate_dr"),
    ],
    "Backup Management": [
        ("View Backup Logs", "view_backup_logs"),
        ("Validate Restore", "validate_restore"),
        ("Escalate Failed Backup", "escalate_backup"),
        ("Upload Backup Evidence", "upload_backup"),
    ],
    "Change Management": [
        ("View Change Ticket", "view_change_ticket"),
        ("Review CAB Approval", "review_cab"),
        ("Escalate Unauthorized Change", "escalate_change"),
    ],
    "Incident Management": [
        ("Open Incident", "open_incident"),
        ("Escalate Incident", "escalate_incident"),
        ("View RCA", "view_rca"),
        ("Approve Closure", "approve_closure"),
    ],
    "Problem Management": [
        ("Review RCA", "review_rca"),
        ("Link Problem Record", "link_problem"),
        ("Escalate Repeat Issue", "escalate_repeat"),
    ],
    "Capacity Management": [
        ("Review Capacity Plan", "review_capacity"),
        ("Approve Scaling", "approve_scaling"),
        ("Escalate Saturation Risk", "escalate_saturation"),
    ],
    "Availability Management": [
        ("Review Uptime", "review_uptime"),
        ("Escalate Availability Risk", "escalate_availability"),
    ],
    "Patch Governance": [
        ("Review Patch Window", "review_patch"),
        ("Escalate Overdue Patch", "escalate_patch"),
        ("Upload Patch Evidence", "upload_patch"),
    ],
    "Vendor Governance": [
        ("Review Vendor SLA", "review_vendor"),
        ("Escalate Contract Gap", "escalate_vendor"),
        ("Upload Vendor Audit", "upload_vendor"),
    ],
}


def _domain_controls(domain: str) -> list[dict]:
    return [
        c for c in get_framework_controls("ITPP")
        if _control_domain("ITPP", c["control"]) == domain
    ]


def _simulation(domain: str, control: dict, idx: int) -> dict:
    name = control["control"]
    seed = idx + len(name)
    if domain == "Disaster Recovery":
        return {
            "simulation_type": "DR drill report validation",
            "status": "Success" if seed % 5 else "Failed",
            "last_run": "2026-05-18 02:00 UTC",
            "detail": f"DR test for {name} — RTO validated at 4h 12m.",
            "overdue": seed % 7 == 0,
        }
    if domain == "Backup Management":
        return {
            "simulation_type": "Backup health check",
            "status": "Healthy" if seed % 4 else "Failed",
            "last_run": "2026-05-23 23:00 UTC",
            "detail": f"Backup job success rate 99.1% — {name}.",
            "overdue": False,
        }
    if domain == "Change Management":
        return {
            "simulation_type": "Change ticket validation",
            "status": "Approved" if seed % 6 else "Unauthorized",
            "last_run": "2026-05-22 11:30 UTC",
            "detail": f"CAB ticket CHG-{1000+idx} linked to {name}.",
            "overdue": seed % 9 == 0,
        }
    if domain == "Incident Management":
        return {
            "simulation_type": "Incident SLA dashboard",
            "status": "Within SLA" if seed % 5 else "Breached",
            "last_run": "2026-05-24 08:00 UTC",
            "detail": f"P1/P2 tracker — {name} SLA compliance 94.5%.",
            "overdue": seed % 8 == 0,
        }
    if domain == "Problem Management":
        return {
            "simulation_type": "Recurring incident trend",
            "status": "Stable" if seed % 4 else "Repeat detected",
            "last_run": "2026-05-20 16:00 UTC",
            "detail": f"Trend analysis for {name} — 3 repeat patterns flagged.",
            "overdue": False,
        }
    if domain == "Capacity Management":
        return {
            "simulation_type": "Utilization heatmap",
            "status": "Normal" if seed % 5 else "Saturation risk",
            "last_run": "2026-05-24 06:00 UTC",
            "detail": f"CPU avg 72% — {name} threshold review due.",
            "overdue": seed % 10 == 0,
        }
    if domain == "Patch Governance":
        return {
            "simulation_type": "Patch compliance scan",
            "status": "Compliant" if seed % 4 else "Overdue",
            "last_run": "2026-05-23 22:00 UTC",
            "detail": f"Patch window validated — {name} within SLA.",
            "overdue": seed % 6 == 0,
        }
    if domain == "Vendor Governance":
        return {
            "simulation_type": "Vendor SLA review",
            "status": "Within SLA" if seed % 5 else "Breached",
            "last_run": "2026-05-21 10:00 UTC",
            "detail": f"Vendor contract review — {name} audit current.",
            "overdue": seed % 8 == 0,
        }
    return {
        "simulation_type": "Uptime dashboard",
        "status": "99.95% uptime" if seed % 4 else "Downtime event",
        "last_run": "2026-05-24 00:00 UTC",
        "detail": f"HA failover validated — {name}.",
        "overdue": False,
    }


def build_itpp_operational_view(role: str = "owner") -> dict:
    """Full ITPP operational governance panel data."""
    domains_out = []
    queue = {f"{i['framework']}::{i['control']}": i for i in build_owner_work_queue(300) if i["framework"] == "ITPP"}
    overdue_drills = 0
    failed_backups = 0
    sla_breaches = 0
    failed_changes = 0
    repeat_problems = 0

    for domain, meta in ITPP_DOMAINS.items():
        controls = _domain_controls(domain)
        ctrl_rows = []
        for idx, ctrl in enumerate(controls):
            ckey = f"ITPP::{ctrl['control']}"
            wf = ecs_state.control_status("ITPP", ctrl["control"])
            sim = _simulation(domain, ctrl, idx)
            if domain == "Disaster Recovery" and sim.get("overdue"):
                overdue_drills += 1
            if domain == "Backup Management" and sim["status"] == "Failed":
                failed_backups += 1
            if domain == "Change Management" and sim["status"] == "Unauthorized":
                failed_changes += 1
            if domain == "Incident Management" and sim["status"] == "Breached":
                sla_breaches += 1
            if domain == "Problem Management" and sim["status"] == "Repeat detected":
                repeat_problems += 1
            qi = queue.get(ckey)
            ctrl_rows.append({
                "control": ctrl["control"],
                "control_id": ctrl["control_id"],
                "workflow_status": wf,
                "simulation": sim,
                "queue_item": qi,
                "evidence_count": len(ctrl["evidences"]),
            })
        approved = sum(1 for r in ctrl_rows if r["workflow_status"] == "approved")
        domains_out.append({
            "name": domain,
            "icon": meta["icon"],
            "summary": meta["summary"],
            "controls": ctrl_rows,
            "control_count": len(ctrl_rows),
            "approved_count": approved,
            "maturity_pct": round((approved / len(ctrl_rows)) * 100, 1) if ctrl_rows else 0,
            "actions": _role_actions(domain, role),
        })

    val = validation_summary("ITPP")
    kpis = {
        "dr_readiness_pct": _dr_readiness(domains_out),
        "dr_success_rate": 91.5,
        "overdue_dr_drills": overdue_drills,
        "critical_app_coverage": 96.0,
        "backup_success_rate": 98.2,
        "failed_backups": failed_backups,
        "restore_tests_passed": 4,
        "offsite_backup_pct": 100.0,
        "failed_changes": failed_changes,
        "emergency_changes": 3,
        "unauthorized_changes": failed_changes,
        "rollback_success_rate": 97.8,
        "open_p1_incidents": 2,
        "sla_breaches": sla_breaches,
        "rca_pending": 1,
        "major_incidents_qtr": 1,
        "repeat_incidents": repeat_problems,
        "unresolved_root_causes": 2,
        "permanent_fix_backlog": 4,
        "saturation_alerts": 3,
        "capacity_plan_current": True,
        "peak_load_validated": True,
        "uptime_pct": 99.94,
        "ha_tests_passed": 5,
        "downtime_events_qtr": 2,
        "validation_effectiveness": val["effectiveness_pct"],
        "failed_validations": val["failed"],
    }
    return {
        "domains": domains_out,
        "kpis": kpis,
        "drill_log": ecs_state.itpp_drill_log[-5:],
        "role": role,
    }


def _dr_readiness(domains: list[dict]) -> float:
    for d in domains:
        if d["name"] == "Disaster Recovery":
            return d["maturity_pct"]
    return 0.0


def _role_actions(domain: str, role: str) -> list[tuple[str, str]]:
    actions = DOMAIN_ACTIONS.get(domain, [])
    if role == "auditor":
        return [(a, c) for a, c in actions if any(w in a for w in ("Review", "Approve", "View", "Assign", "Reassign", "Escalate"))]
    if role in ("cio", "vertical_head", "compliance_head"):
        return [(a, c) for a, c in actions if any(w in a for w in ("Escalate", "View", "Review"))]
    return actions


def execute_itpp_action(action: str, domain: str, user: str, role: str) -> str:
    """Record mock operational action and return notice message."""
    from app.audit_trail import log_event

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    messages = {
        "mock_dr_drill": f"Mock DR drill initiated for {domain or 'Disaster Recovery'} — simulation queued.",
        "escalate_dr": "Failed DR control escalated to CIO workflow queue.",
        "escalate_backup": "Failed backup alert escalated to operations leadership.",
        "escalate_change": "Unauthorized change detected — escalated to Compliance Head.",
        "escalate_incident": "P1 incident escalated — vertical head notified.",
        "escalate_saturation": "Capacity saturation risk escalated for executive review.",
        "escalate_availability": "Availability risk escalated — HA review scheduled.",
        "validate_restore": "Restore validation job started — results in backup logs within 15 min.",
        "view_dr_results": "DR test results loaded in operational panel.",
        "review_cab": "CAB approval package opened for auditor review.",
    }
    msg = messages.get(action, f"ITPP action '{action}' recorded for {domain or 'ITPP'}.")
    ecs_state.itpp_drill_log.append({
        "action": action,
        "domain": domain,
        "user": user,
        "role": role,
        "timestamp": ts,
        "message": msg,
    })
    log_event(
        action=f"ITPP {action.replace('_', ' ').title()}",
        actor=user,
        role=role,
        framework="ITPP",
        control=domain or "Operational",
        detail=msg,
    )
    return msg


def _seed_metric(seed: str, lo: int, hi: int) -> int:
    return (hash(seed) % (hi - lo + 1)) + lo


def build_itpp_landing_cards() -> list[dict]:
    """Category cards for ITPP command center landing."""
    cards = []
    op = build_itpp_operational_view()
    domain_map = {d["name"]: d for d in op["domains"]}
    for domain in ITPP_LANDING_DOMAINS:
        meta = ITPP_DOMAINS.get(domain, {"icon": "📋", "summary": ""})
        d = domain_map.get(domain, {})
        gaps = max(0, d.get("control_count", 0) - d.get("approved_count", 0))
        cards.append({
            "name": domain,
            "label": ITPP_DOMAIN_LABELS.get(domain, domain),
            "icon": meta["icon"],
            "applications": _seed_metric(domain + "apps", 4, 7),
            "controls_coverage": f"{d.get('maturity_pct', _seed_metric(domain + 'mat', 78, 94))}%",
            "policy_compliance": f"{_seed_metric(domain + 'pol', 82, 97)}%",
            "open_gaps": gaps or _seed_metric(domain + "gap", 1, 6),
            "expired_reviews": _seed_metric(domain + "exp", 0, 3),
            "tone": "danger" if gaps > 4 else ("warning" if gaps > 1 else "success"),
        })
    return cards


def build_itpp_domain_view(domain: str) -> dict | None:
    """DR maturity dashboard for a selected ITPP domain."""
    if domain not in ITPP_DOMAINS:
        return None
    op = build_itpp_operational_view()
    domain_data = next((d for d in op["domains"] if d["name"] == domain), None)
    if not domain_data:
        return None
    apps = []
    for idx, app_name in enumerate(ITPP_APPLICATIONS):
        seed = domain + app_name
        apps.append({
            "name": app_name,
            "dr_status": "Ready" if _seed_metric(seed + "dr", 0, 4) else "At Risk",
            "test_success_pct": _seed_metric(seed + "tst", 82, 99),
            "evidence_count": _seed_metric(seed + "ev", 2, 8),
            "overdue": _seed_metric(seed + "od", 0, 3) == 0,
            "pending_reviews": _seed_metric(seed + "pr", 0, 2),
            "maturity_pct": _seed_metric(seed + "m", 75, 98),
        })
    return {
        "domain": domain,
        "icon": ITPP_DOMAINS[domain]["icon"],
        "summary": ITPP_DOMAINS[domain]["summary"],
        "maturity_pct": domain_data.get("maturity_pct", 0),
        "control_count": domain_data.get("control_count", 0),
        "approved_count": domain_data.get("approved_count", 0),
        "dr_test_success_pct": _seed_metric(domain + "drsucc", 88, 98),
        "overdue_applications": sum(1 for a in apps if a["overdue"]),
        "pending_reviews": sum(a["pending_reviews"] for a in apps),
        "applications": apps,
        "controls": domain_data.get("controls", []),
        "actions": domain_data.get("actions", []),
        "kpis": op["kpis"],
    }


def build_itpp_app_view(domain: str, application: str, catalog_controls: list[dict] | None = None) -> dict | None:
    """Application-wise controls and workflow for ITPP domain drill-down."""
    if domain not in ITPP_DOMAINS or application not in ITPP_APPLICATIONS:
        return None
    controls = catalog_controls or get_framework_controls("ITPP")
    domain_controls = [c for c in controls if _control_domain("ITPP", c["control"]) == domain]
    rows = []
    for ctrl in domain_controls:
        app_evs = [ev for ev in ctrl.get("evidences", []) if ev.get("application_name") == application]
        if not app_evs:
            app_evs = ctrl.get("evidences", [])[:1]
        ckey = f"ITPP::{ctrl['control']}"
        rows.append({
            "control": ctrl["control"],
            "control_id": ctrl["control_id"],
            "evidences": app_evs,
            "workflow_status": ecs_state.control_status("ITPP", ctrl["control"]),
            "ckey": ckey,
        })
    pending = sum(1 for r in rows if r["ckey"] in ecs_state.submitted_controls or r["ckey"] in ecs_state.rejected_controls)
    return {
        "domain": domain,
        "application": application,
        "controls": rows,
        "pending_count": pending,
        "maturity_pct": _seed_metric(domain + application + "mat", 78, 96),
    }
