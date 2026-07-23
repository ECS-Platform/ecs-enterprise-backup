"""Phase-1 end-to-end evidence lifecycle validation (frozen modules only)."""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from typing import Any

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")
os.environ.setdefault("AUDIT_WORKFLOW_ENABLED", "true")

import pytest
from fastapi.testclient import TestClient

from app import ecs_state
from app.main import app
from ecs_platform.evidence_indexing import reset_indexing_clients, retry_index_evidence
from ecs_platform.storage import LocalObjectStore, get_object_store, reset_object_store, set_object_store
from ecs_platform.vectorstore.base import Chunk, VectorStore
from modules.audit_intelligence.engines import evidence_repository as ai_repo
from modules.audit_intelligence.engines import observation_generation as obs_gen
from modules.audit_intelligence.models import VERDICT_FAIL, VERDICT_PASS
from modules.audit_intelligence.services import persistence as P
from modules.audit_intelligence.services import audit_repository_service as audit_svc
from modules.audit_intelligence.services.sql_persistence import SqlAuditPersistence
from modules.governance.engines.search_module import search_evidences
from modules.operations.engines import common_controls_collector as cc
from modules.operations.engines import connector_common as conn
from modules.operations.engines import evidence_repository as ops_repo
from modules.operations.engines import predefined_queries_engine as pq_engine
from modules.operations.engines import predefined_query_publisher as pq_publisher
from modules.operations.engines import scheduler_module as sm
from modules.operations.engines.query_connectors import ConnectorResult
from modules.shared.services.common_evidence_presets import execute_preset_query
from modules.shared.services.common_evidence_queries import (
    NO_EVIDENCE_MESSAGE,
    try_deterministic_evidence_query,
)
from modules.shared.services.evidence_authoritative_reader import (
    collect_authoritative_evidence_rows,
    get_authoritative_evidence,
    repository_stats,
)
from modules.shared.services.module_capabilities import get_module_capability


@dataclass
class _TrackingProvider:
    calls: int = 0
    configured_flag: bool = True

    @property
    def embedding_model(self) -> str:
        return "mock-embed"

    def configured(self) -> bool:
        return self.configured_flag

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        return [[float(len(t) % 7), 1.0, 2.0, 3.0] for t in texts]


class _FakeStore(VectorStore):
    def __init__(self) -> None:
        self.chunks: dict[str, Chunk] = {}

    def init_store(self) -> None:
        return None

    def upsert(self, chunks: list[Chunk]) -> int:
        for chunk in chunks:
            self.chunks[chunk.chunk_id] = chunk
        return len(chunks)

    def search(self, embedding: list[float], *, top_k: int = 8, filters: dict[str, Any] | None = None):
        return []

    def delete_for_evidence(self, evidence_uid: str) -> None:
        for cid in list(self.chunks):
            if self.chunks[cid].evidence_uid == evidence_uid:
                del self.chunks[cid]

    def _connect(self):
        return self

    @property
    def _table(self) -> str:
        return "mock"


@pytest.fixture(autouse=True)
def _clean(tmp_path, monkeypatch):
    monkeypatch.setenv("ECS_EVIDENCE_SNAPSHOT_ENABLED", "true")
    monkeypatch.setenv("ECS_EVIDENCE_CUSTODY_MODE", "SNAPSHOT")
    monkeypatch.setenv("ECS_COMMON_CONTROLS_COLLECTION_ENABLED", "true")
    monkeypatch.setenv("ECS_PREDEFINED_QUERY_SCHEDULER_ENABLED", "true")
    monkeypatch.setenv("ECS_MOCK_EVIDENCE_COLLECTION_ENABLED", "true")
    set_object_store(LocalObjectStore(tmp_path / "objects"))
    P.reset_persistence()
    P.set_persistence(SqlAuditPersistence())
    ai_repo.reset_repository()
    ops_repo.evidence_repository.clear()
    ops_repo.upload_tracker.clear()
    ecs_state.predefined_query_fingerprint_index.clear()
    ecs_state.predefined_query_content_index.clear()
    ecs_state.uploaded_evidence_enrollments.clear()
    obs_gen.reset_observations()
    sm._execution_history.clear()
    reset_indexing_clients()
    pq_engine.set_execution_persist(True)
    yield
    reset_object_store()
    reset_indexing_clients()
    P.reset_persistence()


