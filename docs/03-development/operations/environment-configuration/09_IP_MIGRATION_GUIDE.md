# ECS IP / Endpoint Migration Guide

**How to move ECS from `localhost` → Bank UAT → Production → DR by editing
CONFIGURATION ONLY. No source-code changes are required at any step.**

Every host/IP/URL/port ECS uses is resolved from `config/environments/<env>.yaml`
(deep-merged over `_base.yaml`) with `${VAR:-default}` substitution. To move
environments you (a) select the environment with `ECS_ENV` and (b) supply the
target host/IP/secret values via environment variables (or a vault). That's it.

---

## 1. The one rule

```
ECS_ENV = local | uat | prod | dr        # selects the YAML profile
${VAR}  = real endpoint / IP / secret     # supplies the values for that profile
```

No Python/source edit is ever needed to repoint ECS at a new IP.

---

## 2. LOCAL (developer laptop) — the starting point

```bash
export ECS_ENV=local          # or leave unset (local is the default)
./start_ecs.sh                # binds 0.0.0.0:8000, points at docker-compose services
```

Local uses `localhost`/compose service names by design. Validate:

```bash
python scripts/config_tools.py validate-config local     # PASS
python scripts/config_tools.py show-current-config local
```

---

## 3. LOCAL → Bank UAT

You change **only** environment values — no code.

1. Create the UAT env file from the template (git-ignored):
   ```bash
   cp .env.uat.example .env.uat      # deployment knobs
   #   plus connector creds from .env.uat.template / your secret store
   ```
2. Set the **real UAT** hosts/IPs/secrets in `.env.uat`, e.g.:
   ```bash
   ECS_ENV=uat
   ECS_PUBLIC_URL=https://ecs.uat.bank.local
   ECS_REPO_PG_HOST=pg.uat.bank.local        # UAT DB IP/FQDN
   REDIS_HOST=redis.uat.bank.local
   MINIO_ENDPOINT=objectstore.uat.bank.local:9000
   OLLAMA_URL=http://llm.uat.bank.local:11434
   ECS_TARGET_OS_SERVERS=10.a.b.1,10.a.b.2   # UAT assessment targets (CSV)
   ECS_TARGET_DB_SERVERS=10.a.c.1
   # ... connector base URLs + *_env secrets
   ```
3. Load + validate (with secrets) BEFORE starting:
   ```bash
   export ECS_ENV=uat
   set -a; source .env.uat; set +a
   python scripts/config_tools.py validate-uat --check-secrets   # must PASS
   ```
4. Start ECS. It now talks to UAT — the code is byte-for-byte identical to local.

> The validator refuses to let UAT point at `localhost`/loopback, so a copy-paste
> mistake is caught before deploy.

---

## 4. UAT → Production

Same mechanism, prod values:

```bash
cp .env.prod.example .env.prod            # or inject via vault / K8s secrets
# set ECS_ENV=prod, ECS_PUBLIC_URL=https://ecs.bank.internal,
#     ECS_REPO_PG_HOST=pg.prod.bank.internal, REDIS_HOST=redis.prod.bank.internal,
#     MINIO_ENDPOINT=objectstore.prod.bank.internal:9000,
#     OLLAMA_URL=http://llm.prod.bank.internal:11434, secrets from vault, ...

export ECS_ENV=prod
python scripts/config_tools.py validate-prod --check-secrets    # must PASS
python scripts/config_tools.py compare-envs uat prod            # review the deltas
```

Production hardening defaults (`prod.yaml`): SSO on, TLS forced, object-store
secure, JSON logs, scheduler + monitoring on — all overridable by env vars.

---

## 5. Production → DR (failover)

DR mirrors prod on the secondary site. Only the host/IP values change:

```bash
cp .env.dr.example .env.dr                # DR-site hosts + DR vault secrets
# ECS_ENV=dr, ECS_PUBLIC_URL=https://ecs.dr.bank.internal,
#   ECS_REPO_PG_HOST=pg.dr.bank.internal (replica/standby),
#   REDIS_HOST=redis.dr.bank.internal, MINIO_ENDPOINT=objectstore.dr.bank.internal:9000,
#   OLLAMA_URL=http://llm.dr.bank.internal:11434, ECS_TARGET_* = DR-site targets

export ECS_ENV=dr
python scripts/config_tools.py validate-dr --check-secrets      # must PASS
python scripts/config_tools.py compare-envs prod dr             # confirm only hosts differ
```

Start ECS on the DR site. Because DR is config-only, failover requires **no build,
no code branch** — just the DR environment values.

---

## 6. Migration checklist (per environment)

- [ ] `ECS_ENV` set to the target environment.
- [ ] All host/IP/endpoint env vars point at the target landscape (no localhost).
- [ ] Secrets supplied via `.env.<env>` (git-ignored) or a vault.
- [ ] `ECS_TARGET_OS_SERVERS` / `_DB_SERVERS` / `_MW_SERVERS` / `_APPSEC` populated.
- [ ] `python scripts/config_tools.py validate-<env> --check-secrets` → PASS.
- [ ] `compare-envs` reviewed — only endpoints/secrets differ, nothing structural.
- [ ] Object storage + DB reachable from the ECS host (firewall/VPN).
- [ ] Rollback plan ready (see the Rollback Guide) — keep the previous `.env.<env>`.

**No step above edits source code.**

---

## 7. Why no code change is needed

- Endpoints are read through `config.environment_loader` accessors
  (`get_database`, `get_connector`, `get_llm`, `get_application_config`, …), which
  resolve from the active env YAML + env vars.
- Connector engines already default to `localhost` **only as a fallback** and read
  `ECS_*_HOST` first, so setting the env var repoints them.
- Adding a new site/region = a new `config/environments/<env>.yaml` + registering
  the env name; no module changes.
