# Runbook: Degraded Readiness (`/readyz` 503)

The app is alive (`/healthz` 200) but readiness (`/readyz`) returns 503, so the
load balancer stops routing traffic.

> Reference: `app/routes_platform.py` (`/healthz`, `/readyz`)
> · [`../operations/ECS_PRODUCTION_MONITORING_GUIDE.md`](../operations/ECS_PRODUCTION_MONITORING_GUIDE.md)
> · [`../00-start-here/TROUBLESHOOTING_GUIDE.md`](../00-start-here/TROUBLESHOOTING_GUIDE.md).

## What `/readyz` checks
Readiness returns 200 only when the **PostgreSQL evidence repository** is
reachable (a single `SELECT 1`); otherwise 503 with `repository_ok: false`. It is
intentionally lightweight and **never** restarts the pod (that's liveness).

## Symptoms
- `GET /healthz` → 200 but `GET /readyz` → 503; LB shows the pod out of rotation.

## Diagnose
1. `GET /readyz` — read `detail` (truncated DB error).
2. Verify PostgreSQL reachability from the pod (`ECS_REPO_PG_*` host/port/creds,
   private IP, Cloud SQL Auth Proxy).
3. Check network policy / firewall between GKE and Cloud SQL.
4. Confirm DB is up and not at max connections.

## Common causes & remediation
| Cause | Fix |
|-------|-----|
| DB unreachable (network) | Fix VPC peering / private service access / firewall; verify Cloud SQL proxy. |
| Wrong DB config | Correct `ECS_REPO_PG_*` from Secret Manager. |
| DB down / failover | Recover/await failover; see recovery + DR runbooks. |
| Connection exhaustion | Raise Cloud SQL max connections / add pooling; scale replicas within limits. |
| Demo/prototype (no DB) | Expected: readiness is degraded but the app serves in-memory. Not an incident in demo mode. |

## Verify
- `GET /readyz` → 200 `ready`, `repository_ok: true`; LB returns the pod to rotation.

## Escalate
Persistent DB outage → [`../operations/RECOVERY_RUNBOOK.md`](../operations/RECOVERY_RUNBOOK.md)
/ [`../operations/ECS_DISASTER_RECOVERY_PLAN.md`](../operations/ECS_DISASTER_RECOVERY_PLAN.md).
