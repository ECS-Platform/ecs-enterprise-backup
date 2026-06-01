"""AI SDLC Control Tower — orchestration and monitoring data (Phase 2)."""

from __future__ import annotations

from typing import Any

from modules.ai_sdlc.engines.ai_sdlc_workflow_engine import (
    ANCHOR,
    STAGE_ARTIFACTS,
    STAGE_LABELS,
    _controls_for_framework,
    _onboarded_applications,
    control_name_for,
)
from modules.shared.utils.demo_data_standards import BANKING_OWNERS, between, pick, seed

TAB_IDS = (
    "run-scheduler",
    "framework-readiness",
    "action-queue",
    "scheduler-log",
    "ai-recommendations",
)

_TOWER_FRAMEWORKS = [
    "VAPT", "DPSC", "OS Baselining", "Database Baselining",
    "Middleware Baselining", "CSITE", "ITPP", "Regulatory Controls",
]

_STAGE_KEYS = ("requirement", "design", "development", "testing", "go-live")
_STAGE_SHORT = {
    "requirement": "Req",
    "design": "Design",
    "development": "Dev",
    "testing": "Test",
    "go-live": "Go-Live",
}
_STAGE_SLUGS = {
    "Requirements": "requirements",
    "Design": "design",
    "Development": "development",
    "Testing": "testing",
    "Go-Live": "golive",
}

_ACTION_STATUSES = [
    "Pending Submission", "Awaiting Review", "Needs Rework", "Overdue", "Ready For Approval",
]

_RUN_SUMMARY = {
    "applications_scanned": 142,
    "frameworks_assessed": 8,
    "controls_assessed": 4872,
    "evidence_items_scanned": 18341,
    "open_findings": 127,
    "applications_ready_golive": 19,
    "applications_requiring_attention": 37,
}


def _readiness_tone(pct: int) -> str:
    if pct >= 80:
        return "green"
    if pct >= 55:
        return "amber"
    return "red"


def _stage_key_from_label(label: str) -> str:
    for k, v in STAGE_LABELS.items():
        if v == label or _STAGE_SHORT.get(k) == label:
            return k
    aliases = {"Req": "requirement", "Dev": "development", "Test": "testing"}
    return aliases.get(label, label.lower())


def build_run_scheduler() -> dict[str, Any]:
    s = _RUN_SUMMARY
    matrix = []
    for fw in _TOWER_FRAMEWORKS:
        cells = []
        for sk in _STAGE_KEYS:
            pct = between(seed("rsm", fw, sk), 58, 97)
            cells.append({
                "stage_key": sk,
                "stage_label": STAGE_LABELS[sk],
                "stage_short": _STAGE_SHORT[sk],
                "readiness_pct": pct,
                "tone": _readiness_tone(pct),
            })
        matrix.append({"framework": fw, "cells": cells})
    return {
        "execution_steps": [
            {"phase": "Loading Applications...", "result": f"{s['applications_scanned']} Applications Loaded"},
            {"phase": "Loading Frameworks...", "result": f"{s['frameworks_assessed']} Frameworks Mapped"},
            {"phase": "Loading Controls...", "result": f"{s['controls_assessed']:,} Controls Assessed"},
            {"phase": "Loading Evidence...", "result": f"{s['evidence_items_scanned']:,} Evidence Records Scanned"},
            {"phase": "Calculating Requirement Readiness...", "result": "Completed"},
            {"phase": "Calculating Controlled Design Readiness...", "result": "Completed"},
            {"phase": "Calculating Controlled Development Readiness...", "result": "Completed"},
            {"phase": "Calculating Controlled Testing Readiness...", "result": "Completed"},
            {"phase": "Calculating Controlled Go-Live Readiness...", "result": "Completed"},
            {"phase": "Generating Findings Summary...", "result": "Completed"},
            {"phase": "Generating Readiness Report...", "result": "Completed"},
            {"phase": "Scheduler Run Complete", "result": ""},
        ],
        "summary": s,
        "readiness_matrix": {
            "stage_columns": [_STAGE_SHORT[k] for k in _STAGE_KEYS],
            "rows": matrix,
        },
    }


def build_framework_readiness() -> dict[str, Any]:
    stage_cols = [STAGE_LABELS[k] for k in _STAGE_KEYS]
    rows = []
    for fw in _TOWER_FRAMEWORKS:
        cells = []
        for sk in _STAGE_KEYS:
            pct = between(seed("ctfrc", fw, sk), 42, 98)
            cells.append({
                "stage": STAGE_LABELS[sk],
                "stage_key": sk,
                "readiness_pct": pct,
                "tone": _readiness_tone(pct),
            })
        rows.append({"framework": fw, "cells": cells})
    return {"stage_columns": stage_cols, "heatmap": rows}


