# ECS Deployment Pack (Examples — Non-Production Until Security Review)

> **⚠️ These are EXAMPLE templates.** They contain **placeholders only** — no real
> IPs, hostnames, or secrets — and are **not production-ready until reviewed and
> approved by the bank's security/platform team**. Treat every `<...>` as a value
> to be supplied from a **secret manager** or environment config, never committed.

This pack gives platform/SRE teams a concrete starting point for deploying ECS
(the Evidence Collection System) into UAT/production. It complements the operations
runbooks in [`docs/operations/`](../docs/operations) and the readiness register in
`docs/production/PRODUCTION_READINESS_GAP_REGISTER.md`.

---

## Contents

| File | Purpose |
|------|---------|
| `docker-compose.prod.example.yml` | Single-host container deployment (app + reverse proxy). |
| `nginx/ecs.conf.example` | Reverse-proxy / TLS termination in front of ECS. |
| `systemd/ecs.service.example` | Run ECS as a managed systemd service (VM deployment). |
| `kubernetes/ecs-deployment.example.yaml` | K8s Deployment (replicas, probes, resources, env). |
| `kubernetes/ecs-service.example.yaml` | K8s Service (ClusterIP; front with an Ingress). |
| `kubernetes/ecs-configmap.example.yaml` | Non-secret configuration (env). |
| `kubernetes/ecs-secret.example.yaml` | Secret **shape only** — populate from a secrets manager. |

---

## The ECS runtime, in one line

ECS is a FastAPI app started with:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Container image: build from the repo `Dockerfile` (Python 3.12-slim, exposes 8000).

---

## Health probes

Use these for liveness/readiness (all offline-safe, no live external calls):

| Probe | Endpoint | Notes |
|-------|----------|-------|
| Liveness | `GET /healthz` | Process up; does no I/O so a slow dependency never restarts a healthy pod. |
| Readiness | `GET /readyz` | Returns 200 when the PostgreSQL repository is reachable, else 503; gate traffic on 200. |
| App health | `GET /api/audit/health` | Application-level `ok`/`degraded` summary (never leaks secrets). |
| Integrations | `GET /api/audit/integrations/health` | Config-only adapter health (masked). |

> Query params `?role=owner&user=probe` may be required depending on auth config;
> in production with auth enabled, use an unauthenticated health path or a probe
> service account per the security review.

---

## Environment configuration

Generate placeholder env templates and populate them from your secret store:

```bash
python scripts/generate_env_template.py --env uat     # -> .env.uat.template
python scripts/generate_env_template.py --env prod    # -> .env.prod.template
```

- **Never commit** the populated `.env.uat` / `.env.prod` (git-ignored).
- In Kubernetes, split **non-secret** config into the ConfigMap and **secrets**
  into the Secret (sourced from a secrets manager / external-secrets operator).

---

## Data & dependencies (production)

- **Postgres (durable audit persistence).** Provision Postgres and apply
  `docs/DB_SCHEMA_AUDIT_INTELLIGENCE.sql`. Set `ECS_AUDIT_DB_URL` from a secret
  manager. See `docs/audit-intelligence/AUDIT_INTELLIGENCE_PERSISTENCE_GUIDE.md`.
- **Object storage (evidence artifacts, optional).** If storing raw evidence
  blobs, use S3-compatible object storage (the demo compose uses MinIO). ECS
  stores **hashes + metadata**, never secrets, in the DB.
- **Secrets manager.** Vault / cloud secrets / K8s Secrets — inject as env at
  startup. ECS only ever displays `SET`/`MISSING`, never secret values.

---

## Pre-deploy checklist (summary)

1. Security review of these examples completed and sign-off recorded.
2. Postgres provisioned + schema applied; `ECS_AUDIT_DB_URL` in the secret store.
3. Secrets populated in the secret manager (never in Git).
4. Reverse proxy / Ingress configured with TLS.
5. Health probes wired (liveness `/healthz`, readiness `/readyz`).
6. Run the production smoke check: `python scripts/run_production_smoke.py --strict`.
7. Follow `docs/operations/DEPLOYMENT_RUNBOOK.md` and `PRODUCTION_CHECKLIST.md`.

> Nothing in this pack should be applied to a bank environment without completing
> the checklist and obtaining security approval.
