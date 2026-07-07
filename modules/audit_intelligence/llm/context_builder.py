"""Context builder — assembles deterministic + RAG/evidence context for a prompt.

Reuses the existing RAG retriever (``ecs_platform.llm_engine.EvidenceRetriever``)
and prompt builder where a vector store + embeddings are available; degrades
gracefully to deterministic-only context when RAG is unavailable (offline / no
embeddings), so the workbench never crashes.

Output is a single assembled user-prompt string plus structured metadata
(source references, whether RAG was used, context sizes).
"""

from __future__ import annotations

from typing import Any


def _retrieve_rag(question: str, *, top_k: int, scope_filters: dict[str, Any] | None) -> dict[str, Any]:
    """Best-effort RAG retrieval. Returns {contexts, used, error}. Never raises."""
    try:
        from ecs_platform.llm_engine import EvidenceRetriever

        retriever = EvidenceRetriever()
        ctx = retriever.retrieve(question, scope_filters=scope_filters or None, top_k=top_k)
        return {"contexts": ctx.contexts, "used": bool(ctx.contexts), "error": ""}
    except Exception as exc:  # noqa: BLE001 - RAG optional; fall back to deterministic-only
        return {"contexts": [], "used": False, "error": f"{type(exc).__name__}: {exc}"}


def _format_deterministic(det: dict[str, Any]) -> str:
    """Render the deterministic result as a compact, LLM-readable block."""
    if not det:
        return "ECS deterministic result: (none available)"
    lines = [f"ECS deterministic result: {det.get('answer_text', '').strip()}"]
    for key in ("count", "by_framework", "by_severity", "by_status", "by_application",
                "average_readiness_percent", "highest_gap_framework", "top_applications"):
        if key in det and det[key] not in (None, "", {}, []):
            lines.append(f"- {key}: {det[key]}")
    rows = det.get("rows") or []
    if rows:
        lines.append(f"- sample_rows ({min(len(rows), 5)} of {det.get('row_total', len(rows))}):")
        for r in rows[:5]:
            if isinstance(r, dict):
                compact = {k: r.get(k) for k in ("observation_id", "application", "framework",
                                                 "observation_severity", "status", "owner",
                                                 "due_date", "control_id", "age_days")
                           if r.get(k) not in (None, "")}
                lines.append(f"    * {compact or r}")
            else:
                lines.append(f"    * {r}")
    return "\n".join(lines)


def _format_rag(contexts: list[dict[str, Any]]) -> str:
    """Render RAG evidence as numbered, citable [E#] blocks (reuses ECS convention)."""
    if not contexts:
        return ""
    blocks = []
    for idx, ctx in enumerate(contexts, start=1):
        meta = ctx.get("metadata", {}) or {}
        header = (f"[E{idx}] source={ctx.get('source_system', meta.get('source_system', '?'))} "
                  f"app={meta.get('application', '?')} uid={ctx.get('evidence_uid', '?')}")
        blocks.append(f"{header}\n{ctx.get('text', '')}".strip())
    return "Evidence context:\n" + "\n\n".join(blocks)


def build_context(
    *,
    prompt: dict[str, Any],
    user_query: str,
    entities: dict[str, Any],
    deterministic_result: dict[str, Any] | None,
    top_k: int = 8,
    use_rag: bool = True,
) -> dict[str, Any]:
    """Assemble the final user prompt from deterministic + (optional) RAG context.

    Returns ``{assembled_prompt, system_prompt, rag_used, rag_error,
    source_references, deterministic_block, rag_block}``. Never raises.
    """
    system_prompt = str(prompt.get("system_prompt") or "")
    template = str(prompt.get("user_prompt_template") or "{deterministic_result}")

    det_block = _format_deterministic(deterministic_result or {})

    rag = {"contexts": [], "used": False, "error": ""}
    required_ctx = set(prompt.get("required_context", []) or [])
    wants_evidence = bool(required_ctx & {"evidence", "evidence_packs", "connector_evidence"}) or use_rag
    if use_rag and wants_evidence and user_query.strip():
        scope_filters = {}
        if entities.get("application"):
            scope_filters["application"] = entities["application"]
        rag = _retrieve_rag(user_query, top_k=top_k, scope_filters=scope_filters or None)

    rag_block = _format_rag(rag["contexts"]) if rag["used"] else ""

    # Compose the deterministic_result slot the templates reference.
    combined_context = det_block + (("\n\n" + rag_block) if rag_block else "")

    # Safe template fill: templates use {deterministic_result}, {user_query},
    # {application_or_all}. Missing keys must not crash.
    fill = {
        "deterministic_result": combined_context,
        "user_query": user_query,
        "application_or_all": entities.get("application") or "all applications",
    }
    try:
        assembled = template.format_map(_SafeDict(fill))
    except Exception:  # noqa: BLE001
        assembled = f"{combined_context}\n\nQuestion: {user_query}"

    # Source references: deterministic sources + RAG evidence uids.
    source_references = list((deterministic_result or {}).get("source_references", []))
    for ctx in rag["contexts"]:
        uid = ctx.get("evidence_uid")
        if uid:
            source_references.append(str(uid))

    return {
        "assembled_prompt": assembled,
        "system_prompt": system_prompt,
        "rag_used": rag["used"],
        "rag_error": rag["error"],
        "rag_context_count": len(rag["contexts"]),
        "source_references": source_references,
        "deterministic_block": det_block,
        "rag_block": rag_block,
    }


class _SafeDict(dict):
    """dict for str.format_map that leaves unknown placeholders intact."""

    def __missing__(self, key: str) -> str:  # noqa: D401
        return "{" + key + "}"