def build_action_queue() -> dict[str, Any]:
    apps = _onboarded_applications()
    rows = []
    for i in range(36):
        s = seed("ctaq", i)
        app = pick(s, apps)
        fw = pick(s >> 2, app["frameworks"])
        ctrl = pick(s >> 4, _controls_for_framework(fw))
        stage_label = pick(s >> 6, list(STAGE_LABELS.values()))
        sk = _stage_key_from_label(stage_label)
        status = pick(s >> 8, _ACTION_STATUSES)
        due = ANCHOR.replace(day=min(28, between(s >> 10, 1, 28)))
        rows.append({
            "activity_id": f"ACT-CT-{i+1:04d}",
            "application": app["application_name"],
            "framework": fw,
            "control_id": ctrl["control_id"],
            "control_name": control_name_for(ctrl["control_id"]),
            "stage": stage_label,
            "stage_key": sk,
            "owner": pick(s >> 12, BANKING_OWNERS),
            "status": status,
            "due_date": due.strftime("%Y-%m-%d"),
        })
    return {"rows": rows}


def build_action_queue_detail(activity_id: str) -> dict[str, Any] | None:
    queue = build_action_queue()
    row = next((r for r in queue["rows"] if r["activity_id"] == activity_id), None)
    if not row:
        return None
    s = seed("ctaqd", activity_id)
    sk = row["stage_key"]
    artifacts = STAGE_ARTIFACTS.get(sk, ["Evidence Document"])
    return {
        **row,
        "artifact_required": pick(s, artifacts),
        "comments": [
            {"author": row["owner"], "text": pick(s >> 2, [
                "Awaiting security team review.",
                "Please upload latest scan report.",
                "Rework requested — missing control mapping.",
            ]), "at": ANCHOR.strftime("%Y-%m-%d %H:%M UTC")},
        ],
        "approval_history": [
            {
                "timestamp": ANCHOR.strftime("%Y-%m-%d %H:%M UTC"),
                "action": "Submitted",
                "actor": row["owner"],
                "from_status": "Pending Submission",
                "to_status": row["status"],
                "comments": "",
            },
        ],
        "audit_trail": [
            {
                "timestamp": ANCHOR.strftime("%Y-%m-%d %H:%M UTC"),
                "action": "Work Item Created",
                "actor": "ECS Scheduler",
                "detail": f"{row['application']} · {row['framework']} · {row['control_id']}",
            },
            {
                "timestamp": ANCHOR.strftime("%Y-%m-%d %H:%M UTC"),
                "action": "Status Update",
                "actor": row["owner"],
                "detail": f"Status set to {row['status']}",
            },
        ],
    }


def build_scheduler_log() -> dict[str, Any]:
    s = _RUN_SUMMARY
    entries = [
        ("13:45:01", "Scheduler Started"),
        ("13:45:03", f"{s['applications_scanned']} Applications Loaded"),
        ("13:45:06", f"{s['frameworks_assessed']} Frameworks Mapped"),
        ("13:45:08", f"{s['controls_assessed']:,} Controls Assessed"),
        ("13:45:11", f"{s['evidence_items_scanned']:,} Evidence Records Scanned"),
        ("13:45:15", "Requirement Readiness Calculated"),
        ("13:45:18", "Controlled Design Readiness Calculated"),
        ("13:45:21", "Controlled Development Readiness Calculated"),
        ("13:45:25", "Controlled Testing Readiness Calculated"),
        ("13:45:29", "Controlled Go-Live Readiness Calculated"),
        ("13:45:32", f"{s['open_findings']} Open Findings Detected"),
        ("13:45:35", "Readiness Report Generated"),
        ("13:45:37", "Scheduler Run Completed"),
    ]
    return {
        "run_id": f"ECS-SCAN-{ANCHOR.strftime('%Y%m%d')}-001",
        "status": "Completed",
        "entries": [{"time": t, "message": m, "level": "info"} for t, m in entries],
        "auto_refresh_seconds": 30,
    }


def build_ai_recommendations() -> dict[str, Any]:
    apps = _onboarded_applications()
    recs = []
    templates = [
        (
            "Testing evidence missing for {n} remediation activities.",
            "Upload remediation validation report and security signoff.",
        ),
        (
            "Design artifact pending approval for {n} controls.",
            "Submit HLD and threat model for AppSec review.",
        ),
        (
            "Requirement traceability gap on {n} tier-1 controls.",
            "Complete control requirement matrix before design gate.",
        ),
        (
            "Development configuration standard not uploaded for {n} environments.",
            "Upload build and deployment configuration evidence.",
        ),
    ]
    for i, app in enumerate(apps[:16]):
        s = seed("ctrec2", i)
        fw = pick(s, app["frameworks"])
        ctrl = pick(s >> 2, _controls_for_framework(fw))
        sk = pick(s >> 4, _STAGE_KEYS)
        stage_label = STAGE_LABELS[sk]
        n = between(s >> 6, 1, 5)
        obs_tpl, rec_tpl = pick(s >> 8, templates)
        from_pct = between(s >> 10, 68, 88)
        to_pct = min(from_pct + between(s >> 12, 4, 12), 99)
        recs.append({
            "application": app["application_name"],
            "framework": fw,
            "control_id": ctrl["control_id"],
            "control_name": control_name_for(ctrl["control_id"]),
            "stage": stage_label,
            "stage_key": sk,
            "observation": obs_tpl.format(n=n),
            "recommendation": rec_tpl,
            "readiness_impact": f"{stage_label} readiness increases from {from_pct}% to {to_pct}%.",
            "readiness_from_pct": from_pct,
            "readiness_to_pct": to_pct,
            "actionable": True,
        })
    return {"rows": recs}


