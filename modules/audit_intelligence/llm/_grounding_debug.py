"""TEMPORARY grounding DEBUG logger for Audit LLM verification.

Enable with: ECS_AUDIT_LLM_GROUNDING_DEBUG=1

Does not alter retrieval or business logic — write-only side effects.
Remove or leave disabled after grounding verification.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_ENABLED = (os.environ.get("ECS_AUDIT_LLM_GROUNDING_DEBUG") or "").strip().lower() in {
    "1", "true", "yes", "on",
}

_LOG_PATH = Path(
    os.environ.get(
        "ECS_AUDIT_LLM_GROUNDING_LOG",
        "data/debug/audit_llm_grounding_debug.log",
    )
)


def enabled() -> bool:
    return _ENABLED


def _write(text: str) -> None:
    if not _ENABLED:
        return
    try:
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(text)
            if not text.endswith("\n"):
                fh.write("\n")
    except Exception:  # noqa: BLE001 - debug must never break the pipeline
        pass
    try:
        print(text, flush=True)
    except Exception:  # noqa: BLE001
        pass


def section(title: str) -> None:
    bar = "=" * 72
    _write(f"\n{bar}\n{title}\n{bar}")


def log_query(query: str) -> None:
    section("LOG 1 - USER QUERY")
    _write("QUERY:")
    _write(query or "")


def log_raw_pgvector_hits(hits: list[Any]) -> None:
    section("LOG 2 - RAW PGVECTOR RESULTS (before deduplication)")
    if not hits:
        _write("(no hits)")
        return
    for rank, h in enumerate(hits, start=1):
        meta = getattr(h, "metadata", None) or {}
        if not isinstance(meta, dict):
            meta = {}
        _write(
            f"Rank {rank}\n"
            f"  evidence_uid: {getattr(h, 'evidence_uid', '')}\n"
            f"  filename: {meta.get('filename', '')}\n"
            f"  content_hash: {meta.get('content_hash', '')}\n"
            f"  score: {getattr(h, 'score', '')}\n"
            f"  framework: {meta.get('framework', '')}\n"
            f"  control: {meta.get('control_id') or meta.get('control', '')}\n"
            f"  application: {meta.get('application', '')}\n"
        )


def log_deduped_contexts(contexts: list[dict[str, Any]]) -> None:
    section("LOG 3 - DEDUPLICATED RESULTS (used for LLM context)")
    if not contexts:
        _write("(no contexts after dedupe)")
        return
    for rank, ctx in enumerate(contexts, start=1):
        meta = ctx.get("metadata") or {}
        if not isinstance(meta, dict):
            meta = {}
        _write(
            f"Rank {rank}\n"
            f"  UID: {ctx.get('evidence_uid', '')}\n"
            f"  content_hash: {meta.get('content_hash', '')}\n"
            f"  filename: {meta.get('filename', '')}\n"
            f"  score: {ctx.get('score', '')}\n"
            f"  framework: {meta.get('framework', '')}\n"
            f"  control: {meta.get('control_id') or meta.get('control', '')}\n"
            f"  application: {meta.get('application', '')}\n"
        )


def log_retrieved_evidence_text(contexts: list[dict[str, Any]]) -> None:
    section("LOG 4 - RETRIEVED CONTEXT (COMPLETE text sent toward LLM)")
    if not contexts:
        _write("(no evidence contexts)")
        return
    for idx, ctx in enumerate(contexts, start=1):
        meta = ctx.get("metadata") or {}
        if not isinstance(meta, dict):
            meta = {}
        uid = ctx.get("evidence_uid") or meta.get("evidence_id") or ""
        filename = meta.get("filename") or ""
        content = ctx.get("text") or ""
        _write(
            "========================\n"
            f"Evidence {idx}\n"
            f"UID: {uid}\n"
            f"Filename: {filename}\n"
            f"Content:\n{content}\n"
            "========================"
        )


def log_final_prompt(*, system_prompt: str, user_prompt: str) -> None:
    section("LOG 5 - FINAL PROMPT SENT TO LLM")
    _write("--- SYSTEM PROMPT ---")
    _write(system_prompt or "(empty)")
    _write("\n--- USER PROMPT (assembled; includes evidence context) ---")
    _write(user_prompt or "(empty)")


def log_llm_response(response: str) -> None:
    section("LOG 6 - RAW LLM RESPONSE (before formatting)")
    _write(response or "(empty)")
