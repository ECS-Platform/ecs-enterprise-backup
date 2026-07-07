# ECS Final Repository Health Report

**Generated:** Final enterprise consolidation pass (pre-UAT).
**Repository:** `ecs-enterprise-backup` · **Branch:** `cursor/predefined-queries-module`.
**Nature:** Read-only reconciliation + audit. No features added, no modules
redesigned, no parallel implementations. All numbers below are **verified from
code**, not from prose.

> **Verified ground truth:** 187 predefined controls · 21 technologies ·
> 11 enterprise integration adapters · 13 predefined-query connectors (+ shared
> `ms_graph_base`) · 21 Docker Compose services · `compileall` clean ·
> `docker compose config` valid.

---

## 1. Repository maturity — **A (feature-complete, pre-UAT)**

| Dimension | Score | Notes |
|-----------|-------|-------|
| Feature completeness | ✅ A | All advertised capabilities present and wired end-to-end. |
| Code health | ✅ A | `python -m compileall` clean across `modules/`. |
| Consistency | ✅ A- | Catalog/connector counts reconciled this pass; minor historical-report drift remains (non-blocking). |
| Additive discipline | ✅ A | New tech (Aerospike) added via the supplementary catalog + shared bases; no engine/connector duplication. |

---

## 2. Documentation maturity — **A- (comprehensive; minor historical drift)**

- **240 Markdown documents** across 29 areas; indexed by
  [DOCUMENTATION_INVENTORY.md](../DOCUMENTATION_INVENTORY.md) and
  [architecture/ARCHITECTURE_INDEX.md](../architecture/ARCHITECTURE_INDEX.md).
- **API reference** ([API/ECS_API_REFERENCE.md](../developer-manual/ECS_API_REFERENCE.md)) and
  **documentation audit** ([DOCUMENTATION_AUDIT_REPORT.md](DOCUMENTATION_AUDIT_REPORT.md))
  already exist and were **not** regenerated.
- **Fixed this pass:** stale "167 controls / 20 technologies" → "187 / 21" in
  `DEMO_RUNBOOK.md`, `LEADERSHIP_DEMO_SCRIPT.md`, `TECHNOLOGY_MAPPING_GUIDE.md`
  (Aerospike addition).
- **Residual drift (accepted):** some AUDIT/executive/phase reports cite demo-seed
  dataset numbers that differ from the live catalog. Documented in
  [AUDIT/ECS_DOCUMENTATION_INVENTORY.md](ECS_DOCUMENTATION_INVENTORY.md) §5;
  historical reports are intentionally immutable.

---

## 3. Testing maturity — **A- (broad mocked coverage; no live deps)**

- 22+ dedicated integration/connector/predefined-query/scheduler test files,
  including: `test_integration_adapters_mocked`, `test_integration_connectors_deepening`,
  `test_enterprise_connector_auth_headers`, `test_enterprise_connectors_uat_config`,
  `test_ms_graph_connectors`, `test_{sharepoint,teams,outlook}_graph_connector`,
  `test_aerospike_support`, `test_uat_asset_scheduler`, `test_audit_persistence_foundation`,
  and the `test_predefined_*` family.
- All connector tests use **mocked transports** (no live network, no containers).
- Count-coupled assertions reconciled to 187 (`test_predefined_extended_technology_queries`,
  `test_predefined_db_frontend`).
- **Gap:** no live/soak/load testing (by design for this phase) — see §9.

---

## 4. Connector maturity — **A (uniform base; secret-safe)**

### 4.1 Enterprise integration adapters (11) — Task 3
`servicenow_cmdb, archer, sharepoint_graph, teams_graph, outlook_graph, jira,
confluence, sonarqube, checkmarx, prisma_cloud, tripwire` (registry:
`modules/operations/integrations/__init__.py`).

All 11 inherit the shared `_base.py` (and Graph ones `ms_graph_base.py`), providing
uniformly: `get_config` (env/YAML), `is_configured`, `masked_config` (SET/MISSING),
`health_check`, injectable transport, bounded **retry/backoff**, **timeout**,
consistent `{ok, source, status, items, errors}` responses, secret-safe `repr`, and
**pagination** where the API supports it (offset/limit or Graph `@odata.nextLink`).

| Connector | health_check | masked_config | mocked tests | env config | retry/timeout | pagination |
|-----------|:---:|:---:|:---:|:---:|:---:|:---:|
| ServiceNow CMDB | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (Table API) |
| Archer | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| SharePoint (Graph) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (nextLink) |
| Teams (Graph) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (nextLink) |
| Outlook (Graph) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (nextLink) |
| Jira | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Confluence | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| SonarQube | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Checkmarx | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Prisma Cloud | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Tripwire | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### 4.2 Predefined-query connectors (13)
`postgresql, mysql, oracle, sqlserver, mongodb, redis, yugabyte, aerospike,
kubernetes, linux, sonarqube, trivy, gitleaks`. Reconciled this pass:
`connector_for_technology("Aerospike")` was the one confirmed gap (blocked the Run
button) and is now wired (returns `AerospikeConnector` via docker-exec, consistent
with Redis).

