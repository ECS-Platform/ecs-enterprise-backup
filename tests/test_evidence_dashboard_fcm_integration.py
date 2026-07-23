"""Evidence Dashboard × Framework Control Master integration tests."""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")

from fastapi.testclient import TestClient

from app import ecs_state
from app.main import app
from modules.executive_overview.engines.demo_seed import seed_demo_workflow_state
from modules.frameworks.services.framework_control_master_service import (
    get_framework_control_master_service,
)
from modules.shared.services.module_capabilities import get_module_capability

client = TestClient(app, raise_server_exceptions=False)


def _reset_and_seed():
    ecs_state.uploaded_evidence_enrollments.clear()
    ecs_state.approved_controls.clear()
    ecs_state.submitted_controls.clear()
    ecs_state.rejected_controls.clear()
    from modules.governance.engines import fcm_evidence_demo_seed as seed_mod

    seed_mod._seeded = False
    from modules.executive_overview.engines import demo_seed as demo_mod

    demo_mod._seeded = False
    seed_demo_workflow_state()


def test_mapping_report_assignments_exist():
    svc = get_framework_control_master_service()
    assignments = svc._repo.list_application_assignments()
    assert len(assignments) >= 8
    net = next(a for a in assignments if a["application"] == "Net Banking")
    assert "pci_dss" in net["framework_ids"]
    assert "itpp" in net["framework_ids"]


def test_owner_sees_assigned_applications_only():
    _reset_and_seed()
    svc = get_framework_control_master_service()
    apps = svc.list_assigned_applications("owner")
    assert apps == ["Mobile Banking", "Net Banking", "Payments"]
    progress = svc.build_evidence_dashboard_progress(role="owner")
    assert progress["selected_application"] in apps
    assert all(c["application"] in apps for c in progress["control_rows"])


def test_progress_chart_has_segment_buckets():
    _reset_and_seed()
    svc = get_framework_control_master_service()
    progress = svc.build_evidence_dashboard_progress(
        role="owner", application="Net Banking"
    )
    assert progress["chart_rows"]
    row = next(r for r in progress["chart_rows"] if r["framework_id"] == "pci_dss")
    segs = row["segments"]
    assert segs["closed"] >= 1 or segs["pending"] >= 1 or segs["blocked"] >= 1


def test_control_closes_when_all_requirements_accepted():
    _reset_and_seed()
    svc = get_framework_control_master_service()
    drill = svc.build_evidence_progress_drill(
        "pci_dss", "PCI-C-01", "Net Banking"
    )
    assert drill["ok"] is True
    assert drill["control_status"] == "closed"
    statuses = [r["status"] for r in drill["evidence_requirements"]]
    assert statuses.count("accepted") >= 1


def test_drill_down_path():
    _reset_and_seed()
    svc = get_framework_control_master_service()
    drill = svc.build_evidence_progress_drill(
        "itpp", "ITPP-C-03", "Net Banking"
    )
    assert drill["ok"] is True
    assert "Information Technology" in drill["drill_path"][0] or "ITPP" in drill["drill_path"][0]
    assert drill["policy"]
    assert drill["procedures"]


def test_evidence_dashboard_module_includes_fcm_progress():
    _reset_and_seed()
    view = get_module_capability("evidence_dashboard", "owner")
    assert "fcm_progress" in view
    assert view["fcm_progress"]["chart_rows"]


def test_api_fcm_progress():
    _reset_and_seed()
    resp = client.get(
        "/api/evidence-dashboard/fcm-progress?role=owner&application=Net%20Banking"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["selected_application"] == "Net Banking"


def test_evidence_dashboard_framework_progress_tab():
    _reset_and_seed()
    resp = client.get(
        "/mvp/evidence-dashboard?role=owner&user=U&tab=framework_progress&application=Net%20Banking"
    )
    assert resp.status_code == 200
    html = resp.text
    assert "Framework Progress" in html
    assert "ecsFcmStackChart" in html
    assert "PCI DSS" in html or "pci" in html.lower()


def test_hierarchy_policy_control_procedure_evidence():
    svc = get_framework_control_master_service()
    detail = svc.get_control_detail("pci_dss", "PCI-C-01")
    assert detail["ok"] is True
    assert detail["framework"]["id"] == "pci_dss"
    assert detail["linked_policies"]
    assert detail["control"]["procedures"]
    assert detail["control"]["evidence_requirements"]
    assert detail["control"]["policy_refs"]


def test_compliance_and_cio_see_all_assignment_applications():
    svc = get_framework_control_master_service()
    all_apps = sorted({a["application"] for a in svc._repo.list_application_assignments()})
    for role in ("compliance_head", "cio"):
        apps = svc.list_assigned_applications(role)
        assert apps == all_apps
        progress = svc.build_evidence_dashboard_progress(role=role, application=all_apps[0])
        assert progress["applications"] == all_apps


def test_owner_drill_rejects_out_of_scope_application():
    _reset_and_seed()
    svc = get_framework_control_master_service()
    drill = svc.build_evidence_progress_drill(
        "itpp", "ITPP-C-01", "Treasury", role="owner"
    )
    assert drill["ok"] is False
    assert "role scope" in drill["message"].lower()


def test_repository_abstraction_source_type():
    svc = get_framework_control_master_service()
    assert svc.source_type == "file"
    listed = svc.list_frameworks()
    assert listed["source_type"] == "file"
    assert len(listed["frameworks"]) == 10
