"""Audit LLM retrieval quality: logical-evidence dedupe after PGVector search."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ecs_platform.llm_engine.retriever import (
    EvidenceRetriever,
    _dedupe_contexts,
    _logical_evidence_key,
)
from ecs_platform.vectorstore.base import SearchHit


@dataclass
class _FakeProvider:
    dim: int = 4

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * self.dim for _ in texts]


@dataclass
class _FakeStore:
    hits: list[SearchHit] = field(default_factory=list)
    last_top_k: int | None = None
    last_filters: dict[str, Any] | None = None

    def search(
        self,
        embedding: list[float],
        *,
        top_k: int = 8,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchHit]:
        self.last_top_k = top_k
        self.last_filters = filters
        return list(self.hits[:top_k])


def _hit(
    uid: str,
    *,
    score: float,
    content_hash: str = "",
    evidence_key: str = "",
    framework: str = "",
    control: str = "",
    filename: str = "",
    text: str = "",
) -> SearchHit:
    return SearchHit(
        chunk_id=f"{uid}:0",
        evidence_uid=uid,
        text=text or f"body for {uid}",
        score=score,
        metadata={
            "evidence_id": uid,
            "content_hash": content_hash,
            "evidence_key": evidence_key,
            "framework": framework,
            "control": control,
            "control_id": control,
            "filename": filename,
        },
    )


def test_logical_key_prefers_content_hash():
    meta = {
        "content_hash": "abc123",
        "evidence_key": "KEY-1",
        "framework": "PCI DSS",
        "control": "8.3",
        "filename": "mfa.pdf",
    }
    assert _logical_evidence_key(meta, "EVD-1") == "hash:abc123"
    assert _logical_evidence_key(meta, "EVD-2") == _logical_evidence_key(meta, "EVD-99")


def test_logical_key_falls_back_to_evidence_key_then_meta():
    assert _logical_evidence_key({"evidence_key": "PCI-8.3-MFA"}, "EVD-1") == "key:PCI-8.3-MFA"
    assert (
        _logical_evidence_key(
            {"framework": "PCI DSS", "control_id": "8.3", "filename": "mfa.pdf"},
            "EVD-1",
        )
        == "meta:PCI DSS|8.3|mfa.pdf"
    )
    assert _logical_evidence_key({}, "EVD-9") == "uid:EVD-9"


def test_dedupe_keeps_highest_ranked_and_refills_to_limit():
    # Same content_hash across six UIDs (the investigated PCI 8.3 copies), plus
    # two distinct hashes. Rank order must be preserved; Top-3 unique expected.
    shared = "sha-pci-8.3-identical"
    contexts = [
        {"evidence_uid": "EVD-23306", "score": 0.99, "metadata": {"content_hash": shared}},
        {"evidence_uid": "EVD-26355", "score": 0.98, "metadata": {"content_hash": shared}},
        {"evidence_uid": "EVD-27165", "score": 0.97, "metadata": {"content_hash": shared}},
        {"evidence_uid": "EVD-28072", "score": 0.96, "metadata": {"content_hash": shared}},
        {"evidence_uid": "EVD-51012", "score": 0.95, "metadata": {"content_hash": shared}},
        {"evidence_uid": "EVD-UNIQUE-A", "score": 0.90, "metadata": {"content_hash": "hash-a"}},
        {"evidence_uid": "EVD-UNIQUE-B", "score": 0.85, "metadata": {"content_hash": "hash-b"}},
    ]
    out = _dedupe_contexts(contexts, limit=3)
    assert [c["evidence_uid"] for c in out] == ["EVD-23306", "EVD-UNIQUE-A", "EVD-UNIQUE-B"]


def test_retrieve_overfetches_and_returns_unique_top_k():
    shared = "same-logical-payload"
    store = _FakeStore(
        hits=[
            _hit("EVD-23306", score=0.99, content_hash=shared, filename="pci_8_3.pdf"),
            _hit("EVD-26355", score=0.98, content_hash=shared, filename="pci_8_3.pdf"),
            _hit("EVD-27165", score=0.97, content_hash=shared, filename="pci_8_3.pdf"),
            _hit("EVD-28072", score=0.96, content_hash=shared, filename="pci_8_3.pdf"),
            _hit("EVD-28099", score=0.95, content_hash=shared, filename="pci_8_3.pdf"),
            _hit("EVD-51012", score=0.94, content_hash=shared, filename="pci_8_3.pdf"),
            _hit("EVD-TLS-1", score=0.80, content_hash="tls-hash", filename="tls.pdf"),
            _hit("EVD-ENC-1", score=0.70, content_hash="enc-hash", filename="enc.pdf"),
            _hit("EVD-LOG-1", score=0.60, content_hash="log-hash", filename="log.pdf"),
        ]
    )
    retriever = EvidenceRetriever(
        provider=_FakeProvider(),
        store=store,
        rag_cfg={"top_k": 5, "min_score": 0.0, "max_context_chunks": 12},
    )
    result = retriever.retrieve("Summarize PCI DSS 8.3 evidence", top_k=3)

    # Over-fetch so refill toward unique Top-K is possible.
    assert store.last_top_k == 15  # 3 * 5
    uids = [c["evidence_uid"] for c in result.contexts]
    assert uids == ["EVD-23306", "EVD-TLS-1", "EVD-ENC-1"]
    hashes = [c["metadata"]["content_hash"] for c in result.contexts]
    assert hashes == ["same-logical-payload", "tls-hash", "enc-hash"]
    assert len(set(hashes)) == 3


def test_retrieve_preserves_api_shape_and_source_metadata():
    store = _FakeStore(
        hits=[
            _hit(
                "EVD-1",
                score=0.9,
                content_hash="h1",
                evidence_key="KEY-1",
                framework="PCI DSS",
                control="8.3",
                filename="mfa.pdf",
                text="MFA evidence body",
            )
        ]
    )
    retriever = EvidenceRetriever(
        provider=_FakeProvider(),
        store=store,
        rag_cfg={"top_k": 5, "min_score": 0.0, "max_context_chunks": 12},
    )
    result = retriever.retrieve("evidence summary", top_k=5)
    assert result.question == "evidence summary"
    assert len(result.contexts) == 1
    ctx = result.contexts[0]
    assert ctx["evidence_uid"] == "EVD-1"
    assert ctx["text"] == "MFA evidence body"
    assert ctx["score"] == 0.9
    assert ctx["metadata"]["filename"] == "mfa.pdf"
    assert ctx["metadata"]["framework"] == "PCI DSS"
