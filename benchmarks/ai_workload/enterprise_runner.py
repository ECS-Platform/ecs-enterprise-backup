"""Enterprise AI workload benchmark runner for ECS (Neev capacity planning).

This is the integration layer that the rest of the enterprise benchmark already
expects: ``workload_profiles`` and ``reporting`` both reference it. It ties the
EXISTING pieces together and adds nothing that duplicates ECS logic:

    workload_profiles.default_profiles()      # realistic enterprise scenarios
        -> ecs_platform.rag.answer(...)        # EXISTING RAG pipeline + retrieval
            -> provider.generate_with_metadata # EXISTING provider instrumentation
        -> ecs_platform.llm_engine.metrics_logger.persist_rag_metric (EXISTING)
    bench_statistics.summarize(...)            # EXISTING stats (min..P99, stddev)
    capacity_planning.plan(...)                # EXISTING measured/estimated/projected
    reporting.build_report / write_report      # EXISTING aggregation + artifacts

Reuse > Extend > Measure. Never Replace / Duplicate / Rewrite.

Engineering properties
----------------------
* concurrency = 1 (single stream — the only mode the lightweight framework
  supports and the only mode capacity_planning's "estimated" basis assumes).
* Rate limited by ``max_requests_per_minute`` (token-bucket-free min-interval).
* Memory-safe for an 8 GB authoring box AND a 16 GB runner: each request is run,
  its slim metric row is flushed to disk immediately, then the large objects
  (answer text, citations) are released and ``gc.collect()`` is called. Prior
  results are NOT retained in memory — the final report is built by re-reading
  the flushed JSONL from disk.
* LLM-unavailable safe: if the provider is unreachable/unconfigured the RAG
  pipeline returns mode ``fallback``/``no_evidence``/``error``; the runner records
  the measured fields (from the persisted metric row), leaves token/LLM-latency
  fields at their measured values (0 when no model call happened), and continues.
* Graceful stop: on memory pressure or ``MemoryError`` the loop stops and a report
  is still produced from everything already flushed.

No ECS source, instrumentation, or existing benchmark module is modified.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from benchmarks.ai_workload import reporting, workload_profiles
from benchmarks.ai_workload.capacity_planning import CapacityAssumptions, WorstCaseAssumptions
from benchmarks.ai_workload.workload_profiles import WorkloadProfile

# Supported benchmark modes (configuration-driven; single execution path).
BENCHMARK_MODES = ("standard", "worst_case")

_REQUESTS_FILE = "enterprise_requests.jsonl"
_RUN_META_FILE = "enterprise_run_meta.json"
_RUN_LOG_FILE = "enterprise_run.log"


# --------------------------------------------------------------------------- #
# Configuration (extends the conventions of benchmark_runner.RunnerConfig).
# --------------------------------------------------------------------------- #
@dataclass
class EnterpriseRunnerConfig:
    role: str = "cio"
    user: str = "benchmark-runner"
    concurrency: int = 1                      # enforced == 1
    max_requests_per_minute: int = 3
    output_dir: str = "benchmarks/output"
    run_sync_once: bool = False              # ecs_platform.ingestion.sync_all
    reindex_before_run: bool = False         # ecs_platform.rag.reindex_evidence
    profile_keys: list[str] = field(default_factory=list)   # empty -> all profiles
    categories: list[str] = field(default_factory=list)     # empty -> all categories
    memory_guard_min_mb: int = 512           # 0 disables the soft memory guard
    capacity_assumptions: dict[str, Any] = field(default_factory=dict)
    # Configuration-driven mode (single execution path):
    #   "standard"   -> base enterprise catalog, standard report (default, unchanged).
    #   "worst_case" -> base catalog + worst-case tier, worst-case report sections.
    benchmark_mode: str = "standard"
    # Operator-tunable worst-case scaling / growth inputs (capacity_planning.
    # WorstCaseAssumptions). Empty -> documented defaults. Only used in worst_case mode.
    worst_case_assumptions: dict[str, Any] = field(default_factory=dict)
    # Additive, backward-compatible hook: extra WorkloadProfile objects to run in
    # addition to the base catalog. Empty -> behaviour unchanged. (worst_case mode
    # injects workload_profiles.worst_case_profiles() automatically.)
    extra_profiles: list[Any] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "EnterpriseRunnerConfig":
        data = data or {}
        mode = str(data.get("benchmark_mode", "standard")).strip().lower() or "standard"
        if mode not in BENCHMARK_MODES:
            raise ValueError(f"benchmark_mode must be one of {BENCHMARK_MODES}, got {mode!r}.")
        return cls(
            role=str(data.get("role", "cio")),
            user=str(data.get("user", "benchmark-runner")),
            concurrency=int(data.get("concurrency", 1)),
            max_requests_per_minute=int(data.get("max_requests_per_minute", 3)),
            output_dir=str(data.get("output_dir", "benchmarks/output")),
            run_sync_once=bool(data.get("run_sync_once", False)),
            reindex_before_run=bool(data.get("reindex_before_run", False)),
            profile_keys=list(data.get("profile_keys", []) or []),
            categories=list(data.get("categories", []) or []),
            memory_guard_min_mb=int(data.get("memory_guard_min_mb", 512)),
            capacity_assumptions=dict(data.get("capacity_assumptions", {}) or {}),
            benchmark_mode=mode,
            worst_case_assumptions=dict(data.get("worst_case_assumptions", {}) or {}),
        )

    @property
    def is_worst_case(self) -> bool:
        return self.benchmark_mode == "worst_case"


# --------------------------------------------------------------------------- #
# Small helpers (stdlib only).
# --------------------------------------------------------------------------- #
def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dir(path: str) -> Path:
    out = Path(path)
    out.mkdir(parents=True, exist_ok=True)
    return out


def _flush_jsonl(path: Path, row: dict[str, Any]) -> None:
    """Append one row and fsync so a crash/OOM never loses completed work."""
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def _log(log_path: Path, message: str) -> None:
    line = f"[{_utc_now()}] {message}"
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
        fh.flush()
    print(line)


def _available_mb() -> float | None:
    """Best-effort available-memory probe. Returns None if it cannot be measured.

    Uses psutil when present; otherwise tries the Linux /proc and macOS vm_stat
    paths. Never raises — memory guarding is advisory.
    """
    try:
        import psutil  # type: ignore

        return psutil.virtual_memory().available / (1024 * 1024)
    except Exception:  # noqa: BLE001
        pass
    try:  # Linux
        with open("/proc/meminfo", "r", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) / 1024.0
    except Exception:  # noqa: BLE001
        pass
    return None


def _select_profiles(config: EnterpriseRunnerConfig,
                     extra_profiles: list[WorkloadProfile] | None = None) -> list[WorkloadProfile]:
    """Resolve the profiles to run.

    ``extra_profiles`` is an OPTIONAL additive catalog (e.g. the worst-case
    profiles) appended to the base catalog before key/category filtering. When it
    is None the behavior is identical to before (full backward compatibility).
    """
    catalog = list(workload_profiles.default_profiles())
    if extra_profiles:
        # Append any profiles whose keys are not already in the base catalog.
        seen = {p.key for p in catalog}
        catalog.extend(p for p in extra_profiles if p.key not in seen)

    if config.profile_keys:
        wanted_keys = set(config.profile_keys)
        profiles = [p for p in catalog if p.key in wanted_keys]
    else:
        profiles = catalog

    if config.categories:
        wanted = set(config.categories)
        profiles = [p for p in profiles if p.category in wanted]
    return profiles


def _persisted_metric(out_dir: Path, request_id: str) -> dict[str, Any]:
    """Recover the full measured metric row for a request from the EXISTING
    instrumentation output (``rag_metrics.jsonl``).

    ``answer()`` only embeds a ``metrics`` dict on the grounded success path, but
    it persists a full row in EVERY branch (success / fallback / no_evidence /
    error). Reading it back lets the runner capture measured fields even when the
    LLM is unavailable — without changing instrumentation.
    """
    path = out_dir / "rag_metrics.jsonl"
    if not request_id or not path.is_file():
        return {}
    found: dict[str, Any] = {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:  # scan forward; keep the last match (newest write)
                line = line.strip()
                if not line or request_id not in line:
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if row.get("request_id") == request_id:
                    found = row
    except OSError:
        return {}
    return found


# Measured fields produced by the existing instrumentation (see rag.answer()).
_METRIC_FIELDS = (
    "retrieved_documents",
    "retrieved_chunks",
    "prompt_size_chars",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "retrieval_latency_ms",
    "prompt_build_latency_ms",
    "llm_latency_ms",
    "end_to_end_latency_ms",
)


def _build_row(profile: WorkloadProfile, res: dict[str, Any],
               metrics: dict[str, Any], system_prompt: str,
               runner_ms: int) -> dict[str, Any]:
    """Assemble the flat per-request row consumed by ``reporting``."""
    # MEASURED — benchmark-known prompt inputs (no instrumentation change needed).
    system_chars = len(system_prompt or "")
    user_chars = len(profile.question or "")
    system_bytes = len((system_prompt or "").encode("utf-8"))
    user_bytes = len((profile.question or "").encode("utf-8"))

    prompt_size_chars = metrics.get("prompt_size_chars")
    # DERIVED — clearly suffixed so provenance is never ambiguous.
    if isinstance(prompt_size_chars, (int, float)):
        context_chars_derived = max(0, int(prompt_size_chars) - user_chars)
        prompt_bytes_derived = int(prompt_size_chars)  # ASCII approx (see reporting notes)
    else:
        context_chars_derived = None
        prompt_bytes_derived = None

    row: dict[str, Any] = {
        "timestamp": _utc_now(),
        # profile identity
        "profile_key": profile.key,
        "workload": profile.name,
        "category": profile.category,
        "prompt_class": profile.prompt_class,
        "response_intent": profile.response_intent,
        "top_k": profile.top_k,
        # request outcome
        "ok": bool(res.get("ok")),
        "grounded": bool(res.get("grounded")),
        "mode": res.get("mode", ""),
        "provider": res.get("provider", "") or metrics.get("provider", ""),
        "model": res.get("model", "") or metrics.get("model_name", ""),
        "request_id": res.get("request_id", ""),
        "error": res.get("answer", "") if res.get("mode") == "error" else "",
        # MEASURED — benchmark inputs
        "system_prompt_chars": system_chars,
        "system_prompt_bytes": system_bytes,
        "user_prompt_chars": user_chars,
        "user_prompt_bytes": user_bytes,
        # DERIVED
        "retrieved_context_chars_derived": context_chars_derived,
        "prompt_bytes_derived": prompt_bytes_derived,
        "runner_end_to_end_ms": runner_ms,
    }
    # MEASURED — from existing instrumentation (metrics dict / persisted row).
    for f in _METRIC_FIELDS:
        row[f] = metrics.get(f)
    return row


# --------------------------------------------------------------------------- #
# Runner.
# --------------------------------------------------------------------------- #
def run(config: EnterpriseRunnerConfig,
        extra_profiles: list[WorkloadProfile] | None = None) -> dict[str, str]:
    """Execute the enterprise workload benchmark. Returns written artifact paths.

    Pure orchestration over existing ECS components. Never raises for a single
    failed request; a hard memory condition stops the loop gracefully and a report
    is still produced from already-flushed rows.

    ``extra_profiles`` is an OPTIONAL additive catalog (e.g. the worst-case
    profiles). Omitting it preserves the original behavior exactly.
    """
    if config.concurrency != 1:
        raise ValueError("enterprise_runner supports only concurrency=1 (single-stream).")
    if config.max_requests_per_minute <= 0:
        raise ValueError("max_requests_per_minute must be > 0.")

    out_dir = _ensure_dir(config.output_dir)
    # Route the EXISTING instrumentation's persistence to our output directory.
    os.environ["ECS_BENCHMARK_DIR"] = str(out_dir)

    requests_path = out_dir / _REQUESTS_FILE
    log_path = out_dir / _RUN_LOG_FILE
    # Fresh run: start a clean requests file (report is rebuilt from it).
    requests_path.write_text("", encoding="utf-8")
    log_path.write_text("", encoding="utf-8")

    # Configuration-driven mode: worst_case injects the worst-case workload tier so
    # the SAME single execution path measures the heaviest realistic scenarios.
    mode_extra: list[WorkloadProfile] = []
    if config.is_worst_case:
        mode_extra = list(workload_profiles.worst_case_profiles())
    # Forward the mode tier + explicit argument + any config-provided extra_profiles
    # (additive, backward compatible: None/empty -> identical to prior behaviour).
    effective_extra = (mode_extra
                       + list(extra_profiles or [])
                       + list(getattr(config, "extra_profiles", []) or []))
    profiles = _select_profiles(config, effective_extra or None)
    _log(log_path, f"enterprise benchmark start: mode={config.benchmark_mode}, "
                   f"{len(profiles)} profiles, concurrency=1, "
                   f"max_rpm={config.max_requests_per_minute}, out={out_dir}")

    # Optional one-time data preparation (reuse existing flows).
    if config.run_sync_once:
        from ecs_platform.ingestion import sync_all

        _log(log_path, "run_sync_once=true -> ecs_platform.ingestion.sync_all(index=True)")
        sync_all(actor=config.user, role=config.role, index=True)
    if config.reindex_before_run:
        from ecs_platform.rag import reindex_evidence

        _log(log_path, "reindex_before_run=true -> ecs_platform.rag.reindex_evidence()")
        report = reindex_evidence()
        (out_dir / "reindex_report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")

    # Resolve the EXISTING RAG entry point + system prompt (read-only use).
    from ecs_platform.rag import answer
    try:
        from ecs_platform.llm_engine.prompt_builder import SYSTEM_PROMPT
    except Exception:  # noqa: BLE001 - never block the run on a prompt import
        SYSTEM_PROMPT = ""

    min_interval = 60.0 / float(config.max_requests_per_minute)
    last_started = 0.0
    completed = 0
    stopped_reason = "completed"

    for idx, profile in enumerate(profiles):
        # --- soft memory guard (advisory; results are already durable) ---
        if config.memory_guard_min_mb > 0:
            avail = _available_mb()
            if avail is not None and avail < config.memory_guard_min_mb:
                stopped_reason = f"memory_pressure (<{config.memory_guard_min_mb}MB available)"
                _log(log_path, f"GRACEFUL STOP before '{profile.name}': {stopped_reason}; "
                               f"{completed} requests already flushed.")
                break

        # --- rate limit (single stream) ---
        now = time.perf_counter()
        if last_started and (now - last_started) < min_interval:
            time.sleep(min_interval - (now - last_started))
        last_started = time.perf_counter()

        _log(log_path, f"req#{idx} START '{profile.name}' (top_k={profile.top_k}, "
                       f"class={profile.prompt_class}->{profile.response_intent})")
        t0 = time.perf_counter()
        try:
            res = answer(profile.question, role=config.role, user=config.user, top_k=profile.top_k)
        except MemoryError:
            stopped_reason = "MemoryError during request"
            _log(log_path, f"GRACEFUL STOP: MemoryError on '{profile.name}'; "
                           f"{completed} requests already flushed.")
            break
        except Exception as exc:  # noqa: BLE001 - capture, never abort the suite
            res = {"ok": False, "grounded": False, "mode": "error",
                   "answer": f"runner-caught error: {exc}", "request_id": ""}
        runner_ms = int((time.perf_counter() - t0) * 1000)

        # MEASURED metrics: prefer the embedded dict; otherwise recover the
        # persisted instrumentation row (covers fallback/no_evidence/error).
        metrics = res.get("metrics") or _persisted_metric(out_dir, res.get("request_id", ""))

        row = _build_row(profile, res, metrics, SYSTEM_PROMPT, runner_ms)
        _flush_jsonl(requests_path, row)
        completed += 1
        _log(log_path, f"req#{idx} DONE ok={row['ok']} mode={row['mode']} "
                       f"provider={row['provider'] or 'n/a'} model={row['model'] or 'n/a'} "
                       f"docs={row['retrieved_documents']} in_tok={row['input_tokens']} "
                       f"out_tok={row['output_tokens']} total_tok={row['total_tokens']} "
                       f"e2e_ms={row['end_to_end_latency_ms']}")

        # --- release temporary objects; do not retain results in memory ---
        del res, metrics, row
        gc.collect()

    # --- build report from disk (no in-memory retention of prior results) ---
    # Single reporting framework: in worst_case mode the SAME build_report appends
    # the worst-case capacity sections + executive summary (Measured / Worst-Case /
    # Projected / Forecast kept strictly separate). Standard mode is unchanged.
    rows = _read_rows(requests_path)
    assumptions = CapacityAssumptions.from_dict(config.capacity_assumptions)
    wc_assumptions = (WorstCaseAssumptions.from_dict(config.worst_case_assumptions)
                      if config.is_worst_case else None)
    report = reporting.build_report(
        rows, assumptions,
        include_worst_case=config.is_worst_case,
        worst_case_assumptions=wc_assumptions,
    )
    report["meta"]["run_status"] = stopped_reason
    report["meta"]["profiles_planned"] = len(profiles)
    report["meta"]["profiles_completed"] = completed
    paths = reporting.write_report(report, rows, out_dir)

    run_meta = {
        "generated_at": _utc_now(),
        "run_status": stopped_reason,
        "profiles_planned": len(profiles),
        "profiles_completed": completed,
        "benchmark_mode": config.benchmark_mode,
        "config": {
            "role": config.role, "user": config.user,
            "benchmark_mode": config.benchmark_mode,
            "max_requests_per_minute": config.max_requests_per_minute,
            "profile_keys": config.profile_keys, "categories": config.categories,
            "run_sync_once": config.run_sync_once, "reindex_before_run": config.reindex_before_run,
            "memory_guard_min_mb": config.memory_guard_min_mb,
            "worst_case_assumptions": config.worst_case_assumptions if config.is_worst_case else {},
        },
        "artifacts": {**paths, "requests_jsonl": str(requests_path),
                      "rag_metrics_jsonl": str(out_dir / "rag_metrics.jsonl")},
    }
    (out_dir / _RUN_META_FILE).write_text(json.dumps(run_meta, indent=2, ensure_ascii=True),
                                          encoding="utf-8")
    _log(log_path, f"enterprise benchmark {stopped_reason}: {completed}/{len(profiles)} "
                   f"requests; report={paths.get('report')}")
    return {**paths, "run_meta": str(out_dir / _RUN_META_FILE), "log": str(log_path)}


def _read_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    return rows


# --------------------------------------------------------------------------- #
# CLI.
# --------------------------------------------------------------------------- #
def _load_config(path: Path | None) -> EnterpriseRunnerConfig:
    if path is None:
        return EnterpriseRunnerConfig()
    with path.open("r", encoding="utf-8") as fh:
        return EnterpriseRunnerConfig.from_dict(json.load(fh))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the ECS enterprise AI workload benchmark (reuses existing ECS).")
    parser.add_argument("--config", type=str, default="",
                        help="Optional JSON config path "
                             "(default: benchmarks/config/enterprise_workload_config.json if present).")
    parser.add_argument("--profiles", type=str, default="",
                        help="Comma-separated profile keys to run (overrides config).")
    parser.add_argument("--categories", type=str, default="",
                        help="Comma-separated categories to run (overrides config).")
    parser.add_argument("--max-rpm", type=int, default=0,
                        help="Override max_requests_per_minute (>0).")
    parser.add_argument("--mode", type=str, default="", choices=["", *BENCHMARK_MODES],
                        help="Benchmark mode (overrides config): standard | worst_case.")
    parser.add_argument("--list", action="store_true",
                        help="List the full workload catalog (default + worst-case) and exit.")
    args = parser.parse_args(argv)

    if args.list:
        for p in workload_profiles.all_profiles():
            print(f"{p.key:22s} {p.category:18s} {p.prompt_class:6s}->{p.response_intent:8s} "
                  f"top_k={p.top_k:<3d} {p.name}")
        return 0

    cfg_path: Path | None = None
    if args.config:
        cfg_path = Path(args.config)
    else:
        default_cfg = Path("benchmarks/config/enterprise_workload_config.json")
        cfg_path = default_cfg if default_cfg.is_file() else None

    config = _load_config(cfg_path)
    if args.profiles:
        config.profile_keys = [k.strip() for k in args.profiles.split(",") if k.strip()]
    if args.categories:
        config.categories = [c.strip() for c in args.categories.split(",") if c.strip()]
    if args.max_rpm and args.max_rpm > 0:
        config.max_requests_per_minute = args.max_rpm
    if args.mode:
        config.benchmark_mode = args.mode

    run(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
