"""Supplementary predefined-query catalog (code-defined, additive).

The primary control library is an Excel workbook
(``ECS_Query_Driven_Control_Library_Consolidated.xlsx``) loaded by
``predefined_queries_engine``. This module adds SUPPLEMENTARY database queries
for PostgreSQL, YugabyteDB, and Aurora MySQL that extend coverage without
touching the binary Excel file.

Design:
  * Catalog is DATA ONLY — no execution logic lives here (execution stays in the
    connectors / engine). This keeps the query catalog separate from execution.
  * Entries are merged into the loaded controls by ``predefined_queries_engine``.
    Excel entries always win on ``control_id`` collision, so this file is purely
    additive and never overrides the workbook.
  * ``technology`` is stated explicitly here (the engine's text-based detection is
    a fallback for Excel rows that omit it).
  * No credentials, IPs, or endpoints are stored here — only SQL text and metadata.

Each entry:
    {
        "control_id":         str,   # unique id, e.g. "PGX-001"
        "control_name":       str,
        "framework_coverage": str,   # comma-separated framework names
        "query":              str,   # SQL text
        "description":        str,
        "evidence_type":      str,
        "technology":         str,   # "PostgreSQL" | "YugabyteDB" | "Aurora MySQL"
    }
"""

from __future__ import annotations

from typing import Any

_FW_DB = "DB Baselining, ISO27001, RBI Cyber Security"


def _entry(cid: str, name: str, query: str, tech: str, desc: str) -> dict[str, Any]:
    return {
        "control_id": cid,
        "control_name": name,
        "framework_coverage": _FW_DB,
        "query": query,
        "description": desc,
        "evidence_type": "Database configuration query output",
        "technology": tech,
    }


# ---------------------------------------------------------------------------
# PostgreSQL supplementary queries
# ---------------------------------------------------------------------------
POSTGRESQL_QUERIES: list[dict[str, Any]] = [
    _entry("PGX-001", "PostgreSQL SSL Enabled", "SHOW ssl;", "PostgreSQL",
           "Confirms whether SSL/TLS is enabled on the PostgreSQL server."),
    _entry("PGX-002", "PostgreSQL Password Encryption", "SHOW password_encryption;", "PostgreSQL",
           "Reports the password hashing algorithm (e.g. scram-sha-256)."),
    _entry("PGX-003", "PostgreSQL Replication Status", "SELECT * FROM pg_stat_replication;", "PostgreSQL",
           "Lists active replication connections and their state."),
    _entry("PGX-004", "PostgreSQL User Privileges",
           "SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolcanlogin FROM pg_roles;", "PostgreSQL",
           "Enumerates roles and their high-level privilege attributes."),
    _entry("PGX-005", "PostgreSQL Database Sizes",
           "SELECT datname, pg_database_size(datname) AS size_bytes FROM pg_database;", "PostgreSQL",
           "Reports on-disk size of each database."),
    _entry("PGX-006", "PostgreSQL Active Sessions",
           "SELECT datname, usename, application_name, client_addr, state FROM pg_stat_activity;", "PostgreSQL",
           "Lists current sessions with client address and state."),
    _entry("PGX-007", "PostgreSQL Installed Extensions",
           "SELECT extname, extversion FROM pg_extension;", "PostgreSQL",
           "Enumerates installed extensions and versions."),
    _entry("PGX-008", "PostgreSQL Audit Extension Check",
           "SELECT extname FROM pg_extension WHERE extname IN ('pgaudit');", "PostgreSQL",
           "Checks whether the pgaudit auditing extension is installed."),
]


