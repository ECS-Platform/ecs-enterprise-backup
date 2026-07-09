"""GCP/GKE infrastructure sizing estimator for ECS.

Turns a :class:`benchmarks.capacity.profiles.CapacityProfile` into estimates for:
  1. GKE compute (CPU/RAM per request, connector, scheduler, prompt; pod
     requests/limits; replica count; node-pool sizing),
  2. PostgreSQL / pgvector (row growth, vector storage, index overhead, Cloud SQL
     tier, storage/month & /year),
  3. GCS object storage (evidence + versions + exports + reports + logs; 1y/5y),
  4. Cloud Logging volume (app/connector/scheduler/LLM/audit logs per day).

REUSE: token sizing comes from ``modules.audit_intelligence.llm.token_estimator``
and the vector/storage arithmetic mirrors
``benchmarks.ai_workload.capacity_planning`` (``CapacityAssumptions``). This module
adds only the infra mapping — pure arithmetic, no network, no ECS/LLM calls.

Every per-unit number lives in :class:`SizingConstants` (documented + overridable)
so estimates are transparent and tunable, not magic.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from benchmarks.capacity.profiles import CapacityProfile

_GIB = 1024 ** 3
_MIB = 1024 ** 2
_KIB = 1024


def _gib(b: float) -> float:
    return round(b / _GIB, 4)


def _round(x: float, n: int = 2) -> float:
    return round(float(x), n)


@dataclass
class SizingConstants:
    """Documented per-unit sizing assumptions (all overridable).

    These are conservative planning constants, NOT measurements. Override any of
    them per engagement (e.g. from a real benchmark run).
    """

    # ---- GKE compute: per-unit CPU (millicores) + RAM (MiB) ----
    cpu_ms_per_api_request: float = 40.0      # avg CPU-ms per API request
    ram_mib_per_api_request: float = 4.0      # transient RAM per in-flight request
    cpu_ms_per_connector_run: float = 800.0   # connector fetch+normalize+ingest
    ram_mib_per_connector_run: float = 64.0
    cpu_ms_per_scheduler_job: float = 200.0   # plan/route/dispatch overhead
    ram_mib_per_scheduler_job: float = 16.0
    cpu_ms_per_prompt_run: float = 1500.0     # deterministic assemble + (RAG) retrieve
    ram_mib_per_prompt_run: float = 256.0     # context assembly working set

    # ---- Pod baseline + shape ----
    pod_base_cpu_ms: float = 250.0            # idle/framework CPU per pod
    pod_base_ram_mib: float = 512.0           # base RAM per pod (app + libs)
    pod_cpu_request_ms: float = 500.0         # recommended request per pod
    pod_cpu_limit_ms: float = 1000.0
    pod_ram_request_mib: float = 1024.0
    pod_ram_limit_mib: float = 2048.0
    target_cpu_utilization: float = 0.6       # HPA target -> headroom
    working_hours_per_day: float = 9.0
    peak_to_average_factor: float = 3.0
    min_replicas: int = 2                     # HA floor

    # ---- Node pool (e2-standard-4 by default: 4 vCPU / 16 GiB) ----
    node_vcpu: int = 4
    node_ram_gib: float = 16.0
    node_allocatable_factor: float = 0.75     # usable after system/daemonset overhead

    # ---- PostgreSQL row sizes (bytes, incl. per-row + index share) ----
    bytes_per_control_row: int = 1024
    bytes_per_evidence_meta_row: int = 2048
    bytes_per_observation_row: int = 1536
    bytes_per_prompt_history_row: int = 3072
    bytes_per_benchmark_result_row: int = 4096
    pg_index_overhead_factor: float = 0.35    # +35% for indexes
    observations_per_app_per_year: int = 60

    # ---- Vector store (pgvector) ----
    embedding_dimensions: int = 768           # config/vectorstore.yaml default
    bytes_per_dimension: int = 4              # float32
    vector_index_overhead_factor: float = 1.3
    chunks_per_evidence: float = 4.0          # avg chunks embedded per evidence

    # ---- GCS object storage ----
    benchmark_export_kb: float = 512.0        # per prompt benchmark export
    audit_report_mb: float = 2.0              # per audit report
    reports_per_app_per_month: float = 2.0
    log_export_fraction: float = 0.5          # fraction of daily logs archived to GCS

    # ---- Logging (bytes per event) ----
    bytes_per_app_log: int = 512
    app_logs_per_api_request: float = 3.0
    bytes_per_connector_log: int = 1024
    connector_logs_per_run: float = 5.0
    bytes_per_scheduler_log: int = 768
    scheduler_logs_per_job: float = 4.0
    bytes_per_llm_log: int = 2048
    llm_logs_per_prompt: float = 2.0
    bytes_per_audit_log: int = 1024
    audit_logs_per_api_request: float = 0.5

    working_days_per_month: int = 22
    months_per_year: int = 12

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_overrides(cls, overrides: dict[str, Any] | None) -> "SizingConstants":
        overrides = overrides or {}
        known = {k: overrides[k] for k in overrides if k in cls.__dataclass_fields__}
        return cls(**known)


# --------------------------------------------------------------------------- #
# Token feed (reuses the ECS token estimator)
# --------------------------------------------------------------------------- #
def _avg_prompt_tokens(measured: dict[str, Any] | None) -> dict[str, float]:
    """Average input/output/total tokens per prompt.

    Uses MEASURED values when supplied (from a real audit-LLM benchmark run);
    otherwise derives a deterministic estimate from a representative prompt via the
    existing ``token_estimator`` (chars/4) so the infra feed matches ECS.
    """
    if measured and measured.get("avg_total_tokens"):
        avg_in = float(measured.get("avg_input_tokens") or 0)
        avg_out = float(measured.get("avg_output_tokens") or 0)
        avg_total = float(measured.get("avg_total_tokens") or (avg_in + avg_out))
        return {"input": avg_in, "output": avg_out, "total": avg_total,
                "_source": "measured"}
    # Deterministic estimate from a representative audit prompt + retrieved context.
    try:
        from modules.audit_intelligence.llm import token_estimator as te

        representative = (
            "Summarize the audit readiness and evidence coverage for the "
            "application across all mapped frameworks and controls, listing gaps, "
            "stale evidence, and recommended remediations with citations. "
        ) * 8  # ~ realistic large audit instruction + retrieved context stand-in
        est = te.estimate_prompt(
            system_prompt="You are an audit intelligence assistant.",
            assembled_prompt=representative,
            expected_output_tokens=512,
            token_profile="medium_8k",
            ram_profile="local_16gb_safe",
        )
        return {"input": float(est["input_tokens"]), "output": float(est["output_tokens"]),
                "total": float(est["total_tokens"]), "_source": "estimated (token_estimator)"}
    except Exception:  # noqa: BLE001 - never fail sizing on estimator import
        return {"input": 1500.0, "output": 512.0, "total": 2012.0, "_source": "fallback"}


# --------------------------------------------------------------------------- #
# 1. GKE compute
# --------------------------------------------------------------------------- #
def _gke_compute(p: CapacityProfile, c: SizingConstants) -> dict[str, Any]:
    # Daily CPU-ms per workload class.
    api_cpu_ms = p.api_requests_per_day * c.cpu_ms_per_api_request
    conn_cpu_ms = p.connector_runs_per_day * c.cpu_ms_per_connector_run
    sched_cpu_ms = p.scheduler_jobs_per_day * c.cpu_ms_per_scheduler_job
    prompt_cpu_ms = p.prompt_runs_per_day * c.cpu_ms_per_prompt_run
    total_cpu_ms_day = api_cpu_ms + conn_cpu_ms + sched_cpu_ms + prompt_cpu_ms

    # Convert daily CPU-ms to average cores during working hours, then peak cores.
    work_seconds = c.working_hours_per_day * 3600.0
    avg_cores = (total_cpu_ms_day / 1000.0) / work_seconds if work_seconds else 0.0
    peak_cores = avg_cores * c.peak_to_average_factor

    # Concurrent-request RAM (peak) + base.
    peak_rps = (p.api_requests_per_day / work_seconds * c.peak_to_average_factor) if work_seconds else 0.0
    req_ram_mib = peak_rps * c.ram_mib_per_api_request
    prompt_ram_mib = c.ram_mib_per_prompt_run  # a prompt pool holds working sets
    peak_ram_mib = req_ram_mib + prompt_ram_mib

    # Replicas: enough cores at target utilization, HA floor.
    usable_cpu_per_pod = (c.pod_cpu_request_ms / 1000.0) * c.target_cpu_utilization
    replicas_for_cpu = peak_cores / usable_cpu_per_pod if usable_cpu_per_pod else c.min_replicas
    recommended_replicas = max(c.min_replicas, int(replicas_for_cpu) + 1)

    return {
        "per_unit_cpu_ms": {
            "api_request": c.cpu_ms_per_api_request,
            "connector_run": c.cpu_ms_per_connector_run,
            "scheduler_job": c.cpu_ms_per_scheduler_job,
            "prompt_run": c.cpu_ms_per_prompt_run,
        },
        "per_unit_ram_mib": {
            "api_request": c.ram_mib_per_api_request,
            "connector_run": c.ram_mib_per_connector_run,
            "scheduler_job": c.ram_mib_per_scheduler_job,
            "prompt_run": c.ram_mib_per_prompt_run,
        },
        "daily_cpu_core_hours": {
            "api": _round(api_cpu_ms / 1000.0 / 3600.0, 3),
            "connectors": _round(conn_cpu_ms / 1000.0 / 3600.0, 3),
            "scheduler": _round(sched_cpu_ms / 1000.0 / 3600.0, 3),
            "prompts": _round(prompt_cpu_ms / 1000.0 / 3600.0, 3),
            "total": _round(total_cpu_ms_day / 1000.0 / 3600.0, 3),
        },
        "avg_cores_working_hours": _round(avg_cores, 3),
        "peak_cores": _round(peak_cores, 3),
        "peak_requests_per_second": _round(peak_rps, 3),
        "peak_ram_mib": _round(peak_ram_mib, 1),
        "recommended_pod": {
            "cpu_request": f"{int(c.pod_cpu_request_ms)}m",
            "cpu_limit": f"{int(c.pod_cpu_limit_ms)}m",
            "memory_request": f"{int(c.pod_ram_request_mib)}Mi",
            "memory_limit": f"{int(c.pod_ram_limit_mib)}Mi",
        },
        "recommended_replicas": recommended_replicas,
        "_basis": "Daily per-unit CPU-ms x workload counts -> peak cores at "
                  "peak_to_average_factor; replicas at target CPU utilization with HA floor.",
    }


def _node_pool(p: CapacityProfile, c: SizingConstants, gke: dict[str, Any]) -> dict[str, Any]:
    replicas = gke["recommended_replicas"]
    # Total requested resources across replicas.
    total_cpu_cores = replicas * (c.pod_cpu_request_ms / 1000.0)
    total_ram_gib = replicas * (c.pod_ram_request_mib / 1024.0)
    alloc_cpu = c.node_vcpu * c.node_allocatable_factor
    alloc_ram = c.node_ram_gib * c.node_allocatable_factor
    nodes_for_cpu = total_cpu_cores / alloc_cpu if alloc_cpu else 0
    nodes_for_ram = total_ram_gib / alloc_ram if alloc_ram else 0
    nodes = max(2, int(max(nodes_for_cpu, nodes_for_ram)) + 1)  # +1 headroom, min 2
    return {
        "node_machine_type": f"e2-standard-{c.node_vcpu}",
        "node_vcpu": c.node_vcpu,
        "node_ram_gib": c.node_ram_gib,
        "replicas": replicas,
        "total_cpu_request_cores": _round(total_cpu_cores, 2),
        "total_ram_request_gib": _round(total_ram_gib, 2),
        "recommended_nodes": nodes,
        "_basis": "Replicas x pod requests / node allocatable (75%); +1 node headroom, min 2 (multi-AZ).",
    }


# --------------------------------------------------------------------------- #
# 2. PostgreSQL / pgvector
# --------------------------------------------------------------------------- #
def _postgres(p: CapacityProfile, c: SizingConstants) -> dict[str, Any]:
    idx = 1.0 + c.pg_index_overhead_factor

    control_bytes = p.total_controls() * c.bytes_per_control_row * idx
    evidence_meta_bytes = p.total_evidences() * c.bytes_per_evidence_meta_row * idx

    # Yearly growth of append-heavy tables.
    obs_year = p.apps * c.observations_per_app_per_year
    obs_bytes_year = obs_year * c.bytes_per_observation_row * idx
    prompt_hist_year = p.prompt_runs_per_day * c.working_days_per_month * c.months_per_year
    prompt_bytes_year = prompt_hist_year * c.bytes_per_prompt_history_row * idx
    bench_rows_year = 52 * 50  # ~weekly benchmark of ~50 prompts (documented)
    bench_bytes_year = bench_rows_year * c.bytes_per_benchmark_result_row * idx

    # Vectors.
    vec_bytes_per_chunk = c.embedding_dimensions * c.bytes_per_dimension * c.vector_index_overhead_factor
    total_chunks = p.total_evidences() * c.chunks_per_evidence
    vector_bytes = total_chunks * vec_bytes_per_chunk
    new_chunks_year = (p.apps * p.new_evidence_per_app_per_month * c.months_per_year) * c.chunks_per_evidence
    vector_bytes_year = new_chunks_year * vec_bytes_per_chunk

    base_bytes = control_bytes + evidence_meta_bytes + vector_bytes
    growth_bytes_year = obs_bytes_year + prompt_bytes_year + bench_bytes_year + vector_bytes_year
    year1 = base_bytes + growth_bytes_year
    year5 = base_bytes + growth_bytes_year * p.retention_years

    tier = _cloud_sql_tier(_gib(year1))

    return {
        "row_growth": {
            "control_rows": p.total_controls(),
            "evidence_meta_rows": p.total_evidences(),
            "observation_rows_per_year": obs_year,
            "prompt_history_rows_per_year": int(prompt_hist_year),
            "benchmark_result_rows_per_year": bench_rows_year,
        },
        "storage_gib": {
            "controls": _gib(control_bytes),
            "evidence_metadata": _gib(evidence_meta_bytes),
            "vectors_current": _gib(vector_bytes),
            "index_overhead_factor": idx,
            "growth_per_year": _gib(growth_bytes_year),
            "year_1_total": _gib(year1),
            "year_5_total": _gib(year5),
        },
        "vectors": {
            "embedding_dimensions": c.embedding_dimensions,
            "bytes_per_chunk": _round(vec_bytes_per_chunk, 1),
            "total_chunks": int(total_chunks),
            "new_chunks_per_year": int(new_chunks_year),
        },
        "recommended_cloud_sql": tier,
        "_basis": "Row counts x per-row bytes x (1+index overhead); vectors = dims x 4B x 1.3.",
    }


def _cloud_sql_tier(year1_gib: float) -> dict[str, Any]:
    """Map projected size + implied load to a starting Cloud SQL tier (tunable)."""
    if year1_gib <= 20:
        return {"tier": "db-custom-2-7680", "vcpu": 2, "ram_gib": 7.5,
                "storage_gib": max(20, int(year1_gib * 2)), "ha": "zonal (uat) / regional (prod)"}
    if year1_gib <= 100:
        return {"tier": "db-custom-4-15360", "vcpu": 4, "ram_gib": 15,
                "storage_gib": max(100, int(year1_gib * 1.5)), "ha": "regional"}
    if year1_gib <= 500:
        return {"tier": "db-custom-8-30720", "vcpu": 8, "ram_gib": 30,
                "storage_gib": max(500, int(year1_gib * 1.5)), "ha": "regional"}
    return {"tier": "db-custom-16-61440", "vcpu": 16, "ram_gib": 60,
            "storage_gib": max(1000, int(year1_gib * 1.5)), "ha": "regional + read replicas"}


# --------------------------------------------------------------------------- #
# 3. GCS object storage
# --------------------------------------------------------------------------- #
def _gcs(p: CapacityProfile, c: SizingConstants, logging: dict[str, Any]) -> dict[str, Any]:
    evidence_bytes = p.total_evidences() * p.avg_evidence_size_kb * _KIB
    # Versions accumulate per year at the version rate.
    version_bytes_year = evidence_bytes * (p.evidence_versions_per_year - 1.0)
    new_evidence_bytes_year = (p.apps * p.new_evidence_per_app_per_month * c.months_per_year) \
        * p.avg_evidence_size_kb * _KIB

    bench_export_bytes_year = 52 * (c.benchmark_export_kb * _KIB)
    reports_year = p.apps * c.reports_per_app_per_month * c.months_per_year
    report_bytes_year = reports_year * (c.audit_report_mb * _MIB)
    log_export_bytes_year = logging["total_bytes_per_year"] * c.log_export_fraction

    base = evidence_bytes
    growth_year = (new_evidence_bytes_year + version_bytes_year
                   + bench_export_bytes_year + report_bytes_year + log_export_bytes_year)
    year1 = base + growth_year
    year5 = base + growth_year * p.retention_years

    return {
        "current_evidence_gib": _gib(evidence_bytes),
        "growth_per_year_gib": {
            "new_evidence": _gib(new_evidence_bytes_year),
            "evidence_versions": _gib(version_bytes_year),
            "benchmark_exports": _gib(bench_export_bytes_year),
            "audit_reports": _gib(report_bytes_year),
            "log_exports": _gib(log_export_bytes_year),
            "total": _gib(growth_year),
        },
        "year_1_total_gib": _gib(year1),
        "year_5_total_gib": _gib(year5),
        "retention_years": p.retention_years,
        "_basis": "Evidence count x avg size + versions/exports/reports/log-archive growth.",
    }


# --------------------------------------------------------------------------- #
# 4. Logging / monitoring
# --------------------------------------------------------------------------- #
def _logging(p: CapacityProfile, c: SizingConstants) -> dict[str, Any]:
    app = p.api_requests_per_day * c.app_logs_per_api_request * c.bytes_per_app_log
    conn = p.connector_runs_per_day * c.connector_logs_per_run * c.bytes_per_connector_log
    sched = p.scheduler_jobs_per_day * c.scheduler_logs_per_job * c.bytes_per_scheduler_log
    llm = p.prompt_runs_per_day * c.llm_logs_per_prompt * c.bytes_per_llm_log
    audit = p.api_requests_per_day * c.audit_logs_per_api_request * c.bytes_per_audit_log
    per_day = app + conn + sched + llm + audit
    return {
        "per_day_gib": {
            "application": _gib(app),
            "connector": _gib(conn),
            "scheduler": _gib(sched),
            "llm_execution": _gib(llm),
            "audit_trail": _gib(audit),
            "total": _gib(per_day),
        },
        "per_month_gib": _gib(per_day * 30),
        "per_year_gib": _gib(per_day * 365),
        "total_bytes_per_year": per_day * 365,
        "_basis": "Event counts x events-per-unit x bytes-per-event (Cloud Logging ingestion).",
    }


# --------------------------------------------------------------------------- #
# Top-level
# --------------------------------------------------------------------------- #
def estimate_capacity(
    profile: CapacityProfile,
    *,
    constants: SizingConstants | None = None,
    measured_tokens: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Full GCP capacity estimate for one profile. Pure arithmetic; never raises.

    ``measured_tokens`` (optional) feeds MEASURED per-prompt tokens from a real
    audit-LLM benchmark run; otherwise a deterministic estimate is used.
    """
    c = constants or SizingConstants()
    tokens = _avg_prompt_tokens(measured_tokens)

    gke = _gke_compute(profile, c)
    nodes = _node_pool(profile, c, gke)
    logging = _logging(profile, c)
    postgres = _postgres(profile, c)
    gcs = _gcs(profile, c, logging)

    estimate: dict[str, Any] = {
        "profile": profile.to_dict(),
        "token_feed": tokens,
        "gke_compute": gke,
        "node_pool": nodes,
        "postgres_pgvector": postgres,
        "gcs_object_storage": gcs,
        "logging_monitoring": logging,
        "constants": c.to_dict(),
        "_meta": {
            "kind": "gcp_capacity_estimate",
            "provenance": "ESTIMATE — documented per-unit assumptions x scenario profile. "
                          "Not a measurement. Calibrate constants from a real benchmark run.",
            "token_source": tokens.get("_source"),
        },
    }

    # --- Extended enterprise-infra sections (additive; best-effort so the core
    #     estimate never breaks if an optional estimator import fails) ---
    try:
        from benchmarks.capacity import workload as _wl

        estimate["cpu_breakdown"] = _wl.cpu_breakdown(profile)
        estimate["ram_breakdown"] = _wl.ram_breakdown(profile)
    except Exception:  # noqa: BLE001
        pass
    try:
        from benchmarks.capacity import storage as _st

        base_db = postgres["storage_gib"]["year_1_total"]
        base_gcs = gcs["year_1_total_gib"]
        estimate["db_durability"] = _st.db_durability(profile, base_db)
        estimate["object_storage_detail"] = _st.object_storage_detail(profile, base_gcs)
    except Exception:  # noqa: BLE001
        pass
    try:
        from benchmarks.capacity import network as _nw

        connectors = _nw.connector_benchmark(profile)
        estimate["connector_benchmark"] = connectors
        estimate["db_agent_benchmark"] = _nw.db_agent_benchmark(profile)
        estimate["network"] = _nw.network_bandwidth(profile, connectors)
    except Exception:  # noqa: BLE001
        pass
    try:
        from benchmarks.capacity import ai as _ai

        estimate["ai_throughput"] = _ai.ai_throughput(profile, estimate)
    except Exception:  # noqa: BLE001
        pass
    try:
        from benchmarks.capacity import cost as _cost

        estimate["cost"] = _cost.estimate_cost(estimate)
    except Exception:  # noqa: BLE001
        pass
    try:
        from benchmarks.capacity import kubernetes as _k8s

        estimate["kubernetes"] = _k8s.recommend(estimate)
    except Exception:  # noqa: BLE001
        pass

    return estimate
