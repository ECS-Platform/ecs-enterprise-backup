# ECS UAT IP Configuration Guide

**Purpose:** Show the UAT team exactly how to point ECS at **real UAT servers**
(no `localhost`) — for application, database, web-server, middleware, and
enterprise-connector assets — using the **existing** configuration surfaces. ECS
already ships a UAT asset inventory and connector config; this guide documents the
exact files and keys to edit. **No new/duplicate config is introduced.**

> Golden rules: never commit real hosts/IPs/tenant IDs/secrets; hostnames come
> from `${VAR}` env references (or a git-ignored local file); connector
> credentials come from `ECS_*` env vars / a secret manager, never from YAML.

---

## 1. Files to edit (existing — do NOT duplicate)

| File | Role | Committed? |
|------|------|------------|
| `config/uat_assets.template.yaml` | **Canonical UAT asset inventory template** (placeholders only). Copy it and fill real values in a git-ignored file. | Yes (template) |
| `config/uat_assets.uat.yaml` *(you create by copying)* | Your real UAT asset inventory. | **No — git-ignored** |
| `config/environments/uat.yaml` → `connectors:` | Non-secret connector endpoints/tuning for UAT (Graph/SharePoint/Teams/ServiceNow/Jira/…). | Yes |
| `config/integrations.yaml` → `integrations:` | General integration config (SharePoint/Teams/ServiceNow/Prisma/…) with `*_env` secret refs. | Yes |
| `.env.uat` *(you create)* | Real UAT hostnames + secrets, referenced by `${VAR}` / `*_env`. | **No — git-ignored** |
| `.env.example` | Documents every `ECS_*` variable name. | Yes |

`.gitignore` already blocks `.env*` (except `.env.example`) and local UAT asset
files. Confirm with `git status` before every commit.

---

## 2. The UAT asset inventory (schema the scheduler reads)

ECS's asset-driven scheduler consumes the inventory via
`asset_discovery.discover_from_manual`. The **recognized keys per asset** are:

```
asset_id, hostname (or name), technology, environment, application (or app),
owner, ports, operating_system (or os), criticality, image, asset_type
```

- **Baseline assets** (databases/OS/middleware) set `technology` → routed to the
  predefined-query collector for that technology.
- **Connector assets** (SharePoint/Teams/ServiceNow/Jira/…) set `asset_type` →
  routed to the matching enterprise adapter. `technology` is optional for these.
- **Frameworks are derived** from the technology (via the control mapping) — you
  do **not** list them per asset.

### 2.1 Sample UAT asset config (copy + fill)

```bash
cp config/uat_assets.template.yaml config/uat_assets.uat.yaml
# edit config/uat_assets.uat.yaml — kept out of Git
```

```yaml
# config/uat_assets.uat.yaml  (git-ignored; real UAT values)
environment: "${ECS_ENV:-uat}"

assets:
  # ---- Web server (baseline; routes to NGINX predefined queries) ----
  - asset_id: netbanking-web-uat-01
    hostname: "${ECS_UAT_NGINX_HOST:-nginx.netbanking.uat.bank.internal}"
    technology: NGINX
    environment: UAT
    application: "Net Banking"
    owner: "app_owner_name"
    ports: ["443"]
    criticality: High

  # ---- Database (baseline; routes to Oracle predefined queries) ----
  - asset_id: netbanking-db-uat-01
    hostname: "${ECS_UAT_ORACLE_HOST:-oracle.netbanking.uat.bank.internal}"
    technology: Oracle
    environment: UAT
    application: "Net Banking"
    owner: "db_owner_name"
    ports: ["1521"]
    criticality: High

  # ---- Enterprise connector asset (routes to the SharePoint adapter) ----
  - asset_id: netbanking-sharepoint-evidence
    hostname: "${ECS_UAT_SHAREPOINT_SITE:-<sharepoint-site-id>}"
    asset_type: sharepoint
    environment: UAT
    application: "Evidence Library"
    owner: "grc_owner_name"
    criticality: Medium
```

> **Conceptual mapping** to the requested `uat_environment` / `host` / `port` /
> `protocol` / `framework_scope` shape: ECS expresses the same intent with
> `environment: uat` (top-level), `hostname` (= host), `ports` (= port list), and
> **derives** `framework_scope` from `technology`. Keep using `hostname`/`ports`/
> `technology` because that is what the loader reads — do not add a second,
> parallel asset file.

### 2.2 Set the real hosts via env (recommended — nothing in Git)

```bash
# .env.uat  (git-ignored)
export ECS_ENV=uat
export ECS_UAT_NGINX_HOST=nginx.netbanking.uat.bank.internal
export ECS_UAT_ORACLE_HOST=oracle.netbanking.uat.bank.internal
export ECS_UAT_SHAREPOINT_SITE=<real-sharepoint-site-id>
# ... one ECS_UAT_*_HOST per asset in the inventory
```

---

## 3. Configuration surfaces by asset class

| Asset class | Where the endpoint is set | Env var(s) |
|-------------|---------------------------|-----------|
| Application / web server (NGINX/Apache/Tomcat) | asset inventory `hostname` | `ECS_UAT_NGINX_HOST`, `ECS_UAT_APACHE_HOST`, `ECS_UAT_TOMCAT_HOST` |
| Databases (Oracle/PostgreSQL/SQL Server/Mongo/Redis/Aerospike/Yugabyte) | asset inventory `hostname`; connector target in `config/environments/uat.yaml`/`.env.uat` | `ECS_UAT_*_HOST`, `ECS_ORACLE_HOST`, `ECS_PG_HOST`, `AEROSPIKE_HOST`, … |
| OS / middleware (Linux/RHEL) | asset inventory `hostname` | `ECS_UAT_LINUX_HOST` |
| SharePoint (Graph) | `config/environments/uat.yaml` `connectors.sharepoint_graph`; `config/integrations.yaml` `sharepoint` | `ECS_GRAPH_SITE_ID`, `ECS_SHAREPOINT_SITE_HOSTNAME`, `ECS_SHAREPOINT_SITE_PATH` |
| Teams (Graph) | `config/environments/uat.yaml` `connectors.teams_graph`; `integrations.yaml` `teams` | `ECS_TEAMS_TEAM_ID`, `ECS_TEAMS_CHANNEL_ID` |
| Microsoft Graph (shared) | `config/environments/uat.yaml` `connectors.ms_graph` | `ECS_GRAPH_TENANT_ID`, `ECS_GRAPH_CLIENT_ID`, `ECS_GRAPH_CLIENT_SECRET`, `ECS_GRAPH_AUTHORITY_URL` |
| ServiceNow | `config/environments/uat.yaml` `connectors.servicenow_cmdb`; `integrations.yaml` `servicenow` | `ECS_SERVICENOW_BASE_URL`, `ECS_SERVICENOW_CLIENT_ID/SECRET` or `_USERNAME/_PASSWORD` |
| Jira / Confluence | `config/environments/uat.yaml` `connectors.jira_adapter`/`confluence_adapter` | `ECS_JIRA_BASE_URL`+`ECS_JIRA_API_TOKEN`; `ECS_CONFLUENCE_BASE_URL`+`ECS_CONFLUENCE_API_TOKEN` |
| SonarQube / Prisma / Checkmarx / Tripwire / Archer | `config/environments/uat.yaml` `connectors.*` | `ECS_SONARQUBE_BASE_URL`+`ECS_SONARQUBE_TOKEN`; `ECS_PRISMA_CLOUD_*`; `ECS_CHECKMARX_*`; `ECS_TRIPWIRE_*`; `ECS_ARCHER_*` |

Full Microsoft Graph / SharePoint / Teams setup:
[microsoft_graph_sharepoint_teams_uat_testing.md](../graph-api/microsoft_graph_sharepoint_teams_uat_testing.md).

---

## 4. How `localhost` is replaced

1. **Local/demo default** uses `localhost` container hostnames (from `_base.yaml`).
2. For UAT, set `ECS_ENV=uat` and provide real hostnames via env / your
   git-ignored `config/uat_assets.uat.yaml`. The `${VAR:-placeholder}` pattern
   means the env value wins; nothing localhost-specific remains.
3. The validator **enforces** this: in `--mode uat` any resolved hostname of
   `localhost` / `127.0.0.1` / `0.0.0.0` / `::1` is a hard **error**.

```bash
export ECS_ENV=uat; set -a; source .env.uat; set +a
python scripts/validate_uat_config.py --assets config/uat_assets.uat.yaml --mode uat
```

---

## 5. How the scheduler picks UAT assets

`scripts/run_uat_asset_scheduler.py` loads the asset inventory, classifies each
asset's technology (fingerprinting), and routes it:

