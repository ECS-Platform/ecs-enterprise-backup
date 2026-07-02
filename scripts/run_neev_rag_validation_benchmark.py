"""Neev RAG validation benchmark (additive, full ECS pipeline)."""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class Scenario:
    key: str
    query: str
    top_k: int
    evidence_limit: int


SUPPORTED_PROFILES = [
    "small",
    "medium",
    "full",
    "enterprise",
    "large_repository_300",
    "large_repository_500",
    "large_repository_600",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dir(path: str) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _scenarios_from_profiles(raw: str, top_k: int) -> list[Scenario]:
    names = [x.strip() for x in (raw or "small").split(",") if x.strip()]
    if not names:
        names = ["small"]
    if "all" in names:
        names = list(SUPPORTED_PROFILES)

    top_k_effective = top_k if top_k and top_k > 0 else 20
    catalog: dict[str, Scenario] = {
        "small": Scenario(
            key="small",
            query=(
                "Provide audit-ready compliance readiness summary for a focused scope using "
                "retrieved evidence only. Include key controls, observations, owners, gaps, "
                "and citations."
            ),
            top_k=top_k_effective,
            evidence_limit=50,
        ),
        "medium": Scenario(
            key="medium",
            query=(
                "Assess cross-domain control effectiveness for the current repository scope. "
                "Summarize control health, recurring deficiencies, remediation ownership, and "
                "evidence-backed compliance gaps with citations."
            ),
            top_k=top_k_effective,
            evidence_limit=100,
        ),
        "full": Scenario(
            key="full",
            query=(
                "Generate an enterprise audit-preparation assessment across applications and "
                "framework-aligned controls in scope. Highlight risk concentration, unresolved "
                "findings, and evidence-backed actions with citations."
            ),
            top_k=top_k_effective,
            evidence_limit=250,
        ),
        "enterprise": Scenario(
            key="enterprise",
            query=(
                "Produce an enterprise-wide governance and compliance readiness view across the "
                "available repository corpus. Include control maturity patterns, systemic gaps, "
                "owner accountability, and prioritized remediation with citations."
            ),
            top_k=top_k_effective,
            evidence_limit=500,
        ),
        "large_repository_300": Scenario(
            key="large_repository_300",
            query=(
                "For a large repository sample, provide a broad compliance posture summary with "
                "cross-application observations, control status trends, high-risk exceptions, "
                "and evidence-backed recommendations with citations."
            ),
            top_k=top_k_effective,
            evidence_limit=300,
        ),
        "large_repository_500": Scenario(
            key="large_repository_500",
            query=(
                "Using a deeper repository slice, evaluate enterprise control consistency and "
                "coverage. Report critical deficiencies, remediation ownership clarity, and "
                "framework-relevant evidence support with citations."
            ),
            top_k=top_k_effective,
            evidence_limit=500,
        ),
        "large_repository_600": Scenario(
            key="large_repository_600",
            query=(
                "Using the largest repository scope, deliver an enterprise-level consolidated "
                "audit readiness narrative: key compliance strengths, cross-cutting weaknesses, "
                "control breakdown hotspots, and evidence-prioritized actions with citations."
            ),
            top_k=top_k_effective,
            evidence_limit=600,
        ),
    }

    out: list[Scenario] = []
    for name in names:
        if name not in catalog:
            raise ValueError(f"Unknown profile '{name}'.")
        out.append(catalog[name])
    return out


def _estimate_tokens(text: str, chars_per_token: float = 4.0) -> int:
    return int(max(1, round(len(text or "") / chars_per_token)))


def run_scenario(
    sc: Scenario,
    *,
    dry_run: bool,
    provider_name: str | None,
    num_ctx: int | None,
    max_output_tokens: int | None,
    timeout_seconds: int,
    output_dir: Path,
) -> dict[str, Any]:
    from ecs_platform.llm_engine.prompt_builder import SYSTEM_PROMPT, build_rag_prompt
    from ecs_platform.llm_engine.provider import get_provider, set_benchmark_generation_config
    from ecs_platform.repository import EvidenceRepository
    from ecs_platform.vectorstore import Chunk, chunk_text, get_vector_store
    from ecs_platform.config import load_vectorstore_config

    if provider_name:
        os.environ["ECS_LLM_PROVIDER"] = provider_name
    if timeout_seconds:
        os.environ["ECS_LLM_TIMEOUT_SECONDS"] = str(timeout_seconds)
    set_benchmark_generation_config(num_predict=max_output_tokens, num_ctx=num_ctx, timeout_seconds=timeout_seconds)

    rec: dict[str, Any] = {
        "timestamp": _utc_now(),
        "scenario": sc.key,
        "profile": sc.key,
        "top_k": sc.top_k,
        "provider": "",
        "model": "",
        "status": "MEASURED",
        "dry_run": dry_run,
    }

    # Step 1: Evidence loading through repository layer (system of record).
    t0 = time.perf_counter()
    with EvidenceRepository() as repo:
        rows = repo.search_evidence(limit=sc.evidence_limit)
        docs = [repo.evidence_by_uid(r["evidence_uid"]) for r in rows]
    rec["object_storage_source"] = "EvidenceRepository"
    rec["object_storage_load_ms"] = int((time.perf_counter() - t0) * 1000)
    rec["files_loaded"] = len([d for d in docs if d])
    rec["total_bytes"] = sum(len((f"{d.get('title','')}\n{d.get('content','')}").encode("utf-8")) for d in docs if d)

    # Step 2: OCR/Text extraction reuse (repository normalized text payload).
    t0 = time.perf_counter()
    extracted: list[dict[str, Any]] = []
    for d in docs:
        if not d:
            continue
        text = f"{d.get('title', '')}\n{d.get('content', '')}".strip()
        extracted.append(
            {
                "uid": d.get("evidence_uid", ""),
                "text": text,
                "source_system": d.get("source_system", ""),
                "object_type": d.get("object_type", ""),
                "application": d.get("application", ""),
            }
        )
    rec["ocr_source"] = "Repository normalized evidence text"
    rec["ocr_time_ms"] = int((time.perf_counter() - t0) * 1000)
    rec["extracted_characters"] = sum(len(x["text"]) for x in extracted)
    rec["extracted_words"] = sum(len(x["text"].split()) for x in extracted)

    # Step 3: Chunking via ECS vectorstore.chunk_text + ECS chunk config.
    cfg = (load_vectorstore_config().get("vectorstore", {}) or {}).get("chunking", {})
    chunk_size = int(cfg.get("chunk_size", 1000))
    chunk_overlap = int(cfg.get("chunk_overlap", 150))
    t0 = time.perf_counter()
    chunks: list[dict[str, Any]] = []
    for ex in extracted:
        for idx, piece in enumerate(chunk_text(ex["text"], chunk_size=chunk_size, overlap=chunk_overlap)):
            chunks.append({"uid": ex["uid"], "idx": idx, "text": piece, "meta": ex})
    rec["chunk_source"] = "ecs_platform.vectorstore.chunk_text"
    rec["chunk_time_ms"] = int((time.perf_counter() - t0) * 1000)
    rec["chunk_count"] = len(chunks)
    sizes = [len(c["text"]) for c in chunks]
    rec["avg_chunk_size"] = round((sum(sizes) / len(sizes)), 2) if sizes else 0.0
    rec["max_chunk_size"] = max(sizes) if sizes else 0
    rec["min_chunk_size"] = min(sizes) if sizes else 0

    # Step 4: Embeddings via ECS provider abstraction.
    provider = get_provider()
    rec["provider"] = type(provider).__name__.replace("Provider", "").lower()
    rec["model"] = getattr(provider, "model", "") or ""
    rec["embedding_source"] = "ecs_platform.llm_engine.provider.embed"
    rec["embedding_model"] = getattr(provider, "embedding_model", "") or ""
    t0 = time.perf_counter()
    embeddings = provider.embed([c["text"] for c in chunks]) if chunks else []
    rec["embedding_latency_ms"] = int((time.perf_counter() - t0) * 1000)
    rec["embedding_count"] = len(embeddings)
    rec["embedding_dimension"] = len(embeddings[0]) if embeddings else 0

    # Step 5: PGVector insert via ECS vectorstore.
    store = get_vector_store()
    store.init_store()
    run_id = f"neev-rag-{sc.key}-{uuid.uuid4().hex[:8]}"
    upserts: list[Chunk] = []
    for i, (c, emb) in enumerate(zip(chunks, embeddings)):
        upserts.append(
            Chunk(
                chunk_id=f"{run_id}:{c['uid']}:{c['idx']}:{i}",
                evidence_uid=str(c["uid"]),
                text=c["text"],
                embedding=emb,
                metadata={
                    "source_system": c["meta"]["source_system"],
                    "object_type": c["meta"]["object_type"],
                    "application": c["meta"]["application"],
                    "benchmark_run_id": run_id,
                },
            )
        )
    t0 = time.perf_counter()
    inserted = store.upsert(upserts) if upserts else 0
    rec["vector_source"] = "ecs_platform.vectorstore.pgvector_store"
    rec["vector_insert_latency_ms"] = int((time.perf_counter() - t0) * 1000)
    rec["vectors_inserted"] = inserted
    rec["vector_total"] = 0
    rec["database_size_bytes"] = None
    try:
        with store._connect().cursor() as cur:  # noqa: SLF001
            cur.execute(f"SELECT count(*) FROM {store._table}")  # noqa: SLF001
            rec["vector_total"] = int(cur.fetchone()[0])
            cur.execute("SELECT pg_database_size(current_database())")
            rec["database_size_bytes"] = int(cur.fetchone()[0])
    except Exception:
        pass

    # Step 6: Similarity search (Top-K).
    t0 = time.perf_counter()
    qemb = provider.embed([sc.query])[0]
    rec["query_embedding_ms"] = int((time.perf_counter() - t0) * 1000)
    t0 = time.perf_counter()
    hits = store.search(qemb, top_k=sc.top_k, filters={"benchmark_run_id": run_id})
    rec["retrieval_source"] = "ecs_platform.vectorstore.search"
    rec["retrieval_latency_ms"] = int((time.perf_counter() - t0) * 1000)
    rec["retrieved_chunks"] = len(hits)
    rec["retrieved_docs"] = len({h.evidence_uid for h in hits})
    rec["similarity_scores"] = [round(float(h.score), 6) for h in hits]

    # Step 7: Prompt builder.
    contexts = []
    for h in hits:
        meta = h.metadata or {}
        contexts.append(
            {
                "evidence_uid": h.evidence_uid,
                "source_system": meta.get("source_system", ""),
                "text": h.text,
                "metadata": meta,
            }
        )
    prompt = build_rag_prompt(sc.query, contexts)
    final_prompt = f"{SYSTEM_PROMPT}\n\n{prompt}"
    prompt_path = output_dir / "prompts" / f"{sc.key}.txt"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(final_prompt, encoding="utf-8")
    rec["prompt_builder_source"] = "ecs_platform.llm_engine.prompt_builder"
    rec["prompt_file"] = str(prompt_path)
    rec["prompt_characters"] = len(final_prompt)
    rec["estimated_input_tokens"] = _estimate_tokens(final_prompt)
    rec["estimated_input_source"] = "Prompt length heuristic (chars/4)"

    # Step 8: LLM generation via provider abstraction.
    rec["measured_input_tokens"] = None
    rec["measured_output_tokens"] = None
    rec["total_tokens"] = None
    rec["prompt_eval_count"] = None
    rec["eval_count"] = None
    rec["llm_latency_ms"] = None
    rec["llm_source"] = "ecs_platform.llm_engine.provider.generate_with_metadata"
    if not dry_run:
        t0 = time.perf_counter()
        try:
            _text, usage = provider.generate_with_metadata(prompt, system=SYSTEM_PROMPT)
            rec["llm_latency_ms"] = int((time.perf_counter() - t0) * 1000)
            rec["prompt_eval_count"] = usage.get("input_tokens")
            rec["eval_count"] = usage.get("output_tokens")
            rec["measured_input_tokens"] = usage.get("input_tokens")
            rec["measured_output_tokens"] = usage.get("output_tokens")
            rec["total_tokens"] = usage.get("total_tokens")
        except Exception as exc:  # noqa: BLE001
            rec["status"] = "ERROR"
            rec["error"] = f"{type(exc).__name__}: {exc}"
            rec["llm_latency_ms"] = int((time.perf_counter() - t0) * 1000)
    else:
        rec["status"] = "DRY_RUN"
        rec["error"] = ""

    return rec


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    cols = sorted({k for r in rows for k in r.keys()})
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def write_md(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Neev RAG Validation Benchmark",
        "",
        f"_Generated: {_utc_now()}_",
        "",
        "## Scope and Labels",
        "",
        "- MEASURED: provider/runtime metadata or timed stage measurements.",
        "- ESTIMATED: prompt-size heuristic only (chars/4).",
        "- Sources are explicitly recorded per stage: Object Storage/Repository, OCR/Text, Embedding, PGVector, Similarity Search, LLM.",
        "",
        "## Results",
        "",
        "| Scenario | Status | Files loaded | OCR ms | Chunk count | Embedding count | Embedding ms | Vector insert ms | Retrieval ms | Top-K | Prompt chars | Est. input | Measured input | Measured output | Total tokens | LLM ms | Overall ms |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in rows:
        overall = sum(
            int(r.get(k) or 0)
            for k in [
                "object_storage_load_ms",
                "ocr_time_ms",
                "chunk_time_ms",
                "embedding_latency_ms",
                "vector_insert_latency_ms",
                "retrieval_latency_ms",
                "llm_latency_ms",
            ]
        )
        lines.append(
            f"| {r.get('scenario','')} | {r.get('status','')} | {r.get('files_loaded',0)} | "
            f"{r.get('ocr_time_ms',0)} | {r.get('chunk_count',0)} | {r.get('embedding_count',0)} | "
            f"{r.get('embedding_latency_ms',0)} | {r.get('vector_insert_latency_ms',0)} | "
            f"{r.get('retrieval_latency_ms',0)} | {r.get('top_k',0)} | {r.get('prompt_characters',0)} | "
            f"{r.get('estimated_input_tokens','')} | {r.get('measured_input_tokens','')} | "
            f"{r.get('measured_output_tokens','')} | {r.get('total_tokens','')} | "
            f"{r.get('llm_latency_ms','')} | {overall} |"
        )
    lines += [
        "",
        "## Stage Source Mapping",
        "",
    ]
    for r in rows:
        lines += [
            f"- `{r.get('scenario','')}`: "
            f"Object Storage/Load={r.get('object_storage_source','')}; "
            f"OCR/Text={r.get('ocr_source','')}; "
            f"Chunking={r.get('chunk_source','')}; "
            f"Embedding={r.get('embedding_source','')}; "
            f"PGVector={r.get('vector_source','')}; "
            f"Similarity Search={r.get('retrieval_source','')}; "
            f"Prompt Builder={r.get('prompt_builder_source','')}; "
            f"LLM={r.get('llm_source','')}"
        ]
    path.write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run Neev full RAG validation benchmark.")
    p.add_argument(
        "--profiles",
        default="small",
        help=(
            "Comma-separated profiles or 'all'. Supported: "
            "small,medium,full,enterprise,large_repository_300,large_repository_500,large_repository_600"
        ),
    )
    p.add_argument("--top-k", type=int, default=20, help="Top-K retrieval depth.")
    p.add_argument("--num-ctx", type=int, default=None, help="Benchmark context window override.")
    p.add_argument("--max-output-tokens", type=int, default=512, help="Max generation tokens override.")
    p.add_argument("--provider", default=None, help="Provider override (ollama/gemini/openai/azure_openai/claude).")
    p.add_argument("--timeout-seconds", type=int, default=300, help="LLM request timeout.")
    p.add_argument("--dry-run", action="store_true", help="Skip LLM generation call.")
    p.add_argument("--output-dir", default="benchmark_outputs/neev_rag_validation", help="Output directory.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = _ensure_dir(args.output_dir)
    scenarios = _scenarios_from_profiles(args.profiles, args.top_k)

    rows: list[dict[str, Any]] = []
    for sc in scenarios:
        t0 = time.perf_counter()
        row = run_scenario(
            sc,
            dry_run=args.dry_run,
            provider_name=args.provider,
            num_ctx=args.num_ctx,
            max_output_tokens=args.max_output_tokens,
            timeout_seconds=args.timeout_seconds,
            output_dir=out,
        )
        row["overall_benchmark_duration_ms"] = int((time.perf_counter() - t0) * 1000)
        rows.append(row)
        print(
            f"[neev-rag-validation] scenario={sc.key} status={row.get('status')} "
            f"chunks={row.get('chunk_count')} retrieved={row.get('retrieved_chunks')} "
            f"in={row.get('measured_input_tokens')} out={row.get('measured_output_tokens')}"
        )

    write_csv(out / "neev_rag_validation_results.csv", rows)
    write_md(out / "neev_rag_validation_report.md", rows)
    (out / "neev_rag_validation_results.json").write_text(
        json.dumps({"generated_at": _utc_now(), "results": rows}, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    print(f"[neev-rag-validation] wrote artifacts to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
