"""Token estimation + RAM/token-profile compatibility for the audit LLM workbench.

Reuses the existing deterministic estimator
(``benchmarks.ai_workload.realistic_prompt_factory.estimate_tokens``,
chars/4) so estimates match the rest of ECS. Adds:
  * input/output/total token estimates for an assembled prompt,
  * whether a prompt fits a token profile's context budget, and
  * whether a token profile is allowed / restricted / blocked on a RAM profile.

Pure functions — no LLM call, no network. Safe on any machine (dry-run path).
"""

from __future__ import annotations

from typing import Any

from modules.audit_intelligence.llm import prompt_library as _lib

_DEFAULT_CHARS_PER_TOKEN = 4.0


def _chars_per_token() -> float:
    est = _lib.load_benchmark_profiles().get("token_estimation", {}) or {}
    try:
        cpt = float(est.get("chars_per_token", _DEFAULT_CHARS_PER_TOKEN))
        return cpt if cpt > 0 else _DEFAULT_CHARS_PER_TOKEN
    except (TypeError, ValueError):
        return _DEFAULT_CHARS_PER_TOKEN


def estimate_tokens(text: str, chars_per_token: float | None = None) -> int:
    """Deterministic token estimate (reuses the shared benchmark estimator)."""
    cpt = chars_per_token or _chars_per_token()
    try:
        from benchmarks.ai_workload.realistic_prompt_factory import estimate_tokens as _et

        return _et(text or "", chars_per_token=cpt)
    except Exception:  # noqa: BLE001 - fallback to inline formula if import unavailable
        if not text:
            return 0
        return int(round(len(text) / cpt))


def estimate_prompt(
    *,
    system_prompt: str = "",
    assembled_prompt: str = "",
    expected_output_tokens: int = 512,
    token_profile: str = "medium_8k",
    ram_profile: str = "local_16gb_safe",
) -> dict[str, Any]:
    """Full token estimate + profile-compatibility assessment for one prompt.

    Returns input/output/total token estimates, the target context budget, whether
    it fits, and RAM-profile compatibility + warnings. Never raises.
    """
    input_tokens = estimate_tokens(system_prompt) + estimate_tokens(assembled_prompt)
    try:
        output_tokens = max(0, int(expected_output_tokens))
    except (TypeError, ValueError):
        output_tokens = 512
    total_tokens = input_tokens + output_tokens

    context_budget = _lib.token_profile_context(token_profile)
    fits_context = context_budget == 0 or input_tokens <= context_budget
    exceeds_by = max(0, input_tokens - context_budget) if context_budget else 0

    compat = ram_profile_compatibility(ram_profile, token_profile)
    warnings: list[str] = list(compat.get("warnings", []))
    if not fits_context and context_budget:
        warnings.append(
            f"Estimated input {input_tokens} tokens exceeds the {token_profile} "
            f"context budget ({context_budget}) by ~{exceeds_by} tokens."
        )

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "chars_per_token": _chars_per_token(),
        "token_profile": token_profile,
        "context_budget": context_budget,
        "fits_context": fits_context,
        "exceeds_context_by": exceeds_by,
        "ram_profile": ram_profile,
        "ram_profile_allowed": compat["allowed"],
        "ram_profile_restricted": compat["restricted"],
        "execution_mode": compat["execution_mode"],
        "warnings": warnings,
    }


def ram_profile_compatibility(ram_profile: str, token_profile: str) -> dict[str, Any]:
    """Is ``token_profile`` allowed / restricted / blocked on ``ram_profile``?

    Uses the benchmark-profile YAML (allowed/blocked/restricted token profiles and
    execution_mode). ``restricted`` means "supported but selected prompts only,
    concurrency 1" (e.g. 16K on 16 GB). Unknown profiles degrade to allowed=False.
    """
    prof = _lib.get_profile(ram_profile) or {}
    allowed_list = set(prof.get("allowed_token_profiles", []) or [])
    blocked_list = set(prof.get("blocked_token_profiles", []) or [])
    restricted_list = set(prof.get("restricted_token_profiles", []) or [])
    execution_mode = str(prof.get("execution_mode", "llm"))

    allowed = bool(prof) and token_profile in allowed_list and token_profile not in blocked_list
    restricted = token_profile in restricted_list
    warnings: list[str] = []
    if not prof:
        warnings.append(f"Unknown RAM profile '{ram_profile}'.")
    elif token_profile in blocked_list:
        warnings.append(
            f"Token profile '{token_profile}' is BLOCKED on '{ram_profile}' "
            f"(do not force this on this machine)."
        )
    elif token_profile not in allowed_list:
        warnings.append(
            f"Token profile '{token_profile}' is not in the allowed set for "
            f"'{ram_profile}'."
        )
    elif restricted:
        warnings.append(
            f"Token profile '{token_profile}' is RESTRICTED on '{ram_profile}': "
            f"selected prompts only, concurrency 1."
        )
    if prof.get("memory_warning"):
        warnings.append(str(prof["memory_warning"]).strip())

    return {
        "allowed": allowed,
        "restricted": restricted,
        "blocked": token_profile in blocked_list,
        "execution_mode": execution_mode,
        "warnings": warnings,
    }
