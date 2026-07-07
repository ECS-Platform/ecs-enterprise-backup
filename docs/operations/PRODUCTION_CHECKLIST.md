# ECS Production Checklist

A concise go/no-go checklist for promoting ECS to production. Complete every gate
and record sign-off. Pairs with the deployment/validation/rollback runbooks in this
folder and the readiness register in
`docs/production/PRODUCTION_READINESS_GAP_REGISTER.md`.

> No real IPs/hostnames/secrets in this file. All environment specifics live in
> the secret manager / env config.

---

## 1. Security & secrets
- [ ] `deploy/` examples reviewed and approved by security (they ship as
      non-production examples).
- [ ] All secrets sourced from a **secret manager** (Vault / cloud / K8s Secrets);
      **no** secrets in Git.
- [ ] `.env.prod` / `.env.uat` populated locally only and confirmed git-ignored
      (`git check-ignore .env.prod`).
- [ ] Verified ECS logs and API responses show **`SET`/`MISSING`**, never secret
      values (`scripts/run_uat_connector_health.py --adapter all`).
- [ ] TLS enabled at the reverse proxy / Ingress; HTTP redirects to HTTPS.
- [ ] Auth/RBAC enabled (`ECS_AUTH_ENABLED=true`); health probe path agreed.

## 2. Data & persistence
- [ ] Postgres provisioned and reachable; `ECS_AUDIT_DB_URL` in the secret store.
- [ ] Schema applied: `psql "$ECS_AUDIT_DB_URL" -f docs/DB_SCHEMA_AUDIT_INTELLIGENCE.sql`.
- [ ] Durable persistence backend selected at startup (see the persistence guide).
- [ ] Backup/restore verified per `ECS_BACKUP_AND_RECOVERY_GUIDE.md`.
- [ ] Data retention policy agreed (see the gap register).

## 3. Configuration
- [ ] Env templates generated + populated
      (`python scripts/generate_env_template.py --env prod`).
- [ ] Non-secret config in ConfigMap; secrets in Secret (K8s) — no cross-over.
- [ ] Connector base URLs point at approved endpoints (no real hostnames in Git).

## 4. Deployment
- [ ] Image built from the repo `Dockerfile` and pushed to the approved registry
      (pinned tag, never `:latest`).
- [ ] Chosen method applied (systemd / Compose / Kubernetes) per
      [DEPLOYMENT_RUNBOOK.md](DEPLOYMENT_RUNBOOK.md).
- [ ] Replicas ≥ 2 (HA) with rolling updates and readiness gating (K8s).
- [ ] Liveness/readiness probes on `GET /api/audit/health` configured.
- [ ] Resource requests/limits set.

## 5. Validation (must pass)
- [ ] `python scripts/run_production_smoke.py --strict` → PASS.
- [ ] `python scripts/run_production_smoke.py --base-url https://<host> --strict` → PASS.
- [ ] `python scripts/run_uat_connector_health.py --adapter all --no-network` reviewed.
- [ ] Configured adapters healthy (`--live --strict`).
- [ ] Key API + UI routes return 200 (no 404) — see
      [UAT_VALIDATION_RUNBOOK.md](UAT_VALIDATION_RUNBOOK.md).
- [ ] `python scripts/run_ecs_demo_smoke.py` → 10/10 ALL PASS (offline sanity).

## 6. Observability & operations
- [ ] Logs shipped to the platform; **no secrets** present.
- [ ] Metrics/health monitored; alerts on health regression + run failures.
- [ ] Runbooks linked in the on-call system: deployment, UAT validation, connector
      troubleshooting, rollback.
- [ ] Rollback rehearsed / understood ([ROLLBACK_RUNBOOK.md](ROLLBACK_RUNBOOK.md)).

## 7. Sign-off
- [ ] Change record created (version, image tag, approver, window).
- [ ] Gaps and pending items logged in
      `docs/production/PRODUCTION_READINESS_GAP_REGISTER.md`.
- [ ] Go/no-go decision recorded by the accountable owner.

> Any unchecked item in §1 (security/secrets) or §5 (validation) is a **no-go**.
