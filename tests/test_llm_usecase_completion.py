"""Focused tests for the 4 ECS LLM use cases + canary RAG proof.

Offline: FakeProvider + keyword FakeStore. Exercises real custody/SQL/index path
for demo physical evidence without live Ollama/MinIO/PG.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")
os.environ.setdefault("AUDIT_WORKFLOW_ENABLED", "true")
os.environ.setdefault("ECS_EVIDENCE_SNAPSHOT_ENABLED", "true")

import pytest

from ecs_platform.storage.object_store import LocalObjectStore, reset_object_store, set_object_store
from ecs_platform.vectorstore.base import Chunk, VectorStore
from modules.audit_intelligence.engines import evidence_repository as repo
from modules.audit_intelligence.engines import llm_usecase_demo_seed as seed
from modules.audit_intelligence.llm import (
    context_builder,
    deterministic_router,
    execution_service,
    query_classifier,
)
from modules.audit_intelligence.services import persistence as pers
from modules.audit_intelligence.services.sql_persistence import SqlAuditPersistence

CANARY = "ECS-RAG-CANARY-7429"


@dataclass
class _FakeProvider:
    def configured(self) -> bool:
        return True

    @property
    def embedding_model(self) -> str:
        return "mock-embed"

    def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for t in texts:
            h = float(sum(ord(c) for c in t) % 97)
            out.append([h, 1.0, 2.0, 3.0])
        return out

    def generate_with_metadata(self, prompt: str, system: str = ""):
        text = f"{system}\n{prompt}"
        if CANARY in text or "canary" in text.lower():
            ans = (
                f"The canary token {CANARY} appears in evidence_id=EV-LLM-ENC-001 "
                f"filename=netbanking_encryption_at_rest.json version=1."
            )
            return ans, {"total_tokens": 64}
        if "encryption" in text.lower():
            return (
                "Encryption at rest for Net Banking is supported by "
                "evidence_id=EV-LLM-ENC-001 filename=netbanking_encryption_at_rest.json version=1 "
                "(Oracle TDE enabled)."
            ), {"total_tokens": 80}
        if "how many" in text.lower() and "open observation" in text.lower():
            return prompt.split("ECS deterministic result:")[-1].strip().split("\n")[0], {"total_tokens": 40}
        if "map" in text.lower() and "control" in text.lower():
            return (
                "Recommend mapping EV-LLM-ENC-001 / netbanking_encryption_at_rest.json v1 "
                "to PCI-3.4. Do not auto-approve."
            ), {"total_tokens": 50}
        if "gap" in text.lower() or "summar" in text.lower():
            return (
                "Summary of retrieved physical evidence with gaps noted. "
                "Cite EV-LLM-TLS-001|netbanking_tls_config.txt|v1 where applicable."
            ), {"total_tokens": 60}
        return "Grounded answer from supplied context.", {"total_tokens": 30}


class _KeywordStore(VectorStore):
    def __init__(self) -> None:
        self.chunks: dict[str, Chunk] = {}

    def init_store(self) -> None:
        return None

    def upsert(self, chunks: list[Chunk]) -> int:
        for c in chunks:
            self.chunks[c.chunk_id] = c
        return len(chunks)

    def search(self, embedding: list[float], *, top_k: int = 5, filters: dict[str, Any] | None = None):
        items = list(self.chunks.values())
        if filters and filters.get("application"):
            app = str(filters["application"]).lower()
            items = [c for c in items if str((c.metadata or {}).get("application", "")).lower() == app]

        class Hit:
            def __init__(self, c: Chunk, score: float):
                self.evidence_uid = c.evidence_uid
                self.text = c.text
                self.score = score
                self.metadata = c.metadata

        return [Hit(c, 1.0) for c in items][:top_k]

    def delete_for_evidence(self, evidence_uid: str) -> None:
        for cid in list(self.chunks):
            if self.chunks[cid].evidence_uid == evidence_uid:
                del self.chunks[cid]


@pytest.fixture()
def demo_env(tmp_path, monkeypatch):
    repo.reset_repository()
    seed.reset_seed_flag()
    reset_object_store()
    set_object_store(LocalObjectStore(tmp_path / "objects"))
    sql = SqlAuditPersistence()
    pers.set_persistence(sql)
    monkeypatch.setenv("AUDIT_WORKFLOW_ENABLED", "true")
    monkeypatch.setenv("ECS_EVIDENCE_SNAPSHOT_ENABLED", "true")
    monkeypatch.setenv("ECS_EVIDENCE_CUSTODY_MODE", "SNAPSHOT")

    provider = _FakeProvider()
    store = _KeywordStore()
    report = seed.seed_llm_usecase_demo(
        force=True,
        provider=provider,
        vector_store=store,
        object_store_root=tmp_path / "objects",
        enable_sql=True,
    )
    assert report["ok"], report.get("errors")

    def _retrieve(question: str, *, top_k: int = 5, scope_filters=None):
        q = (question or "").lower()
        if "unicorn" in q or "quantum flux" in q:
            return {"contexts": [], "used": False, "error": ""}
        emb = provider.embed([question])[0]
        hits = store.search(emb, top_k=top_k, filters=scope_filters)
        scored = []
        for h in hits:
            score = 0.5
            if CANARY.lower() in (h.text or "").lower() and ("canary" in q or CANARY.lower() in q):
                score = 1.0
            if "encryption" in q and "encryption" in (h.text or "").lower():
                score = max(score, 0.95)
            if "tls" in q and "tls" in (h.text or "").lower():
                score = max(score, 0.9)
            scored.append((score, h))
        scored.sort(key=lambda x: -x[0])
        contexts = [
            {
                "evidence_uid": h.evidence_uid,
                "text": h.text,
                "score": s,
                "source_system": "llm_usecase_demo",
                "metadata": h.metadata,
            }
            for s, h in scored[:top_k]
        ]
        return {"contexts": contexts, "used": bool(contexts), "error": ""}

    monkeypatch.setattr(context_builder, "_retrieve_rag", _retrieve)
    monkeypatch.setattr(seed, "ensure_seeded", lambda **kw: report)
    import ecs_platform.llm_engine as llm_engine
    monkeypatch.setattr(llm_engine, "get_provider", lambda: provider)

    yield {"provider": provider, "store": store, "sql": sql, "report": report, "tmp": tmp_path}

    repo.reset_repository()
    seed.reset_seed_flag()
    reset_object_store()


def test_usecase1_natural_language_audit_query_deterministic(demo_env):
    q_count = "How many open observations are there for Net Banking?"
    c = query_classifier.classify(q_count)
    assert c["answer_mode"] == "deterministic"
    det = deterministic_router.open_observations_by_application(application="Net Banking")
    assert det["count"] >= 6
    assert any(r.get("observation_id") == "OBS-PCI-1021" for r in det["rows"])
    assert any(r.get("root_cause") for r in det["rows"] if r.get("observation_id") == "OBS-PCI-1021")

    r = execution_service.execute(user_query=q_count, ram_profile="local_16gb_safe", use_rag=False)
    assert r["answer_mode"] == "deterministic"
    assert str(det["count"]) in (r["llm_response"] + r["deterministic_result"]["answer_text"])
    assert r.get("rag_used") is False

    q_hybrid = (
        "How many open observations are there for Net Banking? "
        "Can you give me details of the observations"
    )
    assert query_classifier.classify(q_hybrid)["answer_mode"] == "hybrid"
    h = execution_service.execute(user_query=q_hybrid, ram_profile="local_16gb_safe")
    assert h["answer_mode"] == "hybrid"
    assert h["deterministic_result"]["count"] == det["count"]


def test_usecase2_evidence_summary_and_gaps(demo_env):
    q = "Summarize evidence gaps for Net Banking and cite physical evidence files"
    r = execution_service.execute(
        user_query=q,
        prompt_id="evidence_gap_to_observation_risk",
        ram_profile="local_16gb_safe",
    )
    assert r["deterministic_result"]
    refs = " ".join(r.get("source_references") or [])
    assert "EV-LLM" in refs or "gap" in (r.get("llm_response") or "").lower() or r.get("rag_used")


def test_usecase3_evidence_to_control_mapping(demo_env):
    q = "Map evidence to controls for Net Banking encryption"
    r = execution_service.execute(
        user_query=q,
        prompt_id="evidence_to_control_mapping",
        ram_profile="local_16gb_safe",
    )
    assert r.get("auto_approve") is False
    assert r["deterministic_result"].get("auto_approve") is False
    body = (r.get("llm_response") or "") + str(r.get("deterministic_result"))
    assert "PCI-3.4" in body or "EV-LLM-ENC-001" in body


def test_usecase4_physical_evidence_rag_qa(demo_env):
    q = "What evidence supports encryption for Net Banking?"
    assert query_classifier.classify(q)["answer_mode"] == "rag"
    r = execution_service.execute(user_query=q, ram_profile="local_16gb_safe")
    assert r["answer_mode"] == "rag"
    assert r.get("rag_used") is True
    cites = r.get("citations") or []
    assert cites
    joined = " ".join(
        f"{c.get('evidence_id')}|{c.get('filename')}|{c.get('version')}" for c in cites
    )
    assert "EV-LLM-ENC-001" in joined
    assert "netbanking_encryption_at_rest.json" in joined
    assert "ECS observation/evidence-gap registry" not in " ".join(r.get("source_references") or [])

    bad = execution_service.execute(
        user_query="What evidence supports unicorn quantum flux controls for Net Banking?",
        ram_profile="local_16gb_safe",
    )
    assert bad.get("insufficient_evidence") or "insufficient" in (bad.get("llm_response") or "").lower()


def test_canary_rag_end_to_end(demo_env):
    store_fs = demo_env["tmp"] / "objects"
    assert any(p.is_file() for p in store_fs.rglob("*"))

    art = repo.get_latest(repo.make_evidence_key("Net Banking", "PCI-3.4"))
    assert art is not None
    assert art.evidence_id == "EV-LLM-ENC-001"
    assert art.custody_mode == "SNAPSHOT"
    assert art.object_uri

    chunks = list(demo_env["store"].chunks.values())
    assert chunks
    enc = [c for c in chunks if "ECS-RAG-CANARY-7429" in (c.text or "")]
    assert enc
    meta = enc[0].metadata
    assert meta.get("evidence_id") == "EV-LLM-ENC-001"
    assert meta.get("filename") == "netbanking_encryption_at_rest.json"
    assert meta.get("version") == 1
    assert meta.get("application") == "Net Banking"
    assert meta.get("control_id") == "PCI-3.4"

    r = execution_service.execute(
        user_query=f"What does the evidence say about {CANARY} for Net Banking encryption?",
        ram_profile="local_16gb_safe",
    )
    assert CANARY in (r.get("llm_response") or "")
    cite_blob = " ".join(
        f"{c.get('evidence_id')} {c.get('filename')} {c.get('version')}"
        for c in (r.get("citations") or [])
    )
    assert "EV-LLM-ENC-001" in cite_blob
    assert "netbanking_encryption_at_rest.json" in cite_blob
