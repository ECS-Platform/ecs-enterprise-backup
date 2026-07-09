"""GCP cost estimation for the ECS infrastructure benchmark (PART 13).

Applies a configurable rate table to the sizing outputs (compute, Cloud SQL, GCS,
logging, monitoring, network) to produce monthly / annual / 5-year cost
projections with a growth curve.

RATES ARE ILLUSTRATIVE PLANNING DEFAULTS (currency-neutral, approximate GCP list
prices) and MUST be replaced with a current quote before any spend decision.
Every rate lives in :class:`CostRates` and is overridable. Pure arithmetic.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


def _round(x: float, n: int = 2) -> float:
    return round(float(x), n)


@dataclass
class CostRates:
    """Illustrative GCP unit rates (override with a real quote)."""

    # Compute (per vCPU-hour / per GiB-hour, on-demand e2-ish)
    cost_per_vcpu_hour: float = 0.031
    cost_per_gib_ram_hour: float = 0.0042
    hours_per_month: float = 730.0

    # Cloud SQL (per vCPU-hour / GiB-RAM-hour / GiB storage-month)
    sql_cost_per_vcpu_hour: float = 0.0413
    sql_cost_per_gib_ram_hour: float = 0.007
    sql_cost_per_gib_storage_month: float = 0.17
    sql_ha_multiplier: float = 2.0          # regional HA ~2x

    # GCS (per GiB-month by tier)
    gcs_standard_per_gib_month: float = 0.020
    gcs_nearline_per_gib_month: float = 0.010
    gcs_coldline_per_gib_month: float = 0.004
    gcs_archive_per_gib_month: float = 0.0012

    # Logging / Monitoring
    logging_per_gib: float = 0.50           # Cloud Logging ingestion
    monitoring_per_month_base: float = 50.0

    # Network egress (per GiB; cross-cloud/internet)
    egress_per_gib: float = 0.12

    # Load balancer + misc fixed
    load_balancer_per_month: float = 25.0

    currency: str = "USD (illustrative)"
    months_per_year: int = 12

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_overrides(cls, overrides: dict[str, Any] | None) -> "CostRates":
        overrides = overrides or {}
        known = {k: overrides[k] for k in overrides if k in cls.__dataclass_fields__}
        return cls(**known)


def estimate_cost(estimate: dict[str, Any], rates: CostRates | None = None) -> dict[str, Any]:
    """Monthly/annual/5-year GCP cost from a capacity estimate. Never raises."""
    r = rates or CostRates()
    gke = estimate.get("gke_compute", {})
    nodes = estimate.get("node_pool", {})
    pg = estimate.get("postgres_pgvector", {})
    gcs = estimate.get("gcs_object_storage", {})
    logs = estimate.get("logging_monitoring", {})
    net = estimate.get("network", {})

    # --- Compute (nodes x machine size x hours) ---
    node_count = float(nodes.get("recommended_nodes", 2))
    node_vcpu = float(nodes.get("node_vcpu", 4))
    node_ram = float(nodes.get("node_ram_gib", 16))
    compute_month = node_count * (
        node_vcpu * r.cost_per_vcpu_hour + node_ram * r.cost_per_gib_ram_hour
    ) * r.hours_per_month

    # --- Cloud SQL ---
    sql = pg.get("recommended_cloud_sql", {})
    sql_vcpu = float(sql.get("vcpu", 2))
    sql_ram = float(sql.get("ram_gib", 7.5))
    sql_storage = float(sql.get("storage_gib", 20))
    ha_mult = r.sql_ha_multiplier if "regional" in str(sql.get("ha", "")) else 1.0
    sql_month = (
        (sql_vcpu * r.sql_cost_per_vcpu_hour + sql_ram * r.sql_cost_per_gib_ram_hour)
        * r.hours_per_month + sql_storage * r.sql_cost_per_gib_storage_month
    ) * ha_mult

    # --- GCS (blended: most recent in STANDARD, older tiered down) ---
    gcs_gib = float(gcs.get("year_1_total_gib", 0))
    # Rough tier split: 40% standard, 25% nearline, 20% coldline, 15% archive.
    gcs_month = gcs_gib * (
        0.40 * r.gcs_standard_per_gib_month + 0.25 * r.gcs_nearline_per_gib_month
        + 0.20 * r.gcs_coldline_per_gib_month + 0.15 * r.gcs_archive_per_gib_month
    )

    # --- Logging + Monitoring ---
    logs_gib_month = float(logs.get("per_month_gib", 0))
    logging_month = logs_gib_month * r.logging_per_gib
    monitoring_month = r.monitoring_per_month_base

    # --- Network egress (cross-cloud + object + api monthly) ---
    egress_gib_month = float(net.get("total_egress_estimate_gib_per_month", 0)) if net else 0.0
    network_month = egress_gib_month * r.egress_per_gib

    lb_month = r.load_balancer_per_month

    monthly = {
        "compute": _round(compute_month),
        "cloud_sql": _round(sql_month),
        "object_storage": _round(gcs_month),
        "logging": _round(logging_month),
        "monitoring": _round(monitoring_month),
        "network_egress": _round(network_month),
        "load_balancer": _round(lb_month),
    }
    monthly_total = _round(sum(monthly.values()))
    annual_total = _round(monthly_total * r.months_per_year)

    # 5-year growth curve: storage + logging grow ~year-over-year with data.
    growth_curve = []
    for yr in range(1, 6):
        # Storage/logging scale with cumulative data; compute/SQL step with scale (held flat here).
        storage_factor = 1.0 + 0.6 * (yr - 1)   # ~60% cumulative storage growth/yr
        yr_monthly = (monthly["compute"] + monthly["cloud_sql"] + monthly["monitoring"]
                      + monthly["load_balancer"]
                      + (monthly["object_storage"] + monthly["logging"] + monthly["network_egress"])
                      * storage_factor)
        growth_curve.append({"year": yr, "monthly": _round(yr_monthly),
                             "annual": _round(yr_monthly * r.months_per_year)})
    five_year_total = _round(sum(g["annual"] for g in growth_curve))

    return {
        "currency": r.currency,
        "monthly_breakdown": monthly,
        "monthly_total": monthly_total,
        "annual_total": annual_total,
        "five_year_total": five_year_total,
        "growth_curve": growth_curve,
        "rates": r.to_dict(),
        "_disclaimer": "ILLUSTRATIVE — default GCP-like list rates. Replace CostRates "
                       "with a current quote before any spend decision. Excludes "
                       "committed-use discounts, support, and data-transfer specifics.",
    }
