"""AI SDLC Application Onboarding — automated ECS execution workspace."""

from __future__ import annotations

from typing import Any

from app.ai_sdlc_workflow_engine import (
    _controls_for_framework,
    _onboarded_applications,
    control_name_for,
)
from app.demo_data_standards import BANKING_OWNERS, between, pick, seed

_ONBOARDING_SUMMARY = {
    "applications_discovered": 142,
    "framework_mappings": 716,
    "controls_assigned": 4872,
    "evidence_requests": 2140,
    "work_packages_generated": 4872,
    "success_rate_pct": 98.7,
}

_FRAMEWORK_MAPPINGS = [
    ("VAPT", 102),
    ("DPSC", 78),
    ("OS Baselining", 142),
    ("Database Baselining", 81),
    ("Middleware Baselining", 67),
    ("CSITE", 54),
    ("ITPP", 142),
    ("AI Governance Controls", 18),
    ("Regulatory Controls", 96),
]

_WORK_PACKAGE_COUNTS = {
    "requirement": 1102,
    "design": 894,
    "development": 1005,
    "testing": 1121,
    "go_live": 750,
}

_FRAMEWORK_READINESS = [
    {"framework": "VAPT", "applications": 102, "controls": 560, "coverage_pct": 72, "status": "Ready"},
    {"framework": "DPSC", "applications": 78, "controls": 420, "coverage_pct": 65, "status": "In Progress"},
    {"framework": "OS Baselining", "applications": 142, "controls": 900, "coverage_pct": 91, "status": "Ready"},
    {"framework": "Database Baselining", "applications": 81, "controls": 430, "coverage_pct": 67, "status": "In Progress"},
    {"framework": "Middleware Baselining", "applications": 67, "controls": 380, "coverage_pct": 64, "status": "In Progress"},
    {"framework": "CSITE", "applications": 54, "controls": 290, "coverage_pct": 70, "status": "Ready"},
    {"framework": "ITPP", "applications": 142, "controls": 1100, "coverage_pct": 89, "status": "Ready"},
    {"framework": "AI Governance Controls", "applications": 18, "controls": 142, "coverage_pct": 88, "status": "Ready"},
    {"framework": "Regulatory Controls", "applications": 96, "controls": 650, "coverage_pct": 76, "status": "In Progress"},
]


def build_onboarding_shell() -> dict[str, Any]:
    return {
        "title": "Application Onboarding",
        "subtitle": (
            "Discover applications, determine applicable frameworks, assign controls "
            "and generate AI SDLC work packages."
        ),
    }


def build_onboarding_run() -> dict[str, Any]:
    s = _ONBOARDING_SUMMARY
    step2_lines = [f"{fw} mapped to {count} applications" for fw, count in _FRAMEWORK_MAPPINGS]
    return {
        "execution_steps": [
            {
                "step": 1,
                "phase": "Scanning Application Inventory...",
                "results": [f"Applications discovered: {s['applications_discovered']}"],
            },
            {
                "step": 2,
                "phase": "Determining Applicable Frameworks...",
                "results": step2_lines,
            },
            {
                "step": 3,
                "phase": "Loading Framework Control Libraries...",
                "results": [
                    "Frameworks loaded: 9",
                    "Domains loaded: 84",
                    "Controls loaded: 4,872",
                ],
            },
            {
                "step": 4,
                "phase": "Assigning Controls To Applications...",
                "results": [
                    f"Applications processed: {s['applications_discovered']}",
                    f"Control assignments created: {s['controls_assigned']:,}",
                ],
            },
            {
                "step": 5,
                "phase": "Generating AI SDLC Work Packages...",
                "results": [
                    f"Requirement tasks generated: {_WORK_PACKAGE_COUNTS['requirement']:,}",
                    f"Controlled Design tasks generated: {_WORK_PACKAGE_COUNTS['design']:,}",
                    f"Controlled Development tasks generated: {_WORK_PACKAGE_COUNTS['development']:,}",
                    f"Controlled Testing tasks generated: {_WORK_PACKAGE_COUNTS['testing']:,}",
                    f"Go-Live tasks generated: {_WORK_PACKAGE_COUNTS['go_live']:,}",
                ],
            },
            {
                "step": 6,
                "phase": "Preparing ECS Evidence Collection Tasks...",
                "results": [f"Evidence requests created: {s['evidence_requests']:,}"],
            },
            {
                "step": 7,
                "phase": "Onboarding Complete",
                "results": [],
            },
        ],
        "summary": s,
        "framework_readiness": _FRAMEWORK_READINESS,
        "application_results": _application_results(),
    }


