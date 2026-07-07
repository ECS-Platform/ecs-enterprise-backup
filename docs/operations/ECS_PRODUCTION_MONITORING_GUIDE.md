# ECS Production Monitoring Guide

**Purpose:** what to monitor, where the signals are, and alert thresholds. Grounded in `app/routes_platform.py` (`/healthz`, `/readyz`, `/api/platform/health`), `docker-compose.yml` healthchecks, `config/*.yaml`. Documentation only — ECS does not currently ship a metrics exporter (honest gap in §6).

---

## 1. Golden signals

| Signal | Source | Alert threshold |
|---|---|---|
| **App liveness** | `GET /healthz` | any non-200 / no response → page |
| **App readiness** | `GET /readyz` (503 when repo down) | 503 sustained > 2 min → page |
| **Error rate** | app logs (`docker compose logs ecs`) | 5xx > 1% of requests (5 min) → alert |
| **Latency** | reverse-proxy / app logs | p95 > target (set per env) → alert |
| **Saturation** | host CPU/mem | > 85% sustained → alert |

---

## 2. Backing services

| Service | Health signal | Alert |
|---|---|---|
| `postgres` repository | compose `pg_isready`; `/readyz` | down / pool exhausted (vs max 10) / disk > 85% |
| `pgvector` | `pg_isready` on `ecs_vectors` | down; vector count drift vs evidence |
| `minio` | `mc ready local`; console `:9001` | down; bucket errors; disk > 85% |
| `redis` | `redis-cli ping` | down (degraded, not fatal); memory/evictions |
| Ollama (host) | `:11434/api/tags` | daemon down; latency; model unloaded |

---

## 3. Connector monitoring

- **Source:** `GET /api/platform/health` (`health_overview()`) + Integration Health UI.
- **Alert on:** any enabled connector in `auth failed` / `unreachable` / `error`; sync failures; 0-evidence syncs.
- **Sync visibility:** `POST /api/platform/sync/{connector}` results; Scheduler success rate.
- Playbook: `ECS_CONNECTOR_FAILURE_PLAYBOOK.md`.

---

## 4. Application / business signals (in-product)

| Signal | Where | Watch for |
|---|---|---|
| Scheduler success rate | `/mvp/scheduler` | drop below ~98% |
| Connector health % | `/mvp/integration-health` | below ~95% |
| Evidence freshness | `/mvp/evidence-health`, `/mvp/lifecycle` | rising expiring/stale |
| Approval SLA | `/mvp/evidence-approval` | validation time climbing |
| Governance data quality | `/mvp/governance-quality` | completeness/validation drops |
| Audit log growth | `audit_log` table | flat = audit logging stalled |

---

## 5. Recommended alerts (priority)

| Pri | Condition | Action |
|---|---|---|
| P1 | `/healthz` down; `/readyz` 503 > 2 min; DB/MinIO down | page on-call → Support Runbook |
| P1 | Audit log not growing (logging broken) | investigate immediately (compliance impact) |
| P2 | Enabled connector failing; Ollama down | Connector / LLM playbook |
| P2 | Disk > 85% (repo/vector/minio) | expand / prune |
| P3 | Cache (Redis) down; latency elevated | restart; investigate |

---

## 6. Current capability & gap (honest)

| Capability | Status | Recommendation |
|---|---|---|
| Health/readiness probes | ✅ `/healthz`, `/readyz` | wire to LB + uptime monitor |
| Connector health API | ✅ `/api/platform/health` | scrape on interval |
| Container healthchecks | ✅ postgres/pgvector/minio | surface in orchestrator |
| Structured app logs | ⚠️ stdout via uvicorn | ship to log aggregator |
| **Metrics endpoint (Prometheus)** | ❌ not shipped | add exporter or scrape probes/logs |
| **Tracing** | ❌ | add OpenTelemetry (future) |
| **Dashboards/alerting stack** | ❌ (operator-provided) | Grafana/Alertmanager around the signals above |

Until a metrics exporter is added, monitoring relies on **probe polling + log scraping + the in-product health/Integration pages**, which is sufficient for a controlled production rollout.

---

## 7. Daily / weekly operational review

- **Daily:** health endpoints green; connector health; scheduler ran; backup succeeded; audit log growing.
- **Weekly:** restore drill (`validate_backup_restore.sh`); disk trends; evidence freshness; readiness KPIs with product owner.

Escalation and triage: `ECS_SUPPORT_RUNBOOK.md`.

---

## 8. Connector health & runtime references

- **Connector health endpoints:** `GET /api/audit/integrations/health` (all
  adapters, config-based), `GET /api/audit/integrations/{name}/health` (one).
- **Safe manual connector checks:** Connector Test Workbench —
  [../connector_test_workbench_design.md](../connector_test_workbench_design.md).
- **Scheduler dry-run readiness:** `scripts/run_uat_asset_scheduler.py --dry-run`
  (see [../scheduler_runtime_flow.md](../scheduler_runtime_flow.md)).
- **Connector API references:** [../enterprise_connector_api_reference.md](../enterprise_connector_api_reference.md),
  [../microsoft_graph_connector_api_reference.md](../microsoft_graph_connector_api_reference.md).
