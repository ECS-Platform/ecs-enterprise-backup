"""Evidence retriever: embeds the query and runs RBAC-scoped vector search."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ecs_platform.config import load_llm_config
from ecs_platform.llm_engine.provider import LLMProvider, get_provider
from ecs_platform.vectorstore import VectorStore, get_vector_store

# Over-fetch multiplier so Top-K unique refill stays possible when duplicates
# dominate the head of the ranked hit list. Capped to avoid large scans.
_DEDUP_FETCH_MULTIPLIER = 5
_DEDUP_FETCH_CAP = 40


@dataclass
class RetrievedContext:
    question: str
    contexts: list[dict[str, Any]] = field(default_factory=list)

    def as_prompt_inputs(self) -> list[dict[str, Any]]:
        return self.contexts


def _logical_evidence_key(metadata: dict[str, Any] | None, evidence_uid: str) -> str:
    """Stable key for one logical evidence artifact using existing PGVector metadata.

    Preference order (no re-embedding / similarity):
      1. content_hash — identical payload across distinct evidence_uid copies
      2. evidence_key — same logical artifact identity
      3. framework + control + filename — coarse metadata fingerprint
      4. evidence_uid — no cross-hit collapse when metadata is absent
    """
    meta = metadata or {}
    content_hash = str(meta.get("content_hash") or "").strip()
    if content_hash:
        return f"hash:{content_hash}"

    evidence_key = str(meta.get("evidence_key") or "").strip()
    if evidence_key:
        return f"key:{evidence_key}"

    framework = str(meta.get("framework") or "").strip()
    control = str(meta.get("control_id") or meta.get("control") or "").strip()
    filename = str(meta.get("filename") or "").strip()
    if framework or control or filename:
        return f"meta:{framework}|{control}|{filename}"

    return f"uid:{evidence_uid or ''}"


def _dedupe_contexts(
    contexts: list[dict[str, Any]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    """Keep highest-ranked hit per logical evidence; stop at ``limit`` uniques."""
    if limit <= 0:
        return []
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for ctx in contexts:
        key = _logical_evidence_key(ctx.get("metadata"), str(ctx.get("evidence_uid") or ""))
        if key in seen:
            continue
        seen.add(key)
        unique.append(ctx)
        if len(unique) >= limit:
            break
    return unique


class EvidenceRetriever:
    def __init__(self, provider: LLMProvider | None = None, store: VectorStore | None = None,
                 rag_cfg: dict[str, Any] | None = None):
        self._provider = provider or get_provider()
        self._store = store or get_vector_store()
        self._rag = rag_cfg or load_llm_config().get("rag", {})

    def retrieve(self, question: str, *, scope_filters: dict[str, Any] | None = None,
                 top_k: int | None = None) -> RetrievedContext:
        desired_k = int(top_k or self._rag.get("top_k", 8))
        max_chunks = int(self._rag.get("max_context_chunks", 12))
        unique_limit = min(desired_k, max_chunks) if desired_k > 0 else 0

        # Fetch a wider ranked window so dedupe can refill toward Top-K unique.
        fetch_k = min(max(desired_k * _DEDUP_FETCH_MULTIPLIER, desired_k), _DEDUP_FETCH_CAP)
        if fetch_k < 1:
            return RetrievedContext(question=question, contexts=[])

        embedding = self._provider.embed([question])[0]
        hits = self._store.search(
            embedding,
            top_k=fetch_k,
            filters=scope_filters or None,
        )
        # TEMPORARY grounding DEBUG (no retrieval/business logic change).
        try:
            from modules.audit_intelligence.llm import _grounding_debug as _gdbg

            _gdbg.log_raw_pgvector_hits(list(hits or []))
        except Exception:  # noqa: BLE001
            pass
        min_score = float(self._rag.get("min_score", 0.0))
        contexts = [
            {
                "evidence_uid": h.evidence_uid,
                "text": h.text,
                "score": h.score,
                "source_system": (h.metadata or {}).get("source_system"),
                "metadata": h.metadata,
            }
            for h in hits if h.score >= min_score
        ]
        deduped = _dedupe_contexts(contexts, limit=unique_limit)
        try:
            from modules.audit_intelligence.llm import _grounding_debug as _gdbg

            _gdbg.log_deduped_contexts(deduped)
        except Exception:  # noqa: BLE001
            pass
        return RetrievedContext(
            question=question,
            contexts=deduped,
        )
