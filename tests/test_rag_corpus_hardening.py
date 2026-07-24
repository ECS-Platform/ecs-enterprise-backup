"""Focused regression tests for RAG corpus retrieval, reindex reconciliation, and status metrics."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from ecs_platform import rag
from ecs_platform.vectorstore.base import Chunk, SearchHit, VectorStore


@dataclass
class _FakeProvider:
    configured_flag: bool = True
    model: str = "mock"
    embedding_model: str = "mock-embed"

    def configured(self) -> bool:
        return self.configured_flag

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0] for _ in texts]


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
        hits: list[SearchHit] = []
        for chunk in self.chunks.values():
            if filters:
                keep = True
                for key, val in filters.items():
                    meta_val = str((chunk.metadata or {}).get(key, ""))
                    if isinstance(val, (list, tuple, set)):
                        if meta_val not in {str(v) for v in val}:
                            keep = False
                            break
                    elif meta_val != str(val):
                        keep = False
                        break
                if not keep:
                    continue
            hits.append(
                SearchHit(
                    chunk_id=chunk.chunk_id,
                    evidence_uid=chunk.evidence_uid,
                    text=chunk.text,
                    metadata=chunk.metadata,
                    score=1.0,
                )
            )
        return hits[:top_k]

    def delete_for_evidence(self, evidence_uid: str) -> None:
        for cid in list(self.chunks):
            if self.chunks[cid].evidence_uid == evidence_uid:
                del self.chunks[cid]

    def delete_stale_managed_chunks(
        self,
        candidate_chunk_ids: set[str],
        *,
        managed_doc_kinds: tuple[str, ...] = ("evidence", "governance"),
    ) -> int:
        removed = 0
        for cid in list(self.chunks):
            kind = str((self.chunks[cid].metadata or {}).get("doc_kind", ""))
            if kind not in managed_doc_kinds:
                continue
            if cid not in candidate_chunk_ids:
                del self.chunks[cid]
                removed += 1
        return removed

    def indexed_evidence_stats(
        self,
        *,
        evidence_doc_kinds: tuple[str, ...] = ("evidence", "evidence_version"),
    ) -> dict[str, int]:
        kinds = set(evidence_doc_kinds)
        indexed_uids = {
            c.evidence_uid
            for c in self.chunks.values()
            if str((c.metadata or {}).get("doc_kind", "")) in kinds
        }
        indexed_chunks = sum(
            1 for c in self.chunks.values()
            if str((c.metadata or {}).get("doc_kind", "")) in kinds
        )
        return {
            "vector_count": len(self.chunks),
            "indexed_evidence": len(indexed_uids),
            "indexed_chunks": indexed_chunks,
        }

    def _connect(self):
        return self

    @property
    def _table(self) -> str:
        return "mock"


def _seed_pollution_corpus(store: _FakeStore) -> None:
    store.upsert([
        Chunk(
            chunk_id="EV-001:0",
            evidence_uid="EV-001",
            text="encryption configuration for database segment",
            embedding=[1.0, 0.0, 0.0],
            metadata={"doc_kind": "evidence", "application": "Net Banking"},
        ),
        Chunk(
            chunk_id="lineage:99:0",
            evidence_uid="lineage:99",
            text="encryption configuration relationship audit lineage governance",
            embedding=[1.0, 0.0, 0.0],
            metadata={"doc_kind": "governance", "object_type": "relationship"},
        ),
        Chunk(
            chunk_id="external:1:0",
            evidence_uid="external-tool",
            text="encryption configuration external corpus",
            embedding=[1.0, 0.0, 0.0],
            metadata={"doc_kind": "external"},
        ),
    ])


def test_evidence_retrieval_excludes_governance_pollution(monkeypatch):
    store = _FakeStore()
    _seed_pollution_corpus(store)
    provider = _FakeProvider()
    monkeypatch.setattr("ecs_platform.llm_engine.provider.get_provider", lambda: provider)
    monkeypatch.setattr("ecs_platform.vectorstore.get_vector_store", lambda: store)

    uids, mode, _ = rag._retrieve(
        "Show encryption configuration evidence",
        {},
        {},
        5,
    )
    assert mode == "vector"
    assert uids == ["EV-001"]
    assert "lineage:99" not in uids


def test_governance_question_can_retrieve_governance_chunks(monkeypatch):
    store = _FakeStore()
    _seed_pollution_corpus(store)
    provider = _FakeProvider()
    monkeypatch.setattr("ecs_platform.llm_engine.provider.get_provider", lambda: provider)
    monkeypatch.setattr("ecs_platform.vectorstore.get_vector_store", lambda: store)

    uids, mode, _ = rag._retrieve(
        "Show framework coverage and evidence reuse across frameworks",
        {},
        {},
        5,
    )
    assert mode == "vector"
    assert "lineage:99" in uids


def test_reindex_removes_stale_managed_vectors(monkeypatch):
    store = _FakeStore()
    store.upsert([
        Chunk(
            chunk_id="EV-OLD:0",
            evidence_uid="EV-OLD",
            text="stale evidence chunk",
            embedding=[1.0, 0.0, 0.0],
            metadata={"doc_kind": "evidence", "content_hash": "oldhash"},
        ),
        Chunk(
            chunk_id="gov-old:0",
            evidence_uid="gov-old",
            text="stale governance chunk",
            embedding=[1.0, 0.0, 0.0],
            metadata={"doc_kind": "governance", "content_hash": "oldgov"},
        ),
        Chunk(
            chunk_id="ext:0",
            evidence_uid="ext",
            text="external row must survive",
            embedding=[1.0, 0.0, 0.0],
            metadata={"doc_kind": "external", "content_hash": "ext"},
        ),
    ])

    repo = MagicMock()
    repo.search_evidence.return_value = [{"evidence_uid": "EV-NEW"}]
    repo.evidence_by_uid.return_value = {
        "evidence_uid": "EV-NEW",
        "title": "Fresh",
        "content": "fresh evidence body",
        "source_system": "jira",
        "object_type": "ticket",
        "application": "Net Banking",
    }
    repo.__enter__ = lambda self: repo
    repo.__exit__ = lambda *args: None

    provider = _FakeProvider()
    monkeypatch.setattr("ecs_platform.llm_engine.provider.get_provider", lambda: provider)
    monkeypatch.setattr("ecs_platform.vectorstore.get_vector_store", lambda: store)
    monkeypatch.setattr("ecs_platform.config.load_vectorstore_config", lambda: {
        "vectorstore": {"chunking": {"chunk_size": 1000, "chunk_overlap": 150}}
    })
    monkeypatch.setattr("ecs_platform.rag._governance_documents", lambda: [])
    monkeypatch.setattr("ecs_platform.rag._existing_chunk_hashes", lambda _store: {})
    monkeypatch.setattr("ecs_platform.repository.EvidenceRepository", lambda: repo)

    report = rag.reindex_evidence(incremental=False)
    assert report["ok"] is True
    assert report["stale_removed"] == 2
    assert "EV-OLD:0" not in store.chunks
    assert "gov-old:0" not in store.chunks
    assert "ext:0" in store.chunks
    assert any(c.evidence_uid == "EV-NEW" for c in store.chunks.values())


def test_reindex_skips_unchanged_chunks(monkeypatch):
    import hashlib

    store = _FakeStore()
    piece = "Same\nsame evidence body"
    content_hash = hashlib.sha256(piece.encode("utf-8")).hexdigest()[:16]
    store.upsert([
        Chunk(
            chunk_id="EV-SAME:0",
            evidence_uid="EV-SAME",
            text=piece,
            embedding=[1.0, 0.0, 0.0],
            metadata={"doc_kind": "evidence", "content_hash": content_hash},
        ),
    ])

    repo = MagicMock()
    repo.search_evidence.return_value = [{"evidence_uid": "EV-SAME"}]
    repo.evidence_by_uid.return_value = {
        "evidence_uid": "EV-SAME",
        "title": "Same",
        "content": "same evidence body",
        "source_system": "jira",
        "object_type": "ticket",
        "application": "Net Banking",
    }
    repo.__enter__ = lambda self: repo
    repo.__exit__ = lambda *args: None

    provider = _FakeProvider()
    embed_calls = {"n": 0}
    real_embed = provider.embed

    def counting_embed(texts):
        embed_calls["n"] += len(texts)
        return real_embed(texts)

    provider.embed = counting_embed  # type: ignore[method-assign]

    monkeypatch.setattr("ecs_platform.llm_engine.provider.get_provider", lambda: provider)
    monkeypatch.setattr("ecs_platform.vectorstore.get_vector_store", lambda: store)
    monkeypatch.setattr("ecs_platform.config.load_vectorstore_config", lambda: {
        "vectorstore": {"chunking": {"chunk_size": 1000, "chunk_overlap": 150}}
    })
    monkeypatch.setattr("ecs_platform.rag._governance_documents", lambda: [])
    monkeypatch.setattr(
        "ecs_platform.rag._existing_chunk_hashes",
        lambda _store: {"EV-SAME:0": content_hash},
    )
    monkeypatch.setattr("ecs_platform.repository.EvidenceRepository", lambda: repo)

    report = rag.reindex_evidence(incremental=True)
    assert report["ok"] is True
    assert report["skipped_unchanged"] >= 1
    assert report["embedded_chunks"] == 0
    assert embed_calls["n"] == 0


def test_rag_status_indexed_pct_uses_distinct_evidence_overlap(monkeypatch):
    store = _FakeStore()
    for i in range(5):
        store.upsert([
            Chunk(
                chunk_id=f"EV-{i:03d}:0",
                evidence_uid=f"EV-{i:03d}",
                text=f"chunk {i}a",
                embedding=[1.0, 0.0, 0.0],
                metadata={"doc_kind": "evidence"},
            ),
            Chunk(
                chunk_id=f"EV-{i:03d}:1",
                evidence_uid=f"EV-{i:03d}",
                text=f"chunk {i}b",
                embedding=[1.0, 0.0, 0.0],
                metadata={"doc_kind": "evidence"},
            ),
        ])
    for j in range(10):
        store.upsert([
            Chunk(
                chunk_id=f"lineage:{j}:0",
                evidence_uid=f"lineage:{j}",
                text="governance lineage",
                embedding=[1.0, 0.0, 0.0],
                metadata={"doc_kind": "governance"},
            ),
        ])

    repo = MagicMock()
    repo.counts.return_value = {"total": 78}
    repo.__enter__ = lambda self: repo
    repo.__exit__ = lambda *args: None

    monkeypatch.setattr("ecs_platform.llm_engine.provider.get_provider", lambda: _FakeProvider())
    monkeypatch.setattr("ecs_platform.vectorstore.get_vector_store", lambda: store)
    monkeypatch.setattr("ecs_platform.rag.EvidenceRepository", lambda: repo)

    status = rag.rag_status()
    assert status["vector_count"] == 20  # 10 evidence chunks + 10 governance
    assert status["indexed_chunks"] == 10
    assert status["indexed_evidence"] == 5
    assert status["evidence_count"] == 78
    assert status["indexed_pct"] <= 100.0
    assert status["indexed_pct"] == pytest.approx(round(100 * 5 / 78, 1))
    assert status["indexed_pct"] != pytest.approx(round(100 * 20 / 78, 1))
