# ECS Predefined Query Execution Guide

**Type:** Knowledge documentation. No code modified.
**Date:** 2026-06-17
**Grounding:** Every behavioural claim traces to repository files under
`modules/operations/engines/` and `config/environments/`. Items not present in
code are explicitly marked **(Inferred from implementation)**.

Related: `docs/03-development/developer-manual/ENVIRONMENT_CONFIGURATION_FRAMEWORK.md`,
`docs/03-development/developer-manual/ECS_CONFIGURATION_DEPENDENCY_MATRIX.md`,
`docs/OPERATIONS/ECS_CONTROL_AND_EVIDENCE_REUSE_GUIDE.md`,
`docs/01-product/product/ECS_FRAMEWORK_REFERENCE.md`.

---

## 1. Purpose

The **Predefined Queries** module turns a curated control library into
**executable, evidence-producing checks**. Each control row carries a validation
query/command (SQL, shell, API call, scanner invocation). ECS detects the
technology, routes the query to the correct connector, executes it against the
**environment-selected target**, parses the result, and **automatically files
the output as evidence** mapped to the control’s frameworks — with a full audit
trail.

This converts manual, repeated compliance checks into **repeatable,
target-agnostic, environment-driven automation**: the same control library runs
unchanged across Local / Dev / SIT / UAT / Prod, because only the YAML targets
change.

Source of truth for the catalog: `ECS_Query_Driven_Control_Library_Consolidated.xlsx`
loaded by `modules/operations/engines/predefined_queries_engine.py`.

## 2. Architecture

| Layer | Component | Responsibility |
|-------|-----------|----------------|
| Catalog | `predefined_queries_engine.py` | Load controls from Excel, detect technology, derive status, expose dashboard |
| Routing | `connector_for_technology()` / `run_predefined_query()` | Map detected technology → connector |
| Targets | `query_connectors.py` (`build_connector_config`, `get_predefined_target`) | Resolve execution targets from the active environment |
| Connectors | `postgresql_connector.py`, `linux_connector.py`, `sonarqube_connector.py`, `trivy_connector.py`, `gitleaks_connector.py` | Execute against a real target, return `ConnectorResult` |
| Normalisation | `connector_common.py` (`complete_connector_execution`) | One path: audit → evidence → repository → API payload |
| Evidence | `predefined_query_evidence.py` | Build/store evidence records, bridge to the evidence repository |
| Audit | `predefined_query_audit.py` | Per-execution audit log + per-control history |
| Config | `config/environments/<env>.yaml` + `config/environment_loader.py` | Environment-driven targets |

**Technology detection** is deterministic (no AI), via `TECHNOLOGY_RULES` in
`predefined_queries_engine.py`: GitLeaks, Trivy, SonarQube, NGINX, PostgreSQL,
Oracle, Windows, Linux.

**Live execution allow-list:** Live execution is gated by `LIVE_CONTROL_IDS`
(DB-001/002/003, OS-001/002, APP-001/002, APPSEC-001/002) and, for PostgreSQL, an
`ALLOWED_POSTGRESQL_QUERIES` allow-list — a safety control so only vetted,
read-only checks run live. All other controls are catalogued and audit-ready but
not auto-executed.

## 3. Execution flow

```
User triggers control execution (Predefined Queries page)
   │
   ▼
prepare_execution(control_id, user)         # validates query/tech/framework, picks connector
   │
   ▼
run_predefined_query(control_id, user)      # dispatch by technology
   │   ├─ PostgreSQL → run_postgresql_query()  (allow-list enforced)
   │   ├─ Linux      → LinuxConnector(get_linux_config())
   │   ├─ SonarQube  → SonarQubeConnector(get_sonarqube_config())
   │   ├─ Trivy      → TrivyConnector(get_trivy_config())
   │   └─ GitLeaks   → GitLeaksConnector(get_gitleaks_config())
   │
   ▼
connector.connect() → connector.execute(query) → ConnectorResult
   │
   ▼
complete_connector_execution(...)           # single normalisation path
   ├─ record_execution_audit(...)           # audit log (PQ-EXEC-######)
   ├─ prepare_evidence_record(...)          # evidence payload (PQ-EVD-######)
   ├─ register_with_evidence_repository(...)# → register_upload() in evidence_repository
   └─ log_event("Predefined Query Executed")# global audit trail
   │
   ▼
API payload {ok, rows_returned, output, duration_ms, evidence_id, evidence_filename}
```

