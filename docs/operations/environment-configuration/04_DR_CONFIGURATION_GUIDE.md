# ECS Disaster Recovery (DR) Configuration Guide

Configure ECS for the **DR** (secondary) site. DR mirrors production topology; only
the host/IP values differ. Configuration only — failover needs no build/code change.

## Files
- `config/environments/dr.yaml` — DR defaults (`*.dr.bank.internal`, TLS/SSO on).
- `.env.dr.example` — DR deployment knobs (copy to `.env.dr` / DR vault).

## Steps
```bash
cp .env.dr.example .env.dr            # DR-site hosts + DR vault secrets
export ECS_ENV=dr
set -a; source .env.dr; set +a
python scripts/config_tools.py validate-dr --check-secrets     # must PASS
```

## DR = prod shape, DR hosts
```bash
ECS_ENV=dr
ECS_PUBLIC_URL=https://ecs.dr.bank.internal
ECS_REPO_PG_HOST=pg.dr.bank.internal        # replica / standby
REDIS_HOST=redis.dr.bank.internal           ; REDIS_SSL=true
MINIO_ENDPOINT=objectstore.dr.bank.internal:9000 ; MINIO_SECURE=true
ECS_VECTOR_PG_HOST=pgvector.dr.bank.internal
OLLAMA_URL=http://llm.dr.bank.internal:11434
ECS_TARGET_OS_SERVERS=<dr-os-hosts-csv>     ; ECS_TARGET_DB_SERVERS=<dr-db-hosts-csv>
```

## Failover procedure (config-only)
1. Ensure DR data stores are current (DB replica promoted, object store replicated,
   vector store rebuilt/replicated) — data concerns are outside ECS config.
2. `export ECS_ENV=dr`; load `.env.dr`.
3. `python scripts/config_tools.py validate-dr --check-secrets` → PASS.
4. `python scripts/config_tools.py compare-envs prod dr` → confirm only endpoints
   differ (nothing structural/behavioural).
5. Start ECS on the DR site. No rebuild, no code branch.

## Fail-back
Repeat with `ECS_ENV=prod` once the primary is restored. Keep both `.env.prod` and
`.env.dr` under change control (in the vault, not git).

## Notes
- DR is a strict environment: the validator rejects localhost and (with
  `--check-secrets`) requires DR secrets to be present.
- DR can be promoted to serve production, so it keeps prod hardening (SSO, TLS).
