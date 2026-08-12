"""Run the agentic gap-remediation loop (qwen3:8b via the existing Ollama
adapter) over the gap_scenarios.json fixture, strictly sequentially.

Requires a local Ollama daemon with qwen3:8b pulled (see
`config/llm.yaml` / `OLLAMA_URL`). Does not modify baseline_runner.py — the
deterministic baseline is re-run in-process (no disk dependency) purely to
produce an apples-to-apples comparison over the same scenario subset.

Usage:
    python scripts/run_gap_agent.py            # subset: 2 scenarios/tier (8 total), default
    python scripts/run_gap_agent.py --subset    # same as above, explicit
    python scripts/run_gap_agent.py --full      # all 24 scenarios
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _resolve_ollama_url() -> str:
    """This script never imports app.main, so it never gets
    app/env_bootstrap.py's compose-DNS-to-host rewrite. Left unset, provider
    construction falls back to config/llm.yaml's Docker default
    (host.docker.internal), which doesn't resolve on a bare host and fails
    every LLM call with a DNS error. Default explicitly to localhost instead."""
    url = os.environ.get("OLLAMA_URL", "").strip()
    if not url:
        url = "http://localhost:11434"
        os.environ["OLLAMA_URL"] = url
    print(f"[run_gap_agent] OLLAMA_URL={url}")
    return url

from modules.audit_intelligence.gap_resolution.agent_loop import (
    compute_baseline_comparison,
    compute_rollup,
    render_results_table,
    render_rollup,
    run_agent_baseline,
)
from modules.audit_intelligence.gap_resolution.baseline_runner import run_baseline
from modules.audit_intelligence.gap_resolution.llm_call_logger import LLMCallLogger
from modules.audit_intelligence.gap_resolution.scenario_generator import (
    DEFAULT_FIXTURE_PATH,
    write_fixture,
)

SCENARIOS_PER_TIER_SUBSET = 2


def _select_subset(scenarios: list[dict]) -> list[dict]:
    by_tier: dict[str, list[dict]] = {}
    for s in scenarios:
        by_tier.setdefault(s["tier"], []).append(s)
    selected = []
    for tier in sorted(by_tier):
        selected.extend(by_tier[tier][:SCENARIOS_PER_TIER_SUBSET])
    return selected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the agentic gap-remediation loop.")
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE_PATH))
    parser.add_argument("--subset", action="store_true", help="2 scenarios/tier (8 total). Default.")
    parser.add_argument("--full", action="store_true", help="All 24 scenarios.")
    parser.add_argument("--results-jsonl", default="")
    parser.add_argument("--results-md", default="")
    parser.add_argument("--llm-log", default="")
    args = parser.parse_args(argv)

    _resolve_ollama_url()  # before any LLM calls

    mode = "full" if args.full else "subset"

    fixture_path = Path(args.fixture)
    if not fixture_path.exists():
        write_fixture(fixture_path)
    with fixture_path.open("r", encoding="utf-8") as fh:
        all_scenarios = json.load(fh)

    scenarios = all_scenarios if mode == "full" else _select_subset(all_scenarios)

    results_jsonl = Path(args.results_jsonl or f"benchmarks/output/gap_agent_{mode}_results.jsonl")
    results_md = Path(args.results_md or f"benchmarks/output/gap_agent_{mode}_results.md")
    llm_log_path = Path(args.llm_log or f"benchmarks/output/gap_agent_{mode}_llm_calls.jsonl")
    if llm_log_path.exists():
        # Each script invocation is one complete run — start the call log fresh so
        # it reflects exactly this run (LLMCallLogger itself still appends, which
        # is the right default for a long-lived process logging many runs).
        llm_log_path.unlink()

    logger = LLMCallLogger(llm_log_path)

    print(f"Running agentic gap-remediation loop — mode={mode}, {len(scenarios)} scenarios, "
          f"strictly sequential, max 3 tool-calling iterations/task.")
    results = run_agent_baseline(scenarios, logger=logger)

    baseline_results = run_baseline(scenarios)
    comparison = compute_baseline_comparison(results, baseline_results)
    rollup = compute_rollup(results)

    results_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with results_jsonl.open("w", encoding="utf-8") as fh:
        for r in results:
            slim = {k: v for k, v in r.items() if k != "transcript"}
            fh.write(json.dumps(slim, default=str) + "\n")

    table = render_results_table(results)
    rollup_md = render_rollup(rollup, comparison)
    doc = (
        f"# Gap Agent Results ({mode})\n\n"
        f"{table}\n\n"
        f"{rollup_md}\n"
    )
    results_md.parent.mkdir(parents=True, exist_ok=True)
    results_md.write_text(doc, encoding="utf-8")

    print(table)
    print()
    print(rollup_md)
    print(f"\nWrote {len(results)} results to {results_jsonl} and {results_md}")
    print(f"LLM call log: {llm_log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
