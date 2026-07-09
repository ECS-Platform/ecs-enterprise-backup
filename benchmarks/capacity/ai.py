"""AI / LLM throughput estimator for the ECS infrastructure benchmark (PART 7).

Estimates prompts/sec, tokens/sec, embeddings/sec, concurrent prompt capacity,
context-window scaling impact, local Ollama RAM warnings, and remote Gemini
latency/cost assumptions — REUSING the existing token estimator and the profile's
prompt activity. No LLM call, no network.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from benchmarks.capacity.profiles import CapacityProfile


def _round(x: float, n: int = 3) -> float:
    return round(float(x), n)


@dataclass
class AiThroughputConstants:
    local_tokens_per_second: float = 40.0        # Qwen-8b-ish on 16-20GB laptop (planning)
    embedding_ms: float = 60.0                   # per query embedding (local)
    prompt_overhead_ms: float = 300.0            # assemble + retrieve (deterministic)
    concurrency_local_16gb: int = 1              # restricted on 16GB
    concurrency_local_20gb: int = 2
    concurrency_server_gpu: int = 8              # if run on a GPU RAG pool
    remote_gemini_latency_ms: float = 900.0
    remote_gemini_cost_per_1k_input: float = 0.0     # set from a real quote
    remote_gemini_cost_per_1k_output: float = 0.0
    ollama_min_ram_gib_16k: float = 16.0
    ollama_min_ram_gib_20k: float = 20.0
    working_hours_per_day: float = 9.0
    peak_to_average_factor: float = 3.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def ai_throughput(p: CapacityProfile, estimate: dict[str, Any] | None = None,
                  c: AiThroughputConstants | None = None) -> dict[str, Any]:
    """Prompts/tokens/embeddings per second + concurrency + model notes (PART 7)."""
    c = c or AiThroughputConstants()
    # Token cost per prompt: reuse the estimate's token_feed (from token_estimator).
    tokens = (estimate or {}).get("token_feed") or {}
    if not tokens:
        try:
            from benchmarks.capacity.sizing import _avg_prompt_tokens
            tokens = _avg_prompt_tokens(None)
        except Exception:  # noqa: BLE001
            tokens = {"input": 1500.0, "output": 512.0, "total": 2012.0}
    avg_output = float(tokens.get("output") or 512)
    avg_total = float(tokens.get("total") or 2012)

    # Per-prompt latency: overhead + output generation at local token rate.
    gen_ms = (avg_output / c.local_tokens_per_second) * 1000.0 if c.local_tokens_per_second else 0.0
    prompt_ms = c.prompt_overhead_ms + c.embedding_ms + gen_ms
    prompts_per_sec_single = (1000.0 / prompt_ms) if prompt_ms else 0.0
    tokens_per_sec = c.local_tokens_per_second
    embeddings_per_sec = (1000.0 / c.embedding_ms) if c.embedding_ms else 0.0

    # Demand vs capacity.
    work_seconds = c.working_hours_per_day * 3600.0
    peak_prompt_rps = (p.prompt_runs_per_day / work_seconds * c.peak_to_average_factor) if work_seconds else 0.0
    capacity_16 = prompts_per_sec_single * c.concurrency_local_16gb
    capacity_20 = prompts_per_sec_single * c.concurrency_local_20gb
    capacity_server = prompts_per_sec_single * c.concurrency_server_gpu

    return {
        "avg_tokens_per_prompt": _round(avg_total, 1),
        "prompts_per_second_single_stream": _round(prompts_per_sec_single, 3),
        "tokens_per_second_local": _round(tokens_per_sec, 1),
        "embeddings_per_second": _round(embeddings_per_sec, 1),
        "prompt_latency_ms_est": _round(prompt_ms, 1),
        "peak_prompt_rps_demand": _round(peak_prompt_rps, 3),
        "concurrent_capacity": {
            "local_16gb": {"concurrency": c.concurrency_local_16gb,
                           "prompts_per_sec": _round(capacity_16, 3),
                           "meets_demand": capacity_16 >= peak_prompt_rps},
            "local_20gb": {"concurrency": c.concurrency_local_20gb,
                           "prompts_per_sec": _round(capacity_20, 3),
                           "meets_demand": capacity_20 >= peak_prompt_rps},
            "server_gpu_pool": {"concurrency": c.concurrency_server_gpu,
                                "prompts_per_sec": _round(capacity_server, 3),
                                "meets_demand": capacity_server >= peak_prompt_rps},
        },
        "context_window_scaling": {
            "note": "Latency grows with prompt tokens; large contexts (16K/20K) reduce "
                    "throughput and raise RAM. 16GB restricts 20K prompts (concurrency 1).",
            "profiles": ["local_16gb_safe", "local_20gb_extended"],
        },
        "local_ollama_ram_warning": (
            f"16K context needs ~{c.ollama_min_ram_gib_16k} GiB and 20K ~{c.ollama_min_ram_gib_20k} GiB; "
            "run the RAG/LLM workload on a dedicated pool sized accordingly."),
        "remote_gemini_assumptions": {
            "latency_ms": c.remote_gemini_latency_ms,
            "cost_per_1k_input": c.remote_gemini_cost_per_1k_input,
            "cost_per_1k_output": c.remote_gemini_cost_per_1k_output,
            "note": "Remote frees local RAM but adds egress + per-token cost + data-residency "
                    "considerations; set rates from a real quote.",
        },
        "model_comparison_note": "Larger models raise quality + RAM + latency and lower "
                                 "throughput; benchmark per model with the audit-LLM runner "
                                 "(scripts/run_audit_llm_benchmark.py) before sizing.",
        "_basis": "Per-prompt latency = overhead + embedding + output/token-rate; capacity = "
                  "single-stream × concurrency by RAM profile. Tokens reuse the token estimator.",
    }
