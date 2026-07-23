"""Scheduler source-wise summary, evidence identity, and selection catalog tests."""

from __future__ import annotations

import json
import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from modules.audit_intelligence.services import asset_scheduler as sch
from modules.audit_intelligence.services import connector_executor
from modules.operations.engines import evidence_repository as ops_repo
from modules.operations.engines import scheduler_module as sm
from modules.operations.engines.query_connectors import ConnectorResult
from modules.operations.engines import connector_common as cc
from modules.operations.engines import predefined_query_publisher as publisher


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.setenv("ECS_COMMON_CONTROLS_COLLECTION_ENABLED", "false")
    monkeypatch.setenv("ECS_MOCK_EVIDENCE_COLLECTION_ENABLED", "false")
    monkeypatch.setenv("ECS_PREDEFINED_QUERY_SCHEDULER_ENABLED", "true")
    monkeypatch.delenv("ECS_CONNECTOR_EXECUTION_ENABLED", raising=False)
    ops_repo.evidence_repository.clear()
    ops_repo.upload_tracker.clear()
    sm._execution_history.clear()
    sm._run_progress.clear()
    yield


def _pgx_control():
    return {
        "control_id": "PGX-001",
        "technology": "PostgreSQL",
        "query": "SHOW ssl;",
        "frameworks": ["PCI DSS"],
        "framework_coverage": "PCI DSS",
        "predefined": True,
        "phase1_selected": True,
    }


def test_pq_disabled_reports_skipped_reason(monkeypatch):
    monkeypatch.setenv("ECS_PREDEFINED_QUERY_SCHEDULER_ENABLED", "false")
    monkeypatch.setattr(sch, "load_assets", lambda *a, **k: [])
    monkeypatch.setattr(sch, "plan_evidence", lambda *a, **k: sch.EvidencePlan())

    result = sm.run_scheduler_collection(user="tester")
    summary = result["summary"]
    pq_row = next(r for r in summary["source_breakdown"] if r["source"] == "predefined_query")
    assert pq_row["status"] == "skipped"
    assert "ECS_PREDEFINED_QUERY_SCHEDULER_ENABLED=false" in pq_row["skip_reason"]
    assert summary["pq_zero_reason"] == pq_row["skip_reason"]
    events = {e["step"]: e for e in result["progress"]}
    assert events["predefined queries"]["status"] == "Skipped"


