"""Thin entrypoint for the ECS enterprise AI workload benchmark.

Mirrors the convention of ``scripts/run_rag_benchmark.py`` but delegates ALL
logic to ``benchmarks.ai_workload.enterprise_runner`` (no duplicated logic). The
runner reuses the existing ECS RAG pipeline, provider instrumentation, statistics,
capacity-planning and reporting modules.

Usage (run later on the 16 GB benchmark workstation):

    python scripts/run_enterprise_benchmark.py
    python scripts/run_enterprise_benchmark.py --config benchmarks/config/enterprise_workload_config.json
    python scripts/run_enterprise_benchmark.py --profiles maxctx_max,complete_compliance
    python scripts/run_enterprise_benchmark.py --categories framework,baseline
    python scripts/run_enterprise_benchmark.py --list
"""

from __future__ import annotations

import sys

from benchmarks.ai_workload.enterprise_runner import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
