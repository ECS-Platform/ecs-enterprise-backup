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

    # 1. Classification (+ entity extraction), merged with explicit input variables.
    classification = query_classifier.classify(user_query or "")
    entities = {**classification.get("entities", {}), **{k: v for k, v in input_variables.items() if v}}

    # 2. Resolve prompt definition (explicit prompt_id wins; else infer nothing —
    #    the query itself drives deterministic routing).
    prompt = prompt_library.get_prompt(prompt_id) if prompt_id else None
    effective_query_type = (prompt or {}).get("query_type") or classification["query_type"]
    profile = prompt_library.get_profile(ram_profile) or {}
    tprofile = token_profile or (prompt or {}).get("token_profile") or "medium_8k"
    execution_mode = str(profile.get("execution_mode", "llm"))

    # 3. Deterministic context (DB-first). Always computed; LLM may summarize it.
    det = deterministic_router.build_deterministic_context(
        prompt_id or "audit_query_answering", entities)

    # 4. Assemble context (deterministic + optional RAG).
    prompt_for_ctx = prompt or {
        "system_prompt": "", "user_prompt_template": "{deterministic_result}\n\nQuestion: {user_query}",
        "required_context": ["observations", "evidence"],
    }
    top_k = int(profile.get("top_k", 8) or 8)
    ctx = context_builder.build_context(
        prompt=prompt_for_ctx, user_query=user_query, entities=entities,
        deterministic_result=det, top_k=top_k, use_rag=use_rag and execution_mode != "dry_run",
    )
    assembled_prompt = ctx["assembled_prompt"]
    system_prompt = ctx["system_prompt"]

    # 5. Token estimate + RAM/token-profile compatibility.
    expected_out = _resolve_output_tokens(prompt or {"recommended_model_size": "medium"}, profile)
    token_estimate = token_estimator.estimate_prompt(
        system_prompt=system_prompt, assembled_prompt=assembled_prompt,
        expected_output_tokens=expected_out, token_profile=tprofile, ram_profile=ram_profile,
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

    if execution_mode == "dry_run":
        llm_response = ""
        fallback_used = True
        warnings.append("Dry-run profile: token estimate + assembled prompt only, no LLM call.")
        provider_status = {"provider": "none", "model": "", "configured": False, "mode": "dry_run"}
    else:
        _apply_benchmark_limits(profile, tprofile)
        try:
            from ecs_platform.llm_engine import LLMError, get_provider

            provider = get_provider()
            provider_status = _provider_status(provider)
            if provider_model:
                # Non-invasive: record requested model; provider model stays config-driven.
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
            except Exception as exc:  # noqa: BLE001
                fallback_used = True
                warnings.append(f"LLM call failed ({type(exc).__name__}); returned deterministic result.")
                provider_status["error"] = type(exc).__name__
        except Exception as exc:  # noqa: BLE001 - provider import/config failure
            fallback_used = True
            provider_status = {"provider": "unknown", "configured": False, "error": type(exc).__name__}
            warnings.append("LLM provider not available; returned deterministic result.")

    latency_ms = round((time.perf_counter() - started) * 1000, 1)

    # Fallback message when no LLM text was produced.
    if not llm_response and fallback_used and execution_mode != "dry_run":
        llm_response = (
            "[FALLBACK] The local LLM is unavailable, so only the deterministic ECS "
            "result is shown above. Start the local provider (see config/llm.yaml) "
            "to get an LLM-generated summary/analysis."
        )

    return {
        "query": user_query,
        "prompt_id": prompt_id,
        "query_type": effective_query_type,
        "classification": classification,
        "entities": entities,
        "deterministic_result": det,
        "assembled_prompt": assembled_prompt,
        "system_prompt": system_prompt,
        "llm_response": llm_response,
        "confidence": confidence,
        "assumptions": assumptions,
        "limitations": limitations,
        "source_references": ctx["source_references"],
        "rag_used": ctx["rag_used"],
        "token_estimate": token_estimate,
        "latency_ms": latency_ms,
        "provider_status": provider_status,
        "fallback_used": fallback_used,
        "ram_profile": ram_profile,
        "token_profile": tprofile,
        "execution_mode": execution_mode,
        "warnings": warnings,
    }
