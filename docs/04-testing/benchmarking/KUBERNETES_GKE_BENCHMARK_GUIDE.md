# ECS Kubernetes / GKE Benchmark Guide

`benchmarks/capacity/kubernetes.py` turns a capacity estimate into
Kubernetes-object-level recommendations — **no live cluster required**. It
enriches (does not replace) the GKE sizing in `sizing.py`.

## Recommendations produced
- **Workload:** Deployment kind, replicas, pod CPU/memory **requests + limits**,
  separate LLM-RAG pool guidance.
- **HPA:** enabled, min/max replicas, target CPU utilization (60%).
- **Node pool:** machine type, node count, estimated pods/node, multi-AZ note.
- **Cluster Autoscaler:** min/max nodes (bounded by Cloud SQL connections/cost).
- **PodDisruptionBudget:** `minAvailable` for safe upgrades/evictions.
- **Rolling deployment:** strategy, maxSurge/maxUnavailable, headroom note.
- **Pod startup:** readiness `/readyz`, liveness `/healthz`, startup probe window.
- **Headroom assumptions:** allocatable factor, CPU target, peak-to-average.
- **Eviction risk:** risk level + memory-request/limit notes.

## Basis
Derived from the estimate's `gke_compute` (peak cores, pod shape, replicas) and
`ram_breakdown` (peak RAM/replica → eviction risk). Recommendation model only.

## CLI
```bash
python scripts/benchmark_capacity.py --profile enterprise --kubernetes
python scripts/benchmark_capacity.py --profile enterprise --kubernetes --stress
```

## Interpreting
- Apply pod requests/limits + PDB + HPA verbatim as a starting point.
- Run the RAG/LLM workload on its own pool (heavier RAM).
- Bound autoscaler max by Cloud SQL connection limits (see the database guide).
- Full provisioning steps: [`../deployment/GCP_DEPLOYMENT_GUIDE.md`](../../03-development/deployment/GCP_DEPLOYMENT_GUIDE.md).

## Related
- [`ADVANCED_INFRASTRUCTURE_BENCHMARK_GUIDE.md`](ADVANCED_INFRASTRUCTURE_BENCHMARK_GUIDE.md)
- [`INFRASTRUCTURE_BENCHMARK_GUIDE.md`](INFRASTRUCTURE_BENCHMARK_GUIDE.md) §7
