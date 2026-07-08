"""Audit LLM evaluation suite — replay, comparison, grounding, and citation checks.

Additive layer over the existing audit-LLM stack
(:mod:`modules.audit_intelligence.llm.execution_service`). It does NOT replace the
prompt library, execution service, benchmark runner, or RAG — it consumes their
outputs. Everything here is deterministic and offline (no live LLM required),
which makes it safe for tests and for grounding/hallucination checks without a
second model.

Capabilities:
  * :func:`replay`            — re-execute a prompt from a stored execution/benchmark
                               record, deterministically (dry-run RAM profile), so
                               the assembled prompt + token estimate + deterministic
                               result are reproduced without calling the LLM.
  * :func:`compare`           — structured diff of two execution results (token
                               estimate, assumptions, source references, fallback
                               status, response text).
  * :func:`validate_grounding`— classify an answer as grounded / weakly_grounded /
                               unsupported by checking its claims against the
                               evidence context + deterministic result.
  * :func:`validate_citations`— verify every ``[E#]`` / evidence-key citation in the
                               answer is present in the supplied context, and flag
                               citations that reference missing evidence.
"""

from __future__ import annotations

import re
from typing import Any, Optional

# Grounding thresholds (fraction of answer tokens supported by the context).
_GROUNDED_MIN = 0.60
_WEAK_MIN = 0.30

_CITATION_RE = re.compile(r"\[E(\d+)\]")
_WORD_RE = re.compile(r"[a-z0-9][a-z0-9_./-]{2,}")
_STOPWORDS = {
    "the", "and", "for", "are", "with", "that", "this", "from", "have", "has",
    "was", "were", "will", "not", "but", "all", "any", "can", "may", "per",
    "into", "over", "under", "than", "then", "there", "their", "them", "these",
    "those", "such", "which", "while", "about", "above", "below", "been", "being",
    "across", "based", "your", "our", "its", "it's", "a", "an", "of", "to", "in",
    "on", "is", "as", "by", "or", "no",
}


def _tokens(text: str) -> set[str]:
    return {w for w in _WORD_RE.findall((text or "").lower()) if w not in _STOPWORDS}


# --------------------------------------------------------------------------- #
# Replay
# --------------------------------------------------------------------------- #
def replay(record: dict[str, Any], *, live: bool = False) -> dict[str, Any]:
    """Replay a prompt execution from a stored record. Deterministic by default.

    ``record`` may be an execution-service result (has ``prompt_id`` / ``query``)
    or a benchmark row (has ``prompt_id``). Replays via the existing
    ``execution_service.execute``. With ``live=False`` (default) it forces the
    dry-run RAM profile so no LLM is called — ideal for reproducibility + tests.
    Returns ``{ok, replayed, original_ref}``.
    """
    from modules.audit_intelligence.llm import execution_service

    prompt_id = str(record.get("prompt_id") or "")
    query = str(record.get("query") or record.get("user_query") or "")
    token_profile = str(record.get("token_profile") or "")
    ram_profile = "worst_case_enterprise_dry_run" if not live else str(
        record.get("ram_profile") or record.get("benchmark_profile") or "local_16gb_safe")
    if not prompt_id and not query:
        return {"ok": False, "error": "record has no prompt_id or query"}
    replayed = execution_service.execute(
        prompt_id=prompt_id, user_query=query or prompt_id,
        ram_profile=ram_profile, token_profile=token_profile,
        use_rag=bool(live),
    )
    return {
        "ok": True,
        "mode": "live" if live else "dry_run",
        "original_ref": {"prompt_id": prompt_id, "query": query},
        "replayed": replayed,
    }


# --------------------------------------------------------------------------- #
# Compare
# --------------------------------------------------------------------------- #
def _get(result: dict[str, Any], key: str, default=None):
    # Accept either a raw execute() result or a {"result": {...}} envelope.
    if isinstance(result, dict) and "result" in result and isinstance(result["result"], dict):
        result = result["result"]
    return result.get(key, default) if isinstance(result, dict) else default


def compare(result_a: dict[str, Any], result_b: dict[str, Any]) -> dict[str, Any]:
    """Structured diff of two execution results. Never raises."""
    def te(r):
        t = _get(r, "token_estimate", {}) or {}
        return {"input_tokens": t.get("input_tokens", 0),
                "output_tokens": t.get("output_tokens", 0),
                "total_tokens": t.get("total_tokens", 0),
                "fits_context": t.get("fits_context")}

    a_tokens, b_tokens = te(result_a), te(result_b)
    a_src = set(map(str, _get(result_a, "source_references", []) or []))
    b_src = set(map(str, _get(result_b, "source_references", []) or []))
    a_assume = list(_get(result_a, "assumptions", []) or [])
    b_assume = list(_get(result_b, "assumptions", []) or [])
    a_resp = str(_get(result_a, "llm_response", "") or "")
    b_resp = str(_get(result_b, "llm_response", "") or "")
    a_words, b_words = _tokens(a_resp), _tokens(b_resp)

    return {
        "ok": True,
        "token_estimate": {
            "a": a_tokens, "b": b_tokens,
            "delta_total": b_tokens["total_tokens"] - a_tokens["total_tokens"],
        },
        "source_references": {
            "shared": sorted(a_src & b_src),
            "only_a": sorted(a_src - b_src),
            "only_b": sorted(b_src - a_src),
        },
        "assumptions": {
            "only_a": [x for x in a_assume if x not in b_assume],
            "only_b": [x for x in b_assume if x not in a_assume],
            "shared_count": len(set(a_assume) & set(b_assume)),
        },
        "fallback_used": {
            "a": bool(_get(result_a, "fallback_used", False)),
            "b": bool(_get(result_b, "fallback_used", False)),
            "differs": bool(_get(result_a, "fallback_used", False)) != bool(_get(result_b, "fallback_used", False)),
        },
        "response": {
            "a_len": len(a_resp), "b_len": len(b_resp),
            "shared_terms": len(a_words & b_words),
            "only_a_terms": len(a_words - b_words),
            "only_b_terms": len(b_words - a_words),
            "jaccard": round(len(a_words & b_words) / len(a_words | b_words), 3)
            if (a_words | b_words) else 1.0,
        },
    }


