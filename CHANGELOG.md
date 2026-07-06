# Changelog

All notable, milestone-level changes to the Evidence Collection System (ECS) are
documented here. The most recent milestone appears at the top.

Format is loosely based on [Keep a Changelog](https://keepachangelog.com/).

---

## Unreleased

### Added

- **Audit Intelligence layer — Milestone 1** (new package `modules/audit_intelligence/`,
  additive; the predefined-query platform is untouched and used read-only):
  - **Technology → Control → Framework mapping engine**
    (`engines/technology_control_mapping.py` + `services/mapping_service.py`) —
    derives the Technology → Controls → Frameworks graph from the existing 167
    controls (20 technologies, 16 frameworks). Lookup/search/graph/stats APIs.
  - **Asset discovery** (`engines/asset_discovery.py`) — unified asset inventory
    normalized from manual import, the ServiceNow CMDB skeleton (injected/mock
    transport), offline `docker-compose` parsing, and the existing enterprise-GRC
    CMDB; de-duplicated by asset id.
  - **Technology fingerprinting** (`engines/technology_fingerprint.py`) —
    deterministic technology/version inference with a confidence score and audit
    signals; cross-links each asset to applicable controls/frameworks.
  - `services/asset_service.py` — inventory, technology roll-up, fingerprint
    report, and coverage summary.
  - `scripts/audit_intelligence_report.py` — read-only, offline CLI to inspect the
    mapping and asset inventory (text/`--json`).
  - Serializable frozen dataclasses in `models.py`; comprehensive offline tests
    (`test_technology_control_mapping.py`, `test_technology_fingerprint.py`,
    `test_asset_discovery.py`, `test_audit_intelligence_report_cli.py`).
  - Developer guides: `docs/DEVELOPER/TECHNOLOGY_MAPPING_GUIDE.md`,
    `docs/DEVELOPER/ASSET_DISCOVERY_GUIDE.md`.
- Extended predefined-query technology coverage (+62 controls; total 167):
  - Redis `RDX-001..008`, Apache HTTPD `APX-001..008`, Tomcat `TCX-001..008`,
    SQL Server `MSX-001..010`, MongoDB `MGX-001..008`, Kubernetes `K8X-001..010`,
    OpenShift `OCX-001..010`. Each carries a category + expected evidence.
- New connectors (no duplicate logic): `RedisConnector` (redis-cli via the
  container connector), `SQLServerConnector` (pyodbc, optional), `MongoDBConnector`
  (pymongo, optional), `KubernetesConnector` (kubectl), `OpenShiftConnector` (oc).
  Apache HTTPD and Tomcat reuse the existing docker-exec Linux connector. All
  degrade gracefully when a driver/binary/target is unavailable.
- Enterprise integration skeletons: ServiceNow CMDB (asset/CI fetch + mapping
  stubs) and Archer (control/framework fetch + mapping stubs) — config-driven,
  injectable transport, mockable, no real calls; secrets never logged.
- Docker demo targets (opt-in): `apache-demo` + `tomcat-demo`
  (`apache-demo`/`tomcat-demo` + umbrella `infra-demo-extended`), `mongodb-demo`
  (`mongodb-demo` + `db-demo-extended`), and `sqlserver-demo` (optional/heavy,
  `sqlserver-demo` profile only — not in any umbrella/default). Redis reuses the
  existing `redis` service. Kubernetes/OpenShift are documentation-only locally
  (no heavy cluster started by default).
- `scripts/check_predefined_extended_environment.py` — extended-target diagnostic
  (Redis/Apache/Tomcat/MongoDB/SQL Server containers, kubectl/oc availability,
  ServiceNow/Archer config presence). Docker-safe, `--json`, secrets masked.
- Config: `ECS_REDIS_*`, `ECS_APACHE_*`, `ECS_TOMCAT_*`, `ECS_SQLSERVER_*`,
  `ECS_MONGODB_*`, `ECS_KUBECTL_PATH`/`ECS_KUBECONFIG`/`ECS_K8S_TIMEOUT_SECONDS`,
  `ECS_OC_PATH`/`ECS_OPENSHIFT_*`, `ECS_SERVICENOW_*`, `ECS_ARCHER_*` in
  `.env.example` and `config/environments/_base.yaml`. `pymongo` added to
  requirements; `pyodbc` documented as install-on-demand (needs system ODBC).

- Docker demo targets for the predefined infrastructure technologies (all opt-in
  via compose profiles; nothing new starts by default):
  - `nginx-demo` (nginx:1.27-alpine, profiles `nginx-demo` / `infra-demo`) with a
    demo config at `demo-data/nginx/default.conf`.
  - `rhel8-demo` (Red Hat UBI8) and `rhel9-demo` (Red Hat UBI9), profiles
    `rhel-demo` / `infra-demo` — no RHEL entitlement needed.
  - `oracle-demo` (gvenzl/oracle-free:23-slim) under the `oracle-demo` profile
    only — heavy, 16/20 GB recommended, **not** in `infra-demo` or default.
- Per-technology container routing: RHEL 8.x → `ECS_RHEL8_CONTAINER`, RHEL 9.x →
  `ECS_RHEL9_CONTAINER`, NGINX → `ECS_NGINX_CONTAINER`, each falling back to
  `ECS_LINUX_CONTAINER` (reuses the existing Linux docker-exec connector).
- `scripts/check_predefined_technology_environment.py` — infrastructure
  environment diagnostic (Docker + container status + config; never prints
  passwords).
- Config: `ECS_RHEL8_CONTAINER`, `ECS_RHEL9_CONTAINER`, `ECS_RHEL_TIMEOUT_SECONDS`
  in `.env.example` and `config/environments/_base.yaml`; Oracle demo default
  service name `FREEPDB1`.
- Documentation: a Technology Docker demo support matrix and start/stop commands;
  Windows documented as remote/enterprise-only (no local macOS/Linux Docker
  container).
- Oracle predefined query catalog (ORX-001 to ORX-010) with a python-oracledb
  connector (thin mode).
- NGINX predefined query catalog (NGX-001 to NGX-008), executed via the existing
  container shell connector.
- Linux predefined query catalog (LNX-001 to LNX-008).
- Red Hat Enterprise Linux 8.x predefined query catalog (RH8-001 to RH8-008),
  technology label "Red Hat Enterprise Linux 8.x".
- Red Hat Enterprise Linux 9.x predefined query catalog (RH9-001 to RH9-008),
  technology label "Red Hat Enterprise Linux 9.x".
- Predefined Queries page: Technology filter now includes Oracle, NGINX, Linux,
  Red Hat Enterprise Linux 8.x, and Red Hat Enterprise Linux 9.x; Run Query works
  for all of them through the same execution endpoint.
- General CLI runner `scripts/run_predefined_query.py` (`--list`, `--control`,
  `--technology`) covering all technologies (the database-only
  `scripts/run_predefined_db_query.py` continues to work).
- Config: `ECS_ORACLE_*`, `ECS_NGINX_*`, and `ECS_LINUX_*` variables; optional
  `nginx-demo` local container under the `db-targets` compose profile.
- `oracledb` added to `requirements.txt` (Oracle connector; degrades gracefully
  when absent).

### Notes

- Oracle live execution requires an external Oracle endpoint (or an optional
  Oracle XE container on a 16/20 GB machine); no Oracle container starts by
  default. Firewall/network: Oracle TCP 1521; SSH TCP 22 for future remote
  Linux/NGINX modes.

---

## ecs-predefined-db-complete-v1

Released: 2026-07-06

### Summary

Completed ECS Predefined Database Query Module Version 1.

This milestone adds live predefined database query support for PostgreSQL, YugabyteDB, and Aurora MySQL-compatible MySQL, including backend connectors, supplementary query catalog, frontend Run Query integration, technology filtering, onboarding diagnostics, and developer documentation.

### Added

- PostgreSQL predefined query connector
- YugabyteDB predefined query connector using YSQL/PostgreSQL-compatible protocol
- Aurora MySQL-compatible connector
- 26 supplementary predefined database queries:
  - PostgreSQL: PGX-001 to PGX-008
  - YugabyteDB: YBX-001 to YBX-008
  - Aurora MySQL: MYX-001 to MYX-010
- Frontend support for supplementary PGX/YBX/MYX controls
- Technology filter on Predefined Queries page
- Run Query button support for PostgreSQL, YugabyteDB, and Aurora MySQL controls
- Execution history support for supplementary database controls
- Database onboarding diagnostics
- Developer documentation for predefined database query setup
- Frontend regression tests for supplementary database query visibility and run enablement

### Validated

The following representative controls were successfully executed:

- PGX-001 — PostgreSQL SSL check
- YBX-001 — YugabyteDB cluster server check
- MYX-001 — Aurora MySQL/MySQL SSL capability check

Validation covered:

- Docker-based PostgreSQL
- Docker-based YugabyteDB
- Docker-based MySQL 8 as Aurora MySQL-compatible local simulator
- CLI execution
- Frontend visibility
- Frontend Run Query flow
- Execution history
- Unit/regression tests

### Developer Notes

For local Docker testing, the expected database defaults are:

PostgreSQL:

- ECS_PG_HOST=127.0.0.1
- ECS_PG_PORT=5432
- ECS_PG_DATABASE=ecs_demo
- ECS_PG_USER=ecs_user
- ECS_PG_PASSWORD=ecs_password
- ECS_PG_SSLMODE=disable

YugabyteDB:

- ECS_YB_HOST=127.0.0.1
- ECS_YB_PORT=5433
- ECS_YB_DATABASE=yugabyte
- ECS_YB_USER=yugabyte
- ECS_YB_PASSWORD=yugabyte
- ECS_YB_SSLMODE=disable

Aurora MySQL-compatible MySQL:

- ECS_MYSQL_HOST=127.0.0.1
- ECS_MYSQL_PORT=3306
- ECS_MYSQL_DATABASE=ecs_demo
- ECS_MYSQL_USER=ecs_user
- ECS_MYSQL_PASSWORD=ecs_password
- ECS_MYSQL_SSL=false

> These are local, non-production demo defaults for Docker validation only. Do not
> use these credentials outside local development; for UAT/cloud, set real
> endpoints and read-only credentials via `.env` / environment YAML. See
> [docs/DEVELOPER/PREDEFINED_DATABASE_QUERY_MODULE.md](docs/DEVELOPER/PREDEFINED_DATABASE_QUERY_MODULE.md).

### Tag

- ecs-predefined-db-complete-v1
