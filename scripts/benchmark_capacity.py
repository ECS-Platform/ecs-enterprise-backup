#!/usr/bin/env python3
"""ECS GCP/GKE capacity-sizing benchmark CLI.

Estimates GKE compute, Cloud SQL / pgvector, GCS object storage, and Cloud
Logging volume for named scenario profiles (demo -> large enterprise), and writes
JSON + Markdown + CSV reports.

REUSE: this extends the existing ECS benchmark/token framework
(``benchmarks.ai_workload.capacity_planning``, ``modules.audit_intelligence.llm.
token_estimator``) — it does not reimplement token counting or the LLM pipeline.
Pure arithmetic over documented assumptions; no network, no ECS/LLM calls.

USAGE:
  python scripts/benchmark_capacity.py --profile phase1
  python scripts/benchmark_capacity.py --profile enterprise
  python scripts/benchmark_capacity.py --all
  python scripts/benchmark_capacity.py --all --dry-run        # print summary, write nothing
  python scripts/benchmark_capacity.py --profile phase1 --out reports/capacity
  python scripts/benchmark_capacity.py --list                 # list profiles
  # Section reports (print to console):
  python scripts/benchmark_capacity.py --all --cpu
  python scripts/benchmark_capacity.py --all --ram
  python scripts/benchmark_capacity.py --all --database
  python scripts/benchmark_capacity.py --all --network
  python scripts/benchmark_capacity.py --all --storage
  python scripts/benchmark_capacity.py --all --cost
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = "reports/capacity_benchmarks"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="ECS GCP/GKE capacity sizing benchmark.")
    parser.add_argument("--profile", help="Scenario profile key (see --list).")
    parser.add_argument("--all", action="store_true", help="Run every profile.")
    parser.add_argument("--list", action="store_true", help="List available profiles and exit.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Compute + print a summary but write NO report files.")
    parser.add_argument("--out", default=DEFAULT_OUT, help=f"Output dir (default {DEFAULT_OUT}).")
    parser.add_argument("--basename", default="capacity", help="Report file basename.")
    # Section flags: print a specific report to the console (implies dry-run print).
    for sec in ("cpu", "ram", "database", "network", "storage", "cost"):
        parser.add_argument(f"--{sec}", action="store_true",
                            help=f"Print the {sec} benchmark report to the console.")
    args = parser.parse_args(argv)

    from benchmarks.capacity import estimate_capacity, get_profile, list_profiles
    from benchmarks.capacity import report as rpt

    if args.list:
        for key in list_profiles():
            print(f"  {key:12} {get_profile(key).name}")
        return 0

    if args.all:
        keys = list_profiles()
    elif args.profile:
        keys = [args.profile]
    else:
        parser.error("provide --profile <key>, --all, or --list")
        return 2

    try:
        profiles = [get_profile(k) for k in keys]
    except KeyError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    estimates = [estimate_capacity(p) for p in profiles]

    # Section flags: print the requested section report(s) and exit.
    requested_sections = [s for s in ("cpu", "ram", "database", "network", "storage", "cost")
                          if getattr(args, s, False)]
    if requested_sections:
        for sec in requested_sections:
            print(rpt.SECTION_REPORTS[sec](estimates))
            print()
        return 0

    # Console summary (recommendation table) — always printed.
    print(f"ECS GCP Capacity Benchmark — {len(estimates)} profile(s)")
    print("-" * 78)
    for row in rpt.recommendation_table(estimates):
        print(f"  {row['profile']:11} apps={row['apps']:<5} "
              f"replicas={row['replicas']:<3} nodes={row['gke_nodes']:<3} "
              f"sql={row['cloud_sql_tier']:<20} "
              f"db_y1={row['db_year1_gib']}GiB gcs_y1={row['gcs_year1_gib']}GiB "
              f"logs/d={row['logs_per_day_gib']}GiB")
    print("-" * 78)
    print("NOTE: estimates from documented assumptions x profile — not a measurement.")

    if args.dry_run:
        print("[dry-run] no files written.")
        return 0

    paths = rpt.write_reports(estimates, args.out, basename=args.basename)
    print(f"Wrote:\n  {paths['json']}\n  {paths['markdown']}\n  {paths['csv']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
