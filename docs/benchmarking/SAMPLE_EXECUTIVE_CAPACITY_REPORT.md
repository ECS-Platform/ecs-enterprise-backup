<!-- Generated sample — reproduce with: python scripts/benchmark_capacity.py --all --executive --html -->
<!-- Do not hand-edit; regenerate from the workbench. Figures are estimates. -->

# ECS Executive Capacity Planner

> Executive estimate — documented assumptions × profiles; cost rates illustrative. Calibrate before spend decisions.

## Recommended sizing

| Profile | Apps | GKE (repl×nodes) | Pod CPU/Mem | Cloud SQL | GCS y1 | GCS y5 | Cost/mo | Cost 5y |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Developer Laptop | 1 | 2×2 e2-standard-4 | 500m/1024Mi | db-custom-2-7680 | 0.1657 GiB | 0.1657 GiB | 558.25 | 33498.6 |
| Pilot | 2 | 2×2 e2-standard-4 | 500m/1024Mi | db-custom-2-7680 | 1.106 GiB | 3.2035 GiB | 558.63 | 33548.76 |
| Demo / Local | 3 | 2×2 e2-standard-4 | 500m/1024Mi | db-custom-2-7680 | 0.4683 GiB | 0.4683 GiB | 558.33 | 33509.16 |
| Phase 1 — NB / MB / Payments | 3 | 2×2 e2-standard-4 | 500m/1024Mi | db-custom-2-7680 | 2.6738 GiB | 12.7967 GiB | 559.21 | 33625.32 |
| Phase 2 — 15 applications | 15 | 2×2 e2-standard-4 | 500m/1024Mi | db-custom-2-7680 | 11.1052 GiB | 52.9509 GiB | 562.02 | 33996.24 |
| 25 applications | 25 | 2×2 e2-standard-4 | 500m/1024Mi | db-custom-2-7680 | 18.1646 GiB | 86.2833 GiB | 564.47 | 34319.64 |
| 50 applications | 50 | 2×2 e2-standard-4 | 500m/1024Mi | db-custom-2-7680 | 36.0502 GiB | 171.4011 GiB | 570.72 | 35144.64 |
| Enterprise — 100 applications | 100 | 3×2 e2-standard-4 | 500m/1024Mi | db-custom-2-7680 | 68.7311 GiB | 326.4896 GiB | 582.13 | 36650.76 |
| 250 applications | 250 | 6×2 e2-standard-4 | 500m/1024Mi | db-custom-2-7680 | 163.3722 GiB | 1081.3779 GiB | 615.29 | 41027.88 |
| Pan-Bank — 500 applications | 500 | 11×2 e2-standard-4 | 500m/1024Mi | db-custom-2-7680 | 303.4092 GiB | 2003.7016 GiB | 664.33 | 47501.16 |
| 1000 applications | 1000 | 21×4 e2-standard-4 | 500m/1024Mi | db-custom-2-7680 | 656.4509 GiB | 4349.6803 GiB | 1060.79 | 79392.36 |
| Large Enterprise — 2000 applications | 2000 | 41×7 e2-standard-4 | 500m/1024Mi | db-custom-4-15360 | 1313.7728 GiB | 8715.7577 GiB | 1925.62 | 147584.4 |

## Phase-wise sizing

| Phase | Apps | Replicas | Nodes | Cloud SQL | GCS y5 | Cost/mo |
| --- | --- | --- | --- | --- | --- | --- |
| Demo / Local | 3 | 2 | 2 | db-custom-2-7680 | 0.4683 GiB | 558.33 |
| Phase 1 — NB / MB / Payments | 3 | 2 | 2 | db-custom-2-7680 | 12.7967 GiB | 559.21 |
| Enterprise — 100 applications | 100 | 3 | 2 | db-custom-2-7680 | 326.4896 GiB | 582.13 |
| Pan-Bank — 500 applications | 500 | 11 | 2 | db-custom-2-7680 | 2003.7016 GiB | 664.33 |
| Large Enterprise — 2000 applications | 2000 | 41 | 7 | db-custom-4-15360 | 8715.7577 GiB | 1925.62 |

## Top 5 bottlenecks

1. GKE compute: peak ~12.259 cores → 41 replicas (scale the web tier).
2. Cloud SQL: db-custom-4-15360 — connection limits + query load are the DB ceiling.
3. AI/RAG: single-stream ~0.076 prompts/s — prompt concurrency is RAM-bound; use a dedicated RAG pool.
4. Cross-cloud egress: ~71.557 GiB/mo (AWS Net Banking ↔ GCP) — bandwidth + cost.
5. Cloud Logging: ~4.0512 GiB/day ingestion.

## Top 5 risks

1. Pod eviction/OOM risk: low — size memory requests ≥ working set.
2. DB slow-query risk: low at 32.2771 GiB year-1.
3. State externalization required before multi-replica scaling (in-memory ecs_state).
4. Cross-cloud connectivity + IAM must be least-privilege and monitored.
5. Backups/PITR + restore drills required for banking retention/DR.

## Top 5 cost optimizations

1. GCS lifecycle tiering (Nearline/Coldline/Archive) for cold evidence — large storage cost reduction.
2. Compression on evidence (~40.0% savings where compressible).
3. Committed-use discounts / autoscaling to match compute to real demand.
4. PgBouncer + read replicas to right-size Cloud SQL vCPU.
5. Batch small object writes + multipart large uploads to cut GCS op costs.