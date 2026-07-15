"""Focused mocked tests for version-aware evidence PGVector indexing."""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

from dataclasses import dataclass, field
from typing import Any

import pytest

from ecs_platform.evidence_indexing import (
    build_chunk_metadata,
    index_after_persist,
    index_evidence_version,
    reindex_evidence_versions,
    resolve_indexable_text,
    retry_index_evidence,
)
from ecs_platform.storage.object_store import LocalObjectStore, object_key_for_evidence, set_object_store
from ecs_platform.vectorstore.base import Chunk, VectorStore
from modules.audit_intelligence.engines import evidence_repository as repo
from modules.audit_intelligence.models import EvidenceArtifact


@dataclass
class _FakeProvider:
    dim: int = 4
    configured_flag: bool = True

    @property
    def embedding_model(self) -> str:
        return "mock-embed"

    def configured(self) -> bool:
        return self.configured_flag

    def embed(self, texts: list[str]) -> list[list[float]]:
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
def _clean():
    repo.reset_repository()
    set_object_store(None)
    yield
    repo.reset_repository()
    set_object_store(None)


def _artifact(**overrides) -> EvidenceArtifact:
    base = dict(
        evidence_key="Net Banking::C-1",
        version=1,
        control_id="C-1",
        asset_id="Net Banking",
        frameworks=("PCI DSS",),
        content_hash="abc123",
        filename="report.pdf",
        evidence_id="EVD-00001",
        environment="Production",
        source_connector="sharepoint",
        custody_mode="REFERENCE_ONLY",
    )
    base.update(overrides)
    return EvidenceArtifact(**base)


def test_resolve_text_order_snapshot_normalized_metadata():
    art = _artifact(custody_mode="SNAPSHOT")
    snap, source = resolve_indexable_text(art, snapshot_bytes=b"snapshot body")
    assert source == "snapshot"
    assert snap == "snapshot body"

    ref, source2 = resolve_indexable_text(_artifact(), normalized_text="normalized body")
    assert source2 == "normalized"
    assert ref == "normalized body"

    meta, source3 = resolve_indexable_text(_artifact())
    assert source3 == "metadata"
    assert "report.pdf" in meta


def test_index_after_persist_upserts_with_metadata(monkeypatch):
    store = _FakeStore()
    provider = _FakeProvider()
    art = _artifact()

    monkeypatch.setattr(
        "ecs_platform.evidence_indexing._existing_chunk_hashes",
        lambda _store: {},
    )
    monkeypatch.setattr(
        "ecs_platform.config.load_vectorstore_config",
        lambda: {"vectorstore": {"chunking": {"chunk_size": 1000, "chunk_overlap": 150}}},
    )

    report = index_evidence_version(
        art,
        normalized_text="audit evidence body",
        provider=provider,
        store=store,
    )
    assert report["ok"] is True
    assert report["embedded_chunks"] == 1
    chunk = next(iter(store.chunks.values()))
    assert chunk.metadata["evidence_id"] == "EVD-00001"
    assert chunk.metadata["version"] == 1
    assert chunk.metadata["application"] == "Net Banking"
    assert chunk.metadata["control"] == "C-1"
    assert chunk.metadata["connector"] == "sharepoint"
    assert chunk.metadata["custody_mode"] == "REFERENCE_ONLY"


def test_idempotent_skip_unchanged_chunks(monkeypatch):
    store = _FakeStore()
    provider = _FakeProvider()
    art = _artifact()
    piece_hash = build_chunk_metadata(art, text_source="normalized", piece_hash="deadbeef", is_latest=True)[
        "chunk_content_hash"
    ]

    def _existing(_store):
        return {f"EVD-00001:v1:0:{piece_hash}": piece_hash}

    monkeypatch.setattr("ecs_platform.evidence_indexing._existing_chunk_hashes", _existing)
    monkeypatch.setattr(
        "ecs_platform.evidence_indexing._text_hash",
        lambda _text: piece_hash,
    )
    monkeypatch.setattr(
        "ecs_platform.config.load_vectorstore_config",
        lambda: {"vectorstore": {"chunking": {"chunk_size": 1000, "chunk_overlap": 150}}},
    )

    report = index_evidence_version(
        art,
        normalized_text="same text",
        provider=provider,
        store=store,
    )
    assert report["ok"] is True
    assert report["embedded_chunks"] == 0
    assert report["skipped_unchanged"] == 1


def test_skip_superseded_version_by_default(monkeypatch):
    store = _FakeStore()
    provider = _FakeProvider()
    v1 = _artifact(version=1)
    v2 = _artifact(version=2, content_hash="def456")
    repo._STORE[v1.evidence_key] = [v1, v2]

    report = index_evidence_version(v1, normalized_text="old", provider=provider, store=store)
    assert report["skipped"] is True
    assert report["reason"] == "superseded"
    assert store.chunks == {}


def test_preserves_historical_versions_when_forced(monkeypatch):
    store = _FakeStore()
    provider = _FakeProvider()
    v1 = _artifact(version=1)
    v2 = _artifact(version=2, content_hash="def456")
    repo._STORE[v1.evidence_key] = [v1, v2]

    monkeypatch.setattr("ecs_platform.evidence_indexing._existing_chunk_hashes", lambda _store: {})
    monkeypatch.setattr(
        "ecs_platform.config.load_vectorstore_config",
        lambda: {"vectorstore": {"chunking": {"chunk_size": 1000, "chunk_overlap": 150}}},
    )

    r1 = index_evidence_version(
        v1, normalized_text="version one", provider=provider, store=store, skip_if_superseded=False,
    )
    r2 = index_evidence_version(
        v2, normalized_text="version two", provider=provider, store=store, skip_if_superseded=False,
    )
    assert r1["embedded_chunks"] == 1
    assert r2["embedded_chunks"] == 1
    versions = {c.metadata["version"] for c in store.chunks.values()}
    assert versions == {1, 2}


def test_snapshot_bytes_preferred_from_object_store(tmp_path, monkeypatch):
    store = _FakeStore()
    provider = _FakeProvider()
    local = LocalObjectStore(tmp_path)
    set_object_store(local)
    art = _artifact(custody_mode="SNAPSHOT", version=2, content_hash="snap999")
    key = object_key_for_evidence(
        source_connector=art.source_connector,
        evidence_key=art.evidence_key,
        version=art.version,
        content_hash=art.content_hash,
        filename=art.filename,
    )
    local.put_immutable(key, b"snapshot from object store")

    monkeypatch.setattr("ecs_platform.evidence_indexing._existing_chunk_hashes", lambda _store: {})
    monkeypatch.setattr(
        "ecs_platform.config.load_vectorstore_config",
        lambda: {"vectorstore": {"chunking": {"chunk_size": 1000, "chunk_overlap": 150}}},
    )
    report = index_evidence_version(art, provider=provider, store=store)
    assert report["text_source"] == "snapshot"
    assert "snapshot from object store" in next(iter(store.chunks.values())).text


def test_store_evidence_triggers_index_hook(monkeypatch):
    calls: list[str] = []

    def _fake_index(artifact, *, normalized_text=""):
        calls.append(normalized_text)

    monkeypatch.setattr(repo, "_index_artifact", _fake_index)
    art = repo.store_evidence(
        control_id="C-1",
        content="post-persist indexing",
        asset_id="Net Banking",
        filename="x.pdf",
    )
    assert art.version == 1
    assert calls == ["post-persist indexing"]


def test_retry_and_reindex_helpers(monkeypatch):
    store = _FakeStore()
    provider = _FakeProvider()
    v1 = repo.store_evidence(control_id="C-1", content="one", asset_id="app")
    v2 = repo.store_evidence(control_id="C-1", content="two", asset_id="app")
    monkeypatch.setattr("ecs_platform.evidence_indexing._existing_chunk_hashes", lambda _store: {})
    monkeypatch.setattr(
        "ecs_platform.config.load_vectorstore_config",
        lambda: {"vectorstore": {"chunking": {"chunk_size": 1000, "chunk_overlap": 150}}},
    )
    monkeypatch.setattr("ecs_platform.llm_engine.provider.get_provider", lambda: provider)
    monkeypatch.setattr("ecs_platform.vectorstore.get_vector_store", lambda: store)

    retry = retry_index_evidence(v1.evidence_key, 1, normalized_text="one")
    assert retry["ok"] is True
    assert retry["embedded_chunks"] == 1

    bulk = reindex_evidence_versions(include_superseded=False, force=True)
    assert bulk["ok"] is True
    assert bulk["indexed"] >= 1
    assert v2.version == 2


def test_demo_mode_skips_without_provider(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    report = index_evidence_version(
        _artifact(),
        normalized_text="demo",
        provider=_FakeProvider(configured_flag=False),
        store=_FakeStore(),
    )
    assert report["ok"] is True
    assert report["skipped"] is True
    assert report["reason"] == "demo_mode_no_provider"
