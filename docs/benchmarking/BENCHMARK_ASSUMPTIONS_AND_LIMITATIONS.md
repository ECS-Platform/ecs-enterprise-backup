# ECS Benchmark — Assumptions & Limitations

The authoritative catalogue of every assumption behind the Infrastructure
Benchmark Workbench, plus a clear statement of what is **estimated** vs
**measured** vs **calibrated**, and what needs production data to firm up.

> All figures are **estimates** from documented per-unit constants × scenario
> profiles — not measurements. Every constant below is overridable
> (`SizingConstants.from_overrides(...)`, `CostRates.from_overrides(...)`, etc.)
> and should be calibrated from real runs — see [`CALIBRATION_GUIDE.md`](CALIBRATION_GUIDE.md).

## 1. Where assumptions live (source of truth)

| Constants class | Module | Governs |
|-----------------|--------|---------|
| `SizingConstants` | `benchmarks/capacity/sizing.py` | GKE compute, Cloud SQL/pgvector rows, GCS, logging |
| `WorkloadConstants` | `workload.py` | per-operation CPU-ms + per-consumer RAM |
| `DbDurabilityConstants` | `storage.py` | WAL/vacuum/checkpoint/backup/restore/partition |
| `ObjectStorageConstants` | `storage.py` | size distribution, dedup, compression, tiers |
| `ThroughputConstants` | `storage.py` | upload/download latency, ops-cost |
| `NetworkConstants` + `_CONNECTOR_PROFILE` | `network.py` | bandwidth, per-connector, DB Agent |
| `AiThroughputConstants` | `ai.py` | prompts/tokens/embeddings per sec |
| `CostRates` | `cost.py` | GCP unit prices |
| `CapacityProfile` | `profiles.py` | scenario workload drivers |

## 2. Assumption catalogue

Confidence: **M** = medium (defensible planning default), **L** = low (needs
real data), **VL** = very low (order-of-magnitude). Calibrate = how to firm up.

### CPU (`WorkloadConstants`)
| Assumption | Value | Source / reason | Formula | Conf | Calibrate |
|---|---|---|---|---|---|
| CPU-ms / API request | 40 | Framework request overhead (planning) | count×ms→core-h | L | Telemetry CPU % ÷ RPS |
| CPU-ms / connector run | 800 | fetch+normalize+ingest | " | L | Time a real connector run |
| CPU-ms / scheduler job | 200 | plan/route/dispatch | " | L | Scheduler telemetry |
| CPU-ms / prompt run | 1500 | assemble + retrieve (LLM separate) | " | L | Prompt-path telemetry |
| Parse (JSON/CSV/Excel/PDF) | 5/12/60/40 | relative parse cost | " | VL | Profile parsers |
| ZIP/compression/report | 50/25/80 | packaging cost | " | VL | Time exports |
| peak_to_average_factor | 3.0 | busy-minute vs working-hours avg | ×avg | M | Observe peak/avg from logs |

### RAM (`WorkloadConstants`)
| Assumption | Value | Source / reason | Conf | Calibrate |
|---|---|---|---|---|
| RAM MiB / API request | 4 | transient per in-flight request | L | RSS ÷ concurrency |
| RAM MiB / connector run | 64 | buffers + working set | L | Connector RSS |
| RAM MiB / prompt run | 256 | context assembly working set | L | Prompt RSS |
| pod base RAM | 512 MiB | app + libs idle | M | Idle pod RSS |
| caches | 128 MiB | dashboard/mapping TTL caches | M | Cache size at steady state |

### Evidence / storage (`profiles`, `ObjectStorageConstants`)
| Assumption | Value | Source / reason | Conf | Calibrate |
|---|---|---|---|---|
| Average evidence size | 150–350 KB (per profile) | typical config/log/attestation | M | Mean of stored objects |
| Largest evidence (max) | 20× average | worst-case big artifact | L | p100 of stored objects |
| Median / p95 evidence | 0.7× / 3× average | size distribution shape | L | Percentiles of stored objects |
| Evidence versions / year | 2–4 (per profile) | re-collection cadence | M | Version counts in repo |
| Dedup ratio | 0.15 | duplicate evidence savings | L | Dedup analysis on bucket |
| Compression ratio | 0.6 | stored/original (compressible) | L | Compress sample objects |
| chunks / evidence | 4 | RAG chunking | M | Vector store chunk counts |
| embedding dims | 768 | `config/vectorstore.yaml` | **H** | Config-derived (exact) |

### Activity (`CapacityProfile`)
| Assumption | Value | Source / reason | Conf | Calibrate |
|---|---|---|---|---|
| Average connector payload | 250–900 KB (per connector) | `network._CONNECTOR_PROFILE` | L | Capture real responses |
| Average prompt size | token-estimated (chars/4) | `token_estimator` | M | Audit-LLM benchmark |
| Average output tokens | 512 (or measured) | worst-case bound in workbook | M | `run_audit_llm_benchmark` |
| Uploads / day | connector_runs×5 + prompt×0.5 | derived from activity | L | Count uploads/day |
| Reports / day | prompt_runs×0.5 | derived | L | Count reports/day |
| API requests / day | per profile | scenario driver | L | Access-log RPS |

