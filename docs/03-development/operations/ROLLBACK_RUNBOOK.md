# ECS Rollback Runbook

Fast, safe rollback of an ECS deployment when validation fails or a regression is
found post-deploy. Choose the section matching your deployment method.

> Principle: **restore the last known-good version quickly**, then diagnose. ECS
> evidence data lives in Postgres (durable persistence) — rolling back the app
> does not delete evidence.

---

## 0. Decide: rollback vs fix-forward

- Rollback if: health probes fail, routes 404, smoke fails, or a functional
  regression is confirmed and no quick fix is available.
- Fix-forward only for trivial, well-understood config issues (e.g. a missing env
  var) that can be corrected in minutes.

Record the decision (who/when/why) in the change ticket before acting.

---

## 1. Kubernetes

```bash
# See rollout history and roll back to the previous revision:
kubectl rollout history deploy/ecs-app
kubectl rollout undo deploy/ecs-app                 # previous revision
# or a specific one:
kubectl rollout undo deploy/ecs-app --to-revision=<N>
kubectl rollout status deploy/ecs-app               # wait for healthy
```

Config/secret rollback (if changed): re-apply the previous ConfigMap/Secret
version from your GitOps/secret manager, then restart:
```bash
kubectl rollout restart deploy/ecs-app
```

---

## 2. Docker Compose (single host)

```bash
# Repoint to the previous image tag (never :latest in prod) and recreate:
#   edit deploy/docker-compose.prod.example.yml -> image: ecs-app:<previous-tag>
docker compose -f deploy/docker-compose.prod.example.yml --env-file .env.prod up -d
docker compose -f deploy/docker-compose.prod.example.yml ps
```

---

## 3. systemd (VM)

```bash
# If the code lives in a versioned dir / venv, point the unit at the previous
# release and restart:
sudo systemctl stop ecs
#   restore previous /opt/ecs release (symlink swap or checkout previous tag)
sudo systemctl start ecs
sudo systemctl status ecs --no-pager
journalctl -u ecs --since "10 min ago" --no-pager
```

---

## 4. Database schema

The audit schema (`docs/DB_SCHEMA_AUDIT_INTELLIGENCE.sql`) is **additive and
idempotent** (`IF NOT EXISTS`), so a normal app rollback needs **no DB rollback**.
If a migration introduced an incompatible change, restore from the pre-deploy
Postgres backup per `docs/03-development/operations/ECS_BACKUP_AND_RECOVERY_GUIDE.md`. Do not
drop audit tables to "fix" an app issue — that destroys evidence.

---

## 5. Post-rollback validation

```bash
python scripts/run_production_smoke.py --base-url https://<ecs-host> --strict
python scripts/run_uat_connector_health.py --adapter all --no-network
```

Confirm:
- [ ] `GET /api/audit/health` returns 200.
- [ ] Key routes return 200 (no 404).
- [ ] No secrets in logs.
- [ ] Change ticket updated with rollback outcome + root-cause follow-up.

---

## 6. After the incident

- Capture logs (`journalctl` / `docker logs` / `kubectl logs`) for RCA.
- File the root cause and the corrective action; link the failed deploy.
- Re-attempt the deployment only after the fix passes
  [UAT_VALIDATION_RUNBOOK.md](UAT_VALIDATION_RUNBOOK.md).
