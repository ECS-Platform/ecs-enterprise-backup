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
            "note": "Enable PITR/WAL archiving for banking retention; test restores.",
        },
        "_basis": "Daily logical writes x row bytes -> WAL x amplification; backup = live x compression.",
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
        "_basis": "File counts x size distribution; dedup/compression multipliers; "
                  "linear retention growth; GCS tiering by object age.",
    }