### Database (`SizingConstants`, `DbDurabilityConstants`)
| Assumption | Value | Source / reason | Conf | Calibrate |
|---|---|---|---|---|
| Bytes / evidence-meta row | 2048 | row + index share | M | `pg_total_relation_size` |
| Index overhead | +35% | typical index share | M | Index vs table size |
| WAL amplification | 3× | WAL bytes / logical write | L | `pg_stat_wal` |
| Dead-tuple fraction | 0.2 | vacuum churn | L | `pg_stat_user_tables` |
| Backup compression | 0.4 | compressed dump / live | M | Measure a `pg_dump` |
| Observations / app / year | 60 | audit cadence | L | Observation store counts |

### Network (`NetworkConstants`)
| Assumption | Value | Source / reason | Conf | Calibrate |
|---|---|---|---|---|
| Retry rate | 0.05 | transient failures | L | Connector telemetry |
| Timeout rate | 0.01 | " | L | " |
| Cross-cloud connectors | AWS/Azure/GCP/GitHub/AzDO/Prisma flagged | `_CONNECTOR_PROFILE` | M | Network flow logs |
| API response size | 40 KB | avg UI/download payload | L | Access-log byte size |

### Logging / monitoring (`SizingConstants`)
| Assumption | Value | Source / reason | Conf | Calibrate |
|---|---|---|---|---|
| Bytes / app log | 512 | structured line | M | Cloud Logging sample |
| App logs / API request | 3 | per-request log volume | L | Log count ÷ requests |
| Log export fraction | 0.5 | archived to GCS | M | GCS log bucket growth |
| Monitoring base | ₹/$ fixed | Cloud Monitoring | L | Monitoring bill |

### Retention
| Assumption | Value | Source / reason | Conf |
|---|---|---|---|
| Retention years | 1/3/5/7 (per profile) + 1/3/5/7/10 projection | banking retention | M |
| Lifecycle tiers | Nearline 30d / Coldline 90d / Archive 365d | GCS defaults | M |

### Cost (`CostRates`)
| Assumption | Value | Source / reason | Conf | Calibrate |
|---|---|---|---|---|
| All GCP unit rates | illustrative list prices | `CostRates` | **VL** | Replace with a real quote |
| SQL HA multiplier | 2× | regional HA | M | Quote |
| 5-yr storage growth | +60%/yr cumulative | growth curve | L | Actual data growth |

## 3. Estimated vs Measured vs Calibrated

| Dimension | Estimated (default) | Can be Measured | Can be Calibrated |
|---|---|---|---|
| Prompt tokens | ✅ (chars/4) | ✅ audit-LLM benchmark | ✅ `measured_tokens=` |
| CPU / RAM per op | ✅ | ✅ `RuntimeTelemetry` | ✅ `calibrate()` → constants |
| Embedding dims | — (config-exact) | ✅ | n/a (exact) |
| DB row sizes | ✅ | ✅ `pg_total_relation_size` | ✅ override constants |
| WAL / vacuum | ✅ | ✅ `pg_stat_wal` | ✅ |
| Object sizes / distribution | ✅ | ✅ bucket stats | ✅ update profile |
| Network bandwidth | ✅ | ✅ VPC flow logs | ✅ |
| Cost | ✅ (illustrative) | ✅ GCP billing | ✅ `CostRates` |

## 4. Limitations (what the model does / doesn't do)

| Area | Status | Needs |
|------|--------|-------|
| Token sizing | **Estimated** (chars/4) or **measured** via audit-LLM benchmark | Live model run for exact tokens |
| CPU/RAM per workload | **Estimated** | **Production telemetry** (`RuntimeTelemetry` + real load) |
| DB growth / durability | **Estimated** | **Production DB metrics** (`pg_stat_*`, actual sizes) |
| Object storage | **Estimated** | **Cloud monitoring** (bucket stats, op counts) |
| Network / cross-cloud | **Estimated** | **VPC flow logs / egress metrics** |
| Kubernetes sizing | **Recommendation model** (no live cluster) | **Kubernetes metrics** (HPA history, real pod usage) |
| Concurrency / peak | **Coarse** (avg × peak factor) | **Load testing** (see `../testing/ECS_LOAD_TESTING_REFERENCE.md`) |
| Cost | **Illustrative rates** | **GCP quote / billing export** |
| Stress scenarios | **Modeled** (multipliers) | **Executed load test** for real limits |
| End-to-end accuracy | **Uncalibrated** at first | Several **calibration** cycles against telemetry |

## Related
- [`INFRASTRUCTURE_BENCHMARK_GUIDE.md`](INFRASTRUCTURE_BENCHMARK_GUIDE.md) · [`CALIBRATION_GUIDE.md`](CALIBRATION_GUIDE.md) · [`RUNTIME_TELEMETRY_GUIDE.md`](RUNTIME_TELEMETRY_GUIDE.md) · [`BENCHMARK_TRACEABILITY.md`](BENCHMARK_TRACEABILITY.md) · [`BENCHMARK_MATURITY_ASSESSMENT.md`](BENCHMARK_MATURITY_ASSESSMENT.md)
