"""Tests for scheduler priority queue + dead-letter queue + parallel workers.

Additive orchestration over the existing asset scheduler. Fully offline and
deterministic (a per-job executor is injected; no live network). Verifies:
priority ordering, retry exhaustion -> DLQ, DLQ requeue, worker-count clamping,
and backward compatibility with the classic sequential execute_plan.
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
from modules.audit_intelligence.services import scheduler_execution as se

client = TestClient(app)


def _job(asset_id, tech, route=sch.ROUTE_BASELINE, connector="", controls=("DB-001",)):
    # DB-001 is a real predefined control, so an injected executor genuinely runs
    # (success -> completed; raising -> failed), giving deterministic outcomes.
    return sch.PlannedJob(asset_id=asset_id, technology=tech, route=route,
                          connector=connector, scope_kind="technology",
                          scope_value=tech, control_ids=tuple(controls))


def _ok_exec(*a, **k):
    return {"ok": True, "rows_returned": 1, "output_excerpt": "x"}


def _fail_exec(*a, **k):
    raise RuntimeError("boom")


@pytest.fixture(autouse=True)
def _clean_dlq():
    se.reset_dead_letters()
    yield
    se.reset_dead_letters()


# --------------------------------------------------------------------------- #
# Priority ordering
# --------------------------------------------------------------------------- #
def test_priority_derivation():
    assert se.job_priority(_job("a", "Oracle")) == se.PRIORITY_HIGH
    assert se.job_priority(_job("b", "Prisma Cloud", route=sch.ROUTE_CONNECTOR,
                                connector="prisma_cloud", controls=())) == se.PRIORITY_HIGH
    assert se.job_priority(_job("c", "Linux")) == se.PRIORITY_MEDIUM
    assert se.job_priority(_job("d", "Redis", controls=())) == se.PRIORITY_LOW


def test_queue_is_priority_ordered():
    plan = sch.EvidencePlan(jobs=[
        _job("low1", "Redis", controls=()),
        _job("med1", "Linux"),
        _job("high1", "Oracle"),
    ])
    q = se.build_queue(plan)
    assert [it.priority for it in q] == [se.PRIORITY_HIGH, se.PRIORITY_MEDIUM, se.PRIORITY_LOW]


# --------------------------------------------------------------------------- #
# Retry exhaustion -> DLQ
# --------------------------------------------------------------------------- #
def test_retry_exhaustion_places_job_in_dlq():
    plan = sch.EvidencePlan(jobs=[_job("db1", "Oracle")])
    res = se.execute_parallel(plan, workers=1, executor=_fail_exec, max_retries=1,
                              run_connectors=False)
    assert res["summary"]["dead_letter"] == 1
    assert res["summary"]["completed"] == 0
    dlq = se.list_dead_letters()
    assert len(dlq) == 1
    assert dlq[0]["attempts"] == 2  # 1 initial + 1 retry
    assert dlq[0]["last_error"]


def test_success_does_not_dlq():
    plan = sch.EvidencePlan(jobs=[_job("db1", "Oracle"), _job("web1", "Linux")])
    res = se.execute_parallel(plan, workers=1, executor=_ok_exec, run_connectors=False)
    assert res["summary"]["completed"] == 2
    assert res["summary"]["dead_letter"] == 0
    assert se.list_dead_letters() == []


# --------------------------------------------------------------------------- #
# DLQ requeue
# --------------------------------------------------------------------------- #
def test_dlq_requeue_success_clears_it():
    plan = sch.EvidencePlan(jobs=[_job("db1", "Oracle")])
    se.execute_parallel(plan, workers=1, executor=_fail_exec, max_retries=0,
                        run_connectors=False)
    dlq = se.list_dead_letters()
    assert len(dlq) == 1
    item_id = dlq[0]["item_id"]
    rq = se.requeue_dead_letter(item_id, executor=_ok_exec)
    assert rq["ok"] is True
    assert se.list_dead_letters() == []


def test_dlq_requeue_unknown():
    assert se.requeue_dead_letter("does-not-exist")["ok"] is False


def test_dlq_requeue_failure_returns_to_dlq():
    plan = sch.EvidencePlan(jobs=[_job("db1", "Oracle")])
    se.execute_parallel(plan, workers=1, executor=_fail_exec, max_retries=0,
                        run_connectors=False)
    item_id = se.list_dead_letters()[0]["item_id"]
    rq = se.requeue_dead_letter(item_id, executor=_fail_exec)
    assert rq["ok"] is False
    assert len(se.list_dead_letters()) == 1  # back in DLQ


# --------------------------------------------------------------------------- #
# Worker count limits
# --------------------------------------------------------------------------- #
def test_worker_count_clamped_to_max():
    plan = sch.EvidencePlan(jobs=[_job("a", "Oracle")])
    res = se.execute_parallel(plan, workers=999, executor=_ok_exec, run_connectors=False)
    assert res["summary"]["workers"] == se.MAX_WORKERS


def test_worker_count_default_is_one():
    plan = sch.EvidencePlan(jobs=[_job("a", "Oracle")])
    res = se.execute_parallel(plan, executor=_ok_exec, run_connectors=False)
    assert res["summary"]["workers"] == 1


def test_parallel_workers_execute_all_jobs():
    plan = sch.EvidencePlan(jobs=[_job(f"a{i}", "Linux") for i in range(6)])
    res = se.execute_parallel(plan, workers=4, executor=_ok_exec, run_connectors=False)
    assert res["summary"]["workers"] == 4
    assert res["summary"]["completed"] == 6


# --------------------------------------------------------------------------- #
# Backward compatibility
# --------------------------------------------------------------------------- #
def test_classic_execute_plan_unchanged():
    # The original sequential API still works and is untouched.
    plan = sch.EvidencePlan(jobs=[_job("db1", "Oracle")])
    out = sch.execute_plan(plan, executor=_ok_exec, run_connectors=False)
    assert isinstance(out, list) and len(out) == 1
    assert out[0].get("kind") == "baseline"


# --------------------------------------------------------------------------- #
# REST endpoints
# --------------------------------------------------------------------------- #
def test_api_queue():
    r = client.get("/api/audit/scheduler/queue")
    assert r.status_code == 200
    assert "queue" in r.json() and "by_priority" in r.json()


def test_api_dead_letter_list():
    r = client.get("/api/audit/scheduler/dead-letter")
    assert r.status_code == 200
    assert "dead_letter" in r.json()


def test_api_execute_parallel_rbac():
    assert client.post("/api/audit/scheduler/execute-parallel?role=auditor",
                       json={}).status_code == 403
    ok = client.post("/api/audit/scheduler/execute-parallel?role=system_admin",
                     json={"workers": 2})
    assert ok.status_code == 200
    assert "summary" in ok.json()


def test_api_dlq_requeue_unknown_404():
    r = client.post("/api/audit/scheduler/dead-letter/nope/requeue?role=system_admin",
                    json={})
    assert r.status_code == 404


def test_api_dlq_requeue_rbac():
    r = client.post("/api/audit/scheduler/dead-letter/x/requeue?role=auditor", json={})
    assert r.status_code == 403
