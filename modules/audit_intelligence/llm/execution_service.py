"""Prompt execution service — the workbench orchestrator.

Ties the audit LLM pieces together for a single request:
  classify -> deterministic route -> context assembly -> token estimate ->
  (LLM via the EXISTING provider abstraction, or dry-run) -> structured result.

Reuses ``ecs_platform.llm_engine.get_provider`` (config-selected; local Ollama by
default) and ``set_benchmark_generation_config`` for RAM-aware context/timeout.
Never crashes: if the LLM is unavailable it returns the deterministic result plus
a clear fallback message.
"""

from __future__ import annotations

import time
from typing import Any

from modules.audit_intelligence.llm import (
    context_builder,
    deterministic_router,
    prompt_library,
    query_classifier,
    token_estimator,
)

# Output-token guidance per model-size label (used when a profile doesn't cap it).
_OUTPUT_TOKENS_BY_SIZE = {"small": 512, "medium": 1024, "large": 2048}


def _resolve_output_tokens(prompt: dict[str, Any], profile: dict[str, Any]) -> int:
    cap = profile.get("max_output_tokens")
    if cap:
        try:
            return int(cap)
        except (TypeError, ValueError):
            pass
    return _OUTPUT_TOKENS_BY_SIZE.get(str(prompt.get("recommended_model_size", "medium")), 1024)


def _provider_status(provider) -> dict[str, Any]:
    """Config-only provider status (no network). Never raises."""
    try:
        name = type(provider).__name__.replace("Provider", "").lower()
        return {
            "provider": name,
            "model": getattr(provider, "model", ""),
            "configured": bool(provider.configured()),
        }
    except Exception as exc:  # noqa: BLE001
        return {"provider": "unknown", "model": "", "configured": False,
                "error": type(exc).__name__}


def _apply_benchmark_limits(profile: dict[str, Any], token_profile: str) -> None:
    """Feed RAM-profile context/output/timeout to the provider (benchmark hook).

    Uses the existing ``set_benchmark_generation_config`` so the provider owns the
    final value (env > benchmark config > yaml). Never overrides an explicit env var.
    """
    try:
        from ecs_platform.llm_engine.provider import set_benchmark_generation_config

        num_ctx = prompt_library.token_profile_context(token_profile) or profile.get("max_context")
        set_benchmark_generation_config(
            num_ctx=num_ctx,
            num_predict=profile.get("max_output_tokens"),
            timeout_seconds=profile.get("timeout_seconds"),
        )
    except Exception:  # noqa: BLE001 - provider hook optional
        pass