def build_readiness_cell_drill(framework: str, stage: str) -> dict[str, Any]:
    sk = _stage_key_from_label(stage)
    stage_label = STAGE_LABELS.get(sk, stage)
    apps = _onboarded_applications()
    rows = []
    for i in range(8):
        s = seed("rscell", framework, sk, i)
        app = pick(s, apps)
        ctrl = pick(s >> 2, _controls_for_framework(framework))
        rows.append({
            "application": app["application_name"],
            "control": f"{ctrl['control_id']} | {control_name_for(ctrl['control_id'])}",
            "status": pick(s >> 4, ["Approved", "In Review", "Pending", "Needs Rework"]),
            "evidence": f"EV-AISDLC-{between(seed('rsce', framework, sk, i), 1, 999):04d}",
        })
    pct = between(seed("rscpct", framework, sk), 58, 97)
    return {
        "title": f"{framework} · {stage_label} · {pct}%",
        "framework": framework,
        "stage": stage_label,
        "stage_key": sk,
        "readiness_pct": pct,
        "rows": rows,
    }


def build_framework_stage_drill(framework: str, stage_key: str) -> dict[str, Any]:
    sk = stage_key if stage_key in STAGE_LABELS else _stage_key_from_label(stage_key)
    stage_label = STAGE_LABELS.get(sk, stage_key)
    apps = _onboarded_applications()
    pct = between(seed("fwdrill", framework, sk), 42, 98)
    applications = []
    for i in range(6):
        s = seed("fwda", framework, sk, i)
        app = pick(s, apps)
        applications.append({
            "application": app["application_name"],
            "contribution_pct": between(s >> 2, 8, 22),
            "status": pick(s >> 4, ["On Track", "At Risk", "Blocked"]),
        })
    controls = []
    for i, ctrl in enumerate(_controls_for_framework(framework, 5)):
        s = seed("fwdc", framework, sk, ctrl["control_id"])
        controls.append({
            "control_id": ctrl["control_id"],
            "control_name": control_name_for(ctrl["control_id"]),
            "compliance_pct": between(s, 55, 100),
            "evidence_count": between(s >> 2, 1, 8),
        })
    evidence = []
    for i in range(5):
        s = seed("fwde", framework, sk, i)
        evidence.append({
            "evidence_id": f"EV-AISDLC-{between(s, 1, 999):04d}",
            "artifact_type": pick(s >> 2, ["Scan Report", "Policy Document", "Test Result", "Approval Record"]),
            "status": pick(s >> 4, ["Approved", "In Review", "Pending"]),
            "application": pick(s >> 6, apps)["application_name"],
        })
    return {
        "title": f"{framework} — {stage_label} Readiness ({pct}%)",
        "framework": framework,
        "stage": stage_label,
        "stage_key": sk,
        "readiness_pct": pct,
        "applications": applications,
        "controls": controls,
        "evidence": evidence,
    }


_BUILDERS: dict[str, Any] = {
    "run-scheduler": build_run_scheduler,
    "framework-readiness": build_framework_readiness,
    "action-queue": build_action_queue,
    "scheduler-log": build_scheduler_log,
    "ai-recommendations": build_ai_recommendations,
}


def build_control_tower_tab(tab_id: str) -> dict[str, Any] | None:
    fn = _BUILDERS.get(tab_id)
    if not fn:
        return None
    return {"tab_id": tab_id, "data": fn()}


def build_control_tower_shell() -> dict[str, Any]:
    return {
        "title": "AI SDLC Control Tower",
        "subtitle": "ECS scheduler orchestration and readiness monitoring",
        "tabs": [
            {"id": "run-scheduler", "label": "Run Scheduler"},
            {"id": "framework-readiness", "label": "Framework Readiness"},
            {"id": "action-queue", "label": "Action Queue"},
            {"id": "scheduler-log", "label": "Scheduler Log"},
            {"id": "ai-recommendations", "label": "AI Recommendations"},
        ],
    }
