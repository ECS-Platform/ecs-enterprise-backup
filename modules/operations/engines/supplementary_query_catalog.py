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


# ---------------------------------------------------------------------------
# Non-database (infrastructure) supplementary checks — Oracle, NGINX, Linux, RHEL
# ---------------------------------------------------------------------------
_FW_OS = "OS Baselining, ISO27001, RBI Cyber Security"
_FW_MW = "Middleware Baselining, ISO27001, RBI Cyber Security"


def _infra_entry(cid: str, name: str, command: str, tech: str, desc: str,
                 framework: str, evidence: str) -> dict[str, Any]:
    return {
        "control_id": cid,
        "control_name": name,
        "framework_coverage": framework,
        "query": command,
        "description": desc,
        "evidence_type": evidence,
        "technology": tech,
    }


def _os_entry(cid: str, name: str, command: str, tech: str, desc: str) -> dict[str, Any]:
    return _infra_entry(cid, name, command, tech, desc, _FW_OS, "OS configuration command output")


# ---------------------------------------------------------------------------
# Oracle Database supplementary queries (SQL via python-oracledb)
# ---------------------------------------------------------------------------
ORACLE_QUERIES: list[dict[str, Any]] = [
    _entry("ORX-001", "Oracle Version", "SELECT * FROM v$version;", "Oracle",
           "Reports the Oracle Database version banner."),
    _entry("ORX-002", "Oracle Database Open Mode",
           "SELECT name, open_mode, database_role FROM v$database;", "Oracle",
           "Reports database name, open mode, and role."),
    _entry("ORX-003", "Oracle Encryption Wallet Status",
           "SELECT wallet_type, status, wallet_order FROM v$encryption_wallet;", "Oracle",
           "Reports TDE wallet type/status/order."),
    _entry("ORX-004", "Oracle Audit Trail Setting",
           "SELECT name, value FROM v$parameter WHERE name = 'audit_trail';", "Oracle",
           "Reports the audit_trail configuration parameter."),
    _entry("ORX-005", "Oracle Failed Login Profile Settings",
           "SELECT profile, resource_name, limit FROM dba_profiles WHERE resource_name IN "
           "('FAILED_LOGIN_ATTEMPTS','PASSWORD_LOCK_TIME','PASSWORD_LIFE_TIME');", "Oracle",
           "Reports password/lockout policy limits per profile."),
    _entry("ORX-006", "Oracle Privileged Users",
           "SELECT username, account_status, common, oracle_maintained FROM dba_users WHERE "
           "username IN ('SYS','SYSTEM') OR account_status <> 'OPEN';", "Oracle",
           "Lists privileged/locked accounts."),
    _entry("ORX-007", "Oracle Roles Granted To Users",
           "SELECT grantee, granted_role, admin_option, default_role FROM dba_role_privs;", "Oracle",
           "Enumerates role grants and admin option."),
    _entry("ORX-008", "Oracle Tablespace Usage",
           "SELECT tablespace_name, status, contents FROM dba_tablespaces;", "Oracle",
           "Lists tablespaces with status and contents."),
    _entry("ORX-009", "Oracle Datafile Encryption Status",
           "SELECT tablespace_name, encrypted FROM dba_tablespaces;", "Oracle",
           "Reports per-tablespace encryption status."),
    _entry("ORX-010", "Oracle Active Sessions",
           "SELECT username, status, machine, program FROM v$session WHERE username IS NOT NULL;", "Oracle",
           "Lists active non-background sessions."),
]


