"""Generate gap scenarios (if needed) and run the deterministic completeness
baseline over them — no LLM, no network, no DB.

Usage:
    python scripts/run_gap_baseline.py
    python scripts/run_gap_baseline.py --regenerate
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from modules.audit_intelligence.gap_resolution.baseline_runner import (
    DEFAULT_RESULTS_JSONL,
    DEFAULT_RESULTS_MD,
    render_markdown_table,
    run_baseline,
    write_results_jsonl,
    write_results_markdown,
)
from modules.audit_intelligence.gap_resolution.scenario_generator import (
    DEFAULT_FIXTURE_PATH,
    write_fixture,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the deterministic gap-scenario baseline.")
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE_PATH), help="Path to the scenario fixture JSON.")
    parser.add_argument("--regenerate", action="store_true", help="Regenerate the fixture even if it already exists.")
    parser.add_argument("--results-jsonl", default=str(DEFAULT_RESULTS_JSONL))
    parser.add_argument("--results-md", default=str(DEFAULT_RESULTS_MD))
    args = parser.parse_args(argv)

    fixture_path = Path(args.fixture)
    if args.regenerate or not fixture_path.exists():
        write_fixture(fixture_path)

    with fixture_path.open("r", encoding="utf-8") as fh:
        scenarios = json.load(fh)

    results = run_baseline(scenarios)
    write_results_jsonl(results, Path(args.results_jsonl))
    write_results_markdown(results, Path(args.results_md))

    print(render_markdown_table(results))
    print(f"\nWrote {len(results)} results to {args.results_jsonl} and {args.results_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
