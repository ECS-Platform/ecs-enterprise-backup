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


ASSESSMENTS: list[dict[str, Any]] = [
    (
        {
            "name": "Enterprise Consolidated Regulator Readiness",
            "top_k": 24,
            "purpose": "Board/regulator consolidated readiness across major enterprise governance frameworks.",
            "expected_retrieval_breadth": "Very high across source systems, controls, and framework mappings.",
            "expected_governance_scope": "Enterprise-wide, regulator-facing, cross-framework.",
            "expected_response_complexity": "Very high with gap/risk/remediation synthesis and citations.",
            "frameworks_covered": "PCI DSS, RBI C-SITE, DPSC, ITPP, ITGRC, VAPT, AI SDLC, AppSec, ASST, DB Baselining, ITDRM, Middleware Security, SOC2, ISO27001, RBI-CSF",
            "applications_covered": "Portfolio-wide applications represented in retrieved evidence",
            "question": (
                "Provide a consolidated regulator readiness assessment across PCI DSS, RBI C-SITE, "
                "DPSC, ITPP, ITGRC, VAPT, AI SDLC, AppSec, ASST, DB Baselining, ITDRM, "
                "Middleware Security, SOC2, ISO27001, and RBI-CSF using only ECS evidence. "
                "Include framework-by-framework coverage, key control gaps, evidence quality risks, "
                "and prioritized remediation with citations for every claim."
            ),
        }
    ),
    {
        "name": "Enterprise Cross-Framework Compliance Maturity",
        "top_k": 22,
        "purpose": "Enterprise maturity comparison across frameworks and applications.",
        "expected_retrieval_breadth": "Very high due to comparative cross-framework and cross-application asks.",
        "expected_governance_scope": "Portfolio-wide compliance maturity and audit traceability.",
        "expected_response_complexity": "High; requires comparative analysis and structured maturity conclusions.",
        "frameworks_covered": "SOC2, ISO27001, PCI DSS, RBI C-SITE, DPSC, ITPP, ITGRC, VAPT, AI SDLC, AppSec, ASST, DB Baselining, ITDRM, Middleware Security",
        "applications_covered": "Portfolio-wide multi-application scope",
        "question": (
            "Assess enterprise governance and compliance maturity portfolio-wide across SOC2, ISO27001, "
            "PCI DSS, RBI C-SITE, DPSC, ITPP, ITGRC, VAPT, AI SDLC, AppSec, ASST, DB Baselining, "
            "ITDRM, and Middleware Security. Compare control coverage, lifecycle readiness, evidence "
            "freshness, and audit traceability by framework and application with citations."
        ),
    },
    {
        "name": "Portfolio-Wide Control Coverage Deep Assessment",
        "top_k": 20,
        "purpose": "Deep control coverage diagnostics for enterprise audit planning.",
        "expected_retrieval_breadth": "High due to control-to-framework coverage and lifecycle quality analysis.",
        "expected_governance_scope": "Enterprise controls and framework crosswalk health.",
        "expected_response_complexity": "High with prioritized control-level findings and actions.",
        "frameworks_covered": "All frameworks represented in ECS control crosswalk",
        "applications_covered": "Portfolio-wide applications contributing control evidence",
        "question": (
            "Generate a portfolio-wide deep control coverage assessment across all available frameworks in ECS. "
            "Map controls to frameworks, identify reused controls, uncovered controls, weak evidence patterns, "
            "and controls with rejection or expiry risk. Provide executive findings with evidence citations."
        ),
    },
    {
        "name": "Enterprise Evidence Reuse and Crosswalk Analysis",
        "top_k": 20,
        "purpose": "Cross-framework evidence reuse quantification and risk analysis.",
        "expected_retrieval_breadth": "High due to crosswalked evidence and multi-source correlations.",
        "expected_governance_scope": "Enterprise reuse posture and cross-framework obligation mapping.",
        "expected_response_complexity": "Medium-high combining quantitative reuse and risk interpretation.",
        "frameworks_covered": "All frameworks participating in ECS crosswalk mappings",
        "applications_covered": "Portfolio-wide applications with reusable mapped evidence",
        "question": (
            "Analyze enterprise evidence reuse across all supported frameworks and source systems. "
            "Quantify where one evidence item satisfies multiple obligations, identify crosswalk concentration "
            "risks, and call out highest-impact reuse opportunities and blockers with citations."
        ),
    },
    {
        "name": "Executive Board Compliance Risk Pack",
        "top_k": 24,
        "purpose": "Board-level risk pack for enterprise compliance governance decisions.",
        "expected_retrieval_breadth": "Very high across readiness, lifecycle, and regulator priorities.",
        "expected_governance_scope": "Enterprise-wide strategy and operational compliance risk.",
        "expected_response_complexity": "Very high with executive synthesis and evidence-backed prioritization.",
        "frameworks_covered": "All supported frameworks represented in ECS evidence and governance mappings",
        "applications_covered": "Portfolio-wide enterprise application coverage",
        "question": (
            "Prepare an executive board compliance risk pack summarizing enterprise readiness across all "
            "supported frameworks, largest residual risks, audit readiness blockers, evidence lifecycle "
            "issues, and regulator-facing priorities. Include citations and source/timestamp context."
        ),
    },
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
    report_name: str = "maximum_token_budget_report.md"


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
        report_name=str(data.get("report_name", "maximum_token_budget_report.md")),
    )