# ---------------------------------------------------------------------------
# NGINX supplementary checks (shell via docker exec against an NGINX container)
# ---------------------------------------------------------------------------
_NGINX = "NGINX"
NGINX_QUERIES: list[dict[str, Any]] = [
    _infra_entry("NGX-001", "NGINX Version", "nginx -v 2>&1", _NGINX,
                 "Reports the NGINX version.", _FW_MW, "Middleware command output"),
    _infra_entry("NGX-002", "NGINX Config Test", "nginx -t 2>&1", _NGINX,
                 "Validates the NGINX configuration syntax.", _FW_MW, "Middleware command output"),
    _infra_entry("NGX-003", "NGINX TLS Protocol Configuration",
                 "grep -R \"ssl_protocols\" /etc/nginx /etc/nginx/conf.d 2>/dev/null || true", _NGINX,
                 "Shows configured TLS protocols.", _FW_MW, "Middleware command output"),
    _infra_entry("NGX-004", "NGINX TLS Cipher Configuration",
                 "grep -R \"ssl_ciphers\" /etc/nginx /etc/nginx/conf.d 2>/dev/null || true", _NGINX,
                 "Shows configured TLS ciphers.", _FW_MW, "Middleware command output"),
    _infra_entry("NGX-005", "NGINX Server Tokens Disabled",
                 "grep -R \"server_tokens\" /etc/nginx /etc/nginx/conf.d 2>/dev/null || true", _NGINX,
                 "Checks whether server_tokens is disabled.", _FW_MW, "Middleware command output"),
    _infra_entry("NGX-006", "NGINX Access Log Configuration",
                 "grep -R \"access_log\" /etc/nginx /etc/nginx/conf.d 2>/dev/null || true", _NGINX,
                 "Shows access_log configuration.", _FW_MW, "Middleware command output"),
    _infra_entry("NGX-007", "NGINX Error Log Configuration",
                 "grep -R \"error_log\" /etc/nginx /etc/nginx/conf.d 2>/dev/null || true", _NGINX,
                 "Shows error_log configuration.", _FW_MW, "Middleware command output"),
    _infra_entry("NGX-008", "NGINX Enabled Sites",
                 "find /etc/nginx/sites-enabled /etc/nginx/conf.d -maxdepth 2 -type f 2>/dev/null", _NGINX,
                 "Lists enabled site/config files.", _FW_MW, "Middleware command output"),
]


# ---------------------------------------------------------------------------
# Linux generic supplementary checks (shell via docker exec)
# ---------------------------------------------------------------------------
_LNX = "Linux"
LINUX_QUERIES: list[dict[str, Any]] = [
    _os_entry("LNX-001", "Linux OS Release", "cat /etc/os-release", _LNX,
              "Reports OS distribution and version."),
    _os_entry("LNX-002", "Linux Kernel Version", "uname -a", _LNX,
              "Reports kernel version and architecture."),
    _os_entry("LNX-003", "Linux Running Services",
              "systemctl list-units --type=service --state=running --no-pager 2>/dev/null || "
              "service --status-all 2>/dev/null || true", _LNX,
              "Lists running services."),
    _os_entry("LNX-004", "Linux Firewall Status",
              "systemctl is-active firewalld 2>/dev/null || ufw status 2>/dev/null || true", _LNX,
              "Reports host firewall status."),
    _os_entry("LNX-005", "Linux SSH Root Login Setting",
              "grep -Ei \"^\\s*PermitRootLogin\" /etc/ssh/sshd_config 2>/dev/null || true", _LNX,
              "Shows the PermitRootLogin sshd setting."),
    _os_entry("LNX-006", "Linux Password Authentication Setting",
              "grep -Ei \"^\\s*PasswordAuthentication\" /etc/ssh/sshd_config 2>/dev/null || true", _LNX,
              "Shows the PasswordAuthentication sshd setting."),
    _os_entry("LNX-007", "Linux Sudoers Configuration",
              "grep -R \"ALL=\" /etc/sudoers /etc/sudoers.d 2>/dev/null || true", _LNX,
              "Shows sudoers ALL= grants."),
    _os_entry("LNX-008", "Linux Local Users", "cut -d: -f1,3,7 /etc/passwd", _LNX,
              "Lists local users (name, uid, shell)."),
]


