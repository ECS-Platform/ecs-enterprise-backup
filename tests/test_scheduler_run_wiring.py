"""Focused tests for wiring Scheduler -> Run Evidence Collection to the REAL
asset_scheduler / connector_executor path (POST /mvp/scheduler/run).

Proves, offline and deterministically:
  * the selected applications/frameworks reach the backend service;
  * a dry run invokes the planner (asset_scheduler) and performs NO execution;
  * enabled execution (ECS_CONNECTOR_EXECUTION_ENABLED) invokes the connector
    executor via execute_plan;
  * disabled execution makes no connector call / no network;
  * the notice/result shown comes from the ACTUAL run (not fabricated counters).

No live network: asset planning is stubbed to a fixed plan and execute_plan is
spied, so nothing reaches a real connector.
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from modules.audit_intelligence.services import asset_scheduler as sch
from modules.operations.engines import scheduler_module as sm

client = TestClient(app, follow_redirects=False)


def _plan(jobs):
    p = sch.EvidencePlan()
    p.jobs = list(jobs)
    return p


def _job(asset_id="local-sharepoint-evidence", connector="sharepoint_graph",
         application="Evidence Library (mock)", scope_value="sharepoint_graph",
         frameworks=()):
    return sch.PlannedJob(
        asset_id=asset_id, technology="SharePoint", route=sch.ROUTE_CONNECTOR,
        connector=connector, scope_kind="connector", scope_value=scope_value,
        application=application, control_ids=(), frameworks=tuple(frameworks),
    )


def _linux_job(frameworks=("PCI DSS", "ITPP")):
    return sch.PlannedJob(
        asset_id="local-linux-host", technology="Linux", route=sch.ROUTE_BASELINE,
        connector="", scope_kind="technology", scope_value="Linux",
        application="ECS Demo", control_ids=("OS-001",),
        frameworks=tuple(frameworks),
    )


@pytest.fixture(autouse=True)
def _stub_planner(monkeypatch):
    """Stub asset loading + planning so tests never depend on the asset YAML and
    never hit a connector. execute_plan is left to per-test spying."""
    monkeypatch.setattr(sch, "load_assets", lambda *a, **k: [])
    monkeypatch.setattr(
        sch, "plan_evidence",
        lambda *a, **k: _plan([
            _job(),
            _job(asset_id="local-jira-project", connector="jira",
                 application="Change Management (mock)", scope_value="jira"),
            _linux_job(),
        ]),
    )
    # Default: execution flag OFF unless a test overrides it.
    monkeypatch.delenv("ECS_CONNECTOR_EXECUTION_ENABLED", raising=False)
    yield


# --------------------------------------------------------------------------- #
# Service layer
# --------------------------------------------------------------------------- #
def test_dry_run_invokes_planner_and_does_not_execute(monkeypatch):
    calls = {"plan": 0, "execute": 0}

    def _plan_spy(*a, **k):
        calls["plan"] += 1
        return _plan([_job()])

    def _exec_spy(*a, **k):
        calls["execute"] += 1
        return []

    monkeypatch.setattr(sch, "plan_evidence", _plan_spy)
    monkeypatch.setattr(sch, "execute_plan", _exec_spy)

    result = sm.run_scheduler_collection(user="tester")
    assert result["mode"] == "dry-run"
    assert calls["plan"] == 1           # planner ran
    assert calls["execute"] == 0        # nothing executed (no network)
    assert result["planned_jobs"] >= 1


def test_disabled_execution_makes_no_connector_call(monkeypatch):
    executed = {"n": 0}
    monkeypatch.setattr(sch, "execute_plan",
                        lambda *a, **k: executed.__setitem__("n", executed["n"] + 1) or [])
    # Flag off (fixture cleared it) and no transport -> dry run, no execution.
    result = sm.run_scheduler_collection(user="tester")
    assert result["mode"] == "dry-run"
    assert executed["n"] == 0
    assert result["ingested"] == 0


def test_enabled_execution_invokes_connector_executor(monkeypatch):
    monkeypatch.setenv("ECS_CONNECTOR_EXECUTION_ENABLED", "true")
    seen = {"run_connectors": None, "n": 0}

    def _exec_spy(plan, *, run_connectors=True, connector_transport=None, requested_by=""):
        seen["run_connectors"] = run_connectors
        seen["n"] += 1
        return [{"kind": "connector", "connector": "sharepoint_graph", "ingested": 2},
                {"kind": "connector", "connector": "jira", "ingested": 1}]

    monkeypatch.setattr(sch, "execute_plan", _exec_spy)
    result = sm.run_scheduler_collection(user="tester")
    assert result["mode"] == "live"
    assert seen["n"] == 1 and seen["run_connectors"] is True
    assert result["ingested"] == 3          # comes from the actual run receipts
    assert result["results"]


def test_injected_transport_forces_live_without_flag(monkeypatch):
    """A test/explicit caller can inject a transport -> live path even with flag off."""
    passed = {"transport": "MISSING"}

    def _exec_spy(plan, *, run_connectors=True, connector_transport=None, requested_by=""):
        passed["transport"] = connector_transport
        return [{"kind": "connector", "ingested": 0}]

    monkeypatch.setattr(sch, "execute_plan", _exec_spy)
    sentinel = lambda *a, **k: {}  # noqa: E731 - stand-in transport
    result = sm.run_scheduler_collection(user="t", connector_transport=sentinel)
    assert result["mode"] == "live"
    assert passed["transport"] is sentinel


def test_selection_filters_planned_jobs(monkeypatch):
    monkeypatch.setattr(sch, "execute_plan", lambda *a, **k: [])
    # Net Banking maps to the SharePoint evidence-library asset only.
    res = sm.run_scheduler_collection(user="t", applications=["Net Banking"])
    assert res["planned_jobs"] == 1
    assert res["connectors"] == ["sharepoint_graph"]
    # Payments maps to the Jira change-management asset only.
    res_pay = sm.run_scheduler_collection(user="t", applications=["Payments"])
    assert res_pay["planned_jobs"] == 1
    assert res_pay["connectors"] == ["jira"]
    # Framework filter is exact on planned job frameworks.
    res_fw = sm.run_scheduler_collection(user="t", frameworks=["ITPP"])
    assert res_fw["planned_jobs"] == 1
    assert res_fw["connectors"] == []
    # An empty selection means "all".
    res_all = sm.run_scheduler_collection(user="t")
    assert res_all["planned_jobs"] == 3


def test_selection_net_banking_mobile_banking_payments(monkeypatch):
    monkeypatch.setattr(sch, "execute_plan", lambda *a, **k: [])
    monkeypatch.setattr(
        sch, "plan_evidence",
        lambda *a, **k: _plan([
            _job(),
            _job(asset_id="local-sonarqube", connector="sonarqube",
                 application="ECS AppSec Demo", scope_value="sonarqube",
                 frameworks=("AppSec",)),
            _job(asset_id="local-jira-project", connector="jira",
                 application="Change Management (mock)", scope_value="jira"),
        ]),
    )
    assert sm.run_scheduler_collection(applications=["Net Banking"])["planned_jobs"] == 1
    assert sm.run_scheduler_collection(applications=["Mobile Banking"])["planned_jobs"] == 1
    assert sm.run_scheduler_collection(applications=["Payments"])["planned_jobs"] == 1


def test_selection_exact_framework_and_normalized_spelling(monkeypatch):
    monkeypatch.setattr(sch, "execute_plan", lambda *a, **k: [])
    monkeypatch.setattr(
        sch, "plan_evidence",
        lambda *a, **k: _plan([
            _linux_job(frameworks=("PCI DSS",)),
            _linux_job(frameworks=("CSITE",)),
        ]),
    )
    assert sm.run_scheduler_collection(frameworks=["PCI DSS"])["planned_jobs"] == 1
    assert sm.run_scheduler_collection(frameworks=["C-SITE"])["planned_jobs"] == 1


def test_selection_unknown_application_yields_zero_jobs(monkeypatch):
    monkeypatch.setattr(sch, "execute_plan", lambda *a, **k: [])
    res = sm.run_scheduler_collection(user="t", applications=["Not A Real Application"])
    assert res["planned_jobs"] == 0
    assert res["connectors"] == []


def test_selection_unknown_framework_yields_zero_jobs(monkeypatch):
    monkeypatch.setattr(sch, "execute_plan", lambda *a, **k: [])
    res = sm.run_scheduler_collection(user="t", frameworks=["Not A Real Framework"])
    assert res["planned_jobs"] == 0


def test_normalize_helpers_are_deterministic():
    assert sm.normalize_scheduler_applications([]) is None
    assert sm.normalize_scheduler_applications(["Net Banking"]) == frozenset({
        "evidence library (mock)", "local-sharepoint-evidence",
    })
    assert sm.normalize_scheduler_applications(["Unknown App"]) == frozenset()
    assert sm.normalize_scheduler_frameworks(["C-SITE"]) == frozenset({"csite"})


# --------------------------------------------------------------------------- #
# Route layer
# --------------------------------------------------------------------------- #
def test_route_forwards_selected_apps_and_frameworks(monkeypatch):
    captured = {}

    def _svc_spy(*, user, applications, frameworks, **k):
        captured["user"] = user
        captured["applications"] = applications
        captured["frameworks"] = frameworks
        return {"ok": True, "mode": "dry-run", "planned_jobs": 2,
                "connectors": ["sharepoint_graph"], "ingested": 0, "results": []}

    monkeypatch.setattr("modules.shared.routes.routes_mvp.run_scheduler_collection", _svc_spy)
    r = client.post(
        "/mvp/scheduler/run",
        data={"role": "owner", "user": "U",
              "applications": ["Net Banking", "Payments"], "frameworks": ["PCI DSS"]},
    )
    assert r.status_code == 303
    assert captured["applications"] == ["Net Banking", "Payments"]
    assert captured["frameworks"] == ["PCI DSS"]


def test_route_notice_reflects_actual_run(monkeypatch):
    # Dry-run notice mentions planner outcome + the enable flag (no fabricated counts).
    monkeypatch.setattr(
        "modules.shared.routes.routes_mvp.run_scheduler_collection",
        lambda **k: {"ok": True, "mode": "dry-run", "planned_jobs": 4,
                     "connectors": ["sharepoint_graph", "jira"], "ingested": 0, "results": []},
    )
    r = client.post("/mvp/scheduler/run", data={"role": "owner", "user": "U"})
    assert r.status_code == 303
    from urllib.parse import unquote
    loc = unquote(r.headers["location"])
    assert "dry run" in loc.lower()
    assert "4 job(s) planned" in loc
    assert "ECS_CONNECTOR_EXECUTION_ENABLED=true" in loc

    # Live notice reflects ingested count from the real run.
    monkeypatch.setattr(
        "modules.shared.routes.routes_mvp.run_scheduler_collection",
        lambda **k: {"ok": True, "mode": "live", "planned_jobs": 2,
                     "connectors": ["sharepoint_graph"], "ingested": 7, "results": [{"ingested": 7}]},
    )
    r2 = client.post("/mvp/scheduler/run", data={"role": "owner", "user": "U"})
    assert r2.status_code == 303
    assert "7" in r2.headers["location"]
    assert "live" in r2.headers["location"].lower()
