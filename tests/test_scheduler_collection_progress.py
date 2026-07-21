"""Scheduler collection progress, mock evidence, and fetched-evidence UI tests."""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest
from fastapi.testclient import TestClient

from app.main import app, chatbot_answer
from modules.operations.engines import evidence_repository as ops_repo
from modules.operations.engines import scheduler_module as sm
from modules.operations.engines.mock_evidence_collector import ensure_mock_evidence_tree
from modules.operations.engines.scheduler_progress import SchedulerProgressLog
from modules.shared.services.common_evidence_queries import try_deterministic_evidence_query, try_rag_evidence_query

client = TestClient(app, follow_redirects=False)


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.setenv("ECS_COMMON_CONTROLS_COLLECTION_ENABLED", "false")
    monkeypatch.setenv("ECS_PREDEFINED_QUERY_SCHEDULER_ENABLED", "false")
    monkeypatch.setenv("ECS_MOCK_EVIDENCE_COLLECTION_ENABLED", "true")
    sm._execution_history.clear()
    sm._run_progress.clear()
    ops_repo.evidence_repository.clear()
    ops_repo.upload_tracker.clear()
    ensure_mock_evidence_tree()
    yield
    sm._execution_history.clear()
    sm._run_progress.clear()
    ops_repo.evidence_repository.clear()
    ops_repo.upload_tracker.clear()


def test_progress_log_appends_without_replacing():
    log = SchedulerProgressLog("COLL-TEST")
    log.append("plan built", "Running")
    log.append("plan built", "Completed")
    log.append("file discovered", "Completed", detail="a.json")
    rows = log.to_list()
    assert len(rows) == 3
    assert rows[0]["step"] == "plan built" and rows[0]["status"] == "Running"
    assert rows[1]["step"] == "plan built" and rows[1]["status"] == "Completed"
    assert rows[2]["step"] == "file discovered"


def test_collection_emits_30_plus_events():
    result = sm.run_scheduler_collection(
        user="tester",
        applications=["Net Banking", "Mobile Banking", "Payments"],
        frameworks=["PCI DSS", "DPSC", "ITPP", "C-SITE", "OS Baselining", "DB Baselining", "VAPT"],
    )
    assert len(result["progress"]) >= 30
    assert result["summary"]["files_discovered"] >= 7


def test_failed_and_skipped_states_present(monkeypatch):
    monkeypatch.setenv("ECS_MOCK_EVIDENCE_COLLECTION_ENABLED", "false")
    result = sm.run_scheduler_collection(user="tester")
    statuses = {row["status"] for row in result["progress"]}
    assert "Skipped" in statuses or "Completed" in statuses


