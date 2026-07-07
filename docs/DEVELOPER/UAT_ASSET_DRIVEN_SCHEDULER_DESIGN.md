# ECS UAT Asset-Driven Scheduler & Evidence Routing — Design

The asset-driven scheduler is the layer that turns a **UAT/local asset inventory**
into a **bounded, deterministic evidence-collection plan**, routing each asset to
either a baseline predefined-query collector or an existing enterprise connector.

It is **additive** and **reuses** existing ECS engines — it does not redesign
audit intelligence, and it does not duplicate or modify any connector code.

---

## 1. Why this layer exists

ECS already had:
- a **fingerprint engine** (technology from image/name/ports/class),
- an **asset discovery** engine (normalize assets from many sources),
- a **technology → control → framework** mapping,
- an **evidence orchestrator** (run controls; `resolve_scope`),
- **11 enterprise connectors** (ServiceNow, Archer, SharePoint/Teams/Outlook
  Graph, Jira, Confluence, SonarQube, Checkmarx, Prisma Cloud, Tripwire), and
- an **evidence service** (execute + validate runs).

What was missing was the **glue**: read an asset inventory → classify each asset →
decide *how* to collect its evidence (which connector or baseline collector) →
produce a plan the operator can inspect **before** anything runs. That glue is the
asset-driven scheduler.

---

## 2. Scope (in / out)

**In scope (this change):**
- Asset inventory loader (YAML → normalized `Asset` objects).
- Technology classifier + collector router (reusing the fingerprint engine).
- Evidence collection planner (bounded, deterministic).
- Dry-run runner (no side effects) + a CLI.
- Local/template config files (localhost/mock + placeholders only).
- Mocked tests.

**Out of scope (unchanged):**
- Connector implementations (`modules/operations/integrations/`).
- The predefined-query catalog/engine.
- Auth/RBAC, LLM, benchmark modules.
- Live execution wiring for connectors (owned by the connector layer). The
  scheduler can *plan* connector jobs and check *config-only* readiness, but never
  calls a connector.

---

## 3. Architecture

```
config/uat_assets.local.yaml            (localhost/mock; safe for CI + demo)
config/uat_assets.template.yaml         (placeholders only; copy for real UAT)
                │
                ▼
   asset_scheduler.load_assets()
                │  reuse: asset_discovery.discover_from_manual()
                ▼
        list[Asset]  ── fingerprint engine assigns technology + confidence
                │
                ▼
   asset_scheduler.classify_asset()      →  AssetClassification
                │   route precedence:
                │     1) enterprise_connector  (asset_type/tech → adapter)
                │     2) baseline_collector    (tech has predefined controls)
                │     3) unsupported           (fallback → manual review)
                ▼
   asset_scheduler.plan_evidence()        →  EvidencePlan (bounded, deterministic)
                │
                ▼
   asset_scheduler.dry_run()              →  JSON-safe report (NO side effects)
                │   + config-only connector readiness (SET/MISSING)
                ▼
   scripts/run_uat_asset_scheduler.py --config ... --dry-run
```

All new code lives in **one** service module,
`modules/audit_intelligence/services/asset_scheduler.py`, plus the CLI and config.

---

## 4. Routing model

Each asset is routed by **precedence**:

1. **Enterprise connector** — the asset's `asset_type` (preferred) or classified
   technology matches the connector routing table (`_CONNECTOR_ROUTES`), e.g.
   `sharepoint → sharepoint_graph`, `jira → jira`, `sonarqube → sonarqube`,
   `servicenow → servicenow_cmdb`, `teams → teams_graph`, `outlook → outlook_graph`,
   `checkmarx/prisma/tripwire/archer/confluence` likewise. Matching is
   case-insensitive with a token-contains fallback (`"SharePoint Online"` →
   `sharepoint_graph`). Scope = `connector:<adapter>`.
2. **Baseline collector** — the asset's technology has predefined-query controls
   (PostgreSQL, NGINX, Oracle, Redis, Tomcat, Linux/RHEL, MongoDB, SQL Server,
   YugabyteDB, Aurora MySQL, …). Scope = `technology:<name>`; control_ids come
   from `evidence_orchestrator.resolve_scope` / `mapping.controls_for_technology`.
3. **Unsupported** — neither applies. The asset is flagged for **manual review**
   (never a crash). This is the deliberate fallback path.

> Note: **SonarQube** is both a catalog technology *and* a connector; the connector
> route wins (a SonarQube asset is collected via the `sonarqube` adapter).

