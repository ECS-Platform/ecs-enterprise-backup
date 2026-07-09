"""Stress-testing models for the ECS infrastructure benchmark (PART 3).

Estimates the impact of adverse load scenarios (connector storm, scheduler
overload, retry/DLQ storm, concurrent uploads/prompts/DB queries, object-storage
burst, large-file burst, and 100/500/1000 connector/DB-target simulations) by
applying documented multipliers to a profile's baseline activity and re-running
the existing CPU/RAM/network estimators.

Each scenario reports CPU / RAM / network / storage / queue impact, the expected
bottleneck, and a recommended mitigation. No real external calls — pure modeling
that reuses ``workload`` and ``network`` estimators (no duplication).
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from benchmarks.capacity.profiles import CapacityProfile


def _round(x: float, n: int = 3) -> float:
    return round(float(x), n)


# Scenario definitions: multipliers on the baseline profile activity + metadata.
# (each value multiplies the corresponding daily activity count)
_SCENARIOS: dict[str, dict[str, Any]] = {
    "connector_storm": {
        "label": "Connector storm (all connectors fire together)",
        "mult": {"connector_runs_per_day": 10.0},
        "bottleneck": "Connector worker CPU + outbound bandwidth (incl. AWS<->GCP).",
        "mitigation": "Rate-limit connector concurrency; stagger schedules; scale the "
                      "connector worker pool; increase HPA max for connector pods.",
    },
    "scheduler_overload": {
        "label": "Scheduler overload (job surge)",
        "mult": {"scheduler_jobs_per_day": 12.0},
        "bottleneck": "Scheduler dispatch CPU + queue depth.",
        "mitigation": "Increase worker pool + priority queue; shed low-priority jobs; "
                      "apply backoff; cap in-flight jobs.",
    },
    "retry_storm": {
        "label": "Retry storm (mass transient failures)",
        "mult": {"connector_runs_per_day": 4.0, "scheduler_jobs_per_day": 4.0},
        "bottleneck": "Retry queue churn + repeated connector CPU/bandwidth.",
        "mitigation": "Exponential backoff + jitter; circuit-breaker on failing targets; "
                      "cap retries; route persistent failures to DLQ.",
    },
    "dead_letter_growth": {
        "label": "Dead-letter queue growth (unrecoverable failures)",
        "mult": {"scheduler_jobs_per_day": 3.0},
        "bottleneck": "DLQ memory (in-process) + operator triage backlog.",
        "mitigation": "Persist the DLQ; alert on depth; auto-requeue after fix; "
                      "root-cause non-retryable auth/config errors.",
    },
    "concurrent_uploads": {
        "label": "Concurrent evidence uploads",
        "mult": {"connector_runs_per_day": 6.0},
        "bottleneck": "Upload RAM (buffers) + object-storage write throughput.",
        "mitigation": "Stream/multipart uploads; bound upload concurrency; scale GCS "
                      "write path; add backpressure.",
    },
    "concurrent_prompts": {
        "label": "Concurrent prompt runs",
        "mult": {"prompt_runs_per_day": 8.0},
        "bottleneck": "Prompt/embedding RAM + LLM-RAG pool + vector search.",
        "mitigation": "Separate RAG node pool; queue prompts; cap concurrency=1 on "
                      "constrained RAM profiles; cache embeddings.",
    },
    "concurrent_db_queries": {
        "label": "Concurrent DB Agent queries",
        "mult": {"connector_runs_per_day": 5.0, "scheduler_jobs_per_day": 5.0},
        "bottleneck": "Cloud SQL connections + query CPU; DB Agent pool exhaustion.",
        "mitigation": "Right-size connection pool/PgBouncer; add read replicas; "
                      "statement timeouts; limit parallelism.",
    },
    "object_storage_burst": {
        "label": "Object-storage upload burst",
        "mult": {"connector_runs_per_day": 8.0},
        "bottleneck": "GCS write ops/sec + egress; per-operation cost.",
        "mitigation": "Batch small objects; multipart for large; lifecycle to cheaper "
                      "tiers; spread writes across prefixes.",
    },
    "large_evidence_burst": {
        "label": "Large evidence file burst",
        "mult": {"connector_runs_per_day": 3.0},
        "size_mult": 8.0,
        "bottleneck": "Upload/normalize RAM + storage growth + bandwidth.",
        "mitigation": "Multipart upload; stream hashing; compress; cap max object size.",
    },
}

# Fixed-scale simulations (absolute connector/DB-target counts) per PART 3.
_SCALE_SIMS = {
    "sim_100_connectors": {"kind": "connectors", "count": 100},
    "sim_500_connectors": {"kind": "connectors", "count": 500},
    "sim_1000_connectors": {"kind": "connectors", "count": 1000},
    "sim_100_db_targets": {"kind": "db_targets", "count": 100},
    "sim_500_db_targets": {"kind": "db_targets", "count": 500},
    "sim_1000_db_targets": {"kind": "db_targets", "count": 1000},
}


def list_scenarios() -> list[str]:
    return list(_SCENARIOS.keys()) + list(_SCALE_SIMS.keys())


def _impact(base: CapacityProfile, stressed: CapacityProfile, size_mult: float = 1.0) -> dict[str, Any]:
    """Compute CPU/RAM/network/storage/queue deltas between base and stressed."""
    from benchmarks.capacity import network as nw
    from benchmarks.capacity import workload as wl

    if size_mult != 1.0:
        stressed = replace(stressed, avg_evidence_size_kb=stressed.avg_evidence_size_kb * size_mult)

    base_cpu = wl.cpu_breakdown(base)["peak_cores"]
    str_cpu = wl.cpu_breakdown(stressed)["peak_cores"]
    base_ram = wl.ram_breakdown(base)["peak_total_mib"]
    str_ram = wl.ram_breakdown(stressed)["peak_total_mib"]
    base_net = nw.network_bandwidth(base, nw.connector_benchmark(base))["connector_ingress_gib_per_day"]
    str_net = nw.network_bandwidth(stressed, nw.connector_benchmark(stressed))["connector_ingress_gib_per_day"]

    base_upload = base.connector_runs_per_day * 5 * base.avg_evidence_size_kb
    str_upload = stressed.connector_runs_per_day * 5 * stressed.avg_evidence_size_kb
    base_queue = base.scheduler_jobs_per_day
    str_queue = stressed.scheduler_jobs_per_day

    def factor(a: float, b: float) -> float:
        return _round(b / a, 2) if a else None

    return {
        "cpu": {"baseline_peak_cores": base_cpu, "stressed_peak_cores": str_cpu,
                "impact_factor": factor(base_cpu, str_cpu)},
        "ram": {"baseline_peak_mib": base_ram, "stressed_peak_mib": str_ram,
                "impact_factor": factor(base_ram, str_ram)},
        "network": {"baseline_ingress_gib_day": base_net, "stressed_ingress_gib_day": str_net,
                    "impact_factor": factor(base_net, str_net)},
        "storage": {"baseline_upload_kb_day": _round(base_upload), "stressed_upload_kb_day": _round(str_upload),
                    "impact_factor": factor(base_upload, str_upload)},
        "queue": {"baseline_jobs_day": base_queue, "stressed_jobs_day": str_queue,
                  "impact_factor": factor(base_queue, str_queue)},
    }


def run_scenario(profile: CapacityProfile, scenario: str) -> dict[str, Any]:
    """Estimate one stress scenario's impact + bottleneck + mitigation. Never raises."""
    if scenario in _SCENARIOS:
        spec = _SCENARIOS[scenario]
        overrides = {}
        for field_name, mult in spec.get("mult", {}).items():
            overrides[field_name] = int(getattr(profile, field_name) * mult)
        stressed = replace(profile, **overrides)
        impact = _impact(profile, stressed, size_mult=spec.get("size_mult", 1.0))
        return {
            "scenario": scenario,
            "label": spec["label"],
            "multipliers": spec.get("mult", {}),
            "impact": impact,
            "expected_bottleneck": spec["bottleneck"],
            "recommended_mitigation": spec["mitigation"],
        }
    if scenario in _SCALE_SIMS:
        sim = _SCALE_SIMS[scenario]
        count = sim["count"]
        if sim["kind"] == "connectors":
            # Simulate N connector executions in a burst window (~1 hour).
            stressed = replace(profile, connector_runs_per_day=max(profile.connector_runs_per_day, count * 24))
            bottleneck = "Connector worker CPU + outbound/cross-cloud bandwidth."
            mitigation = f"Pool + rate-limit {count} connectors; stagger; scale worker pods."
        else:  # db_targets
            stressed = replace(profile, connector_runs_per_day=max(profile.connector_runs_per_day, count * 12),
                               scheduler_jobs_per_day=max(profile.scheduler_jobs_per_day, count * 12))
            bottleneck = "Cloud SQL connections + DB Agent pool across many targets."
            mitigation = f"PgBouncer + read replicas for {count} targets; bound parallelism."
        impact = _impact(profile, stressed)
        return {
            "scenario": scenario,
            "label": f"Simulate {count} {sim['kind']}",
            "target_count": count,
            "impact": impact,
            "expected_bottleneck": bottleneck,
            "recommended_mitigation": mitigation,
        }
    return {"scenario": scenario, "error": "unknown_scenario",
            "valid": list_scenarios()}


def run_all(profile: CapacityProfile) -> dict[str, Any]:
    """Run every stress scenario for a profile."""
    return {
        "profile": profile.key,
        "scenarios": {name: run_scenario(profile, name) for name in list_scenarios()},
        "_basis": "Baseline activity × documented stress multipliers, re-run through "
                  "the CPU/RAM/network estimators. No external calls.",
    }
