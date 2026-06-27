"""Thin entrypoint for the ECS enterprise AI workload benchmark.

Mirrors the convention of ``scripts/run_rag_benchmark.py`` but delegates ALL
logic to ``benchmarks.ai_workload.enterprise_runner`` (no duplicated logic). The
runner reuses the existing ECS RAG pipeline, provider instrumentation, statistics,
capacity-planning and reporting modules.

Usage (run later on the 16 GB benchmark workstation):

PREFERRED (works on every shell, incl. Windows Git Bash) — run from the repo root
so the ``benchmarks`` / ``ecs_platform`` packages resolve:

    PYTHONPATH=. python3 -m scripts.run_enterprise_benchmark --config benchmarks/config/enterprise_workload_config.json

Other examples:

    PYTHONPATH=. python3 -m scripts.run_enterprise_benchmark --profiles sp_sr --max-rpm 3
    PYTHONPATH=. python3 -m scripts.run_enterprise_benchmark --mode worst_case
    PYTHONPATH=. python3 -m scripts.run_enterprise_benchmark --list

Script-style invocation also works from the repo root:

    python scripts/run_enterprise_benchmark.py --config benchmarks/config/enterprise_workload_config.json
"""

from __future__ import annotations

import sys

from benchmarks.ai_workload.enterprise_runner import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
