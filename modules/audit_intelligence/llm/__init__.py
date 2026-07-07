"""ECS Audit LLM Prompt Workbench (local-LLM audit prompt lifecycle).

A thin layer over the EXISTING ECS LLM/RAG/data engines that adds an audit-focused
prompt library, query classifier, deterministic query router, RAG/context builder,
token estimator, prompt-execution service, and a RAM-aware benchmark runner for
16 GB / 20 GB local laptops.

Nothing here re-implements the LLM provider, RAG retriever, evidence repository,
observation engine, dashboard, or predefined-query engine — it composes them.
"""

from __future__ import annotations

__all__ = [
    "prompt_library",
    "query_classifier",
    "deterministic_router",
    "context_builder",
    "token_estimator",
    "execution_service",
    "benchmark_runner",
]
