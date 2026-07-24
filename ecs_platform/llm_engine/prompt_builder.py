"""Grounded RAG prompt construction. The assistant answers ONLY from evidence."""

from __future__ import annotations

from typing import Any

SYSTEM_PROMPT = (
    "You are the ECS Evidence Assistant for an enterprise GRC (governance, risk, "
    "and compliance) platform. You answer questions strictly using the evidence "
    "context provided. Rules:\n"
    "1. Use ONLY the supplied evidence and ECS governance facts. Never invent facts, "
    "controls, systems, applications, or evidence ids.\n"
    "2. Every factual claim must cite its evidence id like [E1], [E3].\n"
    "3. If NO evidence blocks and NO governance facts were supplied, reply with EXACTLY this "
    "sentence and nothing else: \"No evidence found in ECS repository.\"\n"
    "4. If evidence blocks WERE supplied, never claim that no evidence exists. Summarize the "
    "provided items with [E#] citations; if they only partially match the question, say so "
    "explicitly while still citing what was retrieved.\n"
    "5. Be concise and audit-ready. Prefer specifics (counts, owners, statuses, dates).\n"
    "6. Do not include chain-of-thought or <think> sections; output only the final answer.\n"
)


def build_rag_prompt(question: str, contexts: list[dict[str, Any]]) -> str:
    """Build the user prompt embedding numbered, citable evidence blocks."""
    if not contexts:
        return (
            f"Question: {question}\n\n"
            "No evidence was retrieved from the repository. State that there is "
            "insufficient evidence to answer and recommend which connectors to sync."
        )
    blocks = []
    for idx, ctx in enumerate(contexts, start=1):
        meta = ctx.get("metadata", {}) or {}
        header = (
            f"[E{idx}] source={ctx.get('source_system', meta.get('source_system', '?'))} "
            f"type={meta.get('object_type', '?')} app={meta.get('application', '?')} "
            f"uid={ctx.get('evidence_uid', '?')}"
        )
        blocks.append(f"{header}\n{ctx.get('text', '')}".strip())
    evidence = "\n\n".join(blocks)
    return (
        f"Evidence context:\n{evidence}\n\n"
        f"Question: {question}\n\n"
        "Answer using only the evidence above, citing ids like [E1]. "
        "If insufficient, say so explicitly."
    )