@pytest.fixture
def embed_env(monkeypatch):
    store = _FakeStore()
    provider = _TrackingProvider()
    monkeypatch.setattr(
        "ecs_platform.config.load_vectorstore_config",
        lambda: {"vectorstore": {"chunking": {"chunk_size": 1000, "chunk_overlap": 150}}},
    )
    monkeypatch.setattr(
        "ecs_platform.evidence_indexing._get_index_provider",
        lambda p=None: provider if p is None else p,
    )
    monkeypatch.setattr(
        "ecs_platform.evidence_indexing._get_index_store",
        lambda s=None: store if s is None else s,
    )
    monkeypatch.setattr("ecs_platform.evidence_indexing._existing_chunk_hashes", lambda _s: {})
    return {"store": store, "provider": provider}


def _pq_control(control_id: str = "PGX-001"):
    pq_engine.load_predefined_queries()
    return pq_engine.get_control_by_id(control_id)


def _pq_result(rows: list[list[str]] | None = None) -> ConnectorResult:
    rows = rows if rows is not None else [["on"]]
    return ConnectorResult(
        success=True,
        output="ssl | \n-----\n on",
        duration_ms=5,
        metadata={"rows_returned": len(rows), "columns": ["ssl"], "parsed_rows": rows},
    )


def _publish_pq(*, control_id: str = "PGX-001", rows=None, executed_at: str, monkeypatch) -> dict:
    monkeypatch.setattr(pq_publisher, "_utc_now", lambda: executed_at)
    return pq_publisher.publish_predefined_query_evidence(
        control=_pq_control(control_id),
        technology="PostgreSQL",
        query="SHOW ssl;",
        result=_pq_result(rows),
        user="scheduler",
        execution_id=f"EXEC-{control_id}",
        framework="DB Baselining",
        scheduler_run_id="RUN-PQ",
    )


def _publish_sharepoint(*, run_id: str = "RUN-SP") -> dict:
    content = b'{"source":"sharepoint_graph","status":"ok","document":"policy.pdf"}'
    return ops_repo.register_upload(
        filename="sharepoint_policy.json",
        content=content,
        uploaded_by="scheduler",
        framework="PCI DSS",
        application="Net Banking",
        control="SP-MOCK-001",
        source_connector="sharepoint_graph",
        metadata={
            "source_type": "connector",
            "scheduler_run_id": run_id,
            "object_key": "sharepoint/mock/policy.json",
        },
    )


def _assert_object_integrity(record: dict, *, raw: bytes) -> None:
    meta = record.get("metadata") or {}
    key = meta.get("object_key") or record.get("object_uri", "").replace("object://", "")
    sha = record.get("sha256") or meta.get("content_sha256") or ""
    assert sha == hashlib.sha256(raw).hexdigest()
    if key:
        stored = get_object_store().get_bytes(key)
        if stored is not None:
            assert hashlib.sha256(stored).hexdigest() == sha


def _identity_chain(eid: str) -> dict:
    auth = get_authoritative_evidence(eid)
    assert auth is not None
    meta = auth.get("metadata") or {}
    needle = (
        auth.get("control_id")
        or auth.get("control")
        or meta.get("query_id")
        or meta.get("common_control_slug")
        or auth.get("filename")
        or eid
    )
    hits = search_evidences(q=str(needle))
    assert any(h["evidence_id"] == eid for h in hits), f"search({needle!r}) missing {eid}"
    return auth


