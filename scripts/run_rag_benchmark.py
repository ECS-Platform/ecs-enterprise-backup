"""Execute ECS RAG benchmark queries and persist run-level metrics."""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ecs_platform.rag import answer, reindex_evidence


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=True, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ECS RAG benchmark workload.")
    parser.add_argument(
        "--config",
        default="benchmarks/config/rag_benchmark_config.json",
        help="Path to benchmark config JSON.",
    )
    args = parser.parse_args()

    config = _load_json(Path(args.config))
    output_dir = Path(config.get("output_dir", "benchmarks/output"))
    os.environ["ECS_BENCHMARK_DIR"] = str(output_dir)

    if bool(config.get("reindex_before_run", False)):
        reindex_report = reindex_evidence()
        _write_json(output_dir / "reindex_report.json", reindex_report)

    queries = _load_json(Path(config["question_set_path"]))
    started_at = datetime.now(timezone.utc).isoformat()
    role = str(config.get("role", "cio"))
    user = str(config.get("user", "benchmark-runner"))
    top_k = int(config.get("top_k", 8))

    results: list[dict[str, Any]] = []
    latencies_ms: list[int] = []
    grounded_count = 0
    for q in queries:
        q_start = time.perf_counter()
        res = answer(str(q), role=role, user=user, top_k=top_k)
        q_ms = int((time.perf_counter() - q_start) * 1000)
        latencies_ms.append(q_ms)
        grounded_count += 1 if res.get("grounded") else 0
        results.append(
            {
                "question": q,
                "ok": bool(res.get("ok")),
                "grounded": bool(res.get("grounded")),
                "mode": res.get("mode", ""),
                "request_id": res.get("request_id", ""),
                "latency_ms": q_ms,
                "citation_count": len(res.get("citations", []) or []),
                "model": res.get("model", ""),
                "provider": res.get("provider", ""),
                "metrics": res.get("metrics", {}),
            }
        )

    finished_at = datetime.now(timezone.utc).isoformat()
    summary = {
        "started_at": started_at,
        "finished_at": finished_at,
        "queries": len(queries),
        "grounded_answers": grounded_count,
        "success_rate": round((grounded_count / len(queries)) * 100, 2) if queries else 0.0,
        "latency_ms": {
            "min": min(latencies_ms) if latencies_ms else 0,
            "max": max(latencies_ms) if latencies_ms else 0,
            "avg": round(sum(latencies_ms) / len(latencies_ms), 2) if latencies_ms else 0.0,
        },
    }

    _write_json(output_dir / "benchmark_summary.json", summary)
    _write_json(output_dir / "benchmark_results.json", results)
    print(f"benchmark complete: {summary['queries']} queries, output={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
