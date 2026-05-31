"""AI & SDLC Governance — presentation service (mock data only)."""

from __future__ import annotations

from app.ai_sdlc_governance_mock import (
    build_ai_posture,
    build_ai_registry,
    build_sdlc_gates,
    build_sdlc_stage_detail,
    drill_posture,
    drill_registry,
    drill_sdlc,
)
from app.ai_sdlc_onboarding_engine import (
    build_application_onboarding_drill,
    build_framework_onboarding_drill,
    build_onboarding_run,
    build_onboarding_shell,
)
from app.ai_sdlc_control_tower_engine import (
    build_action_queue_detail,
    build_control_tower_shell,
    build_control_tower_tab,
    build_framework_stage_drill,
    build_readiness_cell_drill,
)
from app.ai_sdlc_workflow_store import (
    build_evidence_viewer,
    build_review_payload,
    list_activities,
    list_evidence,
    perform_status_action,
    perform_upload,
)
from app.ai_sdlc_workflow_engine import (
    build_evidence_collection,
    build_findings_remediation,
    build_landing_workbench,
    build_reports_hub,
    build_stage_worklist,
)

from app.ai_sdlc_reports_engine import build_report


def landing_view() -> dict:
    return build_landing_workbench()


def onboarding_view() -> dict:
    return build_onboarding_shell()


def onboarding_run_view() -> dict:
    return build_onboarding_run()


def onboarding_framework_drill(framework: str) -> dict:
    return build_framework_onboarding_drill(framework)


def onboarding_application_drill(application: str) -> dict:
    return build_application_onboarding_drill(application)


def stage_worklist_view(stage_key: str) -> dict:
    wl = build_stage_worklist(stage_key)
    wl["rows"] = list_activities(stage_key)
    return wl


def evidence_view() -> dict:
    ev = build_evidence_collection()
    ev["rows"] = list_evidence()
    return ev


def evidence_viewer_view(evidence_id: str) -> dict | None:
    return build_evidence_viewer(evidence_id)


def review_view(item_id: str, item_type: str = "") -> dict | None:
    return build_review_payload(item_id, item_type)


def workflow_upload(**kwargs) -> dict:
    return perform_upload(**kwargs)


def workflow_action(action: str, **kwargs) -> dict:
    if action == "upload":
        return perform_upload(kwargs.pop("item_id"), **kwargs)
    return perform_status_action(item_id=kwargs.pop("item_id"), action=action, **kwargs)


def findings_view() -> dict:
    return build_findings_remediation()


def reports_view() -> dict:
    return build_reports_hub()


def report_detail_view(report_id: str) -> dict | None:
    return build_report(report_id)


def control_tower_view() -> dict:
    return build_control_tower_shell()


def control_tower_tab_view(tab_id: str) -> dict | None:
    return build_control_tower_tab(tab_id)


def control_tower_readiness_drill(framework: str, stage: str) -> dict:
    return build_readiness_cell_drill(framework, stage)


def control_tower_framework_drill(framework: str, stage_key: str) -> dict:
    return build_framework_stage_drill(framework, stage_key)


def control_tower_work_item(activity_id: str) -> dict | None:
    return build_action_queue_detail(activity_id)


def posture_view() -> dict:
    return build_ai_posture()


def sdlc_gates_view(release_id: str = "") -> dict:
    return build_sdlc_gates(release_id)


def sdlc_stage_view(stage_key: str, release_id: str = "") -> dict:
    return build_sdlc_stage_detail(stage_key, release_id)


def registry_view() -> dict:
    return build_ai_registry()


def posture_drill(metric: str, item_id: str = "") -> dict:
    return drill_posture(metric, item_id)


def registry_drill(section: str, item_id: str = "") -> dict:
    return drill_registry(section, item_id)


def sdlc_drill(
    metric: str, release_id: str = "", stage_key: str = "", item_id: str = "",
    page: int = 1, severity: str = "", search: str = "",
) -> dict:
    return drill_sdlc(metric, release_id, stage_key, item_id, page=page, severity=severity, search=search)