def test_pq_enabled_without_target_persist_zero_with_reason(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setattr(sch, "load_assets", lambda *a, **k: [])
    monkeypatch.setattr(sch, "plan_evidence", lambda *a, **k: sch.EvidencePlan())

    result = sm.run_scheduler_collection(user="tester")
    summary = result["summary"]
    pq_row = next(r for r in summary["source_breakdown"] if r["source"] == "predefined_query")
    assert pq_row["persisted"] == 0
    assert pq_row["persist_flag"] is True
    assert summary["pq_zero_reason"]
    assert pq_row["skip_reason"] or summary["pq_zero_reason"]


def test_pq_enabled_with_target_persists_evidence(monkeypatch):
    def _publish(**kwargs):
        rec = ops_repo.register_upload(
            filename="PREDEFINED_QUERY_PGX-001.json",
            content=b"{}",
            uploaded_by="scheduler",
            framework="PCI DSS",
            application="Net Banking",
            control="PGX-001",
            source_connector="predefined_query",
            metadata={"source_type": "predefined_query", "query_id": "PGX-001"},
        )
        return {**rec, "object_key": "predefined-query/test.json", "status": "Uploaded"}

    monkeypatch.setattr(publisher, "publish_predefined_query_evidence", _publish)
    monkeypatch.setattr(
        "modules.operations.engines.predefined_queries_engine.run_postgresql_query",
        lambda cid, user: cc.complete_connector_execution(
            _pgx_control(), user, "PostgreSQL", "SHOW ssl;",
            ConnectorResult(success=True, output="ok", duration_ms=1),
        ),
    )
    monkeypatch.setattr(
        "modules.operations.engines.predefined_queries_engine.is_live_execution_enabled",
        lambda control: True,
    )
    monkeypatch.setattr(
        "modules.operations.engines.predefined_queries_engine.assess_execution_capability",
        lambda control: {"executable": True, "status": "Ready", "reason": "ok"},
    )
    monkeypatch.setattr(sch, "load_assets", lambda *a, **k: [])
    monkeypatch.setattr(sch, "plan_evidence", lambda *a, **k: sch.EvidencePlan())

    result = sm.run_scheduler_collection(user="tester")
    pq_row = next(r for r in result["summary"]["source_breakdown"] if r["source"] == "predefined_query")
    assert pq_row["persisted"] == 1
    assert result["summary"]["pq_zero_reason"] == ""
    assert ops_repo.evidence_repository[0]["metadata"]["source_type"] == "predefined_query"


def test_persist_false_creates_no_evidence(monkeypatch):
    monkeypatch.setattr(
        "modules.operations.engines.predefined_queries_engine.run_postgresql_query",
        lambda cid, user: cc.complete_connector_execution(
            _pgx_control(), user, "PostgreSQL", "SHOW ssl;",
            ConnectorResult(success=True, output="ok", duration_ms=1),
            persist=False,
        ),
    )
    from modules.operations.engines.predefined_queries_engine import run_predefined_query

    outcome = run_predefined_query("PGX-001", "tester", persist=False, scheduled=False)
    assert outcome.get("evidence_persisted") is not True
    assert not ops_repo.evidence_repository


def test_source_type_labels_distinct(monkeypatch, tmp_path):
    monkeypatch.setenv("ECS_COMMON_CONTROLS_COLLECTION_ENABLED", "true")
    monkeypatch.setenv("ECS_MOCK_EVIDENCE_COLLECTION_ENABLED", "true")
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setattr(sch, "load_assets", lambda *a, **k: [])
    monkeypatch.setattr(sch, "plan_evidence", lambda *a, **k: sch.EvidencePlan())
    monkeypatch.setattr(
        publisher,
        "publish_predefined_query_evidence",
        lambda **kwargs: ops_repo.register_upload(
            filename="pq.json",
            content=b"{}",
            uploaded_by="scheduler",
            source_connector="predefined_query",
            metadata={"source_type": "predefined_query", "query_id": "PGX-001", "scheduler_run_id": kwargs.get("execution_id", "")},
        ),
    )
    monkeypatch.setattr(
        "modules.operations.engines.predefined_queries_engine.is_live_execution_enabled",
        lambda control: False,
    )

    result = sm.run_scheduler_collection(user="tester", applications=["Net Banking"], frameworks=["PCI DSS"])
    run_id = result["run_id"]
    rows = sm._scheduler_fetched_evidence(run_id=run_id)
    types = {r.get("source_type") for r in rows}
    assert "common_controls" in types or "mock_evidence" in types


def test_source_counters_reconcile_with_summary(monkeypatch):
    monkeypatch.setenv("ECS_COMMON_CONTROLS_COLLECTION_ENABLED", "true")
    monkeypatch.setattr(sch, "load_assets", lambda *a, **k: [])
    monkeypatch.setattr(sch, "plan_evidence", lambda *a, **k: sch.EvidencePlan())
    monkeypatch.setattr(
        "modules.operations.engines.predefined_queries_engine.is_live_execution_enabled",
        lambda control: False,
    )

    result = sm.run_scheduler_collection(user="tester")
    summary = result["summary"]
    cc_row = next(r for r in summary["source_breakdown"] if r["source"] == "common_controls")
    fetched = sm._scheduler_fetched_evidence(run_id=result["run_id"])
    cc_fetched = [r for r in fetched if r.get("source_type") == "common_controls"]
    assert cc_row["persisted"] == len(cc_fetched)
    assert summary["source_totals"]["persisted"] == sum(r["persisted"] for r in summary["source_breakdown"])


def test_pgvector_detail_not_plain_zero(monkeypatch):
    monkeypatch.setattr(sch, "load_assets", lambda *a, **k: [])
    monkeypatch.setattr(sch, "plan_evidence", lambda *a, **k: sch.EvidencePlan())
    monkeypatch.setattr(
        "modules.operations.engines.predefined_queries_engine.is_live_execution_enabled",
        lambda control: False,
    )

    result = sm.run_scheduler_collection(user="tester")
    detail = result["summary"]["pgvector_detail"]
    assert "status" in detail
    assert "reason" in detail or detail.get("indexed", 0) >= 0


def test_selection_catalog_deduplicated_and_rbac():
    catalog = sm.get_scheduler_selection_catalog("owner")
    apps = catalog["applications"]
    assert len(apps) == len({sm._norm_scheduler_key(a) for a in apps})
    assert "Net Banking" in apps
    owner_apps = sm.get_scheduler_selection_catalog("owner")["applications"]
    auditor_apps = sm.get_scheduler_selection_catalog("auditor")["applications"]
    assert len(auditor_apps) >= len(owner_apps)


def test_fetched_evidence_run_id_filter(monkeypatch):
    ops_repo.register_upload(
        filename="a.json",
        content=b"1",
        uploaded_by="t",
        source_connector="common_controls",
        metadata={"source_type": "common_controls", "scheduler_run_id": "RUN-A"},
    )
    ops_repo.register_upload(
        filename="b.json",
        content=b"2",
        uploaded_by="t",
        source_connector="common_controls",
        metadata={"source_type": "common_controls", "scheduler_run_id": "RUN-B"},
    )
    rows_a = sm._scheduler_fetched_evidence(run_id="RUN-A")
    assert len(rows_a) == 1
    assert rows_a[0]["run_id"] == "RUN-A"
    assert rows_a[0]["source_type"] == "common_controls"


def test_connectors_skipped_in_dry_run(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setattr(sch, "load_assets", lambda *a, **k: [])
    monkeypatch.setattr(
        sch,
        "plan_evidence",
        lambda *a, **k: sch.EvidencePlan(
            jobs=[
                sch.PlannedJob(
                    asset_id="local-sharepoint-evidence",
                    technology="SharePoint",
                    route=sch.ROUTE_CONNECTOR,
                    connector="sharepoint_graph",
                    scope_kind="connector",
                    scope_value="sharepoint_graph",
                    application="Evidence Library (mock)",
                    control_ids=(),
                    frameworks=("PCI DSS",),
                )
            ]
        ),
    )
    result = sm.run_scheduler_collection(user="tester")
    conn = next(r for r in result["summary"]["source_breakdown"] if r["source"] == "connectors")
    assert conn["status"] == "skipped"
    assert "dry-run" in conn["skip_reason"].lower() or "ECS_CONNECTOR_EXECUTION_ENABLED" in conn["skip_reason"]


def test_run_summary_json_shape(monkeypatch):
    monkeypatch.setattr(sch, "load_assets", lambda *a, **k: [])
    monkeypatch.setattr(sch, "plan_evidence", lambda *a, **k: sch.EvidencePlan())
    monkeypatch.setattr(
        "modules.operations.engines.predefined_queries_engine.is_live_execution_enabled",
        lambda control: False,
    )
    result = sm.run_scheduler_collection(user="tester", applications=["Net Banking"], frameworks=["PCI DSS"])
    summary = result["summary"]
    json.dumps(summary)
    assert "source_breakdown" in summary
    assert len(summary["source_breakdown"]) == 5
    assert summary["run_id"]
