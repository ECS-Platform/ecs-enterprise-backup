"""Audit LLM prompt-library loader + validation.

Loads ``config/audit_llm_prompt_library.yaml`` into validated, JSON-safe prompt
definitions and ``config/audit_llm_benchmark_profiles.yaml`` into benchmark
profiles + token profiles. Pure data access — no LLM calls, no DB, no network.

Validation is intentionally strict-but-safe: a malformed entry is skipped with a
recorded error (never crashes the app), and the loader caches results in-process.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PROMPT_YAML = _REPO_ROOT / "config" / "audit_llm_prompt_library.yaml"
_PROFILE_YAML = _REPO_ROOT / "config" / "audit_llm_benchmark_profiles.yaml"

#: Fields every prompt definition must carry.
REQUIRED_FIELDS: tuple[str, ...] = (
    "prompt_id", "category", "name", "description", "query_type", "persona",
    "input_variables", "required_context", "system_prompt", "user_prompt_template",
    "expected_output_format", "confidence_policy", "citation_policy", "risk_level",
    "token_profile", "applicable_frameworks", "applicable_roles",
    "recommended_model_size", "local_16gb_supported", "local_20gb_supported",
)

VALID_QUERY_TYPES: frozenset[str] = frozenset({"deterministic", "llm_assisted", "hybrid"})
VALID_TOKEN_PROFILES: frozenset[str] = frozenset({
    "small_4k", "medium_8k", "large_16k", "extended_20k", "worst_case_enterprise_dry_run",
})

_LOCK = threading.RLock()
_CACHE: dict[str, Any] = {}


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        import yaml

        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except Exception:  # noqa: BLE001 - malformed YAML -> empty (never crash)
        return {}
    return data if isinstance(data, dict) else {}


def _validate_prompt(entry: dict[str, Any]) -> list[str]:
    """Return a list of validation errors for one prompt entry ([] == valid)."""
    errs: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in entry:
            errs.append(f"missing field '{field}'")
    qt = entry.get("query_type")
    if qt is not None and qt not in VALID_QUERY_TYPES:
        errs.append(f"invalid query_type '{qt}'")
    tp = entry.get("token_profile")
    if tp is not None and tp not in VALID_TOKEN_PROFILES:
        errs.append(f"invalid token_profile '{tp}'")
    if not isinstance(entry.get("input_variables", []), list):
        errs.append("input_variables must be a list")
    if not isinstance(entry.get("required_context", []), list):
        errs.append("required_context must be a list")
    return errs


def load_prompt_library(*, force: bool = False) -> dict[str, Any]:
    """Load + validate the prompt library. Returns a report with valid prompts.

    Report: ``{"prompts": {id: def}, "order": [ids], "errors": {id: [..]},
    "count": int, "defaults": {...}}``.
    """
    with _LOCK:
        if _CACHE.get("library") is not None and not force:
            return _CACHE["library"]

        raw = _read_yaml(_PROMPT_YAML)
        defaults = raw.get("defaults", {}) or {}
        prompts: dict[str, Any] = {}
        order: list[str] = []
        errors: dict[str, list[str]] = {}

        for entry in raw.get("prompts", []) or []:
            if not isinstance(entry, dict):
                continue
            pid = str(entry.get("prompt_id") or "").strip()
            errs = _validate_prompt(entry)
            if not pid:
                errors.setdefault("<no id>", []).extend(errs or ["missing prompt_id"])
                continue
            if pid in prompts:
                errors.setdefault(pid, []).append("duplicate prompt_id (skipped)")
                continue
            if errs:
                errors[pid] = errs
                # Still register if the core identity fields are present, so the UI
                # can show it; execution paths re-check required fields.
                if any(e.startswith("missing field") for e in errs):
                    continue
            merged = {**{k: defaults.get(k) for k in defaults}, **entry}
            prompts[pid] = merged
            order.append(pid)

        library = {
            "prompts": prompts,
            "order": order,
            "errors": errors,
            "count": len(prompts),
            "defaults": defaults,
            "source": str(_PROMPT_YAML),
        }
        _CACHE["library"] = library
        return library


def load_benchmark_profiles(*, force: bool = False) -> dict[str, Any]:
    """Load benchmark profiles + token profiles + estimation config."""
    with _LOCK:
        if _CACHE.get("profiles") is not None and not force:
            return _CACHE["profiles"]
        raw = _read_yaml(_PROFILE_YAML)
        out = {
            "profiles": raw.get("profiles", {}) or {},
            "token_profiles": raw.get("token_profiles", {}) or {},
            "token_estimation": raw.get("token_estimation", {}) or {},
            "source": str(_PROFILE_YAML),
        }
        _CACHE["profiles"] = out
        return out


def reset_cache() -> None:
    """Clear the in-process cache (tests / after editing the YAML)."""
    with _LOCK:
        _CACHE.clear()


# --------------------------------------------------------------------------- #
# Lookups
# --------------------------------------------------------------------------- #
def list_prompts(*, category: str = "", query_type: str = "",
                 ram_profile: str = "") -> list[dict[str, Any]]:
    """Prompt definitions, optionally filtered by category/query_type/ram support."""
    lib = load_prompt_library()
    out: list[dict[str, Any]] = []
    for pid in lib["order"]:
        p = lib["prompts"][pid]
        if category and p.get("category") != category:
            continue
        if query_type and p.get("query_type") != query_type:
            continue
        if ram_profile == "local_16gb_safe" and not p.get("local_16gb_supported", True):
            continue
        if ram_profile == "local_20gb_extended" and not p.get("local_20gb_supported", True):
            continue
        out.append(p)
    return out


def get_prompt(prompt_id: str) -> dict[str, Any] | None:
    return load_prompt_library()["prompts"].get((prompt_id or "").strip())


def categories() -> list[str]:
    lib = load_prompt_library()
    return sorted({p.get("category", "") for p in lib["prompts"].values() if p.get("category")})


def get_profile(name: str) -> dict[str, Any] | None:
    return load_benchmark_profiles()["profiles"].get((name or "").strip())


def list_profiles() -> list[dict[str, Any]]:
    profs = load_benchmark_profiles()["profiles"]
    return [{"id": k, **(v or {})} for k, v in profs.items()]


def token_profile_context(token_profile: str) -> int:
    """Context-token budget for a named token profile (0 if unknown)."""
    tp = load_benchmark_profiles()["token_profiles"].get((token_profile or "").strip(), {})
    try:
        return int(tp.get("context_tokens", 0) or 0)
    except (TypeError, ValueError):
        return 0
