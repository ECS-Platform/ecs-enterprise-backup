"""Neev production simulation benchmark (additive, no existing benchmark changes).

This benchmark simulates an enterprise production-like ECS pipeline:
Object Storage -> Evidence Repository -> Text/OCR stage -> Chunking -> Embeddings
-> PGVector -> Similarity Search -> Prompt Construction -> LLM.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class Profile:
    key: str
    evidence_docs: int
    top_k: int
    query: str


PROFILES_ORDER = [
    "small",
    "medium",
    "full",
    "enterprise",
    "large_repository_300",
    "large_repository_500",
    "large_repository_600",
]

DEFAULT_OUTPUT_DIR = "benchmark_outputs/neev_production_simulation"
HISTORY_MD = "neev_production_simulation_history.md"
HISTORY_CSV = "neev_production_simulation_history.csv"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dir(path: str) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _parse_profiles(raw: str) -> list[str]:
    values = [x.strip() for x in (raw or "small").split(",") if x.strip()]
    if not values:
        values = ["small"]
    if "all" in values:
        return list(PROFILES_ORDER)
    for v in values:
        if v not in PROFILES_ORDER:
            raise ValueError(f"Unknown profile '{v}'. Allowed: {', '.join(PROFILES_ORDER)} and all")
    return values


def _profile_catalog() -> dict[str, Profile]:
    return {
        "small": Profile(
            key="small",
            evidence_docs=50,
            top_k=20,
            query="Generate a consolidated enterprise readiness assessment with cited evidence and top risks.",
        ),
        "medium": Profile(
            key="medium",
            evidence_docs=100,
            top_k=20,
            query="Assess ISO 27001 control readiness and evidence sufficiency across in-scope applications.",
        ),
        "full": Profile(
            key="full",
            evidence_docs=250,
            top_k=20,
            query="Generate an audit readiness report with gaps, control observations, and remediation priorities.",
        ),
        "enterprise": Profile(
            key="enterprise",
            evidence_docs=500,
            top_k=20,
            query="Create an enterprise-wide compliance posture assessment and remediation roadmap for executive review.",
        ),
        "large_repository_300": Profile(
            key="large_repository_300",
            evidence_docs=300,
            top_k=20,
            query="Build a cross-application governance risk summary with prioritized control failures and owners.",
        ),
        "large_repository_500": Profile(
            key="large_repository_500",
            evidence_docs=500,
            top_k=20,
            query="Provide Pan India enterprise compliance readiness summary with framework-level control mapping and risks.",
        ),
        "large_repository_600": Profile(
            key="large_repository_600",
            evidence_docs=600,
            top_k=20,
            query="Generate a nationwide enterprise remediation and audit preparedness narrative with evidence citations.",
        ),
    }


def _estimate_tokens(text: str, chars_per_token: float = 4.0) -> int:
    return int(max(1, round(len(text or "") / chars_per_token)))


def _section_text(title: str, bullets: list[str]) -> str:
    lines = [f"{title}:", ""]
    lines.extend(f"- {b}" for b in bullets)
    lines.append("")
    return "\n".join(lines)


def _synthetic_document(i: int, profile_key: str, rng: random.Random) -> dict[str, Any]:
    doc_types = [
        ("SOC 2 Assessment", "soc_report"),
        ("ISO 27001 Control Evidence", "iso_evidence"),
        ("Firewall Rule Review", "firewall_review"),
        ("IAM Privileged Access Review", "iam_report"),
        ("Vulnerability Scan Report", "vuln_report"),
        ("Internal Audit Observation", "audit_observation"),
        ("Control Effectiveness Evidence", "control_evidence"),
        ("Application Inventory Snapshot", "app_inventory"),
        ("Infrastructure Security Scan", "infra_scan"),
        ("Patch Compliance Report", "patch_report"),
        ("Configuration Compliance Review", "config_review"),
    ]
    frameworks = ["ISO27001", "SOC2", "NIST-CSF", "RBI-CSF", "PCI-DSS"]
    apps = [
        "CoreBanking", "UPI-Switch", "InternetBanking", "MobileBanking",
        "TreasuryPlatform", "LoanManagement", "CardProcessing", "HRMS",
        "PaymentsGateway", "DataWarehouse", "SIEM", "IAM",
    ]
    regions = ["Mumbai", "Delhi", "Bengaluru", "Chennai", "Hyderabad", "Kolkata"]
    dtype, object_type = doc_types[i % len(doc_types)]
    app = apps[i % len(apps)]
    framework = frameworks[i % len(frameworks)]
    region = regions[i % len(regions)]
    severity = ["Low", "Medium", "High", "Critical"][i % 4]
    score = 50 + (i % 45)

    sections: list[str] = []
    sections.append(_section_text("Executive Summary", [
        f"{dtype} for application {app} in {region} region.",
        f"Framework alignment references {framework} controls and enterprise policy baseline.",
        f"Risk score recorded at {score}/100 with severity {severity}.",
    ]))
    sections.append(_section_text("Scope and Metadata", [
        f"Profile: {profile_key}",
        f"Application: {app}",
        f"Region: {region}",
        f"Business Unit: Banking Operations",
        f"Control Owner: owner_{(i % 25) + 1}@example.com",
    ]))
    sections.append(_section_text("Control Mapping", [
        f"{framework}-CTRL-{(i % 80) + 1:03d} evidence available.",
        f"{framework}-CTRL-{(i % 80) + 2:03d} requires remediation tracking.",
        f"Mapped policy references: Policy-{(i % 35) + 1:03d}.",
    ]))
    sections.append(_section_text("Observations", [
        f"Observation {i+1}-A: deviation in access governance approval workflow.",
        f"Observation {i+1}-B: periodic review frequency exceeded policy threshold by {(i % 7) + 1} days.",
        "Observation notes include audit trace references and timestamped evidence links.",
    ]))
    sections.append(_section_text("Audit Comments", [
        "Prior cycle auditors requested tighter exception governance controls.",
        "Sampling showed mixed remediation closure quality across applications.",
        "Evidence completeness improved compared to previous quarter.",
    ]))
    sections.append(_section_text("Remediation History", [
        f"Action-{i+1}-1 completed for baseline hardening.",
        f"Action-{i+1}-2 in progress for privileged access recertification.",
        "Residual risk accepted temporarily with CIO approval token.",
    ]))
    sections.append(_section_text("Risk Summary", [
        f"Primary risk theme: {dtype.lower()} related control drift.",
        f"Potential impact: service continuity and compliance penalty exposure for {app}.",
        f"Recommended priority: {'Immediate' if severity in ('High', 'Critical') else 'Planned'}",
    ]))

    noise = " ".join(
        f"evidence-marker-{profile_key}-{i}-{j}-control-{rng.randint(1,999)}"
        for j in range(80)
    )
    content = "\n".join(sections) + "\nAppendix:\n" + noise + "\n"
    title = f"{dtype} - {app} - {framework} - Doc {i+1}"

    return {
        "title": title,
        "content": content,
        "object_type": object_type,
        "application": app,
        "framework": framework,
        "region": region,
        "owner": f"owner_{(i % 25) + 1}@example.com",
        "control_mapping": [f"{framework}-CTRL-{(i % 80) + 1:03d}", f"{framework}-CTRL-{(i % 80) + 2:03d}"],
        "framework_mapping": [framework],
    }


def _generate_documents(profile: Profile, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed + hash(profile.key))
    return [_synthetic_document(i, profile.key, rng) for i in range(profile.evidence_docs)]


def _object_store_upload(
    profile: Profile,
    docs: list[dict[str, Any]],
    out_dir: Path,
) -> dict[str, Any]:
    from ecs_platform.config import load_repository_config, resolve_secret

    cfg = (load_repository_config().get("repository", {}) or {}).get("object_store", {})
    enabled = bool(cfg.get("enabled", True))
    endpoint = str(cfg.get("endpoint", "minio:9000"))
    bucket = str(cfg.get("bucket", "ecs-evidence"))
    secure = bool(cfg.get("secure", False))
    access_key = resolve_secret(str(cfg.get("access_key_env", "MINIO_ACCESS_KEY")))
    secret_key = resolve_secret(str(cfg.get("secret_key_env", "MINIO_SECRET_KEY")))

    total_bytes = 0
    t0 = time.perf_counter()
    uploaded = 0
    mode = "local_filesystem_fallback"
    fallback_reason = ""
    base_uri = ""

    if enabled:
        try:
            import boto3  # type: ignore
            from botocore.client import Config  # type: ignore

            endpoint_url = f"http{'s' if secure else ''}://{endpoint}"
            client = boto3.client(
                "s3",
                endpoint_url=endpoint_url,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                config=Config(signature_version="s3v4"),
                region_name="us-east-1",
            )
            try:
                client.head_bucket(Bucket=bucket)
            except Exception:
                client.create_bucket(Bucket=bucket)
            for idx, doc in enumerate(docs):
                key = f"benchmarks/neev-production/{profile.key}/{idx:05d}.txt"
                body = doc["content"].encode("utf-8")
                total_bytes += len(body)
                client.put_object(Bucket=bucket, Key=key, Body=body, ContentType="text/plain")
                uploaded += 1
            mode = "minio"
            base_uri = f"{endpoint_url}/{bucket}/benchmarks/neev-production/{profile.key}/"
        except Exception as exc:  # noqa: BLE001
            fallback_reason = str(exc)

    if mode != "minio":
        local_dir = out_dir / "object_store_fallback" / profile.key
        local_dir.mkdir(parents=True, exist_ok=True)
        for idx, doc in enumerate(docs):
            p = local_dir / f"{idx:05d}.txt"
            payload = doc["content"].encode("utf-8")
            total_bytes += len(payload)
            p.write_bytes(payload)
            uploaded += 1
        base_uri = str(local_dir)

    return {
        "object_storage_mode": mode,
        "object_storage_fallback_reason": fallback_reason,
        "object_storage_upload_latency_ms": int((time.perf_counter() - t0) * 1000),
        "object_storage_object_count": uploaded,
        "object_storage_total_bytes": total_bytes,
        "object_storage_uri": base_uri,
    }


def _insert_repository(profile: Profile, docs: list[dict[str, Any]], object_store_uri: str) -> dict[str, Any]:
    from ecs_platform.repository import EvidenceRepository

    run_id = f"neev-prod-{profile.key}-{uuid.uuid4().hex[:8]}"
    items: list[dict[str, Any]] = []
    for idx, doc in enumerate(docs):
        uid = f"{run_id}-{idx:05d}"
        items.append({
            "evidence_uid": uid,
            "source_system": "neev_benchmark",
            "source_object_id": f"{profile.key}:{idx:05d}",
            "object_type": doc["object_type"],
            "title": doc["title"],
            "content": doc["content"],
            "owner": doc["owner"],
            "url": f"{object_store_uri.rstrip('/')}/{idx:05d}.txt",
            "application": doc["application"],
            "metadata": {
                "benchmark_run_id": run_id,
                "profile": profile.key,
                "framework": doc["framework"],
                "region": doc["region"],
            },
            "control_mapping": doc["control_mapping"],
            "framework_mapping": doc["framework_mapping"],
        })

    t0 = time.perf_counter()
    with EvidenceRepository() as repo:
        inserted = repo.bulk_upsert(items)
    insert_ms = int((time.perf_counter() - t0) * 1000)

    t0 = time.perf_counter()
    with EvidenceRepository() as repo:
        loaded = repo.search_evidence(source_system="neev_benchmark", limit=len(items) + 20)
        selected = [r for r in loaded if r.get("evidence_uid", "").startswith(run_id)]
        full_rows = [repo.evidence_by_uid(r["evidence_uid"]) for r in selected]
    load_ms = int((time.perf_counter() - t0) * 1000)

    return {
        "benchmark_run_id": run_id,
        "repository_insert_time_ms": insert_ms,
        "repository_load_time_ms": load_ms,
        "repository_inserted_count": inserted,
        "repository_loaded_count": len([r for r in full_rows if r]),
        "repository_rows": [r for r in full_rows if r],
    }


def _chunk_embed_index(rows: list[dict[str, Any]], run_id: str) -> dict[str, Any]:
    from ecs_platform.config import load_vectorstore_config
    from ecs_platform.llm_engine.provider import get_provider
    from ecs_platform.vectorstore import Chunk, chunk_text, get_vector_store

    chunk_cfg = (load_vectorstore_config().get("vectorstore", {}) or {}).get("chunking", {})
    chunk_size = int(chunk_cfg.get("chunk_size", 1000))
    overlap = int(chunk_cfg.get("chunk_overlap", 150))

    t0 = time.perf_counter()
    extracted = []
    for row in rows:
        text = (row.get("content") or "").strip()
        extracted.append({"uid": row.get("evidence_uid", ""), "text": text, "row": row})
    ocr_ms = int((time.perf_counter() - t0) * 1000)
    extracted_chars = sum(len(x["text"]) for x in extracted)
    extracted_words = sum(len((x["text"] or "").split()) for x in extracted)

    t0 = time.perf_counter()
    chunks: list[dict[str, Any]] = []
    for ex in extracted:
        parts = chunk_text(ex["text"], chunk_size=chunk_size, overlap=overlap)
        for idx, part in enumerate(parts):
            chunks.append({
                "chunk_id": f"{run_id}:{ex['uid']}:{idx}",
                "evidence_uid": ex["uid"],
                "text": part,
                "metadata": {
                    "benchmark_run_id": run_id,
                    "source_system": ex["row"].get("source_system", ""),
                    "object_type": ex["row"].get("object_type", ""),
                    "application": ex["row"].get("application", ""),
                    "framework": (ex["row"].get("metadata", {}) or {}).get("framework", ""),
                },
            })
    chunk_ms = int((time.perf_counter() - t0) * 1000)
    sizes = [len(c["text"]) for c in chunks]

    provider = get_provider()
    t0 = time.perf_counter()
    embeddings = provider.embed([c["text"] for c in chunks]) if chunks else []
    emb_ms = int((time.perf_counter() - t0) * 1000)
    emb_dim = len(embeddings[0]) if embeddings else 0

    store = get_vector_store()
    store.init_store()
    payload = [
        Chunk(
            chunk_id=c["chunk_id"],
            evidence_uid=c["evidence_uid"],
            text=c["text"],
            embedding=emb,
            metadata=c["metadata"],
        )
        for c, emb in zip(chunks, embeddings)
    ]
    t0 = time.perf_counter()
    inserted = store.upsert(payload) if payload else 0
    vector_insert_ms = int((time.perf_counter() - t0) * 1000)

    total_vectors = 0
    db_size = None
    try:
        with store._connect().cursor() as cur:  # noqa: SLF001
            cur.execute(f"SELECT count(*) FROM {store._table}")  # noqa: SLF001
            total_vectors = int(cur.fetchone()[0])
            cur.execute("SELECT pg_database_size(current_database())")
            db_size = int(cur.fetchone()[0])
    except Exception:
        pass

    return {
        "provider": provider,
        "vector_store": store,
        "ocr_time_ms": ocr_ms,
        "extracted_characters": extracted_chars,
        "extracted_words": extracted_words,
        "documents_processed": len(extracted),
        "chunk_count": len(chunks),
        "avg_chunk_size": round((sum(sizes) / len(sizes)), 2) if sizes else 0.0,
        "largest_chunk": max(sizes) if sizes else 0,
        "smallest_chunk": min(sizes) if sizes else 0,
        "embedding_model": getattr(provider, "embedding_model", ""),
        "embedding_dimension": emb_dim,
        "embedding_count": len(embeddings),
        "embedding_latency_ms": emb_ms,
        "vectors_inserted": inserted,
        "vector_insert_latency_ms": vector_insert_ms,
        "total_vectors": total_vectors,
        "database_size_bytes": db_size,
    }


def _retrieve(profile: Profile, provider: Any, store: Any, run_id: str) -> dict[str, Any]:
    t0 = time.perf_counter()
    qvec = provider.embed([profile.query])[0]
    query_embed_ms = int((time.perf_counter() - t0) * 1000)

    t0 = time.perf_counter()
    hits = store.search(qvec, top_k=profile.top_k, filters={"benchmark_run_id": run_id})
    retrieve_ms = int((time.perf_counter() - t0) * 1000)

    return {
        "query_embedding_latency_ms": query_embed_ms,
        "retrieval_latency_ms": retrieve_ms,
        "retrieved_chunk_count": len(hits),
        "retrieved_doc_count": len({h.evidence_uid for h in hits}),
        "similarity_scores": [round(float(h.score), 6) for h in hits],
        "hits": hits,
    }


def _build_production_prompt(profile: Profile, hits: list[Any]) -> dict[str, Any]:
    from ecs_platform.llm_engine.prompt_builder import SYSTEM_PROMPT

    contexts = []
    for idx, h in enumerate(hits, start=1):
        m = h.metadata or {}
        contexts.append(
            f"[E{idx}] app={m.get('application','?')} framework={m.get('framework','?')} "
            f"type={m.get('object_type','?')} uid={h.evidence_uid}\n{h.text}"
        )

    evidence_section = "\n\n".join(contexts)
    app_set = sorted({(h.metadata or {}).get("application", "unknown") for h in hits})
    fw_set = sorted({(h.metadata or {}).get("framework", "unknown") for h in hits})

    sections: dict[str, str] = {
        "system_prompt": SYSTEM_PROMPT,
        "user_request": profile.query,
        "application_metadata": (
            f"Applications in scope: {', '.join(app_set[:30])}\n"
            f"Repository profile: {profile.key}\n"
            f"Total retrieved documents: {len({h.evidence_uid for h in hits})}"
        ),
        "business_metadata": (
            "Business context: Pan India enterprise operations across retail banking, "
            "payments, treasury, and shared services.\n"
            "Regulatory context: RBI expectations, internal audit obligations, and board-level reporting."
        ),
        "framework_catalogue": (
            f"Frameworks referenced: {', '.join(fw_set[:20])}\n"
            "Controls to assess: preventive, detective, and corrective control effectiveness."
        ),
        "control_mappings": (
            "Map findings to control IDs, owners, residual risks, and due dates where evidence allows."
        ),
        "retrieved_evidence": evidence_section,
        "historical_observations": (
            "Historical observations include repeated IAM exception patterns, delayed patch closure, "
            "and inconsistent approval evidence for privileged access."
        ),
        "previous_audit_comments": (
            "Prior audit comments requested stronger root-cause analysis, measurable remediation evidence, "
            "and clearer accountability mapping."
        ),
        "risk_summaries": (
            "Summarize critical, high, medium risk concentration by application and control domain."
        ),
        "remediation_history": (
            "Reference prior completed remediation actions and unresolved backlog trends."
        ),
        "executive_reporting_instructions": (
            "Produce board-ready summary: top risks, control posture, remediation priority, "
            "regulatory readiness, and immediate actions."
        ),
        "output_format_instructions": (
            "Output sections: Executive Summary, Control Posture, Risk Breakdown, "
            "Remediation Roadmap, Open Questions. Cite evidence as [E#]."
        ),
    }

    user_prompt = "\n\n".join(
        f"{name.replace('_', ' ').title()}:\n{text}" for name, text in sections.items() if name != "system_prompt"
    )
    final_prompt = f"{sections['system_prompt']}\n\n{user_prompt}"

    breakdown = {}
    for name, text in sections.items():
        chars = len(text)
        breakdown[name] = {
            "chars": chars,
            "bytes": len(text.encode("utf-8")),
            "estimated_tokens": _estimate_tokens(text),
        }

    return {
        "system_prompt": sections["system_prompt"],
        "user_prompt": user_prompt,
        "final_prompt": final_prompt,
        "prompt_characters": len(final_prompt),
        "prompt_bytes": len(final_prompt.encode("utf-8")),
        "estimated_tokens": _estimate_tokens(final_prompt),
        "prompt_section_breakdown": breakdown,
    }


def _run_llm(
    *,
    provider: Any,
    system_prompt: str,
    user_prompt: str,
    dry_run: bool,
    max_output_tokens: int,
    timeout_seconds: int,
) -> dict[str, Any]:
    from ecs_platform.llm_engine.provider import set_benchmark_generation_config

    set_benchmark_generation_config(num_predict=max_output_tokens, timeout_seconds=timeout_seconds)

    if dry_run:
        return {
            "status": "DRY_RUN",
            "response_text": "",
            "prompt_eval_count": None,
            "eval_count": None,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "llm_latency_ms": None,
            "early_termination": False,
            "error": "",
        }

    t0 = time.perf_counter()
    try:
        text, usage = provider.generate_with_metadata(user_prompt, system=system_prompt)
        latency = int((time.perf_counter() - t0) * 1000)
        out_tokens = int(usage.get("output_tokens", 0) or 0)
        early = out_tokens < 50
        return {
            "status": "EARLY_TERMINATION" if early else "MEASURED",
            "response_text": text or "",
            "prompt_eval_count": usage.get("input_tokens"),
            "eval_count": usage.get("output_tokens"),
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "total_tokens": usage.get("total_tokens"),
            "llm_latency_ms": latency,
            "early_termination": early,
            "error": "",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "ERROR",
            "response_text": "",
            "prompt_eval_count": None,
            "eval_count": None,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "llm_latency_ms": int((time.perf_counter() - t0) * 1000),
            "early_termination": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def _estimate_neev_recommendation(results: list[dict[str, Any]]) -> dict[str, Any]:
    measured = [r for r in results if r.get("status") == "MEASURED" and r.get("input_tokens") and r.get("output_tokens")]
    if not measured:
        return {
            "estimated_gemini_input_tokens": None,
            "estimated_gemini_output_tokens": None,
            "estimated_gemini_total_tokens": None,
            "recommended_input_tokens_with_headroom": None,
            "recommended_output_tokens_with_headroom": None,
        }
    peak_in = max(int(r["input_tokens"]) for r in measured)
    peak_out = max(int(r["output_tokens"]) for r in measured)
    return {
        "estimated_gemini_input_tokens": peak_in,
        "estimated_gemini_output_tokens": peak_out,
        "estimated_gemini_total_tokens": peak_in + peak_out,
        "recommended_input_tokens_with_headroom": int(round(peak_in * 1.25)),
        "recommended_output_tokens_with_headroom": int(round(peak_out * 1.25)),
    }


def _append_history(out_dir: Path, rows: list[dict[str, Any]]) -> None:
    md_path = out_dir / HISTORY_MD
    csv_path = out_dir / HISTORY_CSV

    new_md = not md_path.exists()
    with md_path.open("a", encoding="utf-8") as fh:
        if new_md:
            fh.write("# Neev Production Simulation History\n\n")
        fh.write(f"## Run @ {_utc_now()}\n\n")
        for r in rows:
            fh.write(
                f"- `{r.get('scenario')}` status={r.get('status')} files={r.get('total_evidence')} "
                f"chunks={r.get('total_chunks')} in={r.get('measured_input_tokens')} "
                f"out={r.get('measured_output_tokens')} total={r.get('total_tokens')}\n"
            )
        fh.write("\n")

    cols = sorted({k for r in rows for k in r.keys()})
    new_csv = not csv_path.exists()
    with csv_path.open("a", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        if new_csv:
            w.writeheader()
        for r in rows:
            w.writerow(r)


def _write_outputs(out_dir: Path, rows: list[dict[str, Any]], payload: dict[str, Any]) -> None:
    csv_path = out_dir / "neev_production_simulation_results.csv"
    json_path = out_dir / "neev_production_simulation_results.json"
    md_path = out_dir / "neev_production_simulation_report.md"

    cols = sorted({k for r in rows for k in r.keys()})
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)

    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")

    lines = [
        "# Neev Production Simulation Benchmark",
        "",
        f"_Generated: {_utc_now()}_",
        "",
        "| Scenario | Status | Evidence | Chunks | Embeddings | Vectors | Retrieved chunks | Prompt chars | Measured input | Measured output | Total tokens | Pipeline latency ms |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in rows:
        lines.append(
            f"| {r.get('scenario')} | {r.get('status')} | {r.get('total_evidence')} | {r.get('total_chunks')} | "
            f"{r.get('embedding_count')} | {r.get('vector_count')} | {r.get('retrieved_chunks')} | "
            f"{r.get('prompt_characters')} | {r.get('measured_input_tokens')} | {r.get('measured_output_tokens')} | "
            f"{r.get('total_tokens')} | {r.get('pipeline_latency_ms')} |"
        )
    recommendation = payload.get("recommendation", {})
    lines += [
        "",
        "## Estimated Gemini Production Tokens",
        "",
        f"- Estimated input tokens: {recommendation.get('estimated_gemini_input_tokens')}",
        f"- Estimated output tokens: {recommendation.get('estimated_gemini_output_tokens')}",
        f"- Estimated total tokens: {recommendation.get('estimated_gemini_total_tokens')}",
        "",
        "## Neev Planning Recommendation",
        "",
        f"- Recommended input tokens (+25% headroom): {recommendation.get('recommended_input_tokens_with_headroom')}",
        f"- Recommended output tokens (+25% headroom): {recommendation.get('recommended_output_tokens_with_headroom')}",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")


def run_profile(profile: Profile, args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    t_pipeline = time.perf_counter()
    docs = _generate_documents(profile, seed=args.seed)

    object_stage = _object_store_upload(profile, docs, out_dir)
    repo_stage = _insert_repository(profile, docs, object_stage["object_storage_uri"])
    process_stage = _chunk_embed_index(repo_stage["repository_rows"], repo_stage["benchmark_run_id"])
    retrieve_stage = _retrieve(profile, process_stage["provider"], process_stage["vector_store"], repo_stage["benchmark_run_id"])
    prompt_stage = _build_production_prompt(profile, retrieve_stage["hits"])

    prompt_file = out_dir / "prompts" / f"{profile.key}.txt"
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    prompt_file.write_text(prompt_stage["final_prompt"], encoding="utf-8")

    llm_stage = _run_llm(
        provider=process_stage["provider"],
        system_prompt=prompt_stage["system_prompt"],
        user_prompt=prompt_stage["user_prompt"],
        dry_run=args.dry_run,
        max_output_tokens=args.max_output_tokens,
        timeout_seconds=args.timeout_seconds,
    )

    provider_name = type(process_stage["provider"]).__name__.replace("Provider", "").lower()
    model_name = getattr(process_stage["provider"], "model", "")

    row = {
        "timestamp": _utc_now(),
        "scenario": profile.key,
        "provider": provider_name,
        "model": model_name,
        "status": llm_stage["status"],
        "object_storage_mode": object_stage["object_storage_mode"],
        "object_storage_upload_latency_ms": object_stage["object_storage_upload_latency_ms"],
        "object_storage_object_count": object_stage["object_storage_object_count"],
        "object_storage_total_bytes": object_stage["object_storage_total_bytes"],
        "repository_insert_time_ms": repo_stage["repository_insert_time_ms"],
        "repository_load_time_ms": repo_stage["repository_load_time_ms"],
        "total_evidence": repo_stage["repository_loaded_count"],
        "ocr_time_ms": process_stage["ocr_time_ms"],
        "extracted_characters": process_stage["extracted_characters"],
        "extracted_words": process_stage["extracted_words"],
        "documents_processed": process_stage["documents_processed"],
        "total_chunks": process_stage["chunk_count"],
        "avg_chunk_size": process_stage["avg_chunk_size"],
        "largest_chunk": process_stage["largest_chunk"],
        "smallest_chunk": process_stage["smallest_chunk"],
        "embedding_model": process_stage["embedding_model"],
        "embedding_dimension": process_stage["embedding_dimension"],
        "embedding_count": process_stage["embedding_count"],
        "embedding_latency_ms": process_stage["embedding_latency_ms"],
        "vectors_inserted": process_stage["vectors_inserted"],
        "vector_insert_latency_ms": process_stage["vector_insert_latency_ms"],
        "vector_count": process_stage["total_vectors"],
        "database_size_bytes": process_stage["database_size_bytes"],
        "retrieval_latency_ms": retrieve_stage["retrieval_latency_ms"],
        "retrieved_chunks": retrieve_stage["retrieved_chunk_count"],
        "retrieved_docs": retrieve_stage["retrieved_doc_count"],
        "similarity_scores_json": json.dumps(retrieve_stage["similarity_scores"], ensure_ascii=True),
        "top_k": profile.top_k,
        "prompt_characters": prompt_stage["prompt_characters"],
        "prompt_bytes": prompt_stage["prompt_bytes"],
        "estimated_tokens": prompt_stage["estimated_tokens"],
        "prompt_section_breakdown_json": json.dumps(prompt_stage["prompt_section_breakdown"], ensure_ascii=True),
        "measured_input_tokens": llm_stage["input_tokens"],
        "measured_output_tokens": llm_stage["output_tokens"],
        "prompt_eval_count": llm_stage["prompt_eval_count"],
        "eval_count": llm_stage["eval_count"],
        "total_tokens": llm_stage["total_tokens"],
        "llm_latency_ms": llm_stage["llm_latency_ms"],
        "early_termination": llm_stage["early_termination"],
        "pipeline_latency_ms": int((time.perf_counter() - t_pipeline) * 1000),
        "error": llm_stage["error"],
        "prompt_file": str(prompt_file),
    }
    return row


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run Neev production simulation benchmark.")
    p.add_argument("--profiles", default="small", help="Comma-separated profiles or --profiles all.")
    p.add_argument("--top-k", type=int, default=20, help="Top-K retrieval override.")
    p.add_argument("--num-ctx", type=int, default=None, help="Optional context window override.")
    p.add_argument("--max-output-tokens", type=int, default=4096, help="LLM max output tokens.")
    p.add_argument("--provider", default=None, help="Optional provider override.")
    p.add_argument("--timeout-seconds", type=int, default=600, help="LLM timeout seconds.")
    p.add_argument("--dry-run", action="store_true", help="Run full pipeline except LLM generation.")
    p.add_argument("--seed", type=int, default=1234, help="Deterministic synthetic generation seed.")
    p.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Output directory.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.provider:
        os.environ["ECS_LLM_PROVIDER"] = str(args.provider)
    if args.num_ctx:
        os.environ["ECS_LLM_CONTEXT_WINDOW"] = str(args.num_ctx)
    if args.timeout_seconds:
        os.environ["ECS_LLM_TIMEOUT_SECONDS"] = str(args.timeout_seconds)

    out_dir = _ensure_dir(args.output_dir)
    selected = _parse_profiles(args.profiles)
    catalog = _profile_catalog()

    rows: list[dict[str, Any]] = []
    for key in selected:
        profile = catalog[key]
        if args.top_k and args.top_k > 0:
            profile = Profile(key=profile.key, evidence_docs=profile.evidence_docs, top_k=args.top_k, query=profile.query)
        row = run_profile(profile, args, out_dir)
        rows.append(row)
        print(
            f"[neev-production-sim] scenario={key} status={row['status']} "
            f"evidence={row['total_evidence']} chunks={row['total_chunks']} "
            f"in={row['measured_input_tokens']} out={row['measured_output_tokens']}"
        )

    recommendation = _estimate_neev_recommendation(rows)
    payload = {
        "generated_at": _utc_now(),
        "profiles": selected,
        "results": rows,
        "recommendation": recommendation,
        "labels": {
            "MEASURED": "Provider/runtime measured values.",
            "ESTIMATED": "Heuristic values (chars/token approximation).",
            "EARLY_TERMINATION": "Output too short to represent realistic enterprise response.",
        },
    }

    _write_outputs(out_dir, rows, payload)
    _append_history(out_dir, rows)
    print(f"[neev-production-sim] wrote outputs to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
