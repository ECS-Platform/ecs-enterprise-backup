"""RAG benchmark metrics persistence helpers (JSONL + CSV)."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any

_CSV_COLUMNS = [
    "timestamp",
    "request_id",
    "question",
    "model_name",
    "provider",
    "retrieval_mode",
    "retrieved_documents",
    "retrieved_chunks",
    "prompt_size_chars",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "retrieval_latency_ms",
    "prompt_build_latency_ms",
    "llm_latency_ms",
    "end_to_end_latency_ms",
]


def _metrics_dir() -> Path:
    root = os.environ.get("ECS_BENCHMARK_DIR", "benchmarks/output").strip() or "benchmarks/output"
    path = Path(root)
    path.mkdir(parents=True, exist_ok=True)
    return path


def persist_rag_metric(metric: dict[str, Any]) -> None:
    """Persist a single metric row in append-only JSONL and CSV files."""
    out_dir = _metrics_dir()
    jsonl_path = out_dir / "rag_metrics.jsonl"
    csv_path = out_dir / "rag_metrics.csv"

    with jsonl_path.open("a", encoding="utf-8") as jf:
        jf.write(json.dumps(metric, ensure_ascii=True) + "\n")

    row = {k: metric.get(k, "") for k in _CSV_COLUMNS}
    first_write = not csv_path.exists() or csv_path.stat().st_size == 0
    with csv_path.open("a", encoding="utf-8", newline="") as cf:
        writer = csv.DictWriter(cf, fieldnames=_CSV_COLUMNS)
        if first_write:
            writer.writeheader()
        writer.writerow(row)