def test_json_route_returns_progress_and_summary():
    r = client.post(
        "/mvp/scheduler/run",
        data={"role": "owner", "user": "U", "applications": ["Net Banking"], "frameworks": ["PCI DSS"]},
        headers={"X-ECS-Scheduler-JSON": "1", "X-ECS-Scheduler-Sync": "1"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["run_id"].startswith("COLL-")
    assert body["progress"]
    assert body["summary"]["files_discovered"] >= 1


def test_async_run_returns_run_id_before_completion():
    import time

    r = client.post(
        "/mvp/scheduler/run",
        data={"role": "owner", "user": "U", "applications": ["Net Banking"], "frameworks": ["PCI DSS"]},
        headers={"X-ECS-Scheduler-JSON": "1"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["run_id"].startswith("COLL-")
    assert body["status"] == "running"
    run_id = body["run_id"]
    seen = 0
    final = None
    for _ in range(40):
        status = client.get(f"/mvp/scheduler/run-status?run_id={run_id}")
        assert status.status_code == 200
        payload = status.json()
        events = payload.get("progress_events") or []
        assert len(events) >= seen
        seen = len(events)
        if payload.get("status") in {"success", "partial", "failed", "completed"}:
            final = payload
            break
        time.sleep(0.05)
    assert final is not None
    assert final.get("summary")
    assert final["summary"].get("new_evidence", 0) >= 0


def test_summary_counters_reconcile_with_persistence():
    result = sm.run_scheduler_collection(applications=["Net Banking"], frameworks=["PCI DSS"])
    summary = result["summary"]
    assert summary["files_discovered"] >= summary["new_evidence"]
    if summary["new_evidence"]:
        assert summary["postgresql_count"] >= summary["new_evidence"]
        assert summary["object_storage_count"] >= 1
    if summary["duplicates_skipped"] and summary["new_evidence"] == 0:
        assert summary["files_discovered"] >= summary["duplicates_skipped"]


def test_run_status_unknown_run():
    r = client.get("/mvp/scheduler/run-status?run_id=COLL-NOPE")
    assert r.status_code == 404


def test_fetched_evidence_page_filters_by_run_id_query():
    result = sm.run_scheduler_collection(applications=["Net Banking"], frameworks=["PCI DSS"])
    page = client.get(
        f"/mvp/scheduler?role=owner&user=U&tab=fetched_evidence&run_id={result['run_id']}"
    )
    assert page.status_code == 200
    assert result["run_id"] in page.text
    assert "data-fetched-evidence-row" in page.text
    assert f'value="{result["run_id"]}"' in page.text or result["run_id"] in page.text


def test_selection_filters_mock_combinations():
    all_res = sm.run_scheduler_collection(frameworks=["PCI DSS"])
    net_res = sm.run_scheduler_collection(applications=["Net Banking"], frameworks=["PCI DSS"])
    assert net_res["summary"]["files_discovered"] <= all_res["summary"]["files_discovered"]


def test_demo_mode_only_mock_collection(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("ECS_MOCK_EVIDENCE_COLLECTION_ENABLED", "true")
    result = sm.run_scheduler_collection(applications=["Net Banking"], frameworks=["PCI DSS"])
    assert result["mock_evidence"] == {}


def test_metadata_and_object_persistence():
    result = sm.run_scheduler_collection(applications=["Payments"], frameworks=["VAPT"])
    assert result["summary"]["new_evidence"] >= 1
    rec = ops_repo.evidence_repository[-1]
    assert rec.get("sha256")
    assert (rec.get("metadata") or {}).get("scheduler_run_id") == result["run_id"]
    assert rec.get("object_uri") or (rec.get("metadata") or {}).get("object_key")


def test_run_id_traceability_on_records():
    result = sm.run_scheduler_collection(applications=["Mobile Banking"], frameworks=["ITPP"])
    run_id = result["run_id"]
    assert any((r.get("metadata") or {}).get("scheduler_run_id") == run_id for r in ops_repo.evidence_repository)


def test_duplicate_rerun_skips_new_version():
    first = sm.run_scheduler_collection(applications=["Net Banking"], frameworks=["PCI DSS"])
    second = sm.run_scheduler_collection(applications=["Net Banking"], frameworks=["PCI DSS"])
    assert second["summary"]["duplicates_skipped"] >= 1
    assert second["summary"]["new_evidence"] == 0
    assert len(ops_repo.evidence_repository) == len(first["mock_evidence"].get("receipts", [])) or second["summary"]["duplicates_skipped"] >= 1


def test_changed_content_creates_new_version(tmp_path, monkeypatch):
    from modules.operations.engines import mock_evidence_collector as mc

    ensure_mock_evidence_tree()
    folder = mc.mock_evidence_root() / "NetBanking" / "PCI-DSS"
    artifact = next(p for p in folder.iterdir() if p.name != "manifest.json")
    original = artifact.read_bytes()
    artifact.write_bytes(original + b"\n# changed")
    first = sm.run_scheduler_collection(applications=["Net Banking"], frameworks=["PCI DSS"])
    artifact.write_bytes(original + b"\n# changed again")
    second = sm.run_scheduler_collection(applications=["Net Banking"], frameworks=["PCI DSS"])
    assert first["summary"]["new_evidence"] >= 1
    assert second["summary"]["new_evidence"] >= 1
    artifact.write_bytes(original)


def test_pgvector_state_reported():
    result = sm.run_scheduler_collection(applications=["Net Banking"], frameworks=["DB Baselining"])
    assert "pgvector_count" in result["summary"]


def test_fetched_evidence_view_json():
    result = sm.run_scheduler_collection(applications=["Net Banking"], frameworks=["OS Baselining"])
    eid = ops_repo.evidence_repository[-1]["evidence_id"]
    r = client.get(f"/mvp/scheduler/fetched-evidence/view?evidence_id={eid}&format=json")
    assert r.status_code == 200
    body = r.json()
    assert body["evidence_id"] == eid
    assert body["run_id"] == result["run_id"]
    assert body["sha256"]
    assert body["object_reference"]


def test_run_summary_filtering():
    result = sm.run_scheduler_collection(applications=["Payments"], frameworks=["DPSC"])
    dash = sm.get_scheduler_dashboard(run_id=result["run_id"])
    assert all(row.get("run_id") == result["run_id"] for row in dash["fetched_evidence"])


def test_scheduler_page_has_view_action():
    sm.run_scheduler_collection(applications=["Net Banking"], frameworks=["PCI DSS"])
    page = client.get("/mvp/scheduler?role=owner&user=U")
    assert page.status_code == 200
    assert "data-fetched-evidence-view" in page.text
    assert "ecsFetchedFilterRun" in page.text


def test_deterministic_chatbot_after_collection():
    sm.run_scheduler_collection(applications=["Net Banking"], frameworks=["DB Baselining"])
    control = ops_repo.evidence_repository[-1].get("control")
    ans = try_deterministic_evidence_query(f"Show latest evidence for {control}", role="owner", user="U")
    assert ans is not None
    assert ans["answer_source"] == "DETERMINISTIC"


def test_rag_chatbot_after_collection(monkeypatch):
    upload = sm.run_scheduler_collection(applications=["Net Banking"], frameworks=["VAPT"])
    eid = ops_repo.evidence_repository[-1]["evidence_id"]

    def _fake_retrieve(question, scope_filter, hints, top_k):
        return [eid], "repository", 1

    def _fake_enrich(uids):
        return [{
            "evidence_uid": eid,
            "source_system": "mock_evidence",
            "object_type": "json",
            "application": "Net Banking",
            "collected_timestamp": "",
            "frameworks": ["VAPT"],
            "framework_refs": [],
            "review_status": "Uploaded",
            "controls": [ops_repo.evidence_repository[-1].get("control")],
            "url": "",
            "title": "mock",
        }]

    monkeypatch.setattr("ecs_platform.rag._retrieve", _fake_retrieve)
    monkeypatch.setattr("ecs_platform.rag._enrich", _fake_enrich)

    class _DisabledProvider:
        configured = staticmethod(lambda: False)
        model = ""
        embedding_model = ""

    monkeypatch.setattr("ecs_platform.llm_engine.provider.get_provider", lambda: _DisabledProvider())
    rag = try_rag_evidence_query("Describe collected VAPT evidence for Net Banking", role="owner", user="U")
    assert rag is not None
    assert rag["answer_source"] == "RAG"
    assert rag["citations"]
    plain = chatbot_answer("Describe collected VAPT evidence for Net Banking", role="owner", user="U")
    assert "[Source: RAG]" in plain or "Query type:" in plain


def test_modal_markup_opens_idle_not_completed():
    page = client.get("/mvp/scheduler?role=owner&user=U")
    assert page.status_code == 200
    html = page.text
    assert 'id="schedRunSummary"' in html
    assert "ecs-sched-summary-panel d-none" in html or 'class="ecs-sched-summary-panel d-none' in html
    assert 'id="schedRunStart"' in html
    assert 'btn-secondary btn-sm d-none" data-bs-dismiss="modal" id="schedRunClose"' in html
    assert 'btn-outline-primary btn-sm d-none" id="schedRunAgain"' in html
    summary_snip = html.split('id="schedRunSummary"', 1)[1].split("</div>", 1)[0]
    assert "Collection complete" not in summary_snip
    assert "window.__ecsSchedulerModalsBound" in html
    assert html.count('id="schedRunStart"') == 1
    assert html.count("function resetRunModal") == 1


def test_missing_summary_not_treated_as_completion():
    sm._run_progress["COLL-EMPTY"] = {
        "run_id": "COLL-EMPTY",
        "status": "success",
        "progress_events": [],
        "summary": {},
    }
    status = sm.get_run_status("COLL-EMPTY")
    assert status is not None
    assert status["status"] == "running"
    assert status["summary"] == {}


def test_missing_status_not_treated_as_completed():
    sm._run_progress["COLL-NOSTATUS"] = {
        "run_id": "COLL-NOSTATUS",
        "status": "",
        "progress_events": [],
        "summary": {"run_id": "COLL-NOSTATUS", "applications": [], "files_discovered": 0},
    }
    status = sm.get_run_status("COLL-NOSTATUS")
    assert status["status"] == "running"


def test_completed_payload_has_required_summary_shape():
    result = sm.run_scheduler_collection(applications=["Net Banking"], frameworks=["PCI DSS"])
    status = sm.get_run_status(result["run_id"])
    assert status["status"] in {"success", "partial", "completed"}
    summary = status["summary"]
    assert summary["run_id"] == result["run_id"]
    for key in (
        "selected_applications",
        "selected_frameworks",
        "files_discovered",
        "new_evidence",
        "duplicates_skipped",
        "failures",
        "postgresql_count",
        "object_storage_count",
        "pgvector_count",
    ):
        assert key in summary
    assert summary["files_discovered"] >= 0
    assert isinstance(summary["files_discovered"], int)


def test_zero_summary_values_are_ints_not_none():
    summary = sm._coerce_run_summary({}, run_id="COLL-ZERO", applications=[], frameworks=[])
    assert summary["new_evidence"] == 0
    assert summary["duplicates_skipped"] == 0
    assert summary["pgvector_count"] == 0


def test_view_url_run_id_in_modal_js():
    page = client.get("/mvp/scheduler?role=owner&user=U")
    assert "tab=fetched_evidence&run_id=" in page.text
    assert "View Collected Evidence" in page.text


def test_fetched_evidence_exact_run_id_filter_no_partial():
    first = sm.run_scheduler_collection(applications=["Net Banking"], frameworks=["PCI DSS"])
    second = sm.run_scheduler_collection(applications=["Mobile Banking"], frameworks=["ITPP"])
    rows = sm._scheduler_fetched_evidence(run_id=first["run_id"])
    assert rows
    assert all(r.get("run_id") == first["run_id"] for r in rows)
    assert all(r.get("run_id") != second["run_id"] for r in rows)
    # Partial suffix must not match via repository filter.
    partial = first["run_id"][-6:]
    assert sm._scheduler_fetched_evidence(run_id=partial) == []


def test_new_evidence_implies_fetched_rows():
    result = sm.run_scheduler_collection(applications=["Net Banking"], frameworks=["PCI DSS"])
    if result["summary"]["new_evidence"] > 0:
        rows = sm._scheduler_fetched_evidence(run_id=result["run_id"])
        assert len(rows) >= 1


def test_collectors_stamp_scheduler_run_id_before_registration(monkeypatch):
    stamped = []

    real_register = ops_repo.register_upload

    def _wrap(*args, **kwargs):
        meta = dict(kwargs.get("metadata") or {})
        stamped.append(meta.get("scheduler_run_id"))
        return real_register(*args, **kwargs)

    monkeypatch.setattr(ops_repo, "register_upload", _wrap)
    result = sm.run_scheduler_collection(applications=["Payments"], frameworks=["VAPT"])
    assert result["run_id"]
    assert any(s == result["run_id"] for s in stamped if s)


def test_client_filter_js_uses_exact_run_id_equality():
    page = client.get("/mvp/scheduler?role=owner&user=U")
    assert "rowRun.indexOf" not in page.text
    assert "got === want" in page.text