def _application_results() -> list[dict[str, Any]]:
    apps = _onboarded_applications()
    presets = [
        ("Net Banking", 9, 52, 84, "Ready"),
        ("Mobile Banking", 8, 48, 79, "In Progress"),
        ("Payments", 7, 44, 82, "Ready"),
        ("Core Banking", 9, 61, 91, "Ready"),
    ]
    rows = []
    seen = set()
    for name, fw_count, ctrl_count, readiness, status in presets:
        rows.append({
            "application": name,
            "frameworks_assigned": fw_count,
            "controls_assigned": ctrl_count,
            "readiness_pct": readiness,
            "status": status,
        })
        seen.add(name)
    for app in apps:
        if app["application_name"] in seen:
            continue
        s = seed("obapp", app["application_name"])
        rows.append({
            "application": app["application_name"],
            "frameworks_assigned": between(s, 5, 9),
            "controls_assigned": between(s >> 2, 32, 58),
            "readiness_pct": between(s >> 4, 68, 94),
            "status": pick(s >> 6, ["Ready", "In Progress", "Pending"]),
        })
        if len(rows) >= 16:
            break
    return rows


def build_framework_onboarding_drill(framework: str) -> dict[str, Any]:
    mapping = next(((f, c) for f, c in _FRAMEWORK_MAPPINGS if f == framework), None)
    if not mapping:
        mapping = (framework, between(seed("obfw", framework), 40, 120))
    fw, app_count = mapping
    readiness = next((r for r in _FRAMEWORK_READINESS if r["framework"] == fw), None)
    if not readiness:
        readiness = {
            "framework": fw,
            "applications": app_count,
            "controls": between(seed("obfwc", fw), 200, 800),
            "coverage_pct": between(seed("obfwp", fw), 58, 92),
            "status": "In Progress",
        }
    s = seed("obfwdrill", fw)
    domains = list(dict.fromkeys(
        c["domain"] for c in _controls_for_framework(fw, 8)
    ))[:6]
    return {
        "title": f"Framework Overview — {fw}",
        "framework": fw,
        "applications_mapped": app_count,
        "domains": domains,
        "controls_assigned": readiness["controls"],
        "readiness_pct": readiness["coverage_pct"],
        "status": readiness["status"],
        "open_gaps": between(s, 3, 18),
        "pending_requirements": between(s >> 2, 12, 48),
        "pending_design": between(s >> 4, 8, 36),
        "pending_testing": between(s >> 6, 6, 28),
        "evidence_pending": between(s >> 8, 15, 62),
        "applications": [
            pick(seed("obfwa", fw, i), _onboarded_applications())["application_name"]
            for i in range(min(8, app_count // 12 + 3))
        ],
    }


def build_application_onboarding_drill(application: str) -> dict[str, Any]:
    apps = _onboarded_applications()
    app = next((a for a in apps if a["application_name"] == application), apps[0])
    s = seed("obappdrill", application)
    fw_list = app.get("frameworks", ["VAPT", "DPSC"])
    controls = []
    for fw in fw_list[:4]:
        for ctrl in _controls_for_framework(fw, 3):
            controls.append({
                "framework": fw,
                "control_id": ctrl["control_id"],
                "control_name": control_name_for(ctrl["control_id"]),
            })
    return {
        "title": f"Application Overview — {application}",
        "application": application,
        "owner": app.get("application_owner", pick(s, BANKING_OWNERS)),
        "frameworks": fw_list,
        "controls_assigned": between(s, 38, 62),
        "readiness_pct": between(s >> 2, 72, 94),
        "open_requirements": between(s >> 4, 4, 14),
        "open_design": between(s >> 6, 3, 11),
        "open_development": between(s >> 8, 3, 12),
        "open_testing": between(s >> 10, 2, 10),
        "open_golive": between(s >> 12, 1, 8),
        "evidence_pending": between(s >> 14, 6, 22),
        "open_findings": between(s >> 16, 0, 5),
        "remediation_status": pick(s >> 18, ["On Track", "At Risk", "Remediation In Progress", "Clear"]),
        "controls": controls[:12],
    }
