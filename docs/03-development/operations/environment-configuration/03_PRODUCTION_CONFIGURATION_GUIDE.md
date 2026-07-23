# ECS Production Configuration Guide

Configure ECS for **PRODUCTION** — configuration only, hardened by default.

## Files
- `config/environments/prod.yaml` — production defaults (SSO on, TLS forced,
  object-store secure, JSON logs, scheduler + monitoring on).
- `.env.prod.example` — deployment knobs (copy to `.env.prod` or inject via vault).
- `.env.prod.template` — connector credential template.

## Steps
```bash
cp .env.prod.example .env.prod        # prefer vault / K8s secrets for real creds
export ECS_ENV=prod
set -a; source .env.prod; set +a      # or inject secrets from the vault
python scripts/config_tools.py validate-prod --check-secrets   # must PASS
```

## Production hardening (defaults; overridable via env)
| Setting | Default | Var |
|---|---|---|
| Auth enabled | true | `ECS_AUTH_ENABLED` |
| Force HTTPS / HSTS | true | `ECS_FORCE_HTTPS`, `ECS_HSTS_ENABLED` |
| SSO | true (saml) | `ECS_SSO_ENABLED`, `ECS_SSO_PROVIDER` |
| Object store secure | true | `MINIO_SECURE` |
| Logging | INFO / json | `ECS_LOG_LEVEL`, `ECS_LOG_FORMAT` |
| Scheduler / monitoring | on | `ECS_SCHEDULER_ENABLED`, `ECS_MONITORING_ENABLED` |
| Local auth bypass | false | `ECS_LOCAL_AUTH_BYPASS` (must stay false) |

## Minimum production variables
```bash
ECS_ENV=prod
ECS_PUBLIC_URL=https://ecs.bank.internal
ECS_REPO_PG_HOST=pg.prod.bank.internal   ; ECS_REPO_PG_PASSWORD=<vault>
REDIS_HOST=redis.prod.bank.internal      ; REDIS_SSL=true
MINIO_ENDPOINT=objectstore.prod.bank.internal:9000 ; MINIO_SECURE=true
OLLAMA_URL=http://llm.prod.bank.internal:11434
ECS_VECTOR_PG_HOST=pgvector.prod.bank.internal
ECS_TARGET_OS_SERVERS=<prod-os-hosts-csv> ; ECS_TARGET_DB_SERVERS=<prod-db-hosts-csv>
```

## Pre-go-live gate
```bash
python scripts/config_tools.py validate-prod --check-secrets   # 0 errors
python scripts/config_tools.py show-current-config prod        # review (secrets masked)
python scripts/config_tools.py compare-envs uat prod           # only endpoints differ
```

## Never
- Never set `localhost`/`host.docker.internal` endpoints (validator blocks it).
- Never commit `.env.prod`; never store secrets in YAML.
- Never enable `ECS_LOCAL_AUTH_BYPASS` in production.
