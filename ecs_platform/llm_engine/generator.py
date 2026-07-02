"""ResponseGenerator: end-to-end grounded RAG answer with citations."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ecs_platform.config import load_llm_config
from ecs_platform.llm_engine.metrics_logger import persist_rag_metric
from ecs_platform.llm_engine.prompt_builder import SYSTEM_PROMPT, build_rag_prompt
from ecs_platform.llm_engine.provider import LLMProvider, get_provider
from ecs_platform.llm_engine.retriever import EvidenceRetriever


@dataclass
class RagAnswer:
    question: str
    answer: str
    citations: list[dict[str, Any]] = field(default_factory=list)
    grounded: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "answer": self.answer,
            "citations": self.citations,
            "grounded": self.grounded,
        }


class ResponseGenerator:
    """Wires retrieval + prompt + LLM into a single auditable answer."""

    def __init__(self, provider: LLMProvider | None = None,
                 retriever: EvidenceRetriever | None = None,
                 rag_cfg: dict[str, Any] | None = None):
        self._provider = provider or get_provider()
        self._retriever = retriever or EvidenceRetriever(provider=self._provider)
        self._rag = rag_cfg or load_llm_config().get("rag", {})

    def answer(self, question: str, *, scope_filters: dict[str, Any] | None = None) -> RagAnswer:
        request_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        started = time.perf_counter()
        retrieved = self._retriever.retrieve(question, scope_filters=scope_filters)
        contexts = retrieved.as_prompt_inputs()

        if not contexts and self._rag.get("refuse_without_evidence", True):
            _persist_metric({
                "timestamp": timestamp,
                "request_id": request_id,
                "question": question,
                "model_name": "",
                "provider": "",
                "retrieval_mode": "vectorstore",
                "retrieved_documents": 0,
                "retrieved_chunks": 0,
                "prompt_size_chars": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "retrieval_latency_ms": 0,
                "prompt_build_latency_ms": 0,
                "llm_latency_ms": 0,
                "end_to_end_latency_ms": int((time.perf_counter() - started) * 1000),
            })
            return RagAnswer(
                question=question,
                answer="There is insufficient evidence in the repository to answer this "
                       "question. Sync the relevant connectors and try again.",
                citations=[],
                grounded=False,
            )

        prompt = build_rag_prompt(question, contexts)
        llm_start = time.perf_counter()
        text, usage = self._provider.generate_with_metadata(prompt, system=SYSTEM_PROMPT)
        llm_ms = int((time.perf_counter() - llm_start) * 1000)
        in_tokens = int(usage.get("input_tokens", 0) or 0)
        out_tokens = int(usage.get("output_tokens", 0) or 0)
        total_tokens = int(usage.get("total_tokens", 0) or (in_tokens + out_tokens))
        _persist_metric({
            "timestamp": timestamp,
            "request_id": request_id,
            "question": question,
            "model_name": self._provider.model,
            "provider": type(self._provider).__name__.replace("Provider", "").lower(),
            "retrieval_mode": "vectorstore",
            "retrieved_documents": len(contexts),
            "retrieved_chunks": len(contexts),
            "prompt_size_chars": len(prompt),
            "input_tokens": in_tokens,
            "output_tokens": out_tokens,
            "total_tokens": total_tokens,
            "retrieval_latency_ms": 0,
            "prompt_build_latency_ms": 0,
            "llm_latency_ms": llm_ms,
            "end_to_end_latency_ms": int((time.perf_counter() - started) * 1000),
        })
        citations = [
            {"ref": f"E{i}", "evidence_uid": c.get("evidence_uid"),
             "source_system": c.get("source_system"), "score": c.get("score")}
            for i, c in enumerate(contexts, start=1)
        ]
        return RagAnswer(question=question, answer=text, citations=citations, grounded=True)


def _persist_metric(row: dict[str, Any]) -> None:
    try:
        persist_rag_metric(row)
    except Exception:  # noqa: BLE001
        pass
