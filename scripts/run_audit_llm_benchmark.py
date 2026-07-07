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

USAGE (both flag styles are accepted):
  # Task-standard form (--profile + --mode dry_run|live):
  python scripts/run_audit_llm_benchmark.py --profile local_16gb_safe --mode dry_run
  python scripts/run_audit_llm_benchmark.py --profile local_16gb_safe --mode live
  python scripts/run_audit_llm_benchmark.py --profile local_20gb_extended --mode dry_run
  python scripts/run_audit_llm_benchmark.py --profile local_20gb_extended --mode live
  # Legacy/equivalent form (--ram-profile + --dry-run/--execute):
  python scripts/run_audit_llm_benchmark.py --ram-profile local_20gb_extended --all --dry-run
  python scripts/run_audit_llm_benchmark.py --prompt observation_count --execute
  python scripts/run_audit_llm_benchmark.py --category executive --dry-run --json

Only two RAM profiles are supported for local laptops (16 GB, 20 GB), plus a
no-LLM ``worst_case_enterprise_dry_run`` helper. ``--mode live`` == ``--execute``;
``--mode dry_run`` == ``--dry-run`` (the default).
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
    _PROFILE_CHOICES = ["local_16gb_safe", "local_20gb_extended", "worst_case_enterprise_dry_run"]
    parser = argparse.ArgumentParser(description="Run ECS audit LLM benchmarks (local).")
    # Task-standard aliases. --profile mirrors --ram-profile; --mode mirrors
    # --execute/--dry-run. Both styles are accepted (default profile 16 GB safe).
    parser.add_argument("--profile", "--ram-profile", dest="ram_profile",
                        default="local_16gb_safe", choices=_PROFILE_CHOICES,
                        help="RAM/benchmark profile (16 GB, 20 GB, or dry-run helper).")
    parser.add_argument("--mode", choices=["dry_run", "live"], default=None,
                        help="dry_run = token estimate only (default); live = call the local LLM.")
    parser.add_argument("--token-profile", default="",
                        help="Override token profile (small_4k/medium_8k/large_16k/extended_20k/worst_case_enterprise_dry_run).")
    parser.add_argument("--prompt", action="append", default=[], help="prompt_id (repeatable).")
    parser.add_argument("--category", default="", help="Run all prompts in a category.")
    parser.add_argument("--all", action="store_true", help="Run all prompts.")
    parser.add_argument("--execute", action="store_true", help="Actually call the LLM (== --mode live).")
    parser.add_argument("--dry-run", action="store_true", default=False,
                        help="Token-estimate only, no LLM call (== --mode dry_run; the default).")
    parser.add_argument("--json", action="store_true", help="Print JSON summary to stdout.")
    parser.add_argument("--no-export", action="store_true", help="Do not write report files.")
    args = parser.parse_args(argv)

    # Resolve execution mode: --mode wins if given, else fall back to --execute.
    if args.mode == "live":
        execute = True
    elif args.mode == "dry_run":
        execute = False
    else:
        execute = args.execute

    from modules.audit_intelligence.llm import benchmark_runner as br

    report = br.run_benchmark(
        prompt_ids=args.prompt or None,
        category=args.category,
        all_prompts=args.all,
        ram_profile=args.ram_profile,
        token_profile=args.token_profile,
        dry_run=not execute,
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
