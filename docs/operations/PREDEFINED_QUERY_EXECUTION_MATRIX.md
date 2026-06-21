# Predefined Query Execution Matrix

**Purpose:** Per-control execution capability for every predefined query control, grounded in the loaded control library and the connector implementations.
**Source:** `ECS_Query_Driven_Control_Library_Consolidated.xlsx` → `predefined_queries_engine.assess_execution_capability()`; connectors under `modules/operations/engines/*_connector.py`; live set `LIVE_CONTROL_IDS`.

## Capability rules

- **Executable (Ready)** requires all of: known technology · implemented connector · control in `LIVE_CONTROL_IDS` · runtime dependency present.
- **Configuration Required** — implemented connector exists, but the control is not wired for live execution (no allow-listed target).
- **Connector Missing** — technology maps to a generic connector that raises `NotImplementedError` (Oracle → `DatabaseConnector`, Windows/NGINX → `SSHConnector`).
- **Unsupported Technology** — query text matched no `TECHNOLOGY_RULES` pattern (`detect_technology → Unknown`).
- **Dependency Missing** — implemented + live but the driver is absent (e.g. PostgreSQL without `psycopg2`). *(Not present in the current environment — `psycopg2` is installed.)*

> "Current Status" and "Expected Status" are identical because the fix made the displayed status equal runtime reality. Every row is **Demo Safe**: executable controls run; non-executable controls show a precise, explainable status and (after the fix) do **not** offer a misleading Run action.

## Matrix (37 controls)

| Control | Technology | Connector | Dependency | Executable | Current Status | Expected Status | Demo Safe |
|---|---|---|---|---|---|---|---|
| AI-001 | Unknown | — | — | No | Unsupported Technology | Unsupported Technology | Yes |
| AI-002 | Unknown | — | — | No | Unsupported Technology | Unsupported Technology | Yes |
| AI-003 | Unknown | — | — | No | Unsupported Technology | Unsupported Technology | Yes |
| APP-001 | SonarQube | SonarQubeConnector | HTTP API | Yes | Ready | Ready | Yes |
| APP-002 | GitLeaks | GitLeaksConnector | docker | Yes | Ready | Ready | Yes |
| APP-003 | Unknown | — | — | No | Unsupported Technology | Unsupported Technology | Yes |
| APP-004 | Trivy | TrivyConnector | docker | No | Configuration Required | Configuration Required | Yes |
| DB-001 | PostgreSQL | PostgreSQLConnector | psycopg2 | Yes | Ready | Ready | Yes |
| DB-002 | PostgreSQL | PostgreSQLConnector | psycopg2 | Yes | Ready | Ready | Yes |
| DB-003 | PostgreSQL | PostgreSQLConnector | psycopg2 | Yes | Ready | Ready | Yes |
| DB-004 | Oracle | DatabaseConnector (NotImplemented) | n/a | No | Connector Missing | Connector Missing | Yes |
| DB-005 | Unknown | — | — | No | Unsupported Technology | Unsupported Technology | Yes |
| DB-006 | Unknown | — | — | No | Unsupported Technology | Unsupported Technology | Yes |
| DB-007 | Unknown | — | — | No | Unsupported Technology | Unsupported Technology | Yes |
| DPSC-001 | Unknown | — | — | No | Unsupported Technology | Unsupported Technology | Yes |
| DPSC-002 | Unknown | — | — | No | Unsupported Technology | Unsupported Technology | Yes |
| ITPP-001 | Unknown | — | — | No | Unsupported Technology | Unsupported Technology | Yes |
| ITPP-002 | Linux | LinuxConnector | docker/ssh | No | Configuration Required | Configuration Required | Yes |
| ITPP-003 | Linux | LinuxConnector | docker/ssh | No | Configuration Required | Configuration Required | Yes |
| ITPP-004 | Unknown | — | — | No | Unsupported Technology | Unsupported Technology | Yes |
| MW-001 | NGINX | SSHConnector (NotImplemented) | n/a | No | Connector Missing | Connector Missing | Yes |
| MW-002 | Unknown | — | — | No | Unsupported Technology | Unsupported Technology | Yes |
| MW-003 | Unknown | — | — | No | Unsupported Technology | Unsupported Technology | Yes |
| OS-001 | Unknown | — | — | No | Unsupported Technology | Unsupported Technology | Yes |
| OS-002 | Linux | LinuxConnector | docker/ssh | Yes | Ready | Ready | Yes |
| OS-003 | Linux | LinuxConnector | docker/ssh | No | Configuration Required | Configuration Required | Yes |
| OS-004 | Unknown | — | — | No | Unsupported Technology | Unsupported Technology | Yes |
| OS-005 | Unknown | — | — | No | Unsupported Technology | Unsupported Technology | Yes |
| OS-006 | Windows | SSHConnector (NotImplemented) | n/a | No | Connector Missing | Connector Missing | Yes |
| OS-007 | Windows | SSHConnector (NotImplemented) | n/a | No | Connector Missing | Connector Missing | Yes |
| PCI-001 | Windows | SSHConnector (NotImplemented) | n/a | No | Connector Missing | Connector Missing | Yes |
| PCI-002 | Unknown | — | — | No | Unsupported Technology | Unsupported Technology | Yes |
| PCI-003 | Oracle | DatabaseConnector (NotImplemented) | n/a | No | Connector Missing | Connector Missing | Yes |
| PCI-004 | Unknown | — | — | No | Unsupported Technology | Unsupported Technology | Yes |
| VAPT-001 | Unknown | — | — | No | Unsupported Technology | Unsupported Technology | Yes |
| VAPT-002 | Unknown | — | — | No | Unsupported Technology | Unsupported Technology | Yes |
| VAPT-003 | Unknown | — | — | No | Unsupported Technology | Unsupported Technology | Yes |

## Totals

| Status | Count |
|---|---|
| Ready (executable) | **6** |
| Configuration Required | **4** |
| Connector Missing | **6** |
| Unsupported Technology | **21** |
| Manual | 0 |
| **Total** | **37** |

## Demo guidance

- **Live execution demo:** use the 6 Ready controls (DB-001/002/003, OS-002, APP-001, APP-002). Ensure `psycopg2` is installed and the demo PostgreSQL/Docker targets are up for live evidence; otherwise execution degrades to a graceful structured error (no 500).
- **Capability storytelling:** the non-Ready statuses are accurate talking points (e.g. "Oracle/Windows connectors are a Phase-2 build → Connector Missing"; "21 controls need a technology mapping → Unsupported Technology").
