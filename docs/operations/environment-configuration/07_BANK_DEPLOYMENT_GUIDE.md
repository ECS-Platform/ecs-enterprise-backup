# ECS Bank Deployment Guide (Config-Only)

Deploying ECS into a bank landscape (UAT/PROD/DR) is a **configuration** exercise.
The application artifact is identical across environments; only config changes.

## What the bank team provides (config values only)
| Category | Values needed |
|---|---|
| ECS app | public FQDN, port, TLS cert (`ECS_PUBLIC_URL`, `ECS_PORT`, `ECS_FORCE_HTTPS`) |
| Evidence DB | PostgreSQL host/port/db/user + password (`ECS_REPO_PG_*`) |
| Redis | host/port/ssl + password (`REDIS_*`) |
| Object store | endpoint/bucket + access/secret keys (`MINIO_*`) |
| Vector store | pgvector host/port/db (`ECS_VECTOR_PG_*`) |
| LLM | inference base URL + model (`OLLAMA_URL`, `ECS_LLM_MODEL`) |
| SSO/IdP | metadata URL + client id/secret (`ECS_SSO_*`) |
| Connectors | per-system base URL + service-account creds (see Connector Guide) |
| Assessment targets | OS/DB/middleware/appsec host lists (`ECS_TARGET_*`) |

## Deployment checklist
1. Pick the environment: `ECS_ENV=uat|prod|dr`.
2. Create the env file: `cp .env.<env>.example .env.<env>` (or configure the vault).
3. Fill in the bank values above (no source edits).
4. Provision secrets in the vault / K8s secret store.
5. **Validate:** `python scripts/config_tools.py validate-<env> --check-secrets` → PASS.
6. **Review:** `python scripts/config_tools.py show-current-config <env>` (secret-safe).
7. **Diff:** `python scripts/config_tools.py compare-envs <lower> <env>` — confirm only
   endpoints/secrets differ.
8. Confirm network reachability (DB, Redis, object store, LLM, connectors) from the
   ECS host (firewall/VPN/security groups).
9. Deploy the (unchanged) ECS artifact; start with `ECS_ENV=<env>`.
10. Post-deploy: hit `/healthz`, `/readyz`, and `GET /api/audit/integrations/health`.

## Guarantees for the bank
- **Zero code changes** to move between environments.
- **No secrets in git** — all via vault / git-ignored env files, masked in output.
- **Localhost is impossible** in UAT/PROD/DR (validator blocks it).
- **Auditable config** — `show-current-config` / `compare-envs` document exactly what
  a given environment resolves to (secret-safe).

## Rollback
Keep the previous environment file / vault version. To roll back, restore it and
restart — see the Rollback Guide.
