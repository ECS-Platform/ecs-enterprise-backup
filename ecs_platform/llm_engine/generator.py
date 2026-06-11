"""ResponseGenerator: end-to-end grounded RAG answer with citations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ecs_platform.config import load_llm_config
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
        retrieved = self._retriever.retrieve(question, scope_filters=scope_filters)
        contexts = retrieved.as_prompt_inputs()

        if not contexts and self._rag.get("refuse_without_evidence", True):
            return RagAnswer(
                question=question,
                answer="There is insufficient evidence in the repository to answer this "
                       "question. Sync the relevant connectors and try again.",
                citations=[],
                grounded=False,
            )

        prompt = build_rag_prompt(question, contexts)
        text = self._provider.generate(prompt, system=SYSTEM_PROMPT)
        citations = [
            {"ref": f"E{i}", "evidence_uid": c.get("evidence_uid"),
             "source_system": c.get("source_system"), "score": c.get("score")}
            for i, c in enumerate(contexts, start=1)
        ]
        return RagAnswer(question=question, answer=text, citations=citations, grounded=True)