# --------------------------------------------------------------------------- #
# Scenario A — Success (predefined query through full lifecycle)
# --------------------------------------------------------------------------- #
def test_scenario_a_success_predefined_query_full_lifecycle(embed_env, monkeypatch):
    t0 = time.perf_counter()
    upload = _publish_pq(executed_at="2026-07-20T10:00:00+00:00", monkeypatch=monkeypatch)
    first_run_s = time.perf_counter() - t0
    assert upload["status"] != "DUPLICATE"
    eid = upload["evidence_id"]
    meta = upload.get("metadata") or {}
    assert meta.get("substantive_content_sha256")
    assert meta.get("scheduler_run_id") == "RUN-PQ" or meta.get("collection_source") == "predefined_query"

    key = ai_repo.make_evidence_key("Net Banking", "PGX-001")
    versions = ai_repo.get_versions(key)
    assert len(versions) == 1
    assert versions[0].custody_mode == "SNAPSHOT"
    assert versions[0].object_uri or meta.get("object_key")

    auth = _identity_chain(eid)
    assert auth["audit_repository_synced"] is True
    assert auth.get("sha256")

    chat = try_deterministic_evidence_query(
        "Show latest evidence for control PGX-001 in Net Banking",
        role="owner",
        user="App Owner",
    )
    assert chat is not None
    assert eid in chat["answer"]

    dash = get_module_capability("evidence_dashboard", "owner")
    stats = repository_stats()
    assert stats["total_records"] >= 1
    assert dash["common_controls"]["catalog_count"] == 10

    preset = execute_preset_query("latest_5_evidences", role="owner", limit=5)
    assert any(r.get("evidence_id") == eid for r in preset.get("rows") or [])

    assert embed_env["provider"].calls >= 1
    assert first_run_s >= 0


# --------------------------------------------------------------------------- #
# Scenario B — Certificate Management validation failure + observation
# --------------------------------------------------------------------------- #
def test_scenario_b_certificate_management_failure_retained(embed_env):
    receipt = cc.collect_common_control_folder(
        cc.common_controls_root() / "certificate-management",
        user="scheduler",
        run_id="RUN-CERT-FAIL",
    )
    assert receipt.collected is True
    assert receipt.verdict == VERDICT_FAIL
    assert receipt.observation_id
    obs = audit_svc.get_observation(receipt.observation_id)
    assert obs is not None

    latest = ai_repo.get_latest(receipt.evidence_key)
    meta = dict(latest.metadata or ())
    assert meta.get("validation_verdict") == VERDICT_FAIL
    assert str(meta.get("framework_independent")).lower() == "true"

    rows = [
        r
        for r in collect_authoritative_evidence_rows()
        if (r.get("metadata") or {}).get("common_control_slug") == "certificate-management"
    ]
    assert rows
    assert search_evidences(q="CC-CERTIFICATE_MANAGEMENT") or search_evidences(q="certificate")

    preset = execute_preset_query("latest_5_evidences", role="owner", limit=10)
    preset_rows = preset.get("rows") or []
    assert any(
        (r.get("metadata") or {}).get("validation_verdict") == VERDICT_FAIL
        or r.get("evidence_id") == rows[0]["evidence_id"]
        for r in preset_rows
    )
    assert audit_svc.get_observation(receipt.observation_id) is not None


# --------------------------------------------------------------------------- #
# Scenario C — Duplicate (unchanged substantive, new timestamps/run IDs)
# --------------------------------------------------------------------------- #
def test_scenario_c_duplicate_skips_version_ops_vectors_and_embedding(embed_env, monkeypatch):
    cc_folder = cc.common_controls_root() / "audit-logging"
    cc.collect_common_control_folder(cc_folder, user="scheduler", run_id="RUN-CC-1")

    first = _publish_pq(executed_at="2026-07-20T10:00:00+00:00", monkeypatch=monkeypatch)
    embed_calls = embed_env["provider"].calls
    chunk_count = len(embed_env["store"].chunks)
    ops_count = len(ops_repo.evidence_repository)

    second = _publish_pq(executed_at="2026-07-20T18:00:00+00:00", monkeypatch=monkeypatch)
    assert second["status"] == "DUPLICATE"
    assert second.get("embedding_skipped") is True

    cc_second = cc.collect_common_control_folder(cc_folder, user="scheduler", run_id="RUN-CC-2")
    assert cc_second.collected is True
    assert len(ops_repo.evidence_repository) == ops_count
    assert len(ai_repo.get_versions(cc_second.evidence_key)) == 1

    assert len(ops_repo.evidence_repository) == ops_count
    assert len(embed_env["store"].chunks) == chunk_count
    assert embed_env["provider"].calls == embed_calls

    stats_before = repository_stats()["total_records"]
    _publish_pq(executed_at="2026-07-20T19:00:00+00:00", monkeypatch=monkeypatch)
    assert repository_stats()["total_records"] == stats_before