**No connector gaps remaining.**

---

## 5. Scheduler maturity — **A (deterministic, offline dry-run)** — Task 6

`modules/audit_intelligence/services/asset_scheduler.py`
(+ `scripts/run_uat_asset_scheduler.py`, `tests/test_uat_asset_scheduler.py`):

- **Asset inventory:** loads `config/uat_assets*.yaml` via
  `asset_discovery.discover_from_manual` (reuses the normalization pipeline).
- **Technology classification:** reuses `technology_fingerprint` (image/name/port/
  hint) — Aerospike classifies generically (image `aerospike/aerospike-server`,
  name `*aerospike*`, ports 3000/13000, hint `aerospike`).
- **Routing:** enterprise-connector route (adapter registry) → baseline-collector
  route (predefined-query controls) → unsupported (manual). Aerospike → baseline
  with its 20 `ASX-*` controls.
- **Evidence planning:** bounded, deterministic `EvidencePlan`.
- **Dry-run:** `dry_run()` is side-effect-free (no sockets, no queries) — CI/demo safe.
- **Docs:** [DEVELOPER/UAT_ASSET_DRIVEN_SCHEDULER_DESIGN.md](../scheduler/UAT_ASSET_DRIVEN_SCHEDULER_DESIGN.md),
  [operations/ECS_SCHEDULER_REFERENCE.md](../operations/ECS_SCHEDULER_REFERENCE.md).

**No scheduler inconsistencies found.** (No per-technology scheduler edits are
required — classification + routing are generic through fingerprinting + mapping.)

---

## 6. Technology coverage — **21 technologies** — Task 2

Consistent across dropdown (`get_technology_filter_options`), technology rules
(`TECHNOLOGY_RULES`), fingerprinting, predefined queries, and (where applicable)
connector registry:

| Technology | Predefined queries | Fingerprint | Docker demo | Notes |
|-----------|:---:|:---:|:---:|-------|
| Oracle (12), PostgreSQL (11), Aurora **MySQL** (11), SQL Server (10), MongoDB (8), Redis (8), **YugabyteDB** (9), **Aerospike** (20) | ✅ | ✅ | ✅ | DB technologies |
| Linux (15), RHEL 8.x (8), RHEL 9.x (8), Windows (3) | ✅ | ✅ | ✅ (RHEL/Ubuntu) | OS; Windows via SSH connector |
| NGINX (9), Apache HTTPD (8), Tomcat (9) | ✅ | ✅ | ✅ | Middleware |
| Kubernetes (10), OpenShift (10) | ✅ | ✅ | (external) | Container platforms |
| SonarQube (1), Trivy (1), GitLeaks (1) | ✅ | ✅ | ✅ (Sonar) | AppSec |
| SharePoint, Teams, Outlook, Jira, Confluence, ServiceNow, Prisma, Checkmarx, Tripwire, Archer | (enterprise connectors) | n/a | n/a | Evidence via integration adapters, not predefined queries |

**Naming reconciliations (expected, not defects):** "MySQL" → **`Aurora MySQL`**,
"Yugabyte" → **`YugabyteDB`**, "RHEL8/9" → **`Red Hat Enterprise Linux 8.x/9.x`**.
**Jenkins/Gitea** are demo source connectors (in `connectors:` config), not
predefined-query technologies — expected. An **`Unknown`** bucket (15 controls)
holds uncategorised Excel-sourced controls; harmless.

**No technology-catalog inconsistencies that affect functionality.**

---

## 7. Predefined query coverage — Task 4

- 187 controls; each has technology mapping, `query` (executable text), framework
  mapping, and (supplementary entries) a category.
- **Execution path + Run Query:** dispatch via `run_predefined_query()` →
  per-technology runner; `prepare_execution()` resolves a connector via
  `connector_for_technology()` — now complete for Aerospike (Run button works).
- **CLI:** `scripts/run_predefined_query.py --control <ID>` /
  `--list [--technology <T>]`.
- **Docs:** [DEVELOPER/PREDEFINED_DATABASE_QUERY_MODULE.md](../developer-manual/PREDEFINED_DATABASE_QUERY_MODULE.md),
  [operations/ECS_PREDEFINED_QUERY_EXECUTION_GUIDE.md](../operations/ECS_PREDEFINED_QUERY_EXECUTION_GUIDE.md),
  [DEVELOPER/AEROSPIKE_LOCAL_TESTING_GUIDE.md](../connectors/AEROSPIKE_LOCAL_TESTING_GUIDE.md).

