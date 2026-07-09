"""Deep storage estimators: DB durability (PART 4) + object-storage detail (PART 5).

Extends ``sizing._postgres`` / ``sizing._gcs`` with the operational/durability
dimensions the infra benchmark asks for:
  * DB: WAL/day, vacuum + autovacuum churn, checkpoint, backup + restore size,
    partition growth, index overhead detail.
  * Object storage: file counts (day/month/year), size distribution
    (avg/median/p95/max), version growth, dedup + compression ratios, per-content
    -type breakdown, retention (1/3/5/7/10y), lifecycle tiers (Nearline/Coldline/
    Archive), bucket layout.

Pure arithmetic over documented assumptions x profile. Reuses the base totals from
``sizing`` to stay consistent (no duplicate size math).
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


def _round(x: float, n: int = 3) -> float:
    return round(float(x), n)


# --------------------------------------------------------------------------- #
# PART 4 — Database durability / operations
# --------------------------------------------------------------------------- #
@dataclass
class DbDurabilityConstants:
    wal_amplification: float = 3.0          # WAL bytes per logical write byte
    dead_tuple_fraction: float = 0.2        # churn generating vacuum work
    autovacuum_daily_passes: float = 6.0
    checkpoint_fraction_of_wal: float = 0.5
    backup_compression_ratio: float = 0.4   # backup size vs live (compressed)
    restore_overhead_factor: float = 1.1    # restore working set vs backup
    partition_by_month: bool = True
    bytes_per_write_row: int = 2048         # avg logical row size for writes
    months_per_year: int = 12
    working_days_per_month: int = 22

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def db_durability(p: CapacityProfile, base_year1_gib: float,
                  c: DbDurabilityConstants | None = None) -> dict[str, Any]:
    """WAL / vacuum / checkpoint / backup / restore / partition estimates (PART 4)."""
    c = c or DbDurabilityConstants()

    # Daily logical writes: evidence meta + observations + prompt history + benchmark.
    daily_writes = (p.connector_runs_per_day * 5      # evidence meta rows
                    + p.prompt_runs_per_day           # prompt history
                    + p.scheduler_jobs_per_day        # scheduler/connector history
                    + p.apps * 0.2)                   # observations (amortized/day)
    daily_write_bytes = daily_writes * c.bytes_per_write_row
    wal_per_day = daily_write_bytes * c.wal_amplification
    checkpoint_per_day = wal_per_day * c.checkpoint_fraction_of_wal
    dead_tuples_per_day = daily_write_bytes * c.dead_tuple_fraction
    backup_size = base_year1_gib * _GIB * c.backup_compression_ratio
    restore_size = backup_size * c.restore_overhead_factor
    monthly_partition_bytes = daily_write_bytes * c.working_days_per_month

    return {
        "daily_writes_est": int(daily_writes),
        "wal_gib_per_day": _gib(wal_per_day),
        "wal_gib_per_month": _gib(wal_per_day * c.working_days_per_month),
        "checkpoint_gib_per_day": _gib(checkpoint_per_day),
        "vacuum": {
            "dead_tuples_gib_per_day": _gib(dead_tuples_per_day),
            "autovacuum_passes_per_day": c.autovacuum_daily_passes,
            "note": "Set autovacuum_vacuum_scale_factor lower for append-heavy history tables.",
        },
        "partitioning": {
            "strategy": "monthly range partitions on history tables" if c.partition_by_month else "none",
            "monthly_partition_gib": _gib(monthly_partition_bytes),
            "yearly_partitions": c.months_per_year if c.partition_by_month else 0,
        },
        "backup": {
            "full_backup_gib": _gib(backup_size),
            "compression_ratio": c.backup_compression_ratio,
            "restore_working_gib": _gib(restore_size),
            "restore_time_minutes_est": _round(max(5.0, _gib(restore_size) * 1.5), 1),  # ~1.5 min/GiB
            "note": "Enable PITR/WAL archiving for banking retention; test restores.",
        },
        "performance": db_performance(p, base_year1_gib),
        "_basis": "Daily logical writes x row bytes -> WAL x amplification; backup = live x compression.",
    }


def db_performance(p: CapacityProfile, base_year1_gib: float) -> dict[str, Any]:
    """Queries/sec, TPS, pool size, slow-query risk, Cloud SQL refinement (PART 6)."""
    work_seconds = 9.0 * 3600.0
    reads_per_day = p.api_requests_per_day * 2.0 + p.prompt_runs_per_day * 3.0   # UI + RAG lookups
    writes_per_day = p.connector_runs_per_day * 5 + p.prompt_runs_per_day + p.scheduler_jobs_per_day
    qps_avg = (reads_per_day + writes_per_day) / work_seconds if work_seconds else 0.0
    qps_peak = qps_avg * 3.0
    tps_peak = (writes_per_day / work_seconds * 3.0) if work_seconds else 0.0

    # Connection pool: enough for peak concurrency with headroom; capped sanely.
    pool = max(10, min(400, int(qps_peak * 0.2) + 10))
    slow_query_risk = "medium" if base_year1_gib > 100 else "low"
    # Refine Cloud SQL vCPU from peak QPS (heuristic: ~150 qps/vCPU sustained).
    refined_vcpu = max(2, int(qps_peak / 150) + 1)

    return {
        "queries_per_second_avg": _round(qps_avg, 2),
        "queries_per_second_peak": _round(qps_peak, 2),
        "transactions_per_second_peak": _round(tps_peak, 2),
        "recommended_connection_pool": pool,
        "recommended_pgbouncer": pool > 100,
        "slow_query_risk": slow_query_risk,
        "index_growth_note": "Index share ~35% of table size; monitor bloat on history tables.",
        "cloud_sql_vcpu_refined_min": refined_vcpu,
        "vacuum_impact": "Schedule autovacuum aggressively on append-heavy history/"
                         "observation tables; watch for wraparound on high-write tenants.",
        "_basis": "Read/write mix -> QPS/TPS at peak; pool from peak concurrency; "
                  "vCPU refined from sustained QPS heuristic.",
    }


# --------------------------------------------------------------------------- #
# PART 5 — Object storage detail
# --------------------------------------------------------------------------- #
@dataclass
class ObjectStorageConstants:
    # Size distribution multipliers relative to the profile's avg_evidence_size_kb.
    median_factor: float = 0.7
    p95_factor: float = 3.0
    max_factor: float = 20.0
    dedup_ratio: float = 0.15               # fraction saved by dedup
    compression_ratio: float = 0.6          # stored/original for compressible types
    sha256_meta_bytes: int = 96             # per object metadata overhead
    # Content-type mix (fraction of evidence objects).
    content_mix: dict[str, float] = field(default_factory=lambda: {
        "pdf": 0.25, "excel": 0.10, "word": 0.05, "csv": 0.10, "json": 0.20,
        "images": 0.15, "zip": 0.05, "logs": 0.10,
    })
    # Lifecycle tiering (age thresholds in days).
    nearline_after_days: int = 30
    coldline_after_days: int = 90
    archive_after_days: int = 365
    months_per_year: int = 12

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def object_storage_detail(p: CapacityProfile, base_year1_gib: float,
                          c: ObjectStorageConstants | None = None) -> dict[str, Any]:
    """File counts, size distribution, dedup/compression, tiers, retention (PART 5)."""
    c = c or ObjectStorageConstants()

    files_per_day = p.connector_runs_per_day * 5 + p.prompt_runs_per_day * 0.5
    files_per_month = files_per_day * 22
    files_per_year = files_per_day * 22 * c.months_per_year

    avg_kb = p.avg_evidence_size_kb
    size_dist = {
        "average_kb": _round(avg_kb, 1),
        "median_kb": _round(avg_kb * c.median_factor, 1),
        "p95_kb": _round(avg_kb * c.p95_factor, 1),
        "max_kb": _round(avg_kb * c.max_factor, 1),
    }

    # Content-type breakdown of the current evidence footprint.
    total_ev = p.total_evidences()
    content_breakdown = {
        t: {"objects": int(total_ev * frac),
            "gib": _gib(total_ev * frac * avg_kb * _KIB)}
        for t, frac in c.content_mix.items()
    }

    # Effective footprint after dedup + compression.
    raw_year1 = base_year1_gib
    after_dedup = raw_year1 * (1.0 - c.dedup_ratio)
    after_compression = after_dedup * c.compression_ratio
    sha_overhead_gib = _gib(total_ev * c.sha256_meta_bytes)

    # Retention projections (linear growth of the yearly delta).
    yearly_delta = raw_year1  # conservative: ~year-1 footprint added per year
    retention = {
        f"{yr}_year_gib": _round(raw_year1 + yearly_delta * (yr - 1), 2)
        for yr in (1, 3, 5, 7, 10)
    }

    # Lifecycle tier distribution (rough steady-state split by age).
    lifecycle = {
        "standard_recent": {"tier": "STANDARD", "age": f"0-{c.nearline_after_days}d"},
        "nearline": {"tier": "NEARLINE", "age": f"{c.nearline_after_days}-{c.coldline_after_days}d"},
        "coldline": {"tier": "COLDLINE", "age": f"{c.coldline_after_days}-{c.archive_after_days}d"},
        "archive": {"tier": "ARCHIVE", "age": f">{c.archive_after_days}d"},
        "note": "Move older evidence to cheaper tiers via GCS lifecycle rules; "
                "keep audit-active evidence in STANDARD.",
    }

    bucket_layout = {
        "recommended_buckets": [
            "ecs-evidence-<env>        (evidence objects, versioned, CMEK)",
            "ecs-reports-<env>         (audit + benchmark reports)",
            "ecs-exports-<env>         (connector/evidence exports, short TTL)",
            "ecs-logs-<env>            (archived logs, lifecycle to Coldline/Archive)",
        ],
        "bucket_count": 4,
        "lifecycle_rules": [
            f"evidence: STANDARD -> NEARLINE @ {c.nearline_after_days}d -> "
            f"COLDLINE @ {c.coldline_after_days}d -> ARCHIVE @ {c.archive_after_days}d",
            "exports: delete @ 30d",
            "logs: NEARLINE @ 30d -> ARCHIVE @ 365d",
        ],
    }

    return {
        "file_counts": {
            "per_day": int(files_per_day),
            "per_month": int(files_per_month),
            "per_year": int(files_per_year),
        },
        "size_distribution": size_dist,
        "content_type_breakdown": content_breakdown,
        "efficiency": {
            "dedup_ratio": c.dedup_ratio,
            "compression_ratio": c.compression_ratio,
            "raw_year1_gib": _round(raw_year1, 2),
            "after_dedup_gib": _round(after_dedup, 2),
            "after_dedup_and_compression_gib": _round(after_compression, 2),
            "sha256_metadata_overhead_gib": sha_overhead_gib,
        },
        "retention_projection_gib": retention,
        "lifecycle_tiers": lifecycle,
        "bucket_layout": bucket_layout,
        "throughput": object_storage_throughput(p, c),
        "_basis": "File counts x size distribution; dedup/compression multipliers; "
                  "linear retention growth; GCS tiering by object age.",
    }


@dataclass
class ThroughputConstants:
    upload_latency_ms_base: float = 80.0        # per-object connect/finalize
    upload_ms_per_mib: float = 12.0             # transfer time per MiB
    download_latency_ms_base: float = 60.0
    download_ms_per_mib: float = 8.0
    small_file_kb_threshold: float = 256.0
    large_file_mib_threshold: float = 5.0       # multipart above this
    class_a_ops_cost_per_10k: float = 0.05      # writes/lists (GCS Class A)
    class_b_ops_cost_per_10k: float = 0.004     # reads (GCS Class B)
    working_days_per_month: int = 22


def object_storage_throughput(p: CapacityProfile,
                              osc: ObjectStorageConstants | None = None,
                              t: ThroughputConstants | None = None) -> dict[str, Any]:
    """Upload/download latency, concurrency, small/large-file, ops-cost (PART 5)."""
    t = t or ThroughputConstants()
    avg_mib = p.avg_evidence_size_kb / 1024.0
    upload_ms = t.upload_latency_ms_base + avg_mib * t.upload_ms_per_mib
    download_ms = t.download_latency_ms_base + avg_mib * t.download_ms_per_mib

    uploads_per_day = p.connector_runs_per_day * 5 + p.prompt_runs_per_day * 0.5
    downloads_per_day = uploads_per_day * 0.3
    work_seconds = 9.0 * 3600.0
    peak_upload_concurrency = max(1, int(uploads_per_day / work_seconds * 3.0)) if work_seconds else 1
    peak_download_concurrency = max(1, int(downloads_per_day / work_seconds * 3.0)) if work_seconds else 1

    is_small = p.avg_evidence_size_kb <= t.small_file_kb_threshold
    is_large = avg_mib >= t.large_file_mib_threshold

    # GCS operation costs (Class A: writes/list; Class B: reads).
    class_a_ops_month = (uploads_per_day * t.working_days_per_month) * 1.2  # write + occasional list
    class_b_ops_month = (downloads_per_day * t.working_days_per_month)
    ops_cost_month = (class_a_ops_month / 10000.0 * t.class_a_ops_cost_per_10k
                      + class_b_ops_month / 10000.0 * t.class_b_ops_cost_per_10k)

    return {
        "upload_latency_ms_avg": _round(upload_ms, 1),
        "download_latency_ms_avg": _round(download_ms, 1),
        "peak_concurrent_uploads": peak_upload_concurrency,
        "peak_concurrent_downloads": peak_download_concurrency,
        "workload_profile": "small-file" if is_small else ("large-file" if is_large else "mixed"),
        "multipart_upload_recommended": is_large,
        "compression_savings_pct": _round((1.0 - (osc or ObjectStorageConstants()).compression_ratio) * 100, 1),
        "lifecycle_savings_note": "Tiering to Nearline/Coldline/Archive can cut storage "
                                  "cost 50-95% for cold evidence.",
        "object_operations_per_month": {
            "class_a_writes_list": int(class_a_ops_month),
            "class_b_reads": int(class_b_ops_month),
        },
        "gcs_operation_cost_per_month": _round(ops_cost_month, 3),
        "_basis": "Latency = base + per-MiB transfer; concurrency from peak rate; "
                  "ops-cost from Class A/B counts (illustrative GCS rates).",
    }
