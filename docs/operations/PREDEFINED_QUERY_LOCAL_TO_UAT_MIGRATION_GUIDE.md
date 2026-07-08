# ECS Predefined Query — Local → UAT / PROD / DR Migration Guide

Move the predefined-query module from `localhost` (Docker demo) to Bank UAT, then
PROD, then DR by **editing configuration only**. No source-code change is needed.

> Companion: the platform-wide config migration is covered in
> [environment-configuration/09_IP_MIGRATION_GUIDE.md](environment-configuration/09_IP_MIGRATION_GUIDE.md).
> This guide is the predefined-query-specific slice.

---

## 1. Where target endpoints come from (3 layers, all config)

| Layer | File | What it sets |
|---|---|---|
| Per-technology connection | `config/environments/<env>.yaml` → `predefined_query_targets:` | host/port/db/user/`*_env`/container per technology |
| Server lists | same file (`os_servers`/`db_servers`/…) or env vars `ECS_TARGET_*` | comma-separated host/IP lists |
| Named target registry | `config/predefined_query_targets.<env>.yaml` | operator-facing named targets (`target_id`, `credential_ref`, `enabled`) |

All three are env-var substituted (`${VAR:-default}`) — nothing is hard-coded in code.

---

## 2. LOCAL (starting point)

```bash
export ECS_ENV=local
docker compose -f docker-compose.predefined-queries.yml --profile minimal up -d
python scripts/run_predefined_query_tests.py validate-targets local   # PASS (localhost allowed)
```

---

## 3. LOCAL → UAT

1. Populate the UAT named-target registry (placeholders → real hosts):
   edit `config/predefined_query_targets.uat.yaml` — set `hostname`/`ip`,
   `credential_ref` (vault path), and `enabled: true` for each target.
2. Point the per-technology config at UAT (either env vars or `uat.yaml`):
   ```bash
   export ECS_ENV=uat
   export ECS_PG_HOST=<uat-postgres> ECS_ORACLE_HOST=<uat-oracle>
   export ECS_NGINX_CONTAINER=""      # remote NGINX uses SSH mode / host, not docker-exec
   export ECS_TARGET_OS_SERVERS=<uat-os-hosts-csv> ECS_TARGET_DB_SERVERS=<uat-db-hosts-csv>
   # secrets from the UAT vault / .env.uat: ECS_PG_PASSWORD, ECS_ORACLE_PASSWORD, ...
   ```
3. Validate BEFORE running (must PASS; localhost is rejected for UAT):
   ```bash
   python scripts/run_predefined_query_tests.py validate-targets uat
   python scripts/check_predefined_technology_environment.py --no-docker-check
   ```
4. Run. The queries are byte-for-byte identical to local — only the targets changed.

---

## 4. UAT → PROD

Repeat §3 with `ECS_ENV=prod` and `config/predefined_query_targets.prod.yaml`
(prod hosts + `vault://ecs/prod/...`). Validate:

```bash
export ECS_ENV=prod
python scripts/run_predefined_query_tests.py validate-targets prod
```

---

## 5. PROD → DR

Repeat with `ECS_ENV=dr` and `config/predefined_query_targets.dr.yaml` (DR-site
hosts + `vault://ecs/dr/...`). DR mirrors prod; only hostnames/IPs change.

```bash
export ECS_ENV=dr
python scripts/run_predefined_query_tests.py validate-targets dr
```

---

## 6. Migration checklist (per environment)

- [ ] `ECS_ENV` set to the target environment.
- [ ] `config/predefined_query_targets.<env>.yaml`: real hosts/ips, `credential_ref`, `enabled: true`.
- [ ] Per-technology endpoints set (env vars or `<env>.yaml`); secrets via vault / `.env.<env>`.
- [ ] `ECS_TARGET_*` server lists populated where used.
- [ ] `validate-targets <env>` → PASS (no localhost, no missing fields, no dup ids).
- [ ] Network path open from the ECS host to each target (firewall/VPN/security groups).
- [ ] Read-only service accounts used.

**No step edits source code.**

---

## 7. Guarantees

- **No hardcoded localhost** in UAT/PROD/DR — the registry validator and the
  config validator both reject it (`tests/test_predefined_query_targets_and_catalog.py`,
  `tests/test_deployment_config.py`).
- **No secrets in git** — only `credential_ref` pointers and `*_env` names.
- **Same catalog everywhere** — the 187 controls run identically; only targets differ.
