# ECS Go-Live Checklist

**Purpose:** the cut-over runbook to take ECS live. Sequenced, with owners and rollback triggers. Grounded in repository configuration and scripts. Documentation only.

> Prerequisite: `ECS_PRODUCTION_CHECKLIST.md` fully signed off.

---

## T-7 days — readiness

- [ ] Production checklist signed (security, DBA, platform, product).
- [ ] Environment provisioned: app host(s), `postgres` repo, `pgvector`, `minio`/S3, `redis`, LLM (Ollama host or managed key).
- [ ] DNS/TLS/reverse proxy configured to app `:8000`.
- [ ] Backup schedule live; one successful backup + restore drill (`validate_backup_restore.sh` exit 0).
- [ ] Monitoring + alerts wired (`/readyz`, 5xx, DB/vector/MinIO/Redis, connector sync).

## T-3 days — data & integrations

- [ ] Frameworks/control library loaded (`/mvp/framework-loader`, `/mvp/framework-admin`).
- [ ] Applications onboarded (`/mvp/platform/onboarding`).
- [ ] Required connectors enabled + authenticated (`/api/platform/health` = Connected); first sync done.
- [ ] Vector store populated; AI Assistant returns grounded citations.
- [ ] RBAC roles mapped to real IdP groups (`config/rbac.yaml` + `auth.yaml`).

## T-1 day — dress rehearsal

- [ ] `./venv/bin/pytest` green; demo-readiness validator READY (in a staging copy).
- [ ] End-to-end smoke as each key persona (CIO, Auditor, Compliance, Admin, Ops).
- [ ] Evidence collect → validate → reuse → report verified on real data.
- [ ] Rollback procedure reviewed; backup taken immediately before cut-over.

## T-0 — cut-over

1. [ ] Maintenance notice sent.
2. [ ] Final backup: `scripts/backup/backup.sh --vector`.
3. [ ] Deploy production app image (no `--reload`, no source bind-mounts).
4. [ ] Set production env: `ECS_AUTH_ENABLED=true`, `DEMO_MODE=false`, real secrets.
5. [ ] Start backing services → confirm container healthchecks (`pg_isready`, `mc ready`).
6. [ ] Start app → `curl /healthz` 200, `curl /readyz` 200.
7. [ ] `curl /api/platform/health` → all enabled connectors Connected.
8. [ ] Smoke: login (real OIDC) → dashboards → a report.
9. [ ] Enable traffic at the proxy/LB.
10. [ ] Announce live.

## T+1 hour — hypercare

- [ ] Watch logs/alerts: 5xx, `/readyz` flaps, connector sync errors, LLM latency.
- [ ] Verify scheduled collection ran.
- [ ] Confirm audit logging writing (`audit_log` rows growing).

## T+1 week

- [ ] Backup ran nightly; restore drill repeated.
- [ ] Review KPI/readiness dashboards with product owner.
- [ ] Close hypercare; hand to BAU support (`ECS_SUPPORT_RUNBOOK.md`).

---

## Rollback triggers (→ `ECS_ROLLBACK_PROCEDURE.md`)

| Trigger | Action |
|---|---|
| `/readyz` 503 unresolved > 15 min | Roll back app / fix DB |
| Auth lockout (no one can log in) | Revert `auth.yaml`/env; re-verify OIDC |
| Data corruption / wrong data shown | Restore from pre-cutover backup |
| Mass connector auth failure | Disable affected connectors; proceed degraded |

**Go/No-Go owner:** ____ · **Date/time:** ____
