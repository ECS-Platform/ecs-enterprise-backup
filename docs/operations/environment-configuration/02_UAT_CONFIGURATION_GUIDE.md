# ECS UAT Configuration Guide

Configure ECS for the bank **UAT** landscape — configuration only.

## Files
- `config/environments/uat.yaml` — non-secret UAT defaults (fake `*.uat.bank.local`).
- `.env.uat.example` — deployment knobs to copy to a git-ignored `.env.uat`.
- `.env.uat.template` — connector credential template.

## Steps
```bash
cp .env.uat.example .env.uat          # then fill REAL uat hosts + secrets
export ECS_ENV=uat
set -a; source .env.uat; set +a
python scripts/config_tools.py validate-uat --check-secrets   # must PASS
./start_ecs.sh
```

## Minimum UAT variables
```bash
ECS_ENV=uat
ECS_PUBLIC_URL=https://ecs.uat.bank.local
ECS_BASE_URL=https://ecs.uat.bank.local
ECS_REPO_PG_HOST=pg.uat.bank.local
ECS_REPO_PG_PASSWORD=<uat-vault>
REDIS_HOST=redis.uat.bank.local
MINIO_ENDPOINT=objectstore.uat.bank.local:9000
MINIO_ACCESS_KEY=<uat>   ;  MINIO_SECRET_KEY=<uat>
OLLAMA_URL=http://llm.uat.bank.local:11434
ECS_TARGET_OS_SERVERS=<uat-os-hosts-csv>
ECS_TARGET_DB_SERVERS=<uat-db-hosts-csv>
# + connector base URLs and *_env secrets (see Connector Configuration Guide)
```

## Rules
- UAT must NOT point at `localhost`/loopback (the validator enforces this).
- Use read-only service accounts for connectors and DB where possible.
- `.env.uat` is git-ignored — never commit real UAT hosts/secrets.
- Populate `ECS_TARGET_*` so live control validation has targets (otherwise the
  validator reports the target lists as required-but-empty).

## Validate & inspect
```bash
python scripts/config_tools.py show-current-config uat
python scripts/config_tools.py compare-envs local uat
```
