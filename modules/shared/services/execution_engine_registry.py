"""Execution engine registry — distinct terminology and dashboard metadata for ECS engines."""

from __future__ import annotations

from typing import Any

_EVIDENCE_SOURCES = [
    "ServiceNow", "GitHub", "Jenkins", "SonarQube", "CrowdStrike",
    "Splunk", "SailPoint", "Prisma", "Qualys",
]

_ONBOARDING_PHASES = [
    "Requirements", "Design", "Development", "Testing", "Go Live",
]

_ONBOARDING_ARTIFACTS = [
    "CTD", "CGLD", "Requirements artifacts", "Design artifacts", "Test artifacts",
]

_ASSESSMENT_CHECKS = [
    "Requirements Phase", "Design Phase", "Development Phase", "Testing Phase", "Go Live Phase",
    "Controlled Documents", "Evidence Readiness", "Approval Readiness", "Governance Readiness",
]


def _avg_runtime(history: list[dict], fallback: int = 40) -> int:
    durations = [h.get("duration_sec", 0) for h in history if h.get("duration_sec")]
    return round(sum(durations) / len(durations)) if durations else fallback


def evidence_collection_engine(*, paused: bool = False, dashboard: dict | None = None) -> dict[str, Any]:
    """Engine 1 — Operations evidence collection."""
    dash = dashboard or {}
    status = dash.get("status", {})
    history = dash.get("execution_history", [])
    last = history[0] if history else {}
    successful = sum(1 for h in history if h.get("status") == "Success")
    failed = sum(1 for h in history if h.get("status") not in ("Success", "Completed"))
    return {
        "engine_key": "evidence_collection",
        "title": "Evidence Collection Engine",
        "run_button_label": "Run Evidence Collection",
        "description": "Collects and refreshes evidence from integrated enterprise platforms.",
        "location": "Operations",
        "sources": list(_EVIDENCE_SOURCES),
        "responsibilities": [
            "Collect evidence from external systems",
            "Refresh inventories, findings, controls, and CMDB data",
            "Refresh IAM, vulnerability, and security tool integrations",
            "Refresh compliance evidence",
        ],
        "run_status": "Paused" if paused else status.get("last_pull_status", "Ready"),
        "last_run": status.get("last_pull_at") or last.get("timestamp", "2026-05-29 02:00:12 IST"),
        "records_processed": status.get("records_last_pull") or last.get("records", 1248),
        "execution_duration_sec": last.get("duration_sec") or status.get("avg_duration_sec", 38),
        "dashboard": {
            "last_run_timestamp": status.get("last_pull_at") or last.get("timestamp", "2026-05-29 02:00:12 IST"),
            "successful_runs": status.get("pulls_completed", successful or 847),
            "failed_runs": failed or 12,
            "avg_runtime_sec": _avg_runtime(history, status.get("avg_duration_sec", 38)),
            "records_processed": status.get("records_last_pull", 1248),
            "applications_affected": 42,
            "frameworks_affected": 8,
        },
    }


def application_onboarding_engine() -> dict[str, Any]:
    """Engine 2 — AI SDLC application onboarding."""
    return {
        "engine_key": "application_onboarding",
        "title": "Application Onboarding Engine",
        "run_button_label": "Onboard Application",
        "description": (
            "Registers a new application and generates governance structures, phases, "
            "documents, and evidence mappings."
        ),
        "location": "AI SDLC Governance → Application Onboarding",
        "phases": list(_ONBOARDING_PHASES),
        "artifacts": list(_ONBOARDING_ARTIFACTS),
        "responsibilities": [
            "Create application profile and register application",
            "Assign owner, criticality, and framework mappings",
            "Create SDLC phases and controlled documents",
            "Create evidence placeholders and readiness records",
        ],
        "run_status": "Ready",
        "last_run": "2026-05-28 09:15:00 IST",
        "records_processed": 4872,
        "execution_duration_sec": 124,
        "dashboard": {
            "last_run_timestamp": "2026-05-28 09:15:00 IST",
            "successful_runs": 156,
            "failed_runs": 3,
            "avg_runtime_sec": 118,
            "records_processed": 4872,
            "applications_affected": 142,
            "frameworks_affected": 9,
        },
    }


def governance_assessment_engine() -> dict[str, Any]:
    """Engine 3 — AI SDLC Control Tower governance assessment."""
    return {
        "engine_key": "governance_assessment",
        "title": "Governance Assessment Engine",
        "run_button_label": "Run Governance Assessment",
        "description": (
            "Evaluates AI SDLC governance posture, readiness, compliance, and control effectiveness."
        ),
        "location": "AI SDLC Governance → AI SDLC Control Tower",
        "checks": list(_ASSESSMENT_CHECKS),
        "responsibilities": [
            "Evaluate SDLC maturity and calculate readiness",
            "Check phase completion and validate controlled documents",
            "Validate evidence completeness and detect missing controls or approvals",
            "Calculate governance posture across onboarded applications",
        ],
        "run_status": "Ready",
        "last_run": "2026-05-29 13:45:37 IST",
        "records_processed": 18341,
        "execution_duration_sec": 36,
        "dashboard": {
            "last_run_timestamp": "2026-05-29 13:45:37 IST",
            "successful_runs": 312,
            "failed_runs": 4,
            "avg_runtime_sec": 36,
            "records_processed": 18341,
            "applications_affected": 142,
            "frameworks_affected": 8,
        },
    }