# ---------------------------------------------------------------------------
# Red Hat Enterprise Linux 8.x supplementary checks
# ---------------------------------------------------------------------------
_RHEL8 = "Red Hat Enterprise Linux 8.x"
RHEL8_QUERIES: list[dict[str, Any]] = [
    _os_entry("RH8-001", "RHEL 8 Version Check", "cat /etc/redhat-release", _RHEL8,
              "Reports the RHEL release string."),
    _os_entry("RH8-002", "RHEL 8 Crypto Policy",
              "update-crypto-policies --show 2>/dev/null || true", _RHEL8,
              "Reports the system-wide crypto policy."),
    _os_entry("RH8-003", "RHEL 8 SELinux Status",
              "getenforce 2>/dev/null || sestatus 2>/dev/null || true", _RHEL8,
              "Reports SELinux enforcement status."),
    _os_entry("RH8-004", "RHEL 8 Firewalld Status",
              "systemctl is-active firewalld 2>/dev/null || true", _RHEL8,
              "Reports firewalld active status."),
    _os_entry("RH8-005", "RHEL 8 Auditd Status",
              "systemctl is-active auditd 2>/dev/null || true", _RHEL8,
              "Reports auditd active status."),
    _os_entry("RH8-006", "RHEL 8 SSH PermitRootLogin",
              "grep -Ei \"^\\s*PermitRootLogin\" /etc/ssh/sshd_config 2>/dev/null || true", _RHEL8,
              "Shows the PermitRootLogin sshd setting."),
    _os_entry("RH8-007", "RHEL 8 Password Authentication",
              "grep -Ei \"^\\s*PasswordAuthentication\" /etc/ssh/sshd_config 2>/dev/null || true", _RHEL8,
              "Shows the PasswordAuthentication sshd setting."),
    _os_entry("RH8-008", "RHEL 8 Installed Security Updates",
              "dnf updateinfo list security installed 2>/dev/null || "
              "yum updateinfo list security installed 2>/dev/null || true", _RHEL8,
              "Lists installed security updates."),
]


# ---------------------------------------------------------------------------
# Red Hat Enterprise Linux 9.x supplementary checks
# ---------------------------------------------------------------------------
_RHEL9 = "Red Hat Enterprise Linux 9.x"
RHEL9_QUERIES: list[dict[str, Any]] = [
    _os_entry("RH9-001", "RHEL 9 Version Check", "cat /etc/redhat-release", _RHEL9,
              "Reports the RHEL release string."),
    _os_entry("RH9-002", "RHEL 9 Crypto Policy",
              "update-crypto-policies --show 2>/dev/null || true", _RHEL9,
              "Reports the system-wide crypto policy."),
    _os_entry("RH9-003", "RHEL 9 SELinux Status",
              "getenforce 2>/dev/null || sestatus 2>/dev/null || true", _RHEL9,
              "Reports SELinux enforcement status."),
    _os_entry("RH9-004", "RHEL 9 Firewalld Status",
              "systemctl is-active firewalld 2>/dev/null || true", _RHEL9,
              "Reports firewalld active status."),
    _os_entry("RH9-005", "RHEL 9 Auditd Status",
              "systemctl is-active auditd 2>/dev/null || true", _RHEL9,
              "Reports auditd active status."),
    _os_entry("RH9-006", "RHEL 9 SSH PermitRootLogin",
              "grep -Ei \"^\\s*PermitRootLogin\" /etc/ssh/sshd_config 2>/dev/null || true", _RHEL9,
              "Shows the PermitRootLogin sshd setting."),
    _os_entry("RH9-007", "RHEL 9 Password Authentication",
              "grep -Ei \"^\\s*PasswordAuthentication\" /etc/ssh/sshd_config 2>/dev/null || true", _RHEL9,
              "Shows the PasswordAuthentication sshd setting."),
    _os_entry("RH9-008", "RHEL 9 FIPS Mode",
              "fips-mode-setup --check 2>/dev/null || cat /proc/sys/crypto/fips_enabled 2>/dev/null || true", _RHEL9,
              "Reports FIPS mode status."),
]


#: Database technologies use exact-SQL allow-lists; these run through DB connectors.
_DB_CATALOG = POSTGRESQL_QUERIES + YUGABYTE_QUERIES + AURORA_MYSQL_QUERIES + ORACLE_QUERIES
#: Shell technologies run curated commands via the docker-exec Linux connector.
_SHELL_CATALOG = NGINX_QUERIES + LINUX_QUERIES + RHEL8_QUERIES + RHEL9_QUERIES
_ALL_CATALOG = _DB_CATALOG + _SHELL_CATALOG


def supplementary_controls() -> list[dict[str, Any]]:
    """Return all supplementary query definitions (deep-ish copies)."""
    return [dict(entry) for entry in _ALL_CATALOG]


#: control_id -> exact query/command, used by the engine's allow-list for live execution.
SUPPLEMENTARY_QUERY_BY_ID: dict[str, str] = {
    entry["control_id"]: entry["query"] for entry in _ALL_CATALOG
}

#: control_ids whose execution is a shell command (via the Linux connector),
#: as opposed to a SQL query via a database connector.
SHELL_CONTROL_IDS: frozenset[str] = frozenset(e["control_id"] for e in _SHELL_CATALOG)