- **baseline_collector** → the predefined-query engine (technology controls), or
- **enterprise_connector** → the matching adapter (by `asset_type`), or
- **unsupported** → flagged for manual review.

```bash
# Dry-run (no network, no queries, no connector calls — safe in CI/UAT):
python scripts/run_uat_asset_scheduler.py --config config/uat_assets.uat.yaml --dry-run
python scripts/run_uat_asset_scheduler.py --config config/uat_assets.uat.yaml --json
python scripts/run_uat_asset_scheduler.py --config config/uat_assets.uat.yaml --strict
```

The dry-run report shows, per asset: classified technology, route,
connector/collector, applicable control IDs, and config-only connector readiness
(`SET`/`MISSING` — never secret values).

---

## 6. How connector routing works

- `asset_scheduler._CONNECTOR_ROUTES` maps `asset_type`/technology →
  `modules.operations.integrations.*` adapter (e.g. `sharepoint` →
  `sharepoint_graph`, `teams` → `teams_graph`, `servicenow` → `servicenow_cmdb`,
  `jira` → `jira`, `confluence` → `confluence`, `prisma` → `prisma_cloud`).
- Baseline technologies (Oracle, NGINX, …) route to the predefined-query
  collector; their live target is resolved from the DB/OS connector config in
  `config/environments/uat.yaml` + `.env.uat`.
- Adapters read credentials from `ECS_*` env vars at call time; masked config is
  visible via `GET /api/audit/integrations` and
  `GET /api/audit/integrations/health` (SET/MISSING only).

---

## 7. Validation commands

```bash
# 1) Validate the UAT config (YAML loads, no localhost in UAT, required fields,
#    connectors reference secrets via env — never inline):
python scripts/validate_uat_config.py \
  --assets config/uat_assets.uat.yaml \
  --connectors config/integrations.yaml \
  --mode uat            # add --strict to fail on placeholder warnings

# 2) Dry-run the scheduler over the inventory:
python scripts/run_uat_asset_scheduler.py --config config/uat_assets.uat.yaml --dry-run

# 3) Config-only connector health (no live calls):
python scripts/run_uat_connector_health.py --adapter all --no-network
#    …or a live probe once creds are set:
python scripts/run_uat_connector_health.py --adapter graph --live

# 4) Compose validity (demo profiles are opt-in):
docker compose config
```

---

## 8. Frontend / manual testing steps

1. `export ECS_ENV=uat; set -a; source .env.uat; set +a`
2. Start ECS: `PYTHONPATH=. uvicorn app.main:app --port 8000`
3. **Integrations page** — open `/mvp/integrations` (or `GET /api/audit/integrations/health`);
   confirm each configured connector shows `configured` with masked config, no secrets.
4. **Predefined queries** — open `/mvp/predefined-queries`, filter by a UAT
   technology (e.g. Oracle/NGINX), and **Run** a `Ready` control against the UAT
   target; confirm evidence is captured.
5. **Evidence health** — open `/mvp/evidence-health`; confirm the new evidence has
   a SHA-256 hash and integrity status.
6. **Scheduler** — open `/mvp/scheduler`; trigger a manual pull and confirm the run
   is recorded.

---

## 9. Rollback steps

- **Config rollback:** stop loading `.env.uat` (open a fresh shell), `unset
  ECS_ENV` (or set `ECS_ENV=local`), and delete/ignore `config/uat_assets.uat.yaml`.
  ECS reverts to the local/demo container hostnames — **no git change** is
  involved because UAT values only ever live in your shell / git-ignored files.
- **If a committed doc/config/script change must be reverted:** `git restore` the
  file (or revert the commit); nothing here changes runtime behaviour, so a
  rollback is a no-op for the running app.
- **Verify rollback:** `python scripts/validate_uat_config.py --assets
  config/uat_assets.template.yaml --mode local` → VALID; `docker compose config`
  → valid.

Cross references:
[microsoft_graph_sharepoint_teams_uat_testing.md](../graph-api/microsoft_graph_sharepoint_teams_uat_testing.md) ·
[connectors/UAT_INTEGRATION_GUIDE.md](../connectors/UAT_INTEGRATION_GUIDE.md) ·
[connectors/ENTERPRISE_CONNECTOR_UAT_SETUP.md](../connectors/ENTERPRISE_CONNECTOR_UAT_SETUP.md).
