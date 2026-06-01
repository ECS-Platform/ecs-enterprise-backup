"""AI SDLC Governance — executable report data builders."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Callable

from modules.ai_sdlc.engines.ai_sdlc_workflow_engine import (
    ANCHOR,
    CONTROL_NAME_POOL,
    SUPPORTED_FRAMEWORKS,
    STAGE_LABELS,
    _controls_for_framework,
    _onboarded_applications,
    build_findings_remediation,
    control_name_for,
)
from modules.shared.utils.demo_data_standards import BANKING_OWNERS, between, pick, seed

_REPORT_IDS = frozenset({
    "app-compliance", "fw-compliance", "readiness", "control-impl",
    "evidence-status", "findings",
})

_IMPL_STATUSES = ["Complete", "In Progress", "Not Started", "Blocked"]


def _months(count: int = 6) -> list[str]:
    out = []
    for i in range(count - 1, -1, -1):
        d = ANCHOR.replace(day=1) - timedelta(days=30 * i)
        out.append(d.strftime("%b %Y"))
    return out


def build_application_compliance_report() -> dict[str, Any]:
    apps = _onboarded_applications()
    rows: list[dict[str, Any]] = []
    for app in apps[:12]:
        for fw in app["frameworks"][:3]:
            for ctrl in _controls_for_framework(fw, 2):
                s = seed("acr", app["application_name"], fw, ctrl["control_id"])
                cid = ctrl["control_id"]
                rows.append({
                    "application": app["application_name"],
                    "framework": fw,
                    "domain": ctrl["domain"],
                    "control_id": cid,
                    "control_name": control_name_for(cid),
                    "implementation_status": pick(s, ["Approved", "In Review", "Pending", "Needs Rework"]),
                })
    return {
        "id": "app-compliance",
        "title": "Application Compliance Report",
        "subtitle": "Application → Framework → Domain → Control implementation status",
        "columns": [
            {"key": "application", "label": "Application", "wrap": True},
            {"key": "framework", "label": "Framework"},
            {"key": "domain", "label": "Domain", "wrap": True},
            {"key": "control_id", "label": "Control ID"},
            {"key": "control_name", "label": "Control Name", "wrap": True},
            {"key": "implementation_status", "label": "Implementation Status"},
        ],
        "rows": rows,
    }


def build_framework_compliance_report() -> dict[str, Any]:
    apps = _onboarded_applications()
    rows = []
    for fw in [f["name"] for f in SUPPORTED_FRAMEWORKS]:
        s = seed("fcr", fw)
        total = between(s, 80, 220)
        complete = between(s >> 2, int(total * 0.55), int(total * 0.92))
        rows.append({
            "framework": fw,
            "applications_in_scope": between(s >> 4, 4, min(len(apps), 18)),
            "controls_total": total,
            "controls_complete": complete,
            "compliance_pct": round(complete / total * 100, 1),
            "evidence_approved_pct": round(between(s >> 6, 62, 96), 1),
        })
    return {
        "id": "fw-compliance",
        "title": "Framework Compliance Report",
        "subtitle": "Framework-level completion and compliance across applications",
        "columns": [
            {"key": "framework", "label": "Framework", "wrap": True},
            {"key": "applications_in_scope", "label": "Applications"},
            {"key": "controls_total", "label": "Controls Total"},
            {"key": "controls_complete", "label": "Controls Complete"},
            {"key": "compliance_pct", "label": "Compliance %"},
            {"key": "evidence_approved_pct", "label": "Evidence Approved %"},
        ],
        "rows": rows,
    }


def build_readiness_report() -> dict[str, Any]:
    apps = _onboarded_applications()
    rows = []
    for app in apps[:14]:
        for fw in app["frameworks"][:2]:
            s = seed("rdy", app["application_name"], fw)
            score = between(s, 58, 98)
            rows.append({
                "application": app["application_name"],
                "framework": fw,
                "readiness_score": score,
                "requirement_gate": pick(s >> 2, ["Passed", "Passed", "Conditional", "Pending"]),
                "design_gate": pick(s >> 4, ["Passed", "Conditional", "Pending"]),
                "testing_gate": pick(s >> 6, ["Passed", "Pending", "Failed"]),
                "go_live_ready": "Yes" if score >= 85 else "Conditional" if score >= 70 else "No",
            })
    return {
        "id": "readiness",
        "title": "Readiness Report",
        "subtitle": "Application readiness by framework across SDLC gates",
        "columns": [
            {"key": "application", "label": "Application", "wrap": True},
            {"key": "framework", "label": "Framework"},
            {"key": "readiness_score", "label": "Readiness Score"},
            {"key": "requirement_gate", "label": "Requirements"},
            {"key": "design_gate", "label": "Design"},
            {"key": "testing_gate", "label": "Testing"},
            {"key": "go_live_ready", "label": "Go-Live Ready"},
        ],
        "rows": rows,
    }


def build_control_implementation_report() -> dict[str, Any]:
    apps = _onboarded_applications()
    rows = []
    for app in apps[:10]:
        fw = app["frameworks"][0]
        ctrl = pick(seed("cir", app["application_name"]), _controls_for_framework(fw))
        cid = ctrl["control_id"]
        s = seed("cir2", cid)
        rows.append({
            "application": app["application_name"],
            "framework": fw,
            "control_id": cid,
            "control_name": control_name_for(cid),
            "requirements": pick(s, _IMPL_STATUSES),
            "design": pick(s >> 2, _IMPL_STATUSES),
            "development": pick(s >> 4, _IMPL_STATUSES),
            "testing": pick(s >> 6, _IMPL_STATUSES),
            "go_live": pick(s >> 8, _IMPL_STATUSES),
        })
    return {
        "id": "control-impl",
        "title": "Control Implementation Report",
        "subtitle": "Requirement, Design, Development, Testing, Go-Live completion status",
        "columns": [
            {"key": "application", "label": "Application", "wrap": True},
            {"key": "framework", "label": "Framework"},
            {"key": "control_id", "label": "Control ID"},
            {"key": "control_name", "label": "Control Name", "wrap": True},
            {"key": "requirements", "label": "Requirements"},
            {"key": "design", "label": "Design"},
            {"key": "development", "label": "Development"},
            {"key": "testing", "label": "Testing"},
            {"key": "go_live", "label": "Go-Live"},
        ],
        "rows": rows,
    }


def build_evidence_status_report() -> dict[str, Any]:
    rows = []
    apps = _onboarded_applications()
    for i, app in enumerate(apps[:16]):
        s = seed("esr", i)
        fw = pick(s, app["frameworks"])
        required = between(s >> 2, 8, 42)
        submitted = between(s >> 4, int(required * 0.5), required)
        approved = between(s >> 6, int(submitted * 0.4), submitted)
        rows.append({
            "application": app["application_name"],
            "framework": fw,
            "evidence_required": required,
            "evidence_submitted": submitted,
            "evidence_approved": approved,
            "pending": max(required - submitted, 0),
            "overdue": between(s >> 8, 0, 5),
        })
    return {
        "id": "evidence-status",
        "title": "Evidence Collection Status Report",
        "subtitle": "Required vs Submitted vs Approved evidence by application",
        "columns": [
            {"key": "application", "label": "Application", "wrap": True},
            {"key": "framework", "label": "Framework"},
            {"key": "evidence_required", "label": "Required"},
            {"key": "evidence_submitted", "label": "Submitted"},
            {"key": "evidence_approved", "label": "Approved"},
            {"key": "pending", "label": "Pending"},
            {"key": "overdue", "label": "Overdue"},
        ],
        "rows": rows,
    }


def build_findings_report() -> dict[str, Any]:
    findings = build_findings_remediation()
    open_rows = [r for r in findings["rows"] if r["status"] in ("Open", "In Progress")][:40]
    return {
        "id": "findings",
        "title": "Findings & Remediation Report",
        "subtitle": "Open findings by application, framework, owner and severity",
        "columns": [
            {"key": "finding_id", "label": "Finding ID"},
            {"key": "application", "label": "Application", "wrap": True},
            {"key": "framework", "label": "Framework"},
            {"key": "domain", "label": "Domain", "wrap": True},
            {"key": "control", "label": "Control"},
            {"key": "severity", "label": "Severity"},
            {"key": "owner", "label": "Owner"},
            {"key": "status", "label": "Status"},
            {"key": "target_date", "label": "Target Date"},
        ],
        "rows": open_rows,
    }


_BUILDERS: dict[str, Callable[[], dict[str, Any]]] = {
    "app-compliance": build_application_compliance_report,
    "fw-compliance": build_framework_compliance_report,
    "readiness": build_readiness_report,
    "control-impl": build_control_implementation_report,
    "evidence-status": build_evidence_status_report,
    "findings": build_findings_report,
}


def build_report(report_id: str) -> dict[str, Any] | None:
    fn = _BUILDERS.get(report_id)
    return fn() if fn else None


def report_ids() -> frozenset[str]:
    return _REPORT_IDS
