"""Left-panel navigation counters — 100% derived from live workflow state."""

from __future__ import annotations

from app import ecs_state
from app.framework_catalog import FRAMEWORK_CATALOG, get_all_evidence_records
from app.module_capabilities import module_counter_rows
from app.workflow_module import (
    build_auditor_review_queue,
    build_leadership_queue,
    build_owner_work_queue,
    framework_pending_count,
)

MODULE_LABELS = {
    "scheduler": "scheduler / aging evidence pulls",
    "upload": "bulk upload actions",
    "evidence_health": "expired or due-for-refresh evidences",
    "search": "evidences pending audit review",
    "completeness": "incomplete or missing controls",
    "reuse": "reuse-mapped open controls",
    "lifecycle": "open lifecycle transitions",
    "comparison": "elevated-risk applications",
    "integrations": "integration sync gaps",
    "enterprise": "escalated or high-risk items",
    "pan_india": "regional open observations",
    "reports": "reports pending generation",
    "audit_prep": "audit preparation gaps",
    "trends": "open trend-tracked observations",
    "onboarding": "applications onboarding in progress",
    "risk_register": "open high/critical enterprise risks",
    "exceptions_td": "TD expired or high-risk exceptions",
    "cmdb": "non-compliant or unmonitored assets",
    "regulatory_mapping": "regulatory coverage gaps",
    "executive_heatmaps": "executive escalation items",
    "integrations_hub": "integration sync failures",
    "correlation": "open cross-tool correlation chains",
    "governance_analytics": "governance trend alerts",
}

MODULE_KEYS = list(MODULE_LABELS.keys())


def _tooltip(count: int, label: str) -> str:
    if count <= 0:
        return f"No pending workflow actions — {label}"
    noun = "action" if count == 1 else "actions"
    return f"{count} pending workflow {noun} — {label}"


def build_nav_counters(role: str = "owner") -> dict:
    owner_q = build_owner_work_queue(limit=500)
    auditor_q = build_auditor_review_queue(limit=500)
    leadership_q = build_leadership_queue(role, limit=500) if role in (
        "cio", "vertical_head", "compliance_head", "functional_head"
    ) else []

    frameworks: dict[str, int] = {}
    framework_tooltips: dict[str, str] = {}
    for fw in FRAMEWORK_CATALOG:
        cnt = framework_pending_count(fw, role)
        frameworks[fw] = cnt
        if role == "auditor":
            label = f"auditor reviews in {fw}"
        elif role in ("cio", "vertical_head", "compliance_head", "functional_head"):
            label = f"executive items in {fw}"
        else:
            label = f"App Owner actions in {fw}"
        framework_tooltips[fw] = _tooltip(cnt, label)

    modules: dict[str, int] = {}
    module_tooltips: dict[str, str] = {}
    for mod in MODULE_KEYS:
        cnt = module_counter_rows(mod, role)
        modules[mod] = cnt
        module_tooltips[mod] = _tooltip(cnt, MODULE_LABELS[mod])

    all_ev = get_all_evidence_records()
    sla_breach = sum(1 for i in owner_q + auditor_q if i.get("sla") == "Breached")

    global_counts = {
        "owner_pending": len(owner_q),
        "auditor_pending": len(auditor_q),
        "rejected": len(ecs_state.rejected_controls),
        "escalated": len(ecs_state.escalated_controls),
        "expired": sum(1 for r in all_ev if r.get("evidence_status") == "Expired"),
        "sla_breach": sla_breach,
        "clarifications": len(ecs_state.clarification_controls),
        "leadership": len(leadership_q),
    }

    return {
        "frameworks": frameworks,
        "framework_tooltips": framework_tooltips,
        "modules": modules,
        "module_tooltips": module_tooltips,
        "global": global_counts,
        "global_tooltips": {
            "owner_pending": _tooltip(global_counts["owner_pending"], "App Owner queue"),
            "auditor_pending": _tooltip(global_counts["auditor_pending"], "Auditor review queue"),
            "leadership": _tooltip(global_counts["leadership"], "executive / leadership queue"),
        },
    }


def counter_for_framework(name: str, counters: dict | None = None) -> int:
    c = counters or build_nav_counters()
    return c["frameworks"].get(name, 0)


def counter_for_module(key: str, counters: dict | None = None) -> int:
    c = counters or build_nav_counters()
    return c["modules"].get(key, 0)
