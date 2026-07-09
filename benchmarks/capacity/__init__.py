"""ECS GCP/GKE capacity-sizing benchmark.

Extends the existing ECS benchmark/token-estimation framework
(``benchmarks.ai_workload.capacity_planning``, ``modules.audit_intelligence.llm.
token_estimator``) with **infrastructure sizing** estimates for a GCP deployment:
GKE compute, Cloud SQL / pgvector, GCS object storage, and Cloud Logging volume,
across named scenario profiles (demo → large-enterprise).

This package REUSES the existing token estimator and capacity arithmetic; it does
not reimplement token counting, the benchmark runner, or the LLM pipeline. Every
number is a transparent estimate from documented per-unit assumptions (see
``sizing.SizingConstants``) times the scenario profile — pure arithmetic, no
network, no ECS/LLM calls.
"""

from __future__ import annotations

from benchmarks.capacity.profiles import PROFILES, CapacityProfile, get_profile, list_profiles
from benchmarks.capacity.sizing import SizingConstants, estimate_capacity
from benchmarks.capacity.workload import WorkloadConstants, cpu_breakdown, ram_breakdown
from benchmarks.capacity.storage import (
    DbDurabilityConstants,
    ObjectStorageConstants,
    db_durability,
    object_storage_detail,
)
from benchmarks.capacity.network import (
    NetworkConstants,
    connector_benchmark,
    db_agent_benchmark,
    network_bandwidth,
)
from benchmarks.capacity.cost import CostRates, estimate_cost
from benchmarks.capacity.telemetry import RuntimeTelemetry, telemetry_availability
from benchmarks.capacity.kubernetes import recommend as kubernetes_recommend
from benchmarks.capacity.stress import list_scenarios, run_all as stress_run_all, run_scenario
from benchmarks.capacity.calibration import calibrate
from benchmarks.capacity.ai import AiThroughputConstants, ai_throughput
from benchmarks.capacity import executive

__all__ = [
    "RuntimeTelemetry",
    "telemetry_availability",
    "kubernetes_recommend",
    "list_scenarios",
    "stress_run_all",
    "run_scenario",
    "calibrate",
    "AiThroughputConstants",
    "ai_throughput",
    "executive",
    "PROFILES",
    "CapacityProfile",
    "get_profile",
    "list_profiles",
    "SizingConstants",
    "estimate_capacity",
    "WorkloadConstants",
    "cpu_breakdown",
    "ram_breakdown",
    "DbDurabilityConstants",
    "ObjectStorageConstants",
    "db_durability",
    "object_storage_detail",
    "NetworkConstants",
    "connector_benchmark",
    "db_agent_benchmark",
    "network_bandwidth",
    "CostRates",
    "estimate_cost",
]
