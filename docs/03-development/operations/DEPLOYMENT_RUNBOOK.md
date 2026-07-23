# ECS Deployment Runbook

Operational, step-by-step procedure to deploy ECS (Evidence Collection System) to
UAT/production. Pairs with the templates in [`deploy/`](../../deploy) and the
[PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md).

> No real IPs/hostnames/secrets appear in this runbook. Every `<...>` is supplied
> from your environment config / secret manager at deploy time.

---

## 0. Prerequisites

- Security review of the `deploy/` examples completed and signed off.
- Container image built and pushed to your registry (from the repo `Dockerfile`).
- Postgres provisioned (for durable audit persistence) and reachable from ECS.
- Secrets available in the secret manager (never in Git).
- Python 3.12 runtime (matches the image base) for any host-run scripts.

---

## 1. Prepare configuration

```bash
# Generate placeholder env templates, then populate from the secret manager.
python scripts/generate_env_template.py --env prod       # -> .env.prod.template
cp .env.prod.template .env.prod                          # populate; DO NOT COMMIT
```

- Split config for Kubernetes: non-secret → ConfigMap, secrets → Secret (sourced
  from a secrets manager). See `deploy/kubernetes/`.
- Confirm `.env.prod` is git-ignored: `git check-ignore .env.prod` → prints the path.

---

## 2. Apply the database schema (durable persistence)

```bash
psql "$ECS_AUDIT_DB_URL" -f docs/DB_SCHEMA_AUDIT_INTELLIGENCE.sql   # idempotent
```

Set `ECS_AUDIT_DB_URL` from the secret manager. See
`docs/03-development/audit-intelligence/AUDIT_INTELLIGENCE_PERSISTENCE_GUIDE.md`.

---

## 3. Start ECS

**Option A — systemd (VM):**
```bash
sudo cp deploy/systemd/ecs.service.example /etc/systemd/system/ecs.service
sudo install -o ecs -g ecs -m 0600 /dev/null /etc/ecs/ecs.env     # then populate
sudo systemctl daemon-reload && sudo systemctl enable --now ecs
```

**Option B — Docker Compose (single host):**
```bash
docker compose -f deploy/docker-compose.prod.example.yml --env-file .env.prod up -d
```

**Option C — Kubernetes:**
```bash
kubectl apply -f deploy/kubernetes/ecs-configmap.example.yaml
# Create the Secret from your secret manager (NOT from the example file):
kubectl create secret generic ecs-secret --from-env-file=.env.prod
kubectl apply -f deploy/kubernetes/ecs-deployment.example.yaml
kubectl apply -f deploy/kubernetes/ecs-service.example.yaml
```

The app starts with `uvicorn app.main:app --host 0.0.0.0 --port 8000`.

---

## 4. Validate the deployment

```bash
# Production smoke (imports, routes, adapters, config masking, persistence, env):
python scripts/run_production_smoke.py --strict

# With a running endpoint:
python scripts/run_production_smoke.py --base-url https://<ecs-host> --strict
```

Then run the route + connector validations (see
[UAT_VALIDATION_RUNBOOK.md](UAT_VALIDATION_RUNBOOK.md)).

---

## 5. Post-deploy

- Confirm health probes are green: `GET /api/audit/health` returns 200.
- Confirm secrets are masked (see the UAT validation runbook §"confirm masking").
- Record the deploy (version, image tag, time, approver) in your change system.
- Keep `.env.prod` only in the secret store / host; never commit it.

---

## Rollback

If validation fails, follow [ROLLBACK_RUNBOOK.md](ROLLBACK_RUNBOOK.md) immediately.
