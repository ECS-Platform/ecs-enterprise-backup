# ECS Disaster Recovery Plan

**Purpose:** recover ECS after catastrophic failure (host/site loss, full data corruption). Builds on `ECS_BACKUP_AND_RECOVERY_GUIDE.md`. Grounded in `docker-compose.yml`, `config/*.yaml`, `scripts/`. Documentation only.

> **Maturity note:** `docs/RECOVERY_RUNBOOK.md` states HA/DR automation/failover are **out of scope for the current phase**. This plan is therefore a **manual, backup-restore-based DR procedure** with a roadmap to automation. It is honest about current capability.

---

## 1. Scope & objectives

| Item | Value |
|---|---|
| Protected assets | `postgres` evidence repository, `minio` object store, `config`/secrets |
| Derived (rebuildable) | `pgvector`, `redis` |
| Current capability | Manual restore from off-host backups (no automated failover) |
| Target RPO | ≤ 24h (nightly) — tighten with WAL archiving |
| Target RTO | Provision + restore time (measure in drills) |

---

## 2. Disaster scenarios & response

| Scenario | Severity | Response |
|---|---|---|
| App host lost | S1 | Re-provision host, deploy app image, point to existing DB/object store |
| Repository DB lost/corrupt | S1 | Provision new Postgres, restore latest dump (§4) |
| Object store lost | S1 | Provision MinIO/S3, restore artifact snapshot, re-link |
| Vector store lost | S2 | Provision pgvector, **re-embed from repository** (no backup needed) |
| Full site loss | S1 | Execute full-site recovery (§5) at DR location |
| Ransomware / tampering | S1 | Restore from **immutable/offline** backup; verify `.sha256` |

---

## 3. Pre-requisites (maintain continuously)

- [ ] Off-host, encrypted backups of repository + object store (aligned windows).
- [ ] `config/*.yaml` in version control; secrets in a secret manager (recoverable).
- [ ] Documented infra-as-config: the 6 backing services + app (this repo's `docker-compose.yml` is the reference topology).
- [ ] Container images available in a registry (or rebuildable from `Dockerfile`).
- [ ] DR contact list + escalation (§7).
- [ ] Last successful restore drill date recorded.

---

## 4. Core recovery procedure (DB + artifacts)

```bash
# 1. Provision Postgres 16 (repository) + pgvector/pg16 + MinIO + Redis
# 2. Set env to new endpoints (ECS_REPO_PG_*, ECS_VECTOR_PG_*, MINIO_*, REDIS_URL)
# 3. Restore repository
scripts/restore/restore.sh --file <offhost>/ecs_repository_<UTC>.dump --create --db ecs_repository
# 4. Restore object store artifacts
mc mirror <offhost>/objects/<UTC> ecs/ecs-evidence
# 5. Start app; init_schema() reconciles; confirm /readyz 200
# 6. Re-embed vectors from repository (rebuild AI index)
# 7. Validate: row counts, dashboards, audit log, a sample evidence file opens
```

---

## 5. Full-site recovery sequence

1. Declare disaster; notify stakeholders; start incident log.
2. Stand up DR environment (compute, network, storage, TLS).
3. Provision backing services (Postgres repo, pgvector, MinIO, Redis).
4. Restore latest **verified** repository dump + object-store snapshot (§4).
5. Deploy production app image; set `ECS_AUTH_ENABLED=true`, `DEMO_MODE=false`, secrets.
6. Re-point/restore IdP (OIDC) reachability; re-enable connectors (credentials from secret store).
7. Re-embed vector store.
8. Health gate: `/healthz` 200, `/readyz` 200, `/api/platform/health` Connected.
9. Persona smoke test; enable traffic; announce.
10. Post-incident review; update RPO/RTO actuals.

---

## 6. Data integrity verification (after any DR restore)

- [ ] `pg_restore --list` clean; checksum verified.
- [ ] Row counts (`evidence`, `audit_log`, `observations`, `frameworks`, `controls`) match source/expected.
- [ ] Sample evidence record resolves to its MinIO artifact (lineage intact).
- [ ] Audit log continuity (no unexplained gaps).
- [ ] Vector count ≈ evidence count after re-embed.

---

## 7. Roles & escalation

| Role | Responsibility |
|---|---|
| DR Lead | Declares disaster, owns sequence, go/no-go |
| DBA | Repository restore + integrity |
| Platform eng | Infra provisioning, app deploy, object/vector/redis |
| Security | Secret recovery, OIDC, tamper verification |
| Product owner | Business comms, acceptance |

---

## 8. Roadmap to automated DR (not implemented — honest gap)

| Capability | Status | Target |
|---|---|---|
| Automated failover / HA replicas | ❌ | Streaming replication + standby promote |
| Continuous WAL archiving (PITR) | ❌ | Tighten RPO to minutes |
| Cross-region object replication | ❌ | MinIO/S3 replication |
| Schema version ledger (Alembic) | ❌ (roadmap in RECOVERY_RUNBOOK §5) | Versioned, reversible migrations |
| Automated DR drills | ❌ | Scheduled game-days |

Until these land, ECS DR is a **tested manual procedure**. Run the restore drill (`validate_backup_restore.sh`) regularly to keep RTO honest.