Failures never crash the page: connection or execution errors return a structured
`{ok: false, error, error_type}` and are still recorded in the audit log
(`complete_connector_execution`, `run_postgresql_query`).

## 4. YAML configuration framework

Targets come from `config/environments/<ECS_ENV>.yaml`, deep-merged over
`_base.yaml` and resolved by `config/environment_loader.py`. The relevant section:

```yaml
predefined_query_targets:
  os_servers:          [...]   # hosts for OS baselining / Linux / VAPT
  db_servers:          [...]   # hosts for DB baselining
  middleware_servers:  [...]   # hosts for middleware baselining
  appsec_targets:      [...]   # endpoints for application security
  postgresql: {host, port, database, user, password_env, timeout_sec}
  linux:      {container, timeout_sec}
  sonarqube:  {base_url, user, token_env, password_env, timeout_sec}
  trivy:      {image, timeout_sec}
  gitleaks:   {scan_path, timeout_sec}
```

Each connector’s `get_*_config()` resolves **active-environment YAML → `ECS_*`
env var → historical default**, so behaviour is identical when no override is
present (verified). Secrets are referenced by env-var **name** only
(`password_env`, `token_env`).

## 5. Environment loading

```
ECS_ENV (local|dev|sit|uat|prod, default local)
   │
   ▼
get_environment_config()  →  _base.yaml  ⊕  <env>.yaml  (deep merge, ${VAR} resolved)
   │
   ▼
get_predefined_query_targets()  →  predefined_query_targets.*
   │
   ▼
get_*_config()  (per connector)   and   build_connector_config()  (full target map)
```

Server target lists can also be overridden at runtime with comma-separated env
vars: `ECS_TARGET_OS_SERVERS`, `ECS_TARGET_DB_SERVERS`, `ECS_TARGET_MW_SERVERS`,
`ECS_TARGET_APPSEC` (handled in `environment_loader._apply_target_overrides`).

## 6. Target selection

* **By technology:** the detected technology selects the connector class
  (`connector_for_technology`).
* **By environment:** the connector’s host/URL/container/image comes from the
  active environment’s `predefined_query_targets`.
* **By framework scope:** `framework_targets.<fw>.target_groups` declares which
  server groups a framework assesses (e.g. `pci_dss → [os_servers, db_servers,
  appsec_targets]`), so a framework run fans out across the right inventory.
  **(Inferred from implementation:** the fan-out mapping is defined in YAML;
  multi-host batch execution per framework is a forward capability — today live
  execution is per-control via the allow-list.)

## 7. Predefined query target YAML model (per environment)

The schema covers the requested categories. Where a category has no dedicated
key today, the mapping to the implemented key is noted **(Inferred from
implementation)**.

| Requested category | YAML location | Notes |
|--------------------|---------------|-------|
| applications | `applications.*` | host/port/base_url per app |
| operating_systems | `predefined_query_targets.os_servers` + `predefined_query_targets.linux` | Linux live via container; OS hosts via list |
| databases | `databases.*` + `predefined_query_targets.db_servers` + `.postgresql` | infra DBs + live PG target |
| web_servers | `predefined_query_targets.middleware_servers` | NGINX/Apache **(Inferred from implementation)** |
| app_servers | `predefined_query_targets.middleware_servers` | **(Inferred from implementation)** |
| middleware | `predefined_query_targets.middleware_servers` | dedicated list |
| cloud_services | `connectors.prisma_cloud`, `connectors.azure_devops` | cloud posture via connectors |
| security_tools | `predefined_query_targets.sonarqube/.trivy/.gitleaks`, `connectors.prisma_cloud` | scanners |
| audit_tools | `connectors.servicenow`, `reporting.export_path` | GRC/ticketing + report sink **(Inferred from implementation)** |
| framework_sources | `framework_targets.*` | per-framework enable + target groups |