def execute(
    *,
    prompt_id: str = "",
    user_query: str = "",
    input_variables: dict[str, Any] | None = None,
    ram_profile: str = "local_16gb_safe",
    token_profile: str = "",
    provider_model: str = "",
    use_rag: bool = True,
) -> dict[str, Any]:
    """Execute the full prompt lifecycle for one request. Never raises.

    Returns the workbench response contract (query, query_type, deterministic_result,
    assembled_prompt, llm_response, confidence, assumptions, limitations,
    source_references, token_estimate, latency_ms, provider_status, fallback_used,
    ram_profile, token_profile, warnings).
    """
    started = time.perf_counter()
    input_variables = input_variables or {}
    warnings: list[str] = []

    # Best-effort demo physical-evidence seed (idempotent; never blocks answering).
    try:
        from modules.audit_intelligence.engines.llm_usecase_demo_seed import ensure_seeded

        ensure_seeded()
    except Exception:  # noqa: BLE001
        pass

    # 1. Classification (+ entity extraction), merged with explicit input variables.
    classification = query_classifier.classify(user_query or "")
    entities = {**classification.get("entities", {}), **{k: v for k, v in input_variables.items() if v}}
    answer_mode = classification.get("answer_mode") or query_classifier.resolve_answer_mode(
        user_query or "", classification.get("query_type", ""))

    # 2. Resolve prompt definition (explicit prompt_id wins; else infer nothing —
    #    the query itself drives deterministic routing).
    prompt = prompt_library.get_prompt(prompt_id) if prompt_id else None
    effective_query_type = (prompt or {}).get("query_type") or classification["query_type"]
    profile = prompt_library.get_profile(ram_profile) or {}
    # Prefer 4K for local 16 GB unless the caller/prompt demands a larger profile.
    default_tp = "small_4k" if ram_profile.startswith("local_16gb") else "medium_8k"
    tprofile = token_profile or (prompt or {}).get("token_profile") or default_tp
    if ram_profile.startswith("local_16gb") and tprofile not in ("small_4k", "medium_8k", "large_16k"):
        tprofile = "small_4k"
    execution_mode = str(profile.get("execution_mode", "llm"))

    # Route prompt_id for evidence-centric intents when caller did not pin one.
    route_id = prompt_id or "audit_query_answering"
    low_q = (user_query or "").lower()
    if not prompt_id:
        if "map" in low_q and "control" in low_q:
            route_id = "evidence_reuse_recommendation"
        elif "gap" in low_q or "summarize evidence" in low_q or "evidence summary" in low_q:
            route_id = "evidence_gap_to_observation_risk"
        elif answer_mode == "deterministic":
            route_id = "observation_count"

    # 3. Deterministic context (DB-first). Always computed for det/hybrid; optional for rag.
    include_det = answer_mode in ("deterministic", "hybrid") or route_id not in (
        "audit_query_answering",
    )
    if answer_mode == "rag":
        include_det = False
    det = deterministic_router.build_deterministic_context(route_id, entities)
    if answer_mode == "rag":
        # Keep a minimal placeholder so templates still fill; do not treat registry as RAG source.
        det = {
            "answer_text": "Answer using retrieved physical evidence chunks only.",
            "count": 0,
            "rows": [],
            "row_total": 0,
            "data_used": ["pgvector_evidence_chunks"],
            "source_references": [],
            "auto_approve": False,
        }

    # Evidence-to-control mapping must never auto-approve.
    if isinstance(det, dict) and ("control" in low_q or "map" in low_q):
        det = {**det, "auto_approve": False}

    # 4. Assemble context (deterministic + optional RAG).
    prompt_for_ctx = prompt or {
        "system_prompt": (
            "You are an ECS audit assistant. Use only supplied facts/evidence. "
            "Cite evidence_id + filename + version. Never invent files. "
            "Never auto-approve controls."
        ),
        "user_prompt_template": "{deterministic_result}\n\nQuestion: {user_query}",
        "required_context": ["observations", "evidence"],
    }
    top_k = min(int(profile.get("top_k", 5) or 5), 5)
    want_rag = bool(use_rag) and answer_mode in ("rag", "hybrid") and execution_mode != "dry_run"
    if answer_mode == "deterministic":
        want_rag = False
    ctx = context_builder.build_context(
        prompt=prompt_for_ctx, user_query=user_query, entities=entities,
        deterministic_result=det, top_k=top_k, use_rag=want_rag,
        include_deterministic=include_det or answer_mode != "rag",
    )
    assembled_prompt = ctx["assembled_prompt"]
    system_prompt = ctx["system_prompt"]

    # 5. Token estimate + RAM/token-profile compatibility.
    expected_out = _resolve_output_tokens(prompt or {"recommended_model_size": "small"}, profile)
    token_estimate = token_estimator.estimate_prompt(
        system_prompt=system_prompt, assembled_prompt=assembled_prompt,
        expected_output_tokens=min(expected_out, 512), token_profile=tprofile, ram_profile=ram_profile,
    )
    warnings.extend(token_estimate.get("warnings", []))

    # 6. Confidence/assumptions/limitations scaffold (always present for llm_assisted).
    confidence = ""
    assumptions: list[str] = []
    limitations: list[str] = []
    if effective_query_type == "llm_assisted":
        confidence = "Medium"
        assumptions = [
            "Historical observation/closure patterns are representative of the coming period.",
            "The demo/UAT dataset reflects the in-scope applications and frameworks.",
        ]
        limitations = [
            "Prediction is probabilistic, not a guarantee.",
            "Local-LLM output quality varies by model size and available RAM.",
        ]

    # 7. Execution: dry-run OR live LLM (with fallback).
    llm_response = ""
    fallback_used = False
    provider_status: dict[str, Any] = {}

    # Pure deterministic counts: return structured answer without requiring LLM/RAG.
    if answer_mode == "deterministic" and execution_mode != "dry_run":
        llm_response = str(det.get("answer_text") or "")
        # Still attempt optional formatting via LLM when available (non-fatal).
        try:
            from ecs_platform.llm_engine import LLMError, get_provider

            provider = get_provider()
            provider_status = _provider_status(provider)
            if provider.configured():
                _apply_benchmark_limits({**profile, "max_output_tokens": 256, "max_context": 4096}, tprofile)
                try:
                    formatted, meta = provider.generate_with_metadata(
                        assembled_prompt or llm_response, system=system_prompt or
                        "Rephrase the deterministic count without changing any number.")
                    if formatted:
                        llm_response = formatted
                    if meta.get("total_tokens"):
                        token_estimate["measured"] = meta
                except LLMError:
                    pass
                except Exception:  # noqa: BLE001
                    pass
        except Exception:  # noqa: BLE001
            provider_status = {"provider": "none", "configured": False}

    elif ctx.get("insufficient_evidence") and answer_mode == "rag":
        llm_response = (
            "Insufficient evidence in the indexed physical evidence corpus. "
            "No matching evidence_id/filename/version citations are available for this question."
        )
        fallback_used = True
        warnings.append("RAG returned no chunks; insufficient-evidence response.")
        provider_status = {"provider": "none", "model": "", "configured": False, "mode": "insufficient_evidence"}

    elif execution_mode == "dry_run":
        llm_response = ""
        fallback_used = True
        warnings.append("Dry-run profile: token estimate + assembled prompt only, no LLM call.")
        provider_status = {"provider": "none", "model": "", "configured": False, "mode": "dry_run"}
    else:
        _apply_benchmark_limits({**profile, "max_context": min(int(profile.get("max_context", 4096) or 4096), 4096)}, tprofile)
        try:
            from ecs_platform.llm_engine import LLMError, get_provider

            provider = get_provider()
            provider_status = _provider_status(provider)
            if provider_model:
                provider_status["requested_model"] = provider_model
            try:
                llm_response, meta = provider.generate_with_metadata(
                    assembled_prompt, system=system_prompt)
                if meta.get("total_tokens"):
                    token_estimate["measured"] = meta
            except LLMError as exc:
                fallback_used = True
                warnings.append(f"LLM unavailable ({type(exc).__name__}); returned deterministic result.")
                provider_status["error"] = str(exc)[:200]
                llm_response = str(det.get("answer_text") or "") if include_det else (
                    "Insufficient evidence or LLM unavailable; cannot answer from physical evidence."
                )
            except Exception as exc:  # noqa: BLE001
                fallback_used = True
                warnings.append(f"LLM call failed ({type(exc).__name__}); returned deterministic result.")
                provider_status["error"] = type(exc).__name__
                llm_response = str(det.get("answer_text") or "") if include_det else (
                    "Insufficient evidence or LLM unavailable; cannot answer from physical evidence."
                )
        except Exception as exc:  # noqa: BLE001 - provider import/config failure
            fallback_used = True
            provider_status = {"provider": "unknown", "configured": False, "error": type(exc).__name__}
            warnings.append("LLM provider not available; returned deterministic result.")
            llm_response = str(det.get("answer_text") or "") if include_det else (
                "Insufficient evidence or LLM unavailable; cannot answer from physical evidence."
            )

    latency_ms = round((time.perf_counter() - started) * 1000, 1)

    if not llm_response and fallback_used and execution_mode != "dry_run" and answer_mode != "rag":
        llm_response = (
            "[FALLBACK] The local LLM is unavailable, so only the deterministic ECS "
            "result is shown above. Start the local provider (see config/llm.yaml) "
            "to get an LLM-generated summary/analysis."
        )

    memory_warnings = [w for w in warnings if "memory" in w.lower() or "swap" in w.lower()]
    profile_memory_note = str(profile.get("memory_warning") or "").strip()
    memory_warning = "; ".join(memory_warnings) or profile_memory_note

    evidence_context = {
        "deterministic_result": det,
        "rag_used": ctx["rag_used"],
        "source_references": ctx["source_references"],
        "required_context": prompt_for_ctx.get("required_context", []),
        "citations": ctx.get("citations", []),
        "insufficient_evidence": ctx.get("insufficient_evidence", False),
        "answer_mode": answer_mode,
    }

    return {
        "query": user_query,
        "prompt_id": prompt_id or route_id,
        "query_type": effective_query_type,
        "answer_mode": answer_mode,
        "classification": classification,
        "entities": entities,
        "deterministic_result": det,
        "evidence_context": evidence_context,
        "assembled_prompt": assembled_prompt,
        "system_prompt": system_prompt,
        "llm_response": llm_response,
        "confidence": confidence,
        "assumptions": assumptions,
        "limitations": limitations,
        "source_references": ctx["source_references"],
        "citations": ctx.get("citations", []),
        "rag_used": ctx["rag_used"],
        "insufficient_evidence": ctx.get("insufficient_evidence", False),
        "token_estimate": token_estimate,
        "latency_ms": latency_ms,
        "provider_status": provider_status,
        "fallback_used": fallback_used,
        "ram_profile": ram_profile,
        "benchmark_profile": ram_profile,
        "token_profile": tprofile,
        "execution_mode": execution_mode,
        "memory_warning": memory_warning,
        "warnings": warnings,
        "auto_approve": False,
    }