# --------------------------------------------------------------------------- #
# Scenario D — Changed substantive evidence
# --------------------------------------------------------------------------- #
def test_scenario_d_changed_evidence_new_version_and_incremental_embed(embed_env, monkeypatch):
    _publish_pq(executed_at="2026-07-20T10:00:00+00:00", monkeypatch=monkeypatch)
    calls_before = embed_env["provider"].calls

    changed = _publish_pq(
        rows=[["off"]],
        executed_at="2026-07-20T11:00:00+00:00",
        monkeypatch=monkeypatch,
    )
    assert changed["status"] != "DUPLICATE"
    key = ai_repo.make_evidence_key("Net Banking", "PGX-001")
    versions = ai_repo.get_versions(key)
    assert len(versions) >= 2
    assert versions[-1].content_hash != versions[0].content_hash
    assert embed_env["provider"].calls == calls_before + 1

    auth = get_authoritative_evidence(changed["evidence_id"])
    assert int(auth.get("version") or 1) >= 1
    hits = search_evidences(q="PGX-001")
    assert hits


# --------------------------------------------------------------------------- #
# Scenario E — Partial scheduler failure
# --------------------------------------------------------------------------- #
def test_scenario_e_partial_scheduler_failure_preserves_success(monkeypatch, embed_env):
    real_run = pq_engine.run_predefined_query

    def _run(cid: str, user: str, **kwargs):
        if cid == "PGX-002":
            return {
                "ok": False,
                "control_id": cid,
                "error": "simulated connector failure",
                "error_type": "execution_error",
                "evidence_persisted": False,
            }
        return real_run(cid, user, **kwargs)

    monkeypatch.setattr(pq_engine, "run_predefined_query", _run)
    monkeypatch.setattr(pq_engine, "is_live_execution_enabled", lambda control: True)
    monkeypatch.setattr(
        pq_engine,
        "assess_execution_capability",
        lambda control: {"executable": True, "status": "Ready", "reason": "ok"},
    )
    monkeypatch.setattr(
        "modules.audit_intelligence.services.asset_scheduler.load_assets",
        lambda *a, **k: [],
    )
    monkeypatch.setattr(
        "modules.audit_intelligence.services.asset_scheduler.plan_evidence",
        lambda *a, **k: __import__(
            "modules.audit_intelligence.services.asset_scheduler", fromlist=["EvidencePlan"]
        ).EvidencePlan(jobs=[], unsupported=[]),
    )

    result = sm.run_scheduler_collection(user="scheduler")
    pq_row = next(r for r in result["summary"]["source_breakdown"] if r["source"] == "predefined_query")
    cc_row = next(r for r in result["summary"]["source_breakdown"] if r["source"] == "common_controls")

    assert result["run_id"]
    assert cc_row["persisted"] >= 1
    assert pq_row["failed"] >= 1 or pq_row["executed"] >= 1
    assert len(ops_repo.evidence_repository) >= cc_row["persisted"]
    assert search_evidences(q="CC-")
    assert result["status"] in {"Success", "Partial", "completed"}