### 7.1 `local.yaml`
- environment: `local`; tenant `local-demo`.
- `predefined_query_targets`: server lists **empty by design** — uses the live
  demo containers (`postgresql:localhost`, `linux:ubuntu-demo`,
  `sonarqube:sonarqube-demo:9000`, `trivy:alpine:3.19`, `gitleaks:<repo>/demo-data/gitleaks-sample`).
- Purpose: reproduce historical demo exactly; no external systems required.

### 7.2 `dev.yaml`
- environment: `dev`; app hosts `*.dev.bank.local`; Jira/Confluence enabled.
- `os_servers: [10.0.10.11, 10.0.10.12]`, `db_servers: [10.0.20.11, 10.0.20.12]`,
  `middleware_servers: [10.0.30.11]`, `appsec_targets: [netbanking.dev…, mobile.dev…]`.

### 7.3 `sit.yaml`
- environment: `sit`; app hosts `*.sit.bank.local`; ServiceNow enabled.
- `os_servers: [10.20.10.1-3]`, `db_servers: [10.20.20.1-2]`,
  `middleware_servers: [10.20.30.1-2]`.

### 7.4 `uat.yaml`
- environment: `uat`; app hosts `*.uat.bank.local`.
- `os_servers: [10.10.10.1, 10.10.10.2]`, `db_servers: [10.10.20.1, 10.10.20.2]`,
  `middleware_servers: [10.10.30.1, 10.10.30.2]`, `appsec_targets: [netbanking.uat…, payments.uat…]`.

### 7.5 `prod.yaml`
- environment: `prod`; app hosts `*.bank.com`; SSO enabled; object store secure.
- `os_servers: [172.16.10.1, 172.16.10.2]`, `db_servers: [172.16.20.1, 172.16.20.2]`,
  `middleware_servers: [172.16.30.1, 172.16.30.2]`, `appsec_targets: [netbanking.bank.com, payments.bank.com]`.

### 7.6 How values are loaded and queries execute
1. `ECS_ENV` selects the file; loader merges `_base ⊕ <env>` and resolves `${VAR}`.
2. A control’s technology is detected from its query text.
3. The matching `get_*_config()` reads the connector block for the active env.
4. The connector connects to the resolved target and runs the query.
5. Output is parsed into a `ConnectorResult`, then filed as evidence + audited.

## 8. Predefined query evidence flow

```
YAML Target (predefined_query_targets.*)
   ↓
Connector (PostgreSQL / Linux / SonarQube / Trivy / GitLeaks)
   ↓
Execution Engine (connector.execute → ConnectorResult)
   ↓
Result Parser (_format_result / connector-specific summary)
   ↓
Evidence Generator (prepare_evidence_record → PQ-EVD-######)
   ↓
Evidence Repository (register_with_evidence_repository → register_upload → EVD-#####)
   ↓
Framework Mapping (framework_coverage / framework_tags)
   ↓
Control Mapping (control_id on evidence + audit)
   ↓
Audit Dashboard (execution audit log + global audit_trail)
   ↓
Executive Dashboard (coverage/KPIs roll up from repository)
```

## 9. Evidence collection

On a successful execution, `complete_connector_execution` (and
`run_postgresql_query`) build a `PredefinedQueryEvidence` record
(`evidence_id=PQ-EVD-######`, `control_id`, `result`, UTC `timestamp`, `user`,
`framework_coverage`) and bridge it into the evidence repository via
`register_upload` — producing a standardised filename
(`PREDEFINED_QUERY_<control_id>.txt`), SHA-256 hash, and integrity status.