**No missing mappings.**

---

## 8. Docker maturity — Task 5

- **21 services**, all optional targets gated behind **profiles**
  (`aerospike`, `demo`, `db-targets`, `infra-demo`, `nginx-demo`, `rhel-demo`,
  `sources`, …). `docker compose config` is **valid**.
- **Configurable ports & localhost-friendly.** Aerospike uses
  `${AEROSPIKE_HOST_PORT:-13000}:3000` (+13001/13002) — **never host 3000**
  (Gitea owns `3000:3000`).
- **Health checks** on core infra (`postgres`, `pgvector`, `minio`); demo targets
  rely on image defaults.

**Findings:**
- 🟡 **Low:** `yugabyte` (profile `db-targets`) and `postgres` (default profile)
  both bind **host port 5433**. No conflict in normal use (different profiles), but
  running `db-targets` alongside defaults would collide. Consider making the
  Yugabyte host port configurable (e.g. `${ECS_YB_HOST_PORT:-5433}`). *Not fixed
  this pass — out of "do not modify Docker unless broken" scope; flagged only.*
- ✅ No other host-port conflicts among default-profile services.

---

## 9. Production readiness — remaining gaps (Task 9; report only)

Tracked in [DEVELOPER/PRODUCTION_READINESS_GAP_REGISTER.md](../production/PRODUCTION_READINESS_GAP_REGISTER.md).
Summary of what remains **operational/environment** work (not product code):

| Area | Status | Gap |
|------|--------|-----|
| Persistence | 🟡 Foundation | In-memory default; wire Postgres (`sql_persistence`) + apply `DB_SCHEMA_AUDIT_INTELLIGENCE.sql`. |
| Secrets | ⛳ Pending | Source from a secret manager (Vault/cloud/K8s); ECS shows SET/MISSING only. |
| Security / auth | ⛳ Pending | Enable auth/RBAC + OIDC/Azure AD mapping in prod (demo runs auth-off). |
| Logging | 🟡 | App logs never leak secrets; ship to platform log aggregation. |
| Monitoring / alerting | ⛳ Pending | Health endpoints exist (`/api/audit/health`); wire metrics + alerts. |
| Deployment / HA | ⛳ Pending | Single-process today; ≥2 replicas need shared durable store (persistence). |
| Backup / DR | 🟡 | Runbooks exist (`operations/ECS_BACKUP_AND_RECOVERY_GUIDE.md`, `ECS_DISASTER_RECOVERY_PLAN.md`); validate against provisioned Postgres. |
| Performance | 🟡 | Bounded pagination + caps in place; no load/soak testing yet. |
| Data retention | ⛳ Pending (policy) | Agree + enforce retention/audit-log policy. |
| Rate limits | 🟡 | Generic retry; no vendor 429/`Retry-After` handling. |

No production gaps are architectural — all are deployment-time configuration/ops.

---

## 10. Known limitations

- In-memory stores are the default; durability is opt-in.
- OAuth tokens cached per-client (no refresh-on-expiry); external rate-limit
  handling is generic.
- Live UAT validation against bank systems is pending (offline-validated only).
- Historical/phase reports contain demo-seed numbers that differ from the live
  catalog (documented drift).

---

## 11. Future roadmap (suggested, non-binding)

1. Enable + wire Postgres persistence; hydrate engines on startup.
2. Integrate secret manager; enable auth/RBAC + OIDC for prod.
3. Add metrics/alerting + centralized logging.
4. HA deployment (≥2 replicas) once state is shared.
5. Live UAT validation per the Bank Developer UAT Checklist.
6. Load/soak testing; token refresh + 429 handling in connectors.
7. Make the Yugabyte demo host port configurable (5433 overlap).

---

## 12. Outstanding production work (one-line)

Provision Postgres + secret manager, enable auth/monitoring/HA, complete live UAT,
and agree data-retention policy — all configuration/ops, no code redesign.

---

## Repository health score: **A- (feature-complete; UAT-ready pending environment wiring)**

- Feature completeness **A** · Connectors **A** · Scheduler **A** · Tech coverage **A**
- Documentation **A-** · Testing **A-** · Production readiness **B** (env/ops pending)

Cross references: [DOCUMENTATION_INVENTORY.md](../DOCUMENTATION_INVENTORY.md) ·
[architecture/ARCHITECTURE_INDEX.md](../architecture/ARCHITECTURE_INDEX.md) ·
[DOCUMENTATION_AUDIT_REPORT.md](DOCUMENTATION_AUDIT_REPORT.md) ·
[API/ECS_API_REFERENCE.md](../developer-manual/ECS_API_REFERENCE.md) ·
[DEVELOPER/PRODUCTION_READINESS_GAP_REGISTER.md](../production/PRODUCTION_READINESS_GAP_REGISTER.md).
