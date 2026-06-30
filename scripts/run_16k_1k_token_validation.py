"""ECS 16K-input / 1K-output local Ollama token-validation benchmark (wrapper).

PURPOSE
-------
A lightweight, SAFE, ADDITIVE wrapper around the existing Neev validation benchmark
(``scripts/run_neev_validation_benchmark.py``) so that two separate 16 GB RAM machines
can check out this branch and run the SAME controlled benchmark:

* one controlled profile (the existing ``full`` scenario),
* ``num_ctx = 16384`` (validate local 16K context-window behaviour),
* ``max_output_tokens = 1024`` (attempt ~1K output generation),
* ``timeout_seconds = 600``, timeout-evidence allowed.

WHY ``full`` / WHY 16K
----------------------
The ``full`` scenario builds a prompt larger than the 16K context window
(~102K chars / ~25.6K estimated input tokens). With ``num_ctx=16384`` the local model
evaluates up to the context window, so the MEASURED input (Ollama ``prompt_eval_count``)
lands around 16K — which is exactly the local 16K context behaviour we want to validate.
This wrapper does NOT create a new prompt framework; it reuses the existing profile.

SCOPE / GUARDRAILS
------------------
* Local Ollama token measurement ONLY. No Docker, no PGVector, no embeddings, no live
  RAG, no physical files. (The underlying Neev benchmark is a prompt-construction +
  LLM-token-measurement benchmark; this wrapper changes none of that logic.)
* Reuses the existing runner functions; it does not modify benchmark logic.
* Runs exactly ONE scenario, never loops, and exits after a single run.
* Writes the normal benchmark artifacts under ``benchmark_outputs/`` AND appends to two
  cumulative history files (never overwriting them):
    - ``benchmark_outputs/16k_1k_validation_history.md``  (timestamped section per run)
    - ``benchmark_outputs/16k_1k_validation_history.csv`` (one row per run)

RUN (16 GB machine, Git Bash)::

    ECS_LLM_PROVIDER=ollama \\
    OLLAMA_URL=http://localhost:11434 \\
    OLLAMA_MODEL=qwen3:8b \\
    PYTHONPATH=. \\
    python -m scripts.run_16k_1k_token_validation

RUN (16 GB machine, Windows CMD)::

    set PYTHONPATH=.
    set ECS_LLM_PROVIDER=ollama
    set OLLAMA_URL=http://localhost:11434
    set OLLAMA_MODEL=qwen3:8b
    python -m scripts.run_16k_1k_token_validation
"""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

# Reuse the EXISTING Neev benchmark runner — no benchmark logic is reimplemented here.
from benchmarks.ai_workload.neev_capacity_projection import NeevAssumptions
from scripts import run_neev_validation_benchmark as neev

# Controlled, safe defaults for the 16 GB local Ollama validation.
SCENARIO_KEY = "full"            # existing profile that exceeds the 16K context window
DEFAULT_NUM_CTX = 16384
DEFAULT_MAX_OUTPUT_TOKENS = 1024
DEFAULT_TIMEOUT_SECONDS = 600

_HISTORY_MD = "16k_1k_validation_history.md"
_HISTORY_CSV = "16k_1k_validation_history.csv"

_HISTORY_CSV_COLUMNS = [
    "timestamp",
    "git_commit",
    "scenario",
    "command",
    "provider",
    "model",
    "num_ctx_requested",
    "max_output_tokens",
    "timeout_seconds",
    "prompt_file",
    "prompt_characters",
    "estimated_input_tokens",
    "measured_input_tokens",
    "measured_output_tokens",
    "measured_total_tokens",
    "status",
    "truncation_suspected",
    "error_message",
]


def _git_commit() -> str:
    """Best-effort short commit hash; never raises (returns 'unknown')."""
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or "unknown"
    except Exception:  # noqa: BLE001 - reporting metadata only
        return "unknown"


def _command_string() -> str:
    """Reconstruct the executed command for the audit log (no secrets involved)."""
    return "python -m scripts.run_16k_1k_token_validation " + " ".join(sys.argv[1:])


def _output_cell(value: Any) -> Any:
    return "" if value is None else value


