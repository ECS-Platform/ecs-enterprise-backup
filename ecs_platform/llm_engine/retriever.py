"""Evidence retriever: embeds the query and runs RBAC-scoped vector search."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ecs_platform.config import load_llm_config
from ecs_platform.llm_engine.provider import LLMProvider, get_provider
from ecs_platform.vectorstore import VectorStore, get_vector_store


@dataclass
class RetrievedContext:
    question: str
    contexts: list[dict[str, Any]] = field(default_factory=list)

    def as_prompt_inputs(self) -> list[dict[str, Any]]:
        return self.contexts


class EvidenceRetriever:
    def __init__(self, provider: LLMProvider | None = None, store: VectorStore | None = None,
                 rag_cfg: dict[str, Any] | None = None):
        self._provider = provider or get_provider()
        self._store = store or get_vector_store()
        self._rag = rag_cfg or load_llm_config().get("rag", {})

    def retrieve(self, question: str, *, scope_filters: dict[str, Any] | None = None,
                 top_k: int | None = None) -> RetrievedContext:
        embedding = self._provider.embed([question])[0]
        hits = self._store.search(
            embedding,
            top_k=int(top_k or self._rag.get("top_k", 8)),
            filters=scope_filters or None,
        )
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
        max_chunks = int(self._rag.get("max_context_chunks", 12))
        return RetrievedContext(question=question, contexts=contexts[:max_chunks])