# --------------------------------------------------------------------------- #
# Grounding / hallucination check
# --------------------------------------------------------------------------- #
def _context_text(evidence_context: dict[str, Any]) -> str:
    """Flatten an evidence_context (+ deterministic result) into one text blob."""
    if not isinstance(evidence_context, dict):
        return str(evidence_context or "")
    parts: list[str] = []
    det = evidence_context.get("deterministic_result")
    if isinstance(det, dict):
        parts.append(str(det.get("answer_text", "")))
        for v in det.values():
            if isinstance(v, (str, int, float)):
                parts.append(str(v))
            elif isinstance(v, list):
                parts.append(" ".join(str(x) for x in v))
    parts.extend(str(s) for s in (evidence_context.get("source_references") or []))
    # Also accept a pre-flattened "text" / "assembled_prompt".
    for k in ("text", "assembled_prompt", "context_text"):
        if evidence_context.get(k):
            parts.append(str(evidence_context[k]))
    return " ".join(parts)


def validate_grounding(answer: str, evidence_context: dict[str, Any]) -> dict[str, Any]:
    """Classify how well an answer is grounded in the evidence context.

    Deterministic lexical-overlap check (no external model): the fraction of the
    answer's significant terms that also appear in the context. Classifies:
      * grounded        (>= 0.60 supported)
      * weakly_grounded (>= 0.30)
      * unsupported     (< 0.30, or empty context with a non-empty answer)
    Returns the ratio, supported/unsupported term samples, and the label.
    """
    ans_terms = _tokens(answer)
    ctx_terms = _tokens(_context_text(evidence_context))
    if not ans_terms:
        return {"ok": True, "grounding": "empty_answer", "supported_ratio": 1.0,
                "unsupported_terms": [], "supported_terms": []}
    if not ctx_terms:
        return {"ok": True, "grounding": "unsupported", "supported_ratio": 0.0,
                "unsupported_terms": sorted(ans_terms)[:20], "supported_terms": []}
    supported = ans_terms & ctx_terms
    unsupported = ans_terms - ctx_terms
    ratio = round(len(supported) / len(ans_terms), 3)
    if ratio >= _GROUNDED_MIN:
        label = "grounded"
    elif ratio >= _WEAK_MIN:
        label = "weakly_grounded"
    else:
        label = "unsupported"
    return {
        "ok": True,
        "grounding": label,
        "supported_ratio": ratio,
        "supported_terms": sorted(supported)[:20],
        "unsupported_terms": sorted(unsupported)[:20],
        "thresholds": {"grounded": _GROUNDED_MIN, "weakly_grounded": _WEAK_MIN},
    }


# --------------------------------------------------------------------------- #
# Citation validation
# --------------------------------------------------------------------------- #
def validate_citations(answer: str, evidence_context: dict[str, Any],
                       *, assembled_prompt: str = "") -> dict[str, Any]:
    """Verify that citations in the answer reference evidence present in context.

    Checks two citation styles:
      * ``[E#]`` markers — must correspond to an evidence block in the assembled
        prompt / context (which numbers evidence as [E1], [E2], ...).
      * evidence keys / uids appearing in the answer — must be in
        ``source_references``.
    Flags any citation that references missing evidence. Returns
    ``{ok, valid, cited, missing, available_source_count}``.
    """
    prompt_text = assembled_prompt or _context_text(evidence_context)
    available_markers = set(_CITATION_RE.findall(prompt_text))
    src_refs = {str(s) for s in (evidence_context.get("source_references", []) or [])} \
        if isinstance(evidence_context, dict) else set()

    cited_markers = set(_CITATION_RE.findall(answer or ""))
    missing_markers = sorted(cited_markers - available_markers, key=lambda x: int(x))

    # Evidence-key style citations: any source_ref token quoted verbatim in answer.
    ans_lower = (answer or "").lower()
    cited_keys = sorted(s for s in src_refs if s and s.lower() in ans_lower)

    missing = [f"[E{m}]" for m in missing_markers]
    valid = not missing
    return {
        "ok": True,
        "valid": valid,
        "cited_markers": sorted(cited_markers, key=lambda x: int(x)) if cited_markers else [],
        "cited_evidence_keys": cited_keys,
        "missing": missing,
        "available_marker_count": len(available_markers),
        "available_source_count": len(src_refs),
    }


def evaluate(result: dict[str, Any]) -> dict[str, Any]:
    """Convenience: run grounding + citation validation over one execution result.

    Uses the result's ``llm_response`` (or falls back to the deterministic answer
    text when the LLM was unavailable) against its ``evidence_context``.
    """
    r = result.get("result", result) if isinstance(result, dict) else {}
    answer = str(r.get("llm_response") or "")
    ev_ctx = r.get("evidence_context") or {}
    if not answer:
        det = (ev_ctx.get("deterministic_result") or {}) if isinstance(ev_ctx, dict) else {}
        answer = str(det.get("answer_text", ""))
    return {
        "ok": True,
        "grounding": validate_grounding(answer, ev_ctx),
        "citations": validate_citations(answer, ev_ctx,
                                        assembled_prompt=str(r.get("assembled_prompt") or "")),
    }
