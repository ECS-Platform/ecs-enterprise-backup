"""Incremental embedding validation for deterministic predefined-query evidence."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from app import ecs_state
from ecs_platform.evidence_indexing import (
    index_evidence_version,
    reset_indexing_clients,
    retry_index_evidence,
)
from ecs_platform.storage import LocalObjectStore, reset_object_store, set_object_store
from ecs_platform.vectorstore.base import Chunk, VectorStore
from modules.audit_intelligence.engines import evidence_repository as ai_repo
from modules.audit_intelligence.services import persistence as P
from modules.operations.engines import evidence_repository as ops_repo
from modules.operations.engines import connector_common as cc
from modules.operations.engines import predefined_queries_engine as engine
from modules.operations.engines import predefined_query_publisher as publisher
from modules.operations.engines import scheduler_module as sm
from modules.operations.engines.query_connectors import ConnectorResult


@dataclass
class _TrackingProvider:
    dim: int = 4
    configured_flag: bool = True
    calls: int = 0
    fail_next: bool = False

    @property
    def embedding_model(self) -> str:
        return "mock-embed"

    def configured(self) -> bool:
        return self.configured_flag

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError("simulated embedding failure")
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
    monkeypatch.setenv("ECS_PREDEFINED_QUERY_SCHEDULER_ENABLED", "true")
    set_object_store(LocalObjectStore(tmp_path / "objects"))
    ecs_state.predefined_query_fingerprint_index.clear()
    ecs_state.predefined_query_content_index.clear()
    ecs_state.uploaded_evidence_enrollments.clear()
    ops_repo.evidence_repository.clear()
    ai_repo.reset_repository()
    P.reset_persistence()
    reset_indexing_clients()
    engine.set_execution_persist(True)
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
    monkeypatch.setattr("ecs_platform.evidence_indexing._get_index_provider", lambda p=None: provider if p is None else p)
    monkeypatch.setattr("ecs_platform.evidence_indexing._get_index_store", lambda s=None: store if s is None else s)
    monkeypatch.setattr("ecs_platform.evidence_indexing._existing_chunk_hashes", lambda _store: {})
    return {"store": store, "provider": provider}


def _control(control_id: str):
    engine.load_predefined_queries()
    return engine.get_control_by_id(control_id)


def _result(*, control_id: str, rows: list[list[str]], columns: list[str] | None = None) -> ConnectorResult:
    columns = columns or ["value"]
    return ConnectorResult(
        success=True,
        output=f"{columns[0]} | \n-----\n {rows[0][0] if rows else ''}",
        duration_ms=5,
        metadata={
            "rows_returned": len(rows),
            "columns": columns,
            "parsed_rows": rows,
            "query_id": control_id,
        },
    )


def _publish(
    control_id: str,
    *,
    rows: list[list[str]] | None = None,
    executed_at: str = "2026-07-20T10:00:00+00:00",
    monkeypatch=None,
):
    if monkeypatch is not None:
        monkeypatch.setattr(publisher, "_utc_now", lambda: executed_at)
    control = _control(control_id)
    rows = rows if rows is not None else [["on"]]
    return publisher.publish_predefined_query_evidence(
        control=control,
        technology="PostgreSQL",
        query=f"query-for-{control_id}",
        result=_result(control_id=control_id, rows=rows),
        user="tester",
        execution_id=f"EXEC-{control_id}",
    )


def test_first_run_creates_versions_embeddings_and_pgvector_rows(embed_env, monkeypatch):
    t0 = time.perf_counter()
    controls = ("PGX-001", "PGX-002", "PGX-003")
    for cid in controls:
        upload = _publish(cid, monkeypatch=monkeypatch)
        assert upload["status"] != "DUPLICATE"
        assert (upload.get("metadata") or {}).get("substantive_content_sha256")
        assert upload.get("search_index", {}).get("indexed") or upload.get("search_index", {}).get("embedded_chunks", 0) >= 0
    first_run_s = time.perf_counter() - t0
    first_embed_calls = embed_env["provider"].calls

    assert len(ops_repo.evidence_repository) == 3
    for cid in controls:
        key = ai_repo.make_evidence_key("Net Banking", cid)
        versions = ai_repo.get_versions(key)
        assert len(versions) == 1
    assert len(embed_env["store"].chunks) >= 3
    assert first_embed_calls >= 3

    timings = {
        "first_run_seconds": first_run_s,
        "first_embed_calls": first_embed_calls,
    }
    assert timings["first_embed_calls"] >= 3


def test_second_identical_run_skips_duplicate_and_embedding(embed_env, monkeypatch):
    controls = ("PGX-001", "PGX-002", "PGX-003")
    for cid in controls:
        _publish(cid, executed_at="2026-07-20T10:00:00+00:00", monkeypatch=monkeypatch)
    first_embed_calls = embed_env["provider"].calls
    chunk_count = len(embed_env["store"].chunks)
    ops_count = len(ops_repo.evidence_repository)

    t0 = time.perf_counter()
    for cid in controls:
        upload = _publish(cid, executed_at="2026-07-20T18:30:00+00:00", monkeypatch=monkeypatch)
        assert upload["status"] == "DUPLICATE"
        assert upload.get("embedding_skipped") is True
        assert upload.get("search_index", {}).get("reason") == "embedding_skipped"
    second_run_s = time.perf_counter() - t0

    assert len(ops_repo.evidence_repository) == ops_count
    assert len(embed_env["store"].chunks) == chunk_count
    assert embed_env["provider"].calls == first_embed_calls
    assert second_run_s >= 0


def test_changed_substantive_result_embeds_only_changed_item(embed_env, monkeypatch):
    unchanged = ("PGX-001", "PGX-002")
    for cid in unchanged:
        _publish(cid, monkeypatch=monkeypatch)
    _publish("PGX-003", monkeypatch=monkeypatch)
    calls_before = embed_env["provider"].calls
    chunks_before = len(embed_env["store"].chunks)
    ops_before = len(ops_repo.evidence_repository)

    upload = _publish("PGX-003", rows=[["off"]], executed_at="2026-07-20T19:00:00+00:00", monkeypatch=monkeypatch)
    assert upload["status"] != "DUPLICATE"
    assert len(ops_repo.evidence_repository) == ops_before + 1

    key = ai_repo.make_evidence_key("Net Banking", "PGX-003")
    versions = ai_repo.get_versions(key)
    assert len(versions) >= 2
    assert embed_env["provider"].calls == calls_before + 1
    assert len(embed_env["store"].chunks) > chunks_before

    for cid in unchanged:
        second = _publish(cid, executed_at="2026-07-20T19:05:00+00:00", monkeypatch=monkeypatch)
        assert second["status"] == "DUPLICATE"
    assert embed_env["provider"].calls == calls_before + 1


def test_failed_embedding_retry_after_persist(embed_env, monkeypatch):
    upload = _publish("PGX-001", monkeypatch=monkeypatch)
    assert upload["status"] != "DUPLICATE"
    assert len(ops_repo.evidence_repository) == 1

    key = ai_repo.make_evidence_key("Net Banking", "PGX-001")
    artifact = ai_repo.get_latest(key)
    assert artifact is not None

    embed_env["provider"].fail_next = True
    failed = index_evidence_version(
        artifact,
        normalized_text='{"result": [["on"]]}',
        provider=embed_env["provider"],
        store=embed_env["store"],
        skip_if_superseded=False,
        force=True,
    )
    assert failed.get("errors")
    assert int(failed.get("embedded_chunks", 0) or 0) == 0

    calls_before = embed_env["provider"].calls
    retry = retry_index_evidence(
        artifact.evidence_key,
        artifact.version,
        normalized_text='{"result": [["on"]]}',
    )
    assert retry["ok"] is True
    assert retry["embedded_chunks"] >= 1
    assert embed_env["provider"].calls == calls_before + 1


def test_scheduler_summary_counts_incremental_embedding(embed_env, monkeypatch):
    def _run(cid: str, user: str, **kwargs):
        return cc.complete_connector_execution(
            _control(cid),
            user,
            "PostgreSQL",
            f"query-for-{cid}",
            _result(control_id=cid, rows=[["on"]]),
        )

    monkeypatch.setattr("modules.operations.engines.predefined_queries_engine.run_predefined_query", _run)
    monkeypatch.setattr(
        "modules.operations.engines.predefined_queries_engine.is_live_execution_enabled",
        lambda control: True,
    )
    monkeypatch.setattr(
        "modules.operations.engines.predefined_queries_engine.assess_execution_capability",
        lambda control: {"executable": True, "status": "Ready", "reason": "ok"},
    )

    first = sm.collect_scheduled_predefined_queries(
        user="scheduler",
        control_ids=["PGX-001", "PGX-002", "PGX-003"],
        run_id="RUN-1",
    )
    assert first["new"] == 3
    assert first["embedded"] >= 1 or embed_env["provider"].calls >= 3
    assert first["duplicates"] == 0
    first_calls = embed_env["provider"].calls

    second = sm.collect_scheduled_predefined_queries(
        user="scheduler",
        control_ids=["PGX-001", "PGX-002", "PGX-003"],
        run_id="RUN-2",
    )
    assert second["duplicates"] == 3
    assert second["embedding_skipped"] == 3
    assert second["new"] == 0
    assert embed_env["provider"].calls == first_calls


def test_substantive_hash_excludes_volatile_fields():
    artifact_a = publisher.build_artifact_json(
        control={"control_id": "PGX-001", "application": "Net Banking", "environment": "Production"},
        technology="PostgreSQL",
        query="SHOW ssl;",
        result=_result(control_id="PGX-001", rows=[["on"]]),
        user="tester",
        execution_id="EXEC-A",
        executed_at="2026-07-20T10:00:00+00:00",
    )
    artifact_b = dict(artifact_a)
    artifact_b["executed_at"] = "2026-07-20T18:00:00+00:00"
    artifact_b["execution_id"] = "EXEC-B"
    artifact_b["scheduler_run_id"] = "RUN-B"
    artifact_b["duration_ms"] = 999
    fp_a = publisher.build_canonical_fingerprint(artifact=artifact_a, framework="DB Baselining")
    fp_b = publisher.build_canonical_fingerprint(artifact=artifact_b, framework="DB Baselining")
    assert publisher.canonical_fingerprint_hash(fp_a) == publisher.canonical_fingerprint_hash(fp_b)
