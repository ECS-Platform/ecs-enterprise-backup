#!/usr/bin/env python3
"""ECS Audit LLM benchmark runner (16 GB / 20 GB local laptops).

Runs audit prompts under a RAM profile in dry-run (token estimate only) or
actual-LLM mode, and writes Markdown + JSON evidence to
``reports/audit_llm_benchmarks/``.

SAFETY:
  * ``--dry-run`` (default) makes NO LLM call and needs no model/Docker/network —
    safe on any machine including 8 GB.
  * Actual LLM execution happens only with ``--execute`` AND a configured local
    provider (config/llm.yaml -> Ollama). If the LLM is unavailable it falls back
    to the deterministic result (never crashes).

USAGE:
  python scripts/run_audit_llm_benchmark.py --ram-profile local_16gb_safe --dry-run
  python scripts/run_audit_llm_benchmark.py --ram-profile local_20gb_extended --all --dry-run
  python scripts/run_audit_llm_benchmark.py --prompt observation_count --execute
  python scripts/run_audit_llm_benchmark.py --category executive --dry-run --json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")
os.environ.setdefault("DEMO_MODE", "true")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run ECS audit LLM benchmarks (local).")
    parser.add_argument("--ram-profile", default="local_16gb_safe",
                        choices=["local_16gb_safe", "local_20gb_extended", "worst_case_enterprise_dry_run"])
    parser.add_argument("--token-profile", default="",
                        help="Override token profile (small_4k/medium_8k/large_16k/extended_20k/worst_case_enterprise_dry_run).")
    parser.add_argument("--prompt", action="append", default=[], help="prompt_id (repeatable).")
    parser.add_argument("--category", default="", help="Run all prompts in a category.")
    parser.add_argument("--all", action="store_true", help="Run all prompts.")
    parser.add_argument("--execute", action="store_true", help="Actually call the LLM (default is dry-run).")
    parser.add_argument("--dry-run", action="store_true", default=False,
                        help="Token-estimate only, no LLM call (this is the default unless --execute).")
    parser.add_argument("--json", action="store_true", help="Print JSON summary to stdout.")
    parser.add_argument("--no-export", action="store_true", help="Do not write report files.")
    args = parser.parse_args(argv)

    from modules.audit_intelligence.llm import benchmark_runner as br

    report = br.run_benchmark(
        prompt_ids=args.prompt or None,
        category=args.category,
        all_prompts=args.all,
        ram_profile=args.ram_profile,
        token_profile=args.token_profile,
        dry_run=not args.execute,
    )

    written = {} if args.no_export else br.export_report(report)

    if args.json:
        print(json.dumps({"summary": report["summary"], "written": written,
                          "effective_mode": report["effective_mode"]}, indent=2, default=str))
    else:
        print(br.render_markdown(report))
        if written:
            print("Reports written:")
            for fmt, path in written.items():
                print(f"  {fmt}: {path}")

    # Exit non-zero only on a hard failure (nothing ran).
    return 0 if report["summary"]["prompts_run"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
