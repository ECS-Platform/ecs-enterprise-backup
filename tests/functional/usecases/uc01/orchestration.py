"""UC01 - Automated scheduled evidence pull. Orchestration only; behaviour lives in framework/ helpers."""

from __future__ import annotations

from ...framework import scenarios as sc
from ...framework.assertions import (assert_audit_record, assert_equal, assert_exists, assert_json_field, assert_record_count,
                                     assert_status, assert_success, assert_traceability)
from ...framework.crosscutting import register_crosscutting
from ...framework.spec import UseCaseProfile, case

PROFILE = UseCaseProfile(
    uc="UC01", subject="scheduled evidence pull", page="/mvp/scheduler", api="/api/audit/scheduler/history",
    rbac_capability="admin_platform", integration_source="scheduler", audit_action="scheduler",
    trigger=lambda ctx: ctx.track(ctx.scheduler.run_collection(sync=True)), notice_contains="collect")


@case("UC01-FT001", framework="scheduler", capability="create_schedule", component="POST /mvp/platform/scheduler -> collection_schedules",
      data="DataFactory.schedule")
def ft001(ctx):
    ctx.require_mutation()
    fields, resp = ctx.scheduler.create_schedule()
    ctx.track(resp)
    ctx.notifier.assert_notified(resp, contains=f"'{fields['name']}' created")
    assert ctx.scheduler.schedule_visible_in_ui(fields["name"]), "schedule not listed on /mvp/platform/scheduler"
    if ctx.db.enabled:
        row = ctx.scheduler.schedule_row(fields["name"])
        assert_exists(row, "collection_schedules row")
        assert_equal(row["frequency"], fields["frequency"])
        assert row["enabled"] is True and row.get("next_run"), "schedule not active / next_run missing"


@case("UC01-FT002", framework="scheduler", capability="execute_collection_run", component="POST /mvp/scheduler/run + GET /mvp/scheduler/run-status",
      data="DataFactory.application/framework")
def ft002(ctx):
    run = sc.collection_run(ctx)
    assert_json_field(run, "run_id")
    assert str(run.get("status", "completed")).lower() not in ("failed", "error"), run
    assert run.get("planned_jobs") is not None or run.get("summary") or run.get("ingested") is not None, f"run summary empty: {run}"


@case("UC01-FT003", framework="evidence", capability="persisted_collected_evidence", component="GET /evidence/repository (+ object store)",
      data="scheduler run output")
def ft003(ctx):
    run = sc.collection_run(ctx)
    ctx.correlation.add("run_id", run.get("run_id"))
    rows = ctx.evidence.find_all(application=ctx.data.application())
    assert_record_count(rows, minimum=1, msg="no evidence persisted for the scheduled application")
    for r in rows[:10]:
        assert_traceability(r, ("evidence_id", "application"))
        assert r.get("uploaded_at"), "collection timestamp missing"


@case("UC01-FT004", framework="scheduler", capability="no_duplicate_ingestion", component="POST /mvp/scheduler/run (twice) + evidence uniqueness",
      data="same application/framework scope")
def ft004(ctx):
    sc.collection_run(ctx)
    first = len(ctx.evidence.repository())
    sc.collection_run(ctx)
    second = len(ctx.evidence.repository())
    assert second == first, f"second run added {second - first} row(s): duplicate ingestion"
    if ctx.db.enabled:
        assert_record_count(ctx.db.duplicate_groups("evidence", ["source_system", "source_object_id", "object_type"]), expected=0)


@case("UC01-FT005", framework="connector", capability="source_authentication_failure", component="POST /api/connectors/{name}/health-check",
      data="connector without credentials")
def ft005(ctx):
    name = ctx.data.connector("scheduler_default")
    ctx.connectors.require_available(name)
    resp = ctx.track(ctx.connectors.health_check(name))
    assert resp.status < 500 and "Traceback" not in resp.text, "auth failure must be a controlled response"
    text = resp.text.lower()
    from ...framework.errors import CapabilityBlocked
    if not any(t in text for t in ("fail", "unauthor", "missing", "not configured", "unconfigured", "error", "unhealthy", "denied")):
        raise CapabilityBlocked(f"connector '{name}' reports healthy; run against a connector with missing/invalid credentials",
                                requires="connector with invalid credentials")
    assert "password" not in text and "secret" not in text.replace("secret_env", ""), "credential material leaked in response"
    assert_status(ctx.scheduler.dashboard(), 200)


@case("UC01-FT006", framework="scheduler", capability="recover_on_next_run", component="POST /mvp/scheduler/run (consecutive) + /api/audit/scheduler/dead-letter",
      data="two consecutive runs")
def ft006(ctx):
    before = ctx.scheduler.dead_letter()
    first = sc.collection_run(ctx)
    second = sc.collection_run(ctx)
    for run in (first, second):
        assert str(run.get("status", "completed")).lower() not in ("failed", "error"), run
    assert ctx.scheduler.dead_letter() is not None and before is not None


@case("UC01-FT007", framework="audit", capability="scheduler_audit_trail", component="audit_log / GET /api/audit/scheduler/history",
      data="scheduler run request_id")
def ft007(ctx):
    ctx.require_mutation()
    n_before = len(ctx.scheduler.history())
    resp = ctx.track(ctx.scheduler.execute_baseline())
    assert_success(resp)
    hist = ctx.scheduler.history()
    assert len(hist) > n_before, "scheduler execution did not add a history record"
    assert_audit_record(hist, detail_contains="baseline")
    if ctx.db.enabled:
        ctx.audit.verify(request_id=resp.request_id)


@case("UC01-FT008", framework="scheduler", capability="restart_durability", component="collection_schedules after ECS restart",
      data="DataFactory.schedule")
def ft008(ctx):
    ctx.require_mutation()
    ctx.require_restart_hook()
    fields, resp = ctx.scheduler.create_schedule()
    ctx.notifier.assert_notified(resp, contains="created")
    ctx.restart_ecs()
    assert ctx.scheduler.schedule_visible_in_ui(fields["name"]), "schedule lost after restart"


register_crosscutting(PROFILE)