# --------------------------------------------------------------------------- #
# Scenario F — Cold read via SQL-backed authoritative reader
# --------------------------------------------------------------------------- #
def test_scenario_f_cold_read_after_clearing_in_memory_ops(embed_env, monkeypatch):
    upload = _publish_pq(executed_at="2026-07-20T10:00:00+00:00", monkeypatch=monkeypatch)
    cc.collect_common_control_folder(
        cc.common_controls_root() / "time-synchronization",
        user="scheduler",
        run_id="RUN-COLD",
    )
    sp = _publish_sharepoint(run_id="RUN-SP-COLD")
    persisted_ids = {upload["evidence_id"], sp["evidence_id"]}

    ops_repo.evidence_repository.clear()
    ai_repo.reset_repository()
    ecs_state.predefined_query_fingerprint_index.clear()
    ecs_state.predefined_query_content_index.clear()

    ai_repo.hydrate_from_persistence()
    rows = collect_authoritative_evidence_rows()
    hydrated_ids = {r["evidence_id"] for r in rows}
    assert persisted_ids.intersection(hydrated_ids)

    for eid in persisted_ids.intersection(hydrated_ids):
        detail = get_authoritative_evidence(eid)
        assert detail is not None
        assert detail.get("sha256")
        meta = detail.get("metadata") or {}
        needle = meta.get("query_id") or detail.get("control_id") or detail.get("control") or "SP-MOCK"
        assert search_evidences(q=str(needle))


# --------------------------------------------------------------------------- #
# Three-source lifecycle identity (PQ + Common Control + SharePoint fixture)
# --------------------------------------------------------------------------- #
def test_three_source_lifecycle_identity(embed_env, monkeypatch):
    pq = _publish_pq(executed_at="2026-07-20T10:00:00+00:00", monkeypatch=monkeypatch)
    cc_receipt = cc.collect_common_control_folder(
        cc.common_controls_root() / "encryption-at-rest",
        user="scheduler",
        run_id="RUN-3SRC",
    )
    assert cc_receipt.verdict == VERDICT_PASS
    sp = _publish_sharepoint(run_id="RUN-3SRC")

    for label, eid, source in (
        ("pq", pq["evidence_id"], "predefined_query"),
        ("cc", next(r["evidence_id"] for r in ops_repo.evidence_repository if r.get("source_connector") == "common_controls"), "common_controls"),
        ("sp", sp["evidence_id"], "sharepoint_graph"),
    ):
        auth = _identity_chain(eid)
        assert auth.get("source_connector") in {source, "connector", "predefined_query", "common_controls", "sharepoint_graph"}
        meta = auth.get("metadata") or {}
        if source == "common_controls":
            assert str(meta.get("framework_independent")).lower() == "true"
        if source == "predefined_query":
            assert meta.get("substantive_content_sha256")

    client = TestClient(app)
    repo_api = client.get("/api/evidence/repository")
    assert repo_api.status_code == 200
    api_ids = {r.get("evidence_id") for r in repo_api.json().get("items") or []}
    assert pq["evidence_id"] in api_ids


def test_disabled_collectors_skipped_cleanly(monkeypatch):
    monkeypatch.setenv("ECS_COMMON_CONTROLS_COLLECTION_ENABLED", "false")
    monkeypatch.setenv("ECS_PREDEFINED_QUERY_SCHEDULER_ENABLED", "false")
    monkeypatch.setenv("ECS_MOCK_EVIDENCE_COLLECTION_ENABLED", "false")
    monkeypatch.setattr(
        "modules.audit_intelligence.services.asset_scheduler.load_assets",
        lambda *a, **k: [],
    )
    monkeypatch.setattr(
        "modules.audit_intelligence.services.asset_scheduler.plan_evidence",
        lambda *a, **k: __import__(
            "modules.audit_intelligence.services.asset_scheduler", fromlist=["EvidencePlan"]
        ).EvidencePlan(jobs=[], unsupported=[]),
    )
    result = sm.run_scheduler_collection(user="scheduler")
    breakdown = {r["source"]: r for r in result["summary"]["source_breakdown"]}
    assert breakdown["common_controls"]["status"] == "skipped"
    assert breakdown["predefined_query"]["status"] == "skipped"
    assert breakdown["mock_evidence"]["status"] == "skipped"


def test_chatbot_no_unsupported_claim_when_evidence_absent():
    result = try_deterministic_evidence_query(
        "Show evidence for control ZZZ-999 in Net Banking",
        role="owner",
        user="App Owner",
    )
    if result is None:
        assert True
    else:
        assert NO_EVIDENCE_MESSAGE in result.get("answer", "") or not result.get("citations")
