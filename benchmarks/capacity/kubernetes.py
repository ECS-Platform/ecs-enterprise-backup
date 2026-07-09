"""Kubernetes / GKE recommendation model (PART 2).

Derives Kubernetes-specific guidance from an existing capacity estimate (produced
by ``sizing.estimate_capacity``) — pod requests/limits, replicas, node pool, HPA,
Cluster Autoscaler, PodDisruptionBudget, rolling-deployment + startup + headroom
assumptions, and eviction-risk notes.

No live cluster is required; this is a pure recommendation model over the capacity
output. It does NOT change the existing GKE sizing in ``sizing.py`` — it enriches
it with K8s-object-level guidance.
"""

from __future__ import annotations

from typing import Any


def _int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def recommend(estimate: dict[str, Any]) -> dict[str, Any]:
    """Full Kubernetes recommendation from a capacity estimate. Never raises."""
    gke = estimate.get("gke_compute", {}) or {}
    nodes = estimate.get("node_pool", {}) or {}
    ram = estimate.get("ram_breakdown", {}) or {}
    profile = estimate.get("profile", {}) or {}

    pod = gke.get("recommended_pod", {}) or {}
    replicas = _int(gke.get("recommended_replicas", 2), 2)
    node_count = _int(nodes.get("recommended_nodes", 2), 2)
    node_type = nodes.get("node_machine_type", "e2-standard-4")
    node_vcpu = _int(nodes.get("node_vcpu", 4), 4)

    # PodDisruptionBudget: keep majority available during voluntary disruptions.
    min_available = max(1, replicas - 1) if replicas > 1 else 1

    # HPA: scale between the HA floor and ~2.5x for burst; CPU target 60%.
    hpa_min = max(2, replicas)
    hpa_max = max(hpa_min + 1, int(replicas * 2.5) + 1)

    # RAM-informed pod memory sanity: bump request if peak RAM per replica is high.
    peak_ram_mib = ram.get("peak_total_mib") or 0
    ram_per_replica = (peak_ram_mib / replicas) if replicas else peak_ram_mib
    mem_note = ""
    try:
        req_mib = int(str(pod.get("memory_request", "1024Mi")).rstrip("Mi"))
        if ram_per_replica > req_mib:
            mem_note = (f"Peak RAM/replica (~{round(ram_per_replica)}Mi) exceeds the "
                        f"memory request ({req_mib}Mi) — consider raising requests or replicas.")
    except (TypeError, ValueError):
        pass

    # Node headroom: pods per node bounded by allocatable vCPU vs pod CPU request.
    try:
        pod_cpu_req = int(str(pod.get("cpu_request", "500m")).rstrip("m"))
        alloc_cpu_ms = node_vcpu * 1000 * 0.75
        pods_per_node = max(1, int(alloc_cpu_ms / pod_cpu_req))
    except (TypeError, ValueError):
        pods_per_node = 4

    return {
        "workload": {
            "kind": "Deployment (stateless web tier)",
            "replicas": replicas,
            "pod_requests": {
                "cpu": pod.get("cpu_request", "500m"),
                "memory": pod.get("memory_request", "1024Mi"),
            },
            "pod_limits": {
                "cpu": pod.get("cpu_limit", "1000m"),
                "memory": pod.get("memory_limit", "2048Mi"),
            },
            "separate_rag_pool": "Run the LLM-RAG workload as its own Deployment/node "
                                 "pool (heavier RAM, different scaling).",
        },
        "hpa": {
            "enabled": True,
            "min_replicas": hpa_min,
            "max_replicas": hpa_max,
            "target_cpu_utilization_percent": 60,
            "note": "Scale on CPU; add a custom RPS metric for latency-sensitive SLOs.",
        },
        "node_pool": {
            "machine_type": node_type,
            "node_count": node_count,
            "pods_per_node_est": pods_per_node,
            "multi_az": "Spread across >=2 zones (regional cluster) for HA.",
        },
        "cluster_autoscaler": {
            "enabled": True,
            "min_nodes": max(2, node_count),
            "max_nodes": max(node_count + 1, node_count * 3),
            "note": "Bound max nodes by Cloud SQL connection limits and cost.",
        },
        "pod_disruption_budget": {
            "min_available": min_available,
            "note": "Protects availability during node upgrades / voluntary evictions.",
        },
        "rolling_deployment": {
            "strategy": "RollingUpdate",
            "max_surge": "25%",
            "max_unavailable": "0",
            "note": "Zero-unavailable rollout needs >=1 spare replica of headroom.",
        },
        "pod_startup": {
            "readiness_probe": "GET /readyz (checks PostgreSQL) — gates traffic.",
            "liveness_probe": "GET /healthz (no I/O) — restarts only on true hangs.",
            "startup_probe": "Allow ~30-60s for app + model warm-up before liveness.",
        },
        "headroom_assumptions": {
            "node_allocatable_factor": 0.75,
            "cpu_target_utilization": 0.60,
            "peak_to_average_factor": 3.0,
            "notes": "Sized for peak = 3x working-hours average at 60% CPU target.",
        },
        "eviction_risk": {
            "risk": "low" if ram_per_replica and peak_ram_mib and ram_per_replica < 1536 else "medium",
            "notes": [n for n in [
                mem_note,
                "Set memory requests>=working set to avoid OOM/eviction under pressure.",
                "Avoid CPU limits far below requests to prevent throttling of prompt/connector work.",
            ] if n],
        },
        "_basis": "Derived from the capacity estimate's GKE compute + RAM breakdown; "
                  "recommendation model only (no live cluster).",
    }