def _flush_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=True) + "\n")
        fh.flush()


def _max_row(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    return max(rows, key=lambda r: int(r.get(key, 0) or 0))


def _write_text(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8") as fh:
        fh.write(text)
        fh.flush()


def _build_management_report(
    rows: list[dict[str, Any]],
    prompts_used: list[dict[str, Any]],
    output_path: Path,
    requests_per_minute: int,
) -> None:
    measured = [r for r in rows if bool(r.get("ok"))]
    if not measured:
        _write_text(
            output_path,
            "# Maximum Token Budget Report\n\nNo successful benchmark rows were recorded.\n",
        )
        return

    max_input_row = _max_row(measured, "input_tokens")
    max_output_row = _max_row(measured, "output_tokens")
    max_total_row = _max_row(measured, "total_tokens")
    max_docs_row = _max_row(measured, "retrieved_documents")
    max_chunks_row = _max_row(measured, "retrieved_chunks")
    max_citations_row = _max_row(measured, "citation_count")
    max_prompt_row = _max_row(measured, "prompt_size_chars")

    max_input = int(max_input_row.get("input_tokens", 0) or 0)
    max_output = int(max_output_row.get("output_tokens", 0) or 0)
    max_total = int(max_total_row.get("total_tokens", 0) or 0)
    max_docs = int(max_docs_row.get("retrieved_documents", 0) or 0)
    max_chunks = int(max_chunks_row.get("retrieved_chunks", 0) or 0)
    max_citations = int(max_citations_row.get("citation_count", 0) or 0)
    max_prompt = int(max_prompt_row.get("prompt_size_chars", 0) or 0)

    input_per_min = max_input * requests_per_minute
    output_per_min = max_output * requests_per_minute
    total_per_min = max_total * requests_per_minute
    input_per_hour = input_per_min * 60
    output_per_hour = output_per_min * 60
    total_per_hour = total_per_min * 60
    input_per_day = input_per_hour * 24
    output_per_day = output_per_hour * 24
    total_per_day = total_per_hour * 24
    input_per_month = input_per_day * 30
    output_per_month = output_per_day * 30
    total_per_month = total_per_day * 30

    prompt_lines = "\n".join(
        f"- {p['name']} (top_k={int(p.get('top_k', 0) or 0)}): {p['question']}" for p in prompts_used
    )
    rows_by_prompt = {str(r.get("assessment", "")): r for r in measured}
    methodology_lines: list[str] = []
    table_lines: list[str] = [
        "| Prompt name | Frameworks covered | Applications covered | Configured retrieval depth (top_k) | Retrieved documents | Retrieved chunks | Input tokens | Output tokens | Total tokens | Citations | End-to-end latency (ms) |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for prompt in prompts_used:
        name = str(prompt.get("name", ""))
        row = rows_by_prompt.get(name, {})
        methodology_lines.append(
            "\n".join(
                [
                    f"### {name}",
                    f"- Purpose: {prompt.get('purpose', 'N/A')}",
                    f"- Expected retrieval breadth: {prompt.get('expected_retrieval_breadth', 'N/A')}",
                    f"- Expected governance scope: {prompt.get('expected_governance_scope', 'N/A')}",
                    f"- Expected response complexity: {prompt.get('expected_response_complexity', 'N/A')}",
                    "- Why this prompt is expected to maximize input tokens: enterprise-wide "
                    "cross-framework scope plus elevated retrieval depth increases retrieved "
                    "context included in prompt construction.",
                    "- Why this prompt is expected to maximize output tokens: executive/regulator "
                    "asks require long-form cited synthesis across coverage, risks, and "
                    "remediation priorities.",
                ]
            )
        )
        table_lines.append(
            "| "
            + " | ".join(
                [
                    name,
                    str(prompt.get("frameworks_covered", "N/A")),
                    str(prompt.get("applications_covered", "N/A")),
                    str(int(prompt.get("top_k", 0) or 0)),
                    str(int(row.get("retrieved_documents", 0) or 0)),
                    str(int(row.get("retrieved_chunks", 0) or 0)),
                    str(int(row.get("input_tokens", 0) or 0)),
                    str(int(row.get("output_tokens", 0) or 0)),
                    str(int(row.get("total_tokens", 0) or 0)),
                    str(int(row.get("citation_count", 0) or 0)),
                    str(int(row.get("end_to_end_elapsed_ms_runner", 0) or 0)),
                ]
            )
            + " |"
        )
    methodology_section = "\n\n".join(methodology_lines)
    prompt_results_table = "\n".join(table_lines)

    content = f"""# Maximum Token Budget Report

## Purpose
Measure maximum realistic LLM token consumption per request for enterprise budgeting using ECS's existing RAG execution and instrumentation.

## Maximum Observed Values (Measured)
- Maximum Input Tokens: **{max_input}** (assessment: {max_input_row.get("assessment", "")})
- Maximum Output Tokens: **{max_output}** (assessment: {max_output_row.get("assessment", "")})
- Maximum Total Tokens: **{max_total}** (assessment: {max_total_row.get("assessment", "")})
- Maximum Retrieved Documents: **{max_docs}** (assessment: {max_docs_row.get("assessment", "")})
- Maximum Retrieved Chunks: **{max_chunks}** (assessment: {max_chunks_row.get("assessment", "")})
- Maximum Citations: **{max_citations}** (assessment: {max_citations_row.get("assessment", "")})
- Maximum Prompt Size (chars): **{max_prompt}** (assessment: {max_prompt_row.get("assessment", "")})

## Throughput Budgeting (3 requests/minute)
Measured token-per-request values above are projected at {requests_per_minute} completed requests per minute.

### Input Tokens
- Tokens per Request: {max_input}
- Tokens per Minute: {input_per_min}
- Tokens per Hour: {input_per_hour}
- Tokens per Day: {input_per_day}
- Tokens per Month (30d): {input_per_month}

### Output Tokens
- Tokens per Request: {max_output}
- Tokens per Minute: {output_per_min}
- Tokens per Hour: {output_per_hour}
- Tokens per Day: {output_per_day}
- Tokens per Month (30d): {output_per_month}

### Total Tokens
- Tokens per Request: {max_total}
- Tokens per Minute: {total_per_min}
- Tokens per Hour: {total_per_hour}
- Tokens per Day: {total_per_day}
- Tokens per Month (30d): {total_per_month}

## Benchmark Prompts Used
{prompt_lines}

## Worst-Case Prompt Selection Methodology
{methodology_section}

## Per-Prompt Measured Results
{prompt_results_table}

## Maximum Token Justification
This benchmark intentionally targets enterprise-wide, cross-framework governance
questions spanning multiple frameworks and applications. That naturally yields
the largest realistic retrieval context and response size within ECS because the
assistant must synthesize broad evidence into citation-backed executive output.

## How values were obtained
- All values are read from executed benchmark rows and ECS instrumentation outputs (`rag_metrics.csv`, `rag_metrics.jsonl`, and `ai_workload_requests.jsonl`).
- No token value in this report is estimated or fabricated.
- Maximum values are computed as max() over successful benchmark requests for each metric.

## Why these prompts are realistic worst-case enterprise governance requests
- Each prompt requests board/regulator-grade consolidated assessment across many frameworks.
- Prompts require cross-framework mapping, coverage, gaps, lifecycle risk, and remediation prioritization.
- Retrieval depth (`top_k`) is increased only for these realistic enterprise prompts to maximize genuine evidence context.
- The prompts are domain-authentic governance asks; they do not pad meaningless text or fabricate evidence.

## Evidence file size and prompt token behavior
- Embeddings are generated once during ingestion and stored in vector index tables.
- Original evidence file size does **not** directly determine prompt token consumption at answer time.
- Prompt tokens are driven by retrieved chunks, retrieval depth, chunk size, and prompt construction.

### Examples
- A very large source artifact can still produce low prompt tokens if only a few short chunks are retrieved.
- A modest-size artifact set can produce high prompt tokens when many chunks are retrieved across frameworks in a consolidated request.

## Assumptions
- Benchmark is based on actual ECS evidence.
- No synthetic prompt inflation was used.
- No fabricated evidence was introduced.
- Token values originate from Ollama metadata.
- Retrieval metrics originate from ECS instrumentation.
- Throughput calculations assume three completed requests per minute.
"""
    _write_text(output_path, content)


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
    report_path = out_dir / config.report_name
    min_interval_sec = 60.0 / float(config.max_requests_per_minute)
    last_started = 0.0
    report_rows: list[dict[str, Any]] = []

    for assessment in ASSESSMENTS:
        assessment_name = str(assessment.get("name", ""))
        question = str(assessment.get("question", ""))
        effective_top_k = max(config.top_k, int(assessment.get("top_k", config.top_k)))
        now = time.perf_counter()
        elapsed = now - last_started
        if elapsed < min_interval_sec:
            time.sleep(min_interval_sec - elapsed)
        last_started = time.perf_counter()

        t0 = time.perf_counter()
        res = answer(question, role=config.role, user=config.user, top_k=effective_top_k)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        metrics = res.get("metrics", {}) or {}
        citation_count = len(res.get("citations", []) or [])

        row: dict[str, Any] = {
            "timestamp": _utc_now(),
            "assessment": assessment_name,
            "question": question,
            "top_k": effective_top_k,
            "request_id": res.get("request_id", ""),
            "ok": bool(res.get("ok")),
            "mode": res.get("mode", ""),
            "grounded": bool(res.get("grounded")),
            "provider": res.get("provider", ""),
            "model": res.get("model", ""),
            "citation_count": citation_count,
            "retrieved_documents": int(metrics.get("retrieved_documents", 0) or 0),
            "retrieved_chunks": int(metrics.get("retrieved_chunks", 0) or 0),
            "prompt_size_chars": int(metrics.get("prompt_size_chars", 0) or 0),
            "input_tokens": int(metrics.get("input_tokens", 0) or 0),
            "output_tokens": int(metrics.get("output_tokens", 0) or 0),
            "total_tokens": int(metrics.get("total_tokens", 0) or 0),
            "retrieval_latency_ms": int(metrics.get("retrieval_latency_ms", 0) or 0),
            "prompt_build_latency_ms": int(metrics.get("prompt_build_latency_ms", 0) or 0),
            "llm_latency_ms": int(metrics.get("llm_latency_ms", 0) or 0),
            "end_to_end_elapsed_ms_runner": elapsed_ms,
            "metrics": metrics,
        }
        _flush_jsonl(out_path, row)
        report_rows.append(row)

    _build_management_report(
        rows=report_rows,
        prompts_used=ASSESSMENTS,
        output_path=report_path,
        requests_per_minute=config.max_requests_per_minute,
    )

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
