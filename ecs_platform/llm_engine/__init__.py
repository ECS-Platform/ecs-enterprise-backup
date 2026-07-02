"""LLM + RAG layer for the ECS evidence assistant."""

from ecs_platform.llm_engine.provider import LLMError, LLMProvider, get_provider
from ecs_platform.llm_engine.prompt_builder import build_rag_prompt
from ecs_platform.llm_engine.retriever import EvidenceRetriever, RetrievedContext
from ecs_platform.llm_engine.generator import ResponseGenerator, RagAnswer

__all__ = [
    "LLMProvider",
    "LLMError",
    "get_provider",
    "build_rag_prompt",
    "EvidenceRetriever",
    "RetrievedContext",
    "ResponseGenerator",
    "RagAnswer",
]