def _interpret_output(record: dict[str, Any], max_output_tokens: int) -> str:
    """Plain-language interpretation of the measured output vs the configured cap."""
    status = record.get("status")
    if status != neev.STATUS_MEASURED:
        if status == neev.STATUS_TIMEOUT:
            return ("LLM call timed out — 1K output was NOT measured (local runtime "
                    "limitation, not an ECS architecture failure).")
        if status == neev.STATUS_ERROR:
            return ("LLM call errored — 1K output was NOT measured. See error message.")
        return ("LLM call was skipped (dry run / no provider) — output NOT measured.")
    out = int(record.get("measured_output_tokens") or 0)
    # "near the cap" => within 5% of the configured max.
    if out >= max_output_tokens * 0.95:
        return (f"The model generated {out:,} output tokens — close to the configured "
                f"{max_output_tokens:,} output cap (generation was cap-bound).")
    return (f"The model generated {out:,} output tokens — below the configured "
            f"{max_output_tokens:,} cap (the model completed before reaching the cap).")


def _interpret_input(record: dict[str, Any], num_ctx: int) -> str:
    """Plain-language interpretation of the measured input vs the 16K context window."""
    if record.get("status") != neev.STATUS_MEASURED:
        est = int(record.get("estimated_input_tokens") or 0)
        return (f"Input tokens were NOT measured this run; ESTIMATED constructed prompt "
                f"size is {est:,} tokens.")
    meas = int(record.get("measured_input_tokens") or 0)
    est = int(record.get("estimated_input_tokens") or 0)
    note = (f"MEASURED input = {meas:,} tokens (Ollama prompt_eval_count); ESTIMATED "
            f"constructed prompt = {est:,} tokens.")
    if record.get("truncation_suspected"):
        note += (f" Truncation suspected: the constructed prompt exceeded the "
                 f"num_ctx={num_ctx:,} window, so MEASURED input reflects the "
                 f"context-window-limited evaluation (validates 16K context behaviour).")
    return note


