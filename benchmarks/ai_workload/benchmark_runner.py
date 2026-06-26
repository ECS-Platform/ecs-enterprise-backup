"""Lightweight ECS AI workload benchmark runner.

Reuses existing ECS implementation:
- RAG pipeline: ecs_platform.rag.answer
- Provider abstraction and token instrumentation: ecs_platform.llm_engine.provider + rag metrics logging
- Existing ingestion flow (optional): ecs_platform.ingestion.sync_all
"""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ASSESSMENTS: list[tuple[str, str]] = [
    ("RBI C-SITE Readiness", "Provide RBI C-SITE readiness assessment with cited ECS evidence."),
    ("PCI DSS Readiness", "Provide PCI DSS readiness assessment with cited ECS evidence."),
    ("DPSC Readiness", "Provide DPSC readiness assessment with cited ECS evidence."),
    ("ITGRC Readiness", "Provide ITGRC readiness assessment with cited ECS evidence."),
    ("CMDB Readiness", "Provide CMDB readiness assessment with cited ECS evidence."),
    ("VAPT Readiness", "Provide VAPT readiness assessment with cited ECS evidence."),
    (
        "Enterprise Consolidated Readiness Assessment",
        "Provide enterprise consolidated readiness assessment across frameworks with citations.",
    ),
]


@dataclass
class RunnerConfig:
    role: str = "cio"
    user: str = "benchmark-runner"
    top_k: int = 5
    concurrency: int = 1
    max_requests_per_minute: int = 3
    run_sync_once: bool = False
    output_dir: str = "benchmarks/output"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dir(path: str) -> Path:
    out = Path(path)
    out.mkdir(parents=True, exist_ok=True)
    return out


def _load_config(path: Path | None) -> RunnerConfig:
    if path is None:
        return RunnerConfig()
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    return RunnerConfig(
        role=str(data.get("role", "cio")),
        user=str(data.get("user", "benchmark-runner")),
        top_k=int(data.get("top_k", 5)),
        concurrency=int(data.get("concurrency", 1)),
        max_requests_per_minute=int(data.get("max_requests_per_minute", 3)),
        run_sync_once=bool(data.get("run_sync_once", False)),
        output_dir=str(data.get("output_dir", "benchmarks/output")),
    )


def _flush_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=True) + "\n")
        fh.flush()


def run(config: RunnerConfig) -> int:
    if config.concurrency != 1:
        raise ValueError("This lightweight runner supports only concurrency=1.")
    if config.max_requests_per_minute <= 0:
        raise ValueError("max_requests_per_minute must be > 0.")

    out_dir = _ensure_dir(config.output_dir)
    os.environ["ECS_BENCHMARK_DIR"] = str(out_dir)

    if config.run_sync_once:
        from ecs_platform.ingestion import sync_all

        sync_all(actor=config.user, role=config.role, index=True)

    from ecs_platform.rag import answer

    out_path = out_dir / "ai_workload_requests.jsonl"
    min_interval_sec = 60.0 / float(config.max_requests_per_minute)
    last_started = 0.0

    for assessment_name, question in ASSESSMENTS:
        now = time.perf_counter()
        elapsed = now - last_started
        if elapsed < min_interval_sec:
            time.sleep(min_interval_sec - elapsed)
        last_started = time.perf_counter()

        t0 = time.perf_counter()
        res = answer(question, role=config.role, user=config.user, top_k=config.top_k)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)

        row: dict[str, Any] = {
            "timestamp": _utc_now(),
            "assessment": assessment_name,
            "question": question,
            "request_id": res.get("request_id", ""),
            "ok": bool(res.get("ok")),
            "mode": res.get("mode", ""),
            "grounded": bool(res.get("grounded")),
            "provider": res.get("provider", ""),
            "model": res.get("model", ""),
            "metrics": res.get("metrics", {}),
            "end_to_end_elapsed_ms_runner": elapsed_ms,
        }
        _flush_jsonl(out_path, row)

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run lightweight ECS AI workload benchmark.")
    parser.add_argument("--config", type=str, default="", help="Optional JSON config path.")
    args = parser.parse_args()

    cfg_path = Path(args.config) if args.config else None
    config = _load_config(cfg_path)
    return run(config)


if __name__ == "__main__":
    raise SystemExit(main())
