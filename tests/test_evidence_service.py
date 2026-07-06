"""Tests for the evidence service facade (Milestone 2) — offline, mocked executor."""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from modules.audit_intelligence.engines import evidence_orchestrator as orch
from modules.audit_intelligence.engines import technology_control_mapping as mapping
from modules.audit_intelligence.services import evidence_service as svc


@pytest.fixture(autouse=True)
def _clean():
    mapping.reset_cache()
    orch.reset_runs()
    yield
    orch.reset_runs()
    mapping.reset_cache()


def _enabled_executor(control_id, user):
    return {"ok": True, "message": "ok", "rows_returned": 1, "duration_ms": 4,
            "output": "enabled", "evidence_id": f"EV-{control_id}", "evidence_filename": "e.txt"}


def test_start_run_returns_serialized_run():
    # Use explicit control_ids and mark executable via a wrapping executor.
    run = svc.start_run(
        scope_kind="control", scope_value="NGX-001",
        control_ids=["NGX-001"], executor=_enabled_executor,
    )
    assert isinstance(run, dict)
    assert run["run_id"].startswith("RUN-")
    assert "summary" in run


def test_run_and_validate_end_to_end():
    # Build a run over NGINX, force executable, execute + validate through service.
    created = orch.create_run(scope_kind="technology", scope_value="NGINX", control_ids=["NGX-003", "NGX-005"])
    for r in created.records:
        r.executable = True

    def signalful(control_id, user):
        out = _enabled_executor(control_id, user)
        if control_id == "NGX-005":
            out["output"] = "server_tokens off; disabled"
        else:
            out["output"] = "TLSv1.2 enabled"
        return out

    orch.execute_run(created.run_id, executor=signalful)
    result = svc.validate_run(created.run_id)
    assert result["run_id"] == created.run_id
    verdicts = {r["control_id"]: r["verdict"] for r in result["results"]}
    assert verdicts["NGX-003"] == "PASS"
    assert verdicts["NGX-005"] == "FAIL"
    assert 0 <= result["compliance"]["compliance_percent"] <= 100
    # Validation folded back onto the run records.
    run = svc.get_run(created.run_id)
    assert all(rec["validation"] is not None for rec in run["records"])


def test_list_runs_and_cancel():
    r = svc.start_run(scope_kind="control", scope_value="NGX-001",
                      control_ids=["NGX-001"], executor=_enabled_executor)
    runs = svc.list_runs()
    assert any(x["run_id"] == r["run_id"] for x in runs)

    # A fresh queued run can be cancelled.
    created = orch.create_run(scope_kind="control", scope_value="NGX-002", control_ids=["NGX-002"])
    cancelled = svc.cancel_run(created.run_id, user="admin")
    assert cancelled["status"] == "Cancelled"


def test_get_missing_run_is_none():
    assert svc.get_run("RUN-nope") is None
    assert svc.validate_run("RUN-nope") is None