def _append_history_md(path: Path, record: dict[str, Any], *, timestamp: str,
                       git_commit: str, command: str, provider: str, model: str,
                       num_ctx: int, max_output_tokens: int,
                       timeout_seconds: int) -> None:
    """Append a timestamped section. Creates the file with a title if missing; never
    overwrites prior content (append-only)."""
    new_file = not path.exists()
    lines: list[str] = []
    if new_file:
        lines += [
            "# ECS 16K-input / 1K-output Local Ollama Token Validation — History", "",
            "Cumulative log. Each run appends a new timestamped section below; prior "
            "sections are preserved.", "",
            "Interpretation reminders:", "",
            "- **MEASURED input** = Ollama `prompt_eval_count` (real, model-reported).",
            "- **MEASURED output** = Ollama `eval_count` (real, model-reported).",
            "- Output near the cap means generation was cap-bound; much lower means the "
            "model completed early.",
            "- A timeout/error means 1K output was NOT measured.", "",
            "---", "",
        ]
    fmt = neev._fmt  # reuse the existing number formatter
    lines += [
        f"## Run @ {timestamp}", "",
        f"- Git commit: `{git_commit}`",
        f"- Command: `{command}`",
        f"- Scenario: `{record.get('scenario_key', SCENARIO_KEY)}` "
        f"({record.get('scenario_name', '')})",
        f"- Provider / model: `{provider}` / `{model}`",
        f"- num_ctx requested: **{num_ctx:,}**; max_output_tokens: **{max_output_tokens:,}**; "
        f"timeout_seconds: **{timeout_seconds}**",
        f"- Prompt file: `{record.get('prompt_file', '')}`",
        f"- Prompt characters: **{fmt(record.get('prompt_chars'))}**",
        f"- Estimated input tokens (ESTIMATED): **{fmt(record.get('estimated_input_tokens'))}**",
        f"- Measured input tokens (MEASURED): **{fmt(record.get('measured_input_tokens'))}**",
        f"- Measured output tokens (MEASURED): **{fmt(record.get('measured_output_tokens'))}**",
        f"- Measured total tokens (MEASURED): **{fmt(record.get('measured_total_tokens'))}**",
        f"- Status: **{record.get('status', '')}**; truncation_suspected: "
        f"**{record.get('truncation_suspected', False)}**",
    ]
    if record.get("error_message"):
        lines.append(f"- Error: {record.get('error_message')}")
    lines += [
        "",
        "Interpretation:", "",
        f"- {_interpret_input(record, num_ctx)}",
        f"- {_interpret_output(record, max_output_tokens)}",
        "",
        "---", "",
    ]
    with path.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def _append_history_csv(path: Path, row: dict[str, Any]) -> None:
    """Append one row. Writes a header only when creating the file (append-only)."""
    new_file = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=_HISTORY_CSV_COLUMNS, extrasaction="ignore")
        if new_file:
            w.writeheader()
        w.writerow({k: _output_cell(row.get(k)) for k in _HISTORY_CSV_COLUMNS})


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Run a single controlled 16K-input / 1K-output local Ollama token "
                    "validation (reuses the existing Neev benchmark; one run, no loops).")
    p.add_argument("--num-ctx", type=int, default=DEFAULT_NUM_CTX,
                   help=f"Ollama context window (default {DEFAULT_NUM_CTX}).")
    p.add_argument("--max-output-tokens", type=int, default=DEFAULT_MAX_OUTPUT_TOKENS,
                   help=f"Output-token cap (default {DEFAULT_MAX_OUTPUT_TOKENS}).")
    p.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS,
                   help=f"HTTP/model timeout seconds (default {DEFAULT_TIMEOUT_SECONDS}).")
    p.add_argument("--output-dir", type=str, default="benchmark_outputs",
                   help="Directory for benchmark artifacts (default: benchmark_outputs).")
    p.add_argument("--seed", type=int, default=1234, help="Deterministic prompt seed.")
    p.add_argument("--chars-per-token", type=float, default=4.0,
                   help="Chars/token basis for ESTIMATED input tokens (planning estimate).")
    p.add_argument("--dry-run", action="store_true",
                   help="Build + capture the prompt and ESTIMATE input tokens; skip the "
                        "LLM call (safe on machines without Ollama).")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # Default to local Ollama unless the operator already set a provider/URL. This only
    # sets process env defaults for THIS run; it does not change repo configuration.
    os.environ.setdefault("ECS_LLM_PROVIDER", "ollama")
    os.environ.setdefault("OLLAMA_URL", "http://localhost:11434")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    prompts_dir = out_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    timestamp = neev._utc_now()
    git_commit = _git_commit()
    command = _command_string()

    # Resolve exactly ONE scenario (the existing `full` profile). No new prompt framework.
    scenarios = neev.select_profiles([SCENARIO_KEY])
    if not scenarios:
        print(f"ERROR: scenario {SCENARIO_KEY!r} not found in the Neev profile catalog.",
              file=sys.stderr)
        return 2
    scenario = scenarios[0]

    provider: Any | None = None
    engine_runtime, model_name = "dry-run", ""
    effective_num_ctx: int | None = None
    if not args.dry_run:
        try:
            provider, engine_runtime, model_name, effective_num_ctx = neev._resolve_provider(
                args.max_output_tokens, args.timeout_seconds, args.num_ctx)
        except Exception as exc:  # noqa: BLE001 - clear message, no traceback dump
            print(f"ERROR: could not initialize the local Ollama provider: {exc}\n"
                  f"Hint: start Ollama (e.g. `ollama serve`) and pull the model "
                  f"(`ollama pull {os.environ.get('OLLAMA_MODEL', 'qwen3:8b')}`), or use "
                  f"--dry-run to only build/capture the prompt.", file=sys.stderr)
            return 2

    mode = "DRY RUN" if args.dry_run else f"FULL RUN ({engine_runtime})"
    print(f"[16k-1k-validation] {mode}: scenario=`{scenario.key}` "
          f"num_ctx={args.num_ctx} max_output_tokens={args.max_output_tokens} "
          f"timeout_seconds={args.timeout_seconds}")
    if not args.dry_run:
        ctx_note = (f"effective_num_ctx={effective_num_ctx}" if effective_num_ctx
                    else "effective_num_ctx=model_default (provider omits num_ctx)")
        print(f"[16k-1k-validation] provider={engine_runtime} model={model_name} "
              f"{ctx_note} | LOCAL Ollama token measurement only")

    # Single controlled run (reuses the existing per-scenario execution + prompt capture).
    record = neev._run_scenario(
        scenario, dry_run=args.dry_run, seed=args.seed,
        chars_per_token=args.chars_per_token, provider=provider,
        engine_runtime=engine_runtime, model_name=model_name,
        num_ctx_requested=args.num_ctx, effective_num_ctx=effective_num_ctx,
        prompts_dir=prompts_dir)

    # Standard benchmark artifacts (reuse the existing writers; single-row inputs).
    records = [record]
    assumptions = NeevAssumptions()
    agg = neev._aggregate(records, assumptions, allow_timeout_evidence=True)
    neev._write_results_csv(out_dir / "neev_validation_results.csv", records)
    neev._write_composition_csv(out_dir / "prompt_composition_report.csv", records)
    neev._write_prompt_summary_csv(prompts_dir / "prompt_summary.csv", records)
    neev._write_projection_csv(out_dir / "neev_capacity_projection.csv", records, assumptions)

    # Cumulative history (append-only; never overwrite).
    provider_label = os.environ.get("ECS_LLM_PROVIDER", "ollama")
    history_md = out_dir / _HISTORY_MD
    history_csv = out_dir / _HISTORY_CSV
    _append_history_md(history_md, record, timestamp=timestamp, git_commit=git_commit,
                       command=command, provider=provider_label,
                       model=(model_name or os.environ.get("OLLAMA_MODEL", "qwen3:8b")),
                       num_ctx=args.num_ctx, max_output_tokens=args.max_output_tokens,
                       timeout_seconds=args.timeout_seconds)
    _append_history_csv(history_csv, {
        "timestamp": timestamp,
        "git_commit": git_commit,
        "scenario": record.get("scenario_key", SCENARIO_KEY),
        "command": command,
        "provider": provider_label,
        "model": model_name or os.environ.get("OLLAMA_MODEL", "qwen3:8b"),
        "num_ctx_requested": args.num_ctx,
        "max_output_tokens": args.max_output_tokens,
        "timeout_seconds": args.timeout_seconds,
        "prompt_file": record.get("prompt_file", ""),
        "prompt_characters": record.get("prompt_chars", ""),
        "estimated_input_tokens": record.get("estimated_input_tokens", ""),
        "measured_input_tokens": record.get("measured_input_tokens"),
        "measured_output_tokens": record.get("measured_output_tokens"),
        "measured_total_tokens": record.get("measured_total_tokens"),
        "status": record.get("status", ""),
        "truncation_suspected": record.get("truncation_suspected", False),
        "error_message": record.get("error_message", ""),
    })

    # Clear console summary.
    fmt = neev._fmt
    print("")
    print("[16k-1k-validation] DONE — one run completed.")
    print(f"  status                 : {record.get('status', '')}")
    print(f"  prompt file            : {(prompts_dir / (scenario.key + '.txt'))}")
    print(f"  prompt characters      : {fmt(record.get('prompt_chars'))}")
    print(f"  estimated input tokens : {fmt(record.get('estimated_input_tokens'))} (ESTIMATED)")
    print(f"  measured input tokens  : {fmt(record.get('measured_input_tokens'))} (MEASURED)")
    print(f"  measured output tokens : {fmt(record.get('measured_output_tokens'))} (MEASURED)")
    print(f"  measured total tokens  : {fmt(record.get('measured_total_tokens'))} (MEASURED)")
    if record.get("error_message"):
        print(f"  error                  : {record.get('error_message')}")
    print("")
    print("  artifacts:")
    print(f"    prompt files dir     : {prompts_dir}/")
    print(f"    prompt summary CSV   : {prompts_dir / 'prompt_summary.csv'}")
    print(f"    results CSV          : {out_dir / 'neev_validation_results.csv'}")
    print(f"    history CSV          : {history_csv}")
    print(f"    history markdown     : {history_md}")
    print("")
    print(f"  interpretation (input) : {_interpret_input(record, args.num_ctx)}")
    print(f"  interpretation (output): {_interpret_output(record, args.max_output_tokens)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