---

## 5. Data model (JSON-safe)

- **`AssetClassification`** — `asset_id`, `technology`, `confidence`, `route`,
  `connector`, `scope_kind`, `scope_value`, `control_ids`, `frameworks`,
  `reasons[]` (auditable "why").
- **`PlannedJob`** — one job: `asset_id`, `technology`, `route`, `connector`,
  `scope_kind`, `scope_value`, `control_ids`, `frameworks`.
- **`EvidencePlan`** — `jobs[]` + `unsupported[]` + a `summary` (counts by route /
  technology, total planned controls).

All expose `to_dict()` for stable CLI/JSON/test surfaces.

---

## 6. Safety guarantees

- **Offline by default.** `dry_run()` opens no socket, runs no query, calls no
  connector. Connector readiness uses only `is_configured()` / `masked_config()`
  (config-only), never `health_check()` (asserted by a test).
- **No secrets / no bank values.** The service handles only non-secret asset
  metadata. Connector credentials stay in env / secret manager and are surfaced
  **masked** (`SET`/`MISSING`) only. The local config is localhost/mock; the
  template is placeholders only (`${VAR:-<placeholder>}`), with a test asserting
  no secret fields and no real hosts.
- **Bounded.** `_MAX_ASSETS = 1000`, `_MAX_CONTROLS_PER_ASSET = 500` cap the plan
  so a large/hostile config cannot explode the run.
- **Never raises on bad input.** Missing/malformed config → empty plan, not a
  crash. Adapter import errors are caught per-connector.
- **Deterministic.** Stable sort (route, technology, asset_id); identical config
  ⇒ identical plan (asserted by a test).

---

## 7. CLI

```bash
# Plan from the safe local/mock inventory (no network, no connector calls):
python scripts/run_uat_asset_scheduler.py --config config/uat_assets.local.yaml --dry-run

# JSON output (for pipelines):
python scripts/run_uat_asset_scheduler.py --config config/uat_assets.local.yaml --json

# Fail CI if any asset is unsupported (inventory gap):
python scripts/run_uat_asset_scheduler.py --config config/uat_assets.local.yaml --strict
```

`--dry-run` is the default and only action; `--no-diagnostics` skips connector
readiness. Exit 0 on success; `--strict` exits 1 when unsupported assets exist.

---

## 8. Real UAT usage

1. `cp config/uat_assets.template.yaml config/uat_assets.uat.yaml` (keep the copy
   **out of Git**).
2. Fill real UAT hostnames via env vars (`${ECS_UAT_*}`) or the git-ignored copy —
   never inline secrets/IPs.
3. Provision connector credentials in env / secret manager (`ECS_*`); verify with
   `scripts/run_uat_connector_health.py` (config-only, or `--live` when ready).
4. `python scripts/run_uat_asset_scheduler.py --config config/uat_assets.uat.yaml --dry-run`
   to review the plan.
5. Execute baseline collections through the **existing** evidence service
   (`asset_scheduler.execute_plan(plan, executor=...)`); connector execution stays
   on the connector layer's path.

See also: `../operations/UAT_VALIDATION_RUNBOOK.md`, `UAT_INTEGRATION_GUIDE.md`.

---

## 9. Extensibility

- **New connector** → add one entry to `_CONNECTOR_ROUTES` (the adapter already
  exists in the registry). No other change.
- **New technology** → nothing to do here; it flows from the catalog + fingerprint
  engine automatically.
- **New asset source** → add a source to `asset_discovery` (existing pattern); the
  scheduler consumes normalized `Asset` objects regardless of source.

---

## 10. Testing

`tests/test_uat_asset_scheduler.py` (offline, no network) covers: config loading,
template parsing (+ placeholder expansion), localhost PostgreSQL/NGINX/port-based
classification, connector routing (SharePoint/Jira/SonarQube/ServiceNow/Teams/
Outlook + substring match), plan generation, dry-run execution, connector
readiness (config-only, secret-safe), a guard that `health_check` is never called,
and the unknown-asset fallback.

---

## 11. Known limitations

- Baseline execution via `execute_plan()` requires an injected executor outside
  production; connector *execution* is intentionally not wired here.
- `resolve_scope` treats `application`/`environment` coarsely (documented upstream);
  the scheduler routes at the **asset/technology** grain, which is finer.
- Durable scheduling/cron is out of scope — this is a planning + dry-run layer;
  hook it into a scheduler/cron externally, or the existing scheduler module.