# ---------------------------------------------------------------------------
# YugabyteDB (YSQL) supplementary queries
# ---------------------------------------------------------------------------
YUGABYTE_QUERIES: list[dict[str, Any]] = [
    _entry("YBX-001", "YugabyteDB Cluster Servers", "SELECT * FROM yb_servers();", "YugabyteDB",
           "Lists cluster nodes reported by the YugabyteDB yb_servers() function."),
    _entry("YBX-002", "YugabyteDB Version", "SELECT version();", "YugabyteDB",
           "Reports the YugabyteDB / PostgreSQL-compatible version banner."),
    _entry("YBX-003", "YugabyteDB Active Sessions",
           "SELECT datname, usename, application_name, client_addr, state FROM pg_stat_activity;", "YugabyteDB",
           "Lists current YSQL sessions with client address and state."),
    _entry("YBX-004", "YugabyteDB User Privileges",
           "SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolcanlogin FROM pg_roles;", "YugabyteDB",
           "Enumerates roles and their high-level privilege attributes."),
    _entry("YBX-005", "YugabyteDB Database Sizes",
           "SELECT datname, pg_database_size(datname) AS size_bytes FROM pg_database;", "YugabyteDB",
           "Reports on-disk size of each database."),
    _entry("YBX-006", "YugabyteDB Table List",
           "SELECT schemaname, tablename, tableowner FROM pg_tables "
           "WHERE schemaname NOT IN ('pg_catalog', 'information_schema');", "YugabyteDB",
           "Lists user tables (excluding catalog schemas)."),
    _entry("YBX-007", "YugabyteDB Extensions",
           "SELECT extname, extversion FROM pg_extension;", "YugabyteDB",
           "Enumerates installed extensions and versions."),
    _entry("YBX-008", "YugabyteDB SSL Check", "SHOW ssl;", "YugabyteDB",
           "Confirms whether SSL/TLS is enabled on the YSQL endpoint."),
]


# ---------------------------------------------------------------------------
# Aurora MySQL supplementary queries
# ---------------------------------------------------------------------------
_FW_MYSQL = "DB Baselining, ISO27001, RBI Cyber Security"

AURORA_MYSQL_QUERIES: list[dict[str, Any]] = [
    _entry("MYX-001", "Aurora MySQL SSL Status", "SHOW VARIABLES LIKE 'have_ssl';", "Aurora MySQL",
           "Reports whether the server supports SSL."),
    _entry("MYX-002", "Aurora MySQL Secure Transport",
           "SHOW VARIABLES LIKE 'require_secure_transport';", "Aurora MySQL",
           "Reports whether secure transport (TLS) is required for connections."),
    _entry("MYX-003", "Aurora MySQL Binary Logging", "SHOW VARIABLES LIKE 'log_bin';", "Aurora MySQL",
           "Reports whether binary logging is enabled."),
    _entry("MYX-004", "Aurora MySQL Audit Variables",
           "SHOW VARIABLES LIKE 'server_audit%';", "Aurora MySQL",
           "Reports server audit plugin variables (if the audit plugin is loaded)."),
    _entry("MYX-005", "Aurora MySQL Users",
           "SELECT user, host, plugin FROM mysql.user;", "Aurora MySQL",
           "Enumerates database accounts and their authentication plugin."),
    _entry("MYX-006", "Aurora MySQL Version", "SELECT VERSION();", "Aurora MySQL",
           "Reports the MySQL/Aurora server version."),
    _entry("MYX-007", "Aurora MySQL Databases", "SHOW DATABASES;", "Aurora MySQL",
           "Lists databases visible to the connecting user."),
    _entry("MYX-008", "Aurora MySQL Process List", "SHOW PROCESSLIST;", "Aurora MySQL",
           "Lists current server threads/connections."),
    _entry("MYX-009", "Aurora MySQL Grants Summary",
           "SELECT user, host, select_priv, insert_priv, update_priv, delete_priv, "
           "create_priv, drop_priv, super_priv FROM mysql.user;", "Aurora MySQL",
           "Summarises global privilege flags per account."),
    _entry("MYX-010", "Aurora MySQL TLS Config", "SHOW VARIABLES LIKE '%ssl%';", "Aurora MySQL",
           "Reports all SSL/TLS-related server variables."),
]


def supplementary_controls() -> list[dict[str, Any]]:
    """Return all supplementary DB query definitions (deep-ish copies)."""
    combined = POSTGRESQL_QUERIES + YUGABYTE_QUERIES + AURORA_MYSQL_QUERIES
    return [dict(entry) for entry in combined]


#: control_id -> exact SQL, used by the engine's allow-list for live execution.
SUPPLEMENTARY_QUERY_BY_ID: dict[str, str] = {
    entry["control_id"]: entry["query"]
    for entry in (POSTGRESQL_QUERIES + YUGABYTE_QUERIES + AURORA_MYSQL_QUERIES)
}
