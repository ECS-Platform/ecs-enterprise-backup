"""Tests for the Evidence Collection Orchestrator (Milestone 2).

Fully offline: a mock executor supplies engine-style result dicts, so no live
Docker/DB/connector is touched. Covers scoping, statuses, retry, cancel, audit
trail, scheduler hooks, and non-executable handling.
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from modules.audit_intelligence.engines import evidence_orchestrator as orch
from modules.audit_intelligence.engines import technology_control_mapping as mapping
from modules.audit_intelligence.models import (
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_CONFIG_REQUIRED,
    STATUS_CONNECTOR_MISSING,
    STATUS_FAILED,
    STATUS_PARTIAL,
    STATUS_QUEUED,
)


@pytest.fixture(autouse=True)
def _clean():
    mapping.reset_cache()
    orch.reset_runs()
    yield
    orch.reset_runs()
    mapping.reset_cache()


def ok_executor(control_id, user):
    return {"ok": True, "message": "done", "rows_returned": 1, "duration_ms": 5,
            "output": "enabled", "evidence_id": f"EV-{control_id}", "evidence_filename": "e.txt"}


def fail_executor(control_id, user):
    return {"ok": False, "error": "boom", "error_type": "error"}


def connector_missing_executor(control_id, user):
    return {"ok": False, "error": "driver missing", "error_type": "connector_unavailable"}


# --------------------------------------------------------------------------- #
# Scope resolution
# --------------------------------------------------------------------------- #
def test_resolve_scope_technology():
    ids = orch.resolve_scope("technology", "NGINX")
    assert ids and all(isinstance(i, str) for i in ids)
    assert "NGX-001" in ids


def test_resolve_scope_framework():
    ids = orch.resolve_scope("framework", "PCI DSS")
    assert ids


def test_resolve_scope_control_and_all():
    assert orch.resolve_scope("control", "NGX-001") == ["NGX-001"]
    assert len(orch.resolve_scope("all")) == len(mapping.all_controls())


def test_resolve_scope_asset_by_dict():
    ids = orch.resolve_scope("asset", {"technology": "NGINX"})
    assert "NGX-001" in ids


# --------------------------------------------------------------------------- #
# Create + execute
# --------------------------------------------------------------------------- #
def test_create_run_queues_records():
    run = orch.create_run(scope_kind="technology", scope_value="NGINX", requested_by="t")
    assert run.status == STATUS_QUEUED
    assert run.records and all(r.status == STATUS_QUEUED for r in run.records)
    assert orch.get_run(run.run_id) is run


def test_execute_run_all_ok_marks_completed():
    run = orch.create_run(scope_kind="control", scope_value="NGX-001")
    # Force executable so the executor is actually called.
    for r in run.records:
        r.executable = True
    out = orch.execute_run(run.run_id, executor=ok_executor)
    assert out.status == STATUS_COMPLETED
    assert all(r.status == STATUS_COMPLETED for r in out.records)
    assert out.records[0].evidence_id == "EV-NGX-001"
    assert out.started_at and out.finished_at


def test_execute_run_all_fail_marks_failed():
    run = orch.create_run(scope_kind="control", scope_value="NGX-001")
    for r in run.records:
        r.executable = True
    out = orch.execute_run(run.run_id, executor=fail_executor)
    assert out.status == STATUS_FAILED
    assert out.records[0].status == STATUS_FAILED


def test_execute_mixed_marks_partial():
    run = orch.create_run(scope_kind="technology", scope_value="NGINX")
    for i, r in enumerate(run.records):
        r.executable = True

    def mixed(control_id, user):
        return ok_executor(control_id, user) if control_id == "NGX-001" else fail_executor(control_id, user)

    out = orch.execute_run(run.run_id, executor=mixed)
    assert out.status == STATUS_PARTIAL
    assert any(r.status == STATUS_COMPLETED for r in out.records)
    assert any(r.status == STATUS_FAILED for r in out.records)


def test_connector_unavailable_maps_to_connector_missing():
    run = orch.create_run(scope_kind="control", scope_value="NGX-001")
    for r in run.records:
        r.executable = True
    out = orch.execute_run(run.run_id, executor=connector_missing_executor)
    assert out.records[0].status == STATUS_CONNECTOR_MISSING


def test_non_executable_marked_config_required_without_calling_executor():
    run = orch.create_run(scope_kind="control", scope_value="NGX-001")
    for r in run.records:
        r.executable = False

    def boom(control_id, user):
        raise AssertionError("executor must not be called for non-executable controls")

    out = orch.execute_run(run.run_id, executor=boom)
    assert out.records[0].status == STATUS_CONFIG_REQUIRED


def test_executor_exception_is_isolated():
    run = orch.create_run(scope_kind="control", scope_value="NGX-001")
    for r in run.records:
        r.executable = True

    def raiser(control_id, user):
        raise RuntimeError("kaboom")

    out = orch.execute_run(run.run_id, executor=raiser)
    assert out.records[0].status == STATUS_FAILED
    assert out.records[0].error_type == "executor_exception"


# --------------------------------------------------------------------------- #
# Retry / cancel
# --------------------------------------------------------------------------- #
def test_retry_failed_reexecutes_only_failures():
    run = orch.create_run(scope_kind="technology", scope_value="NGINX")
    for r in run.records:
        r.executable = True
    orch.execute_run(run.run_id, executor=fail_executor)
    assert run.status == STATUS_FAILED
    # Now retry with an OK executor -> should recover.
    out = orch.retry_failed(run.run_id, executor=ok_executor)
    assert out.status == STATUS_COMPLETED
    assert all(r.attempts >= 2 for r in out.records)


def test_retry_noop_when_nothing_failed():
    run = orch.create_run(scope_kind="control", scope_value="NGX-001")
    for r in run.records:
        r.executable = True
    orch.execute_run(run.run_id, executor=ok_executor)
    out = orch.retry_failed(run.run_id, executor=fail_executor)
    assert out.status == STATUS_COMPLETED  # unchanged; nothing retried


def test_cancel_run():
    run = orch.create_run(scope_kind="technology", scope_value="NGINX")
    out = orch.cancel_run(run.run_id, user="admin")
    assert out.status == STATUS_CANCELLED
    assert all(r.status == STATUS_CANCELLED for r in out.records)


# --------------------------------------------------------------------------- #
# Audit trail + scheduler hooks
# --------------------------------------------------------------------------- #
def test_audit_trail_records_events():
    run = orch.create_run(scope_kind="control", scope_value="NGX-001")
    for r in run.records:
        r.executable = True
    orch.execute_run(run.run_id, executor=ok_executor)
    events = [e["event"] for e in run.audit_trail]
    assert "run_created" in events
    assert "run_started" in events
    assert "run_finished" in events


def test_scheduler_enqueue_does_not_execute():
    run = orch.enqueue_scheduled_run(scope_kind="technology", scope_value="NGINX", schedule_id="S1")
    assert run.status == STATUS_QUEUED
    assert run in orch.due_runs()
    assert any(e["event"] == "scheduled" for e in run.audit_trail)


def test_due_runs_fifo():
    r1 = orch.enqueue_scheduled_run(scope_kind="control", scope_value="NGX-001")
    r2 = orch.enqueue_scheduled_run(scope_kind="control", scope_value="NGX-002")
    due = orch.due_runs()
    assert due.index(r1) < due.index(r2)


def test_run_to_dict_serializable():
    run = orch.create_run(scope_kind="control", scope_value="NGX-001")
    d = run.to_dict()
    assert d["run_id"] == run.run_id
    assert isinstance(d["records"], list)
    assert "summary" in d
