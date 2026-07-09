"""Detailed per-workload CPU and RAM estimators for the ECS infra benchmark.

Extends the coarse GKE compute estimate in ``sizing.py`` with a **per-workload
breakdown** (PART 2 CPU, PART 3 RAM of the infrastructure benchmark): the CPU-ms
and RAM cost of each ECS operation class (REST, auth, RBAC, connector parse,
evidence normalize, SHA-256, validation, upload, scheduler, DLQ, DB Agent, query,
prompt, embedding, vector search, JSON/CSV/Excel/PDF parsing, ZIP/compression,
report gen, background workers, health checks).

Pure arithmetic over documented per-unit constants (``WorkloadConstants``) x the
scenario profile's activity counts. No measurement, no network, no ECS calls —
calibrate the constants from real benchmark runs for production accuracy.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from benchmarks.capacity.profiles import CapacityProfile


def _round(x: float, n: int = 3) -> float:
    return round(float(x), n)


@dataclass
class WorkloadConstants:
    """Per-operation CPU (millicores-ms) + RAM (MiB) unit costs (documented, tunable)."""

    # ---- Request path (per API request) ----
    cpu_ms_rest_request: float = 20.0
    cpu_ms_authentication: float = 8.0     # JWT/OIDC verify
    cpu_ms_authorization: float = 3.0      # RBAC decision
    cpu_ms_rbac_scope: float = 2.0         # scope filtering
    cpu_ms_health_check: float = 1.0
    ram_mib_rest_request: float = 3.0
    ram_mib_auth_context: float = 1.0

    # ---- Connector execution (per connector run) ----
    cpu_ms_connector_fetch: float = 300.0
    cpu_ms_connector_parse: float = 250.0
    cpu_ms_evidence_normalize: float = 120.0
    cpu_ms_metadata_extract: float = 60.0
    cpu_ms_sha256_hash: float = 15.0       # per evidence object
    cpu_ms_evidence_validate: float = 90.0
    cpu_ms_evidence_upload: float = 80.0
    ram_mib_connector_run: float = 48.0
    ram_mib_evidence_object: float = 8.0

    # ---- Scheduler (per job) ----
    cpu_ms_scheduler_dispatch: float = 120.0
    cpu_ms_retry_queue: float = 20.0
    cpu_ms_dead_letter: float = 15.0
    ram_mib_scheduler_worker: float = 24.0
    ram_mib_queue_item: float = 0.5

    # ---- Database Agent + query (per query) ----
    cpu_ms_db_connect: float = 40.0
    cpu_ms_db_query: float = 150.0
    cpu_ms_db_agent_overhead: float = 60.0
    ram_mib_db_pool: float = 32.0
    ram_mib_query_result: float = 6.0

    # ---- LLM / RAG (per prompt run) ----
    cpu_ms_prompt_assemble: float = 200.0
    cpu_ms_embedding_generate: float = 400.0   # per prompt (query embedding)
    cpu_ms_vector_search: float = 120.0
    cpu_ms_prompt_execute: float = 900.0       # deterministic + orchestration (LLM is separate pool)
    ram_mib_prompt_context: float = 192.0
    ram_mib_embedding_buffer: float = 24.0

    # ---- Parsing / packaging (per relevant unit) ----
    cpu_ms_json_parse: float = 5.0             # per API request payload
    cpu_ms_csv_parse: float = 12.0             # per bulk upload
    cpu_ms_excel_parse: float = 60.0           # per Excel evidence
    cpu_ms_pdf_parse: float = 40.0             # per PDF evidence
    cpu_ms_zip_generate: float = 50.0          # per export
    cpu_ms_compression: float = 25.0           # per export
    cpu_ms_report_generate: float = 80.0       # per report
    cpu_ms_background_worker: float = 30.0     # per scheduler job (async)

    # ---- Shares of activity that hit parse/package paths ----
    excel_fraction_of_evidence: float = 0.10
    pdf_fraction_of_evidence: float = 0.25
    bulk_uploads_per_day_factor: float = 0.05  # of connector runs
    exports_per_day: float = 20.0
    reports_per_day_factor: float = 0.5        # of prompt runs

    working_hours_per_day: float = 9.0
    peak_to_average_factor: float = 3.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_overrides(cls, overrides: dict[str, Any] | None) -> "WorkloadConstants":
        overrides = overrides or {}
        known = {k: overrides[k] for k in overrides if k in cls.__dataclass_fields__}
        return cls(**known)


def _daily_evidence_touch(p: CapacityProfile) -> float:
    """Evidence objects processed per day (connector-driven, rough)."""
    # Each connector run yields several evidence objects on average.
    return p.connector_runs_per_day * 5.0


def cpu_breakdown(p: CapacityProfile, c: WorkloadConstants | None = None) -> dict[str, Any]:
    """Per-workload daily CPU cost (core-hours) for every operation class (PART 2)."""
    c = c or WorkloadConstants()
    api = p.api_requests_per_day
    conn = p.connector_runs_per_day
    jobs = p.scheduler_jobs_per_day
    prompts = p.prompt_runs_per_day
    ev_day = _daily_evidence_touch(p)
    queries = p.connector_runs_per_day + p.scheduler_jobs_per_day  # DB-Agent + predefined
    bulk = conn * c.bulk_uploads_per_day_factor
    reports = prompts * c.reports_per_day_factor

    # (label, count, cpu_ms_per_unit)
    items: list[tuple[str, float, float]] = [
        ("rest_api", api, c.cpu_ms_rest_request),
        ("authentication", api, c.cpu_ms_authentication),
        ("authorization", api, c.cpu_ms_authorization),
        ("rbac_scope", api, c.cpu_ms_rbac_scope),
        ("json_parse", api, c.cpu_ms_json_parse),
        ("health_checks", api * 0.1, c.cpu_ms_health_check),
        ("connector_fetch", conn, c.cpu_ms_connector_fetch),
        ("connector_parse", conn, c.cpu_ms_connector_parse),
        ("evidence_normalize", ev_day, c.cpu_ms_evidence_normalize),
        ("metadata_extract", ev_day, c.cpu_ms_metadata_extract),
        ("sha256_hash", ev_day, c.cpu_ms_sha256_hash),
        ("evidence_validate", ev_day, c.cpu_ms_evidence_validate),
        ("evidence_upload", ev_day, c.cpu_ms_evidence_upload),
        ("scheduler_dispatch", jobs, c.cpu_ms_scheduler_dispatch),
        ("retry_queue", jobs * 0.2, c.cpu_ms_retry_queue),
        ("dead_letter_queue", jobs * 0.05, c.cpu_ms_dead_letter),
        ("background_workers", jobs, c.cpu_ms_background_worker),
        ("db_connect", queries, c.cpu_ms_db_connect),
        ("db_query", queries, c.cpu_ms_db_query),
        ("db_agent_overhead", p.connector_runs_per_day, c.cpu_ms_db_agent_overhead),
        ("prompt_assemble", prompts, c.cpu_ms_prompt_assemble),
        ("embedding_generate", prompts, c.cpu_ms_embedding_generate),
        ("vector_search", prompts, c.cpu_ms_vector_search),
        ("prompt_execute", prompts, c.cpu_ms_prompt_execute),
        ("csv_parse", bulk, c.cpu_ms_csv_parse),
        ("excel_parse", ev_day * c.excel_fraction_of_evidence, c.cpu_ms_excel_parse),
        ("pdf_parse", ev_day * c.pdf_fraction_of_evidence, c.cpu_ms_pdf_parse),
        ("zip_generate", c.exports_per_day, c.cpu_ms_zip_generate),
        ("compression", c.exports_per_day, c.cpu_ms_compression),
        ("report_generate", reports, c.cpu_ms_report_generate),
        ("benchmark_execution", 1, 5000.0),  # ~1 benchmark run/day amortized
    ]

    per_op = {}
    total_ms = 0.0
    for label, count, cpu_ms in items:
        ms = count * cpu_ms
        total_ms += ms
        per_op[label] = _round(ms / 1000.0 / 3600.0, 4)  # core-hours/day

    work_seconds = c.working_hours_per_day * 3600.0
    avg_cores = (total_ms / 1000.0) / work_seconds if work_seconds else 0.0
    peak_cores = avg_cores * c.peak_to_average_factor

    return {
        "per_operation_core_hours_per_day": per_op,
        "total_core_hours_per_day": _round(total_ms / 1000.0 / 3600.0, 3),
        "avg_cores_working_hours": _round(avg_cores, 3),
        "peak_cores": _round(peak_cores, 3),
        "_basis": "Σ(operation count/day × per-op CPU-ms) → core-hours; peak via peak_to_average_factor.",
    }


def ram_breakdown(p: CapacityProfile, c: WorkloadConstants | None = None) -> dict[str, Any]:
    """Per-workload peak RAM (MiB) for each memory consumer (PART 3)."""
    c = c or WorkloadConstants()
    work_seconds = c.working_hours_per_day * 3600.0
    peak_rps = (p.api_requests_per_day / work_seconds * c.peak_to_average_factor) if work_seconds else 0.0

    # Concurrency estimates for pooled/queued consumers.
    concurrent_connectors = max(1.0, p.connector_runs_per_day / work_seconds * c.peak_to_average_factor) if work_seconds else 1.0
    concurrent_prompts = max(1.0, p.prompt_runs_per_day / work_seconds * c.peak_to_average_factor) if work_seconds else 1.0
    concurrent_uploads = concurrent_connectors  # uploads ride connector runs

    per_consumer = {
        "api_requests": _round(peak_rps * c.ram_mib_rest_request, 1),
        "auth_context": _round(peak_rps * c.ram_mib_auth_context, 1),
        "connector_runs": _round(concurrent_connectors * c.ram_mib_connector_run, 1),
        "scheduler_workers": _round(c.ram_mib_scheduler_worker * 4, 1),  # small fixed pool
        "db_pools": _round(c.ram_mib_db_pool * 2, 1),                    # repo + vector pools
        "prompt_context": _round(concurrent_prompts * c.ram_mib_prompt_context, 1),
        "embedding_buffers": _round(concurrent_prompts * c.ram_mib_embedding_buffer, 1),
        "concurrent_uploads": _round(concurrent_uploads * c.ram_mib_evidence_object * 4, 1),
        "queue_depth": _round(p.scheduler_jobs_per_day * 0.02 * c.ram_mib_queue_item, 1),
    }
    # Large-object headroom (large evidence / large JSON parsed in memory).
    large_object_headroom = _round(max(64.0, p.avg_evidence_size_kb / 1024.0 * 32), 1)
    per_consumer["large_object_headroom"] = large_object_headroom
    caches = 128.0  # dashboard/mapping TTL caches (fixed working set)
    per_consumer["caches"] = caches

    peak_total = sum(per_consumer.values())
    return {
        "per_consumer_peak_mib": per_consumer,
        "peak_total_mib": _round(peak_total, 1),
        "peak_total_gib": _round(peak_total / 1024.0, 3),
        "high_water_mark_mib": _round(peak_total * 1.25, 1),  # +25% burst headroom
        "_basis": "Peak concurrency × per-consumer RAM + fixed pools/caches + large-object headroom.",
    }