## 10. Evidence validation

* **Integrity:** `compute_hash` (SHA-256) + `integrity_check` set
  `Valid` / `Tamper Detected (simulated)` on every record.
* **Naming policy:** `enforce_naming` standardises evidence filenames
  (`<FRAMEWORK>_<APP>_<DATE>_<file>`).
* **Status derivation:** controls derive `Ready` / `Manual` /
  `Unsupported Technology` (`_derive_status`); execution results carry
  `Success` / `Failed` with friendly error typing (`_friendly_error`).
* **Approval workflow:** filed evidence enters the evidence lifecycle
  (`Draft → … → Approved`) and the auditor review queue (see the reuse guide and
  evidence workflow engine).

## 11. Evidence storage

`evidence_repository.py` holds records with `evidence_id`, standardised
`filename`, `framework_tags`, `application_tags`, `control`, `sha256`,
`integrity`, `lifecycle`, `version`, `reviewer`, `status`. In real environments
the system of record is PostgreSQL (`databases.postgres`) with object storage
for artifacts (`storage.object_store`); the demo uses a deterministic in-process
store so no DB is required.

## 12. Evidence reuse

`_link_reuse` groups evidence by standardised filename into `REUSE-###` groups
and records `linked_controls` across frameworks — one execution result can
satisfy multiple controls/frameworks. `get_reuse_graph` exposes the reuse graph.
Full treatment: `docs/OPERATIONS/ECS_CONTROL_AND_EVIDENCE_REUSE_GUIDE.md`.

## 13. Evidence versioning

`register_upload` sets `version: 1` and calls `record_version(evidence_id,
filename, version, user)`. Re-uploads/re-executions create new versions while
preserving lineage. **(Inferred from implementation:** supersede-on-re-execution
increments the version chain; the audit trail’s `record_version` is the version
ledger.)

## 14. Framework mapping

Each control carries `framework_coverage` (parsed into `frameworks[]` by
`_parse_frameworks`). Evidence inherits the primary framework as `framework_tags`
and the full coverage string, so a single execution maps to every framework the
control serves. The framework catalog (`framework_catalog.py`) provides the
authoritative control→framework structure.

## 15. Control mapping

Every audit and evidence record is keyed by `control_id`. `get_control_by_id`
enriches a control with its `execution_history` and `latest_result`, and
`get_execution_history_for_control` returns the per-control execution ledger.

## 16. Audit traceability

Two complementary trails:
1. **Execution audit log** (`predefined_query_audit.py`): `PQ-EXEC-######` with
   control, user, technology, time, status, duration, rows, query, result,
   framework coverage. Queryable globally (`get_execution_audit_log`) and per
   control (`get_execution_history_for_control`).
2. **Global audit trail** (`audit_trail.log_event`): "Predefined Query Executed"
   events with user, framework, control, and the evidence filename.

Together these give end-to-end traceability: **YAML target → connector →
execution → result → evidence → framework/control → audit → dashboard**, with
who/what/when/where recorded at each hop.

## 17. Current vs inferred vs recommended

| Area | Current state | Inferred | Recommended future |
|------|---------------|----------|--------------------|
| Live execution | Allow-listed controls (PG/Linux/SonarQube/Trivy/GitLeaks) | per-framework fan-out across target lists | Enable batch framework runs across `target_groups` |
| Non-PG DBs | Config slots (Oracle/MySQL/SQL Server) | — | Implement live connectors (Phase 2) |
| Windows | Interface only | — | Implement WinRM/PowerShell connector (Phase 2) |
| Evidence store | In-process demo + Postgres bridge | versioning via record_version | Persist version chain + object-store artifacts in UAT/PROD |
