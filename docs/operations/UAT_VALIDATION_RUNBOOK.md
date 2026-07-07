# ECS UAT Validation Runbook

How to validate an ECS deployment in UAT: routes, connectors, predefined query
execution, audit intelligence, log collection, secret masking, and UAT sign-off.
Everything here is safe to run; no step requires committing secrets or real IPs.

> Prereq: ECS is running (see [DEPLOYMENT_RUNBOOK.md](DEPLOYMENT_RUNBOOK.md)) and
> `.env.uat` is populated from the secret manager (git-ignored).

---

## 1. Start / confirm ECS is up

```bash
# If running locally for validation:
export ECS_ENV=uat; set -a; source .env.uat; set +a
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Confirm the process is healthy:
```bash
curl -fsS "http://127.0.0.1:8000/api/audit/health?role=owner&user=probe"
```

---

## 2. Validate routes

```bash
# Offline platform + route smoke (imports, route registration, adapter registry):
python scripts/run_production_smoke.py --strict
python scripts/run_production_smoke.py --base-url http://127.0.0.1:8000 --strict
```

Spot-check the key API + UI routes return 200 (not 404):
```bash
for p in /api/audit/dashboard /api/audit/assets /api/audit/mapping /api/audit/runs \
         /api/audit/repository /api/audit/observations /api/audit/packs \
         /api/audit/integrations /api/audit/health; do
  curl -s -o /dev/null -w "%{http_code}  $p\n" "http://127.0.0.1:8000$p?role=owner&user=probe"
done
```

---

## 3. Validate connectors (config-only, then live)

```bash
# Config-only (no network): confirms presence + masking for every adapter.
python scripts/run_uat_connector_health.py --adapter all --no-network

# Live probe for configured adapters (only hits endpoints that are configured):
python scripts/run_uat_connector_health.py --adapter all --live --strict
```

Expected: unconfigured adapters report `not_configured` (valid until credentials
are provisioned); configured adapters report `ok` when reachable + authenticated.
Use the printed remediation hints for any failures (see
[CONNECTOR_TROUBLESHOOTING_RUNBOOK.md](CONNECTOR_TROUBLESHOOTING_RUNBOOK.md)).

---

## 4. Validate predefined query execution

```bash
# Environment diagnostic for the predefined-query connectors (no docker check):
python3 scripts/check_predefined_extended_environment.py --no-docker-check
```

Then run a real, read-only baselining check against a UAT target and confirm the
evidence is captured (rows returned, no secret leakage in the excerpt). Review the
run in the UI: `/mvp/audit/evidence-runs`.

---

## 5. Validate audit intelligence

```bash
# Offline end-to-end walkthrough (catalog -> mapping -> run -> validation ->
# observation -> pack -> dashboard -> integrations):
python scripts/run_ecs_demo_smoke.py
```

Then in the UI confirm each surface renders with data:
`/mvp/audit/dashboard`, `/mvp/audit/technology-mapping`, `/mvp/audit/evidence-runs`,
`/mvp/audit/validation-results`, `/mvp/audit/observations`,
`/mvp/audit/repository`, `/mvp/audit/evidence-packs`, `/mvp/audit/executive-readiness`.

---

## 6. Collect logs

```bash
# systemd:
journalctl -u ecs --since "1 hour ago" --no-pager

# Docker Compose:
docker compose -f deploy/docker-compose.prod.example.yml logs --since 1h ecs-app

# Kubernetes:
kubectl logs deploy/ecs-app --since=1h
```

Save logs to the change ticket. **Verify logs contain no secret values** (only
`SET`/`MISSING` markers should appear for credentials).

---

## 7. Confirm secrets are masked

```bash
# Masked config for every adapter (secrets shown as SET/MISSING only):
curl -s "http://127.0.0.1:8000/api/audit/integrations?role=owner&user=probe"

# Health view must never echo a secret value:
python scripts/run_uat_connector_health.py --adapter all --json | \
  grep -iE "password|secret|token" || echo "no raw secrets in output (expected SET/MISSING only)"
```

Any occurrence of a real credential value is a **stop-ship** — investigate before
proceeding.

---

## 8. UAT sign-off

Complete the *Bank Developer UAT Checklist* in
`docs/DEVELOPER/UAT_INTEGRATION_GUIDE.md` per target technology, then record:

- [ ] Routes validated (all 200, no 404).
- [ ] Connectors: configured adapters healthy; masking confirmed.
- [ ] Predefined query executed against a UAT target; evidence reviewed.
- [ ] Audit intelligence surfaces render with data.
- [ ] Logs collected; no secrets present.
- [ ] Sign-off recorded (who / when / scope) and gaps logged in
      `docs/DEVELOPER/PRODUCTION_READINESS_GAP_REGISTER.md`.
