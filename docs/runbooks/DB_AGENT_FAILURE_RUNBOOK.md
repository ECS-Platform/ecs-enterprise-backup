# Runbook: DB Agent Failure

The ECS DB Agent (jump server) won't start, reports degraded readiness, or cannot
reach database/host targets.

> Reference: [`../developer-manual/DATABASE_AGENT_GUIDE.md`](../developer-manual/DATABASE_AGENT_GUIDE.md)
> · [`db_agent/README.md`](../../db_agent/README.md). The DB Agent is a prototype
> and depends on no enterprise security to run.

## Symptoms
- Agent process not serving; `GET /readyz` returns 503; `GET /connectivity`
  reports `not_configured` or `error`; ECS not receiving results.

## Diagnose
1. Liveness: `GET /healthz` (should always be 200 if the process is up).
2. Config (masked): `GET /config` — confirm `db.configured` / `ssh.configured`.
3. Connectivity: `GET /connectivity/database`, `GET /connectivity/ssh`.
4. Security posture: `GET /security` (all `ENABLE_*` should be off in prototype).

## Common causes & remediation
| Cause | Fix |
|-------|-----|
| Target unset | Set `DB_HOST/DB_NAME/DB_USERNAME` (and `SSH_HOST/SSH_USERNAME`) in `.env.db-agent`. |
| DB unreachable | Verify jump-server → DB network path + firewall; check `DB_PORT`, `DB_SSLMODE`. |
| Auth failure | Use a valid **read-only** account; check `DB_PASSWORD` from the secret store. |
| SSH host unreachable | TCP probe fails → open the port / fix `SSH_HOST/SSH_PORT`. |
| Wrong bind | Set `DB_AGENT_HOST`/`DB_AGENT_PORT`; the agent starts even with blank targets. |
| Enabled a security flag without wiring | Prototype stubs are safe no-ops; leave `ENABLE_*` off until implemented. |

`/readyz` 503 with **no targets configured** is expected (signal, not failure) —
the agent keeps serving.

## Verify
- `GET /connectivity` shows configured targets `ok: true`.
- ECS receives uploaded evidence (see evidence-upload runbook).

## Escalate
Network path issues → bank network team; keep ECS routes to internal DBs closed
(collection is via the jump server only).
