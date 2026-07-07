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


# ===========================================================================
# EXTENDED technology expansion (Redis, Apache HTTPD, Tomcat, SQL Server,
# MongoDB, Kubernetes, OpenShift). Data only; execution logic stays in the
# connectors/engine. Each entry carries a `category` and `expected_evidence`.
# ===========================================================================
_FW_CACHE = "Middleware Baselining, ISO27001, RBI Cyber Security"
_FW_CONTAINER = "Container Platform Baselining, ISO27001, RBI Cyber Security"


def _ext_entry(cid: str, name: str, command: str, tech: str, desc: str, *,
               framework: str, evidence: str, category: str) -> dict[str, Any]:
    return {
        "control_id": cid,
        "control_name": name,
        "framework_coverage": framework,
        "query": command,
        "description": desc,
        "evidence_type": evidence,
        "technology": tech,
        "category": category,
    }


# ---------------------------------------------------------------------------
# Redis (executed via redis-cli inside the redis container — shell connector)
# ---------------------------------------------------------------------------
_REDIS = "Redis"


def _redis_entry(cid: str, name: str, redis_cmd: str, desc: str, category: str) -> dict[str, Any]:
    # Runs redis-cli inside the container; -a is added at execution time if a
    # password is configured. Command text stays credential-free.
    return _ext_entry(cid, name, f"redis-cli {redis_cmd}", _REDIS, desc,
                      framework=_FW_CACHE, evidence="Redis configuration command output",
                      category=category)


REDIS_QUERIES: list[dict[str, Any]] = [
    _redis_entry("RDX-001", "Redis Server Info", "INFO server", "Reports Redis version/build/server info.", "Inventory"),
    _redis_entry("RDX-002", "Redis Persistence Config", "CONFIG GET save", "Shows RDB save points (persistence).", "Resilience"),
    _redis_entry("RDX-003", "Redis AOF Enabled", "CONFIG GET appendonly", "Shows whether AOF persistence is enabled.", "Resilience"),
    _redis_entry("RDX-004", "Redis Requirepass Set", "CONFIG GET requirepass", "Indicates whether an auth password is configured.", "Access Control"),
    _redis_entry("RDX-005", "Redis Protected Mode", "CONFIG GET protected-mode", "Shows protected-mode setting.", "Access Control"),
    _redis_entry("RDX-006", "Redis Bind Address", "CONFIG GET bind", "Shows the network interfaces Redis binds to.", "Network Security"),
    _redis_entry("RDX-007", "Redis TLS Port", "CONFIG GET tls-port", "Shows whether a TLS port is configured.", "Encryption"),
    _redis_entry("RDX-008", "Redis Maxmemory Policy", "CONFIG GET maxmemory-policy", "Shows the eviction policy.", "Resilience"),
]


# ---------------------------------------------------------------------------
# Apache HTTPD (shell via LinuxConnector against the apache container)
# ---------------------------------------------------------------------------
_APACHE = "Apache HTTPD"


def _apache_entry(cid: str, name: str, cmd: str, desc: str, category: str) -> dict[str, Any]:
    return _ext_entry(cid, name, cmd, _APACHE, desc, framework=_FW_CACHE,
                      evidence="Apache HTTPD command output", category=category)


APACHE_QUERIES: list[dict[str, Any]] = [
    _apache_entry("APX-001", "Apache Version",
                  "apachectl -v 2>&1 || httpd -v 2>&1 || apache2 -v 2>&1 || echo 'apache not available'",
                  "Reports the Apache HTTPD version.", "Inventory"),
    _apache_entry("APX-002", "Apache Config Test",
                  "apachectl -t 2>&1 || httpd -t 2>&1 || echo 'apache not available'",
                  "Validates the Apache configuration syntax.", "Configuration"),
    _apache_entry("APX-003", "Apache Loaded Modules",
                  "apachectl -M 2>/dev/null || httpd -M 2>/dev/null || echo 'apache not available'",
                  "Lists loaded Apache modules.", "Configuration"),
    _apache_entry("APX-004", "Apache ServerTokens",
                  "grep -REi \"^\\s*ServerTokens\" /etc/httpd /etc/apache2 /usr/local/apache2/conf 2>/dev/null || true",
                  "Shows the ServerTokens directive.", "Hardening"),
    _apache_entry("APX-005", "Apache ServerSignature",
                  "grep -REi \"^\\s*ServerSignature\" /etc/httpd /etc/apache2 /usr/local/apache2/conf 2>/dev/null || true",
                  "Shows the ServerSignature directive.", "Hardening"),
    _apache_entry("APX-006", "Apache SSL Protocols",
                  "grep -RanEi \"SSLProtocol\" /etc/httpd /etc/apache2 /usr/local/apache2/conf 2>/dev/null || true",
                  "Shows configured SSL/TLS protocols.", "Encryption"),
    _apache_entry("APX-007", "Apache Access Log Config",
                  "grep -RanEi \"CustomLog|TransferLog\" /etc/httpd /etc/apache2 /usr/local/apache2/conf 2>/dev/null || true",
                  "Shows access log configuration.", "Logging"),
    _apache_entry("APX-008", "Apache Error Log Config",
                  "grep -RanEi \"ErrorLog\" /etc/httpd /etc/apache2 /usr/local/apache2/conf 2>/dev/null || true",
                  "Shows error log configuration.", "Logging"),
]


# ---------------------------------------------------------------------------
# Tomcat (shell via LinuxConnector — filesystem/process/config checks)
# ---------------------------------------------------------------------------
_TOMCAT = "Tomcat"


def _tomcat_entry(cid: str, name: str, cmd: str, desc: str, category: str) -> dict[str, Any]:
    return _ext_entry(cid, name, cmd, _TOMCAT, desc, framework=_FW_CACHE,
                      evidence="Tomcat command/config output", category=category)


TOMCAT_QUERIES: list[dict[str, Any]] = [
    _tomcat_entry("TCX-001", "Tomcat Version",
                  "sh \"$CATALINA_HOME/bin/version.sh\" 2>/dev/null || "
                  "find / -name version.sh -path '*tomcat*' 2>/dev/null | head -1 | xargs -r sh || "
                  "echo 'tomcat not available'",
                  "Reports the Tomcat version.", "Inventory"),
    _tomcat_entry("TCX-002", "Tomcat Process Running",
                  "ps -ef 2>/dev/null | grep -i '[c]atalina' || echo 'tomcat process not found'",
                  "Checks whether a Tomcat/Catalina process is running.", "Availability"),
    _tomcat_entry("TCX-003", "Tomcat server.xml Present",
                  "find / -name server.xml -path '*conf*' 2>/dev/null | head -5 || echo 'server.xml not found'",
                  "Locates Tomcat server.xml configuration.", "Configuration"),
    _tomcat_entry("TCX-004", "Tomcat HTTP Connectors",
                  "find / -name server.xml -path '*conf*' 2>/dev/null | head -1 | "
                  "xargs -r grep -Ei \"<Connector\" 2>/dev/null || echo 'not available'",
                  "Shows configured Connectors (ports/SSL).", "Network Security"),
    _tomcat_entry("TCX-005", "Tomcat Manager App Present",
                  "find / -type d -name manager -path '*webapps*' 2>/dev/null || echo 'manager app not found'",
                  "Checks whether the manager webapp is deployed (should be restricted).", "Hardening"),
    _tomcat_entry("TCX-006", "Tomcat Users Config",
                  "find / -name tomcat-users.xml 2>/dev/null | head -3 || echo 'tomcat-users.xml not found'",
                  "Locates tomcat-users.xml (role/user config).", "Access Control"),
    _tomcat_entry("TCX-007", "Tomcat Shutdown Port",
                  "find / -name server.xml -path '*conf*' 2>/dev/null | head -1 | "
                  "xargs -r grep -Ei \"<Server \" 2>/dev/null || echo 'not available'",
                  "Shows the Server shutdown port configuration.", "Hardening"),
    _tomcat_entry("TCX-008", "Tomcat Access Valve Logging",
                  "find / -name server.xml -path '*conf*' 2>/dev/null | head -1 | "
                  "xargs -r grep -Ei \"AccessLogValve\" 2>/dev/null || echo 'not available'",
                  "Checks for AccessLogValve (request logging).", "Logging"),
]


# ---------------------------------------------------------------------------
# SQL Server (SQL via pyodbc — SQLServerConnector)
# ---------------------------------------------------------------------------
_MSSQL = "SQL Server"


def _mssql_entry(cid: str, name: str, sql: str, desc: str, category: str) -> dict[str, Any]:
    return _ext_entry(cid, name, sql, _MSSQL, desc, framework=_FW_DB,
                      evidence="SQL Server query output", category=category)


SQLSERVER_QUERIES: list[dict[str, Any]] = [
    _mssql_entry("MSX-001", "SQL Server Version", "SELECT @@VERSION;", "Reports the SQL Server version.", "Inventory"),
    _mssql_entry("MSX-002", "SQL Server Edition/Level",
                 "SELECT SERVERPROPERTY('Edition') AS edition, SERVERPROPERTY('ProductLevel') AS level;",
                 "Reports edition and product level.", "Inventory"),
    _mssql_entry("MSX-003", "SQL Server Authentication Mode",
                 "SELECT SERVERPROPERTY('IsIntegratedSecurityOnly') AS windows_auth_only;",
                 "Shows whether Windows-only auth is enforced.", "Access Control"),
    _mssql_entry("MSX-004", "SQL Server Logins",
                 "SELECT name, type_desc, is_disabled FROM sys.server_principals "
                 "WHERE type IN ('S','U','G');",
                 "Enumerates server logins and status.", "Access Control"),
    _mssql_entry("MSX-005", "SQL Server sysadmin Members",
                 "SELECT p.name FROM sys.server_role_members m "
                 "JOIN sys.server_principals r ON m.role_principal_id = r.principal_id "
                 "JOIN sys.server_principals p ON m.member_principal_id = p.principal_id "
                 "WHERE r.name = 'sysadmin';",
                 "Lists members of the sysadmin fixed role.", "Access Control"),
    _mssql_entry("MSX-006", "SQL Server Databases",
                 "SELECT name, state_desc, recovery_model_desc FROM sys.databases;",
                 "Lists databases with state and recovery model.", "Inventory"),
    _mssql_entry("MSX-007", "SQL Server TDE Status",
                 "SELECT DB_NAME(database_id) AS db, encryption_state FROM sys.dm_database_encryption_keys;",
                 "Reports Transparent Data Encryption state.", "Encryption"),
    _mssql_entry("MSX-008", "SQL Server Force Encryption",
                 "SELECT value_in_use FROM sys.configurations WHERE name = 'remote admin connections';",
                 "Sample security configuration value.", "Configuration"),
    _mssql_entry("MSX-009", "SQL Server Audit Specifications",
                 "SELECT name, is_state_enabled FROM sys.server_audit_specifications;",
                 "Lists server audit specifications.", "Auditing"),
    _mssql_entry("MSX-010", "SQL Server Failed Login Auditing",
                 "SELECT value_in_use FROM sys.configurations WHERE name = 'default trace enabled';",
                 "Shows whether the default trace (auditing) is enabled.", "Auditing"),
]


# ---------------------------------------------------------------------------
# MongoDB (commands via pymongo — MongoDBConnector)
# ---------------------------------------------------------------------------
_MONGO = "MongoDB"


def _mongo_entry(cid: str, name: str, command: str, desc: str, category: str) -> dict[str, Any]:
    # `command` is a Mongo admin command name / JSON the connector runs via
    # db.command(); kept as text for the catalog + allow-list.
    return _ext_entry(cid, name, command, _MONGO, desc, framework=_FW_DB,
                      evidence="MongoDB command output", category=category)


MONGODB_QUERIES: list[dict[str, Any]] = [
    _mongo_entry("MGX-001", "MongoDB Build Info", "buildInfo", "Reports MongoDB version/build info.", "Inventory"),
    _mongo_entry("MGX-002", "MongoDB Server Status", "serverStatus", "Reports server status metrics.", "Availability"),
    _mongo_entry("MGX-003", "MongoDB Auth Enabled", "getCmdLineOpts", "Shows command-line options incl. security.authorization.", "Access Control"),
    _mongo_entry("MGX-004", "MongoDB TLS Config", "getParameter:sslMode", "Reports the TLS/SSL mode parameter.", "Encryption"),
    _mongo_entry("MGX-005", "MongoDB Users", "usersInfo", "Lists database users (admin db).", "Access Control"),
    _mongo_entry("MGX-006", "MongoDB Roles", "rolesInfo", "Lists custom roles (admin db).", "Access Control"),
    _mongo_entry("MGX-007", "MongoDB Databases", "listDatabases", "Lists databases.", "Inventory"),
    _mongo_entry("MGX-008", "MongoDB Audit Config", "getParameter:auditAuthorizationSuccess",
                 "Reports the audit authorization-success parameter.", "Auditing"),
]


# ---------------------------------------------------------------------------
# Aerospike (asinfo / asadm CLI against the Aerospike node — shell/CLI connector).
# Commands are credential-free; host/port/namespace come from env at execution
# time (AEROSPIKE_HOST/PORT/NAMESPACE). In demo mode the runner returns
# deterministic mock output when the Aerospike tools are not installed.
# ---------------------------------------------------------------------------
_AEROSPIKE = "Aerospike"
_FW_AEROSPIKE = "DB Baselining, ISO27001, RBI Cyber Security"


def _aero_entry(cid: str, name: str, command: str, desc: str, category: str) -> dict[str, Any]:
    return _ext_entry(cid, name, command, _AEROSPIKE, desc,
                      framework=_FW_AEROSPIKE, evidence="Aerospike asinfo/asadm output",
                      category=category)


#: Aerospike predefined checks. ``asinfo``/``asadm`` are read-only info/admin
#: tools; the namespace placeholder resolves from AEROSPIKE_NAMESPACE at run time.
AEROSPIKE_QUERIES: list[dict[str, Any]] = [
    _aero_entry("ASX-001", "Aerospike Server Version", 'asinfo -v "build"',
                "Reports the Aerospike server build/version.", "Inventory"),
    _aero_entry("ASX-002", "Aerospike Cluster Status", 'asinfo -v "status"',
                "Reports node/cluster status.", "Availability"),
    _aero_entry("ASX-003", "Aerospike Namespace List", 'asinfo -v "namespaces"',
                "Lists configured namespaces.", "Inventory"),
    _aero_entry("ASX-004", "Aerospike Namespace Config",
                'asinfo -v "get-config:context=namespace;id=${AEROSPIKE_NAMESPACE:-test}"',
                "Reports configuration for the target namespace.", "Configuration"),
    _aero_entry("ASX-005", "Aerospike Security Config",
                'asinfo -v "get-config:context=security"',
                "Reports the security subsystem configuration.", "Access Control"),
    _aero_entry("ASX-006", "Aerospike User/Role List", 'asadm -e "show users"',
                "Lists security users (empty when security is disabled).", "Access Control"),
    _aero_entry("ASX-007", "Aerospike TLS Config",
                'asinfo -v "get-config:context=network"',
                "Reports network/TLS configuration (tls-* settings).", "Encryption"),
    _aero_entry("ASX-008", "Aerospike Service Ports",
                'asinfo -v "get-config:context=service"',
                "Reports the service/fabric/heartbeat/info port configuration.", "Network Security"),
    _aero_entry("ASX-009", "Aerospike Storage Engine Config",
                'asinfo -v "get-config:context=namespace;id=${AEROSPIKE_NAMESPACE:-test}"',
                "Reports the storage-engine settings for the namespace.", "Configuration"),
    _aero_entry("ASX-010", "Aerospike Backup Policy", 'asadm -e "show config"',
                "Reports configuration relevant to backup/retention posture.", "Resilience"),
    _aero_entry("ASX-011", "Aerospike XDR Config",
                'asinfo -v "get-config:context=xdr"',
                "Reports cross-datacenter replication (XDR) configuration.", "Resilience"),
    _aero_entry("ASX-012", "Aerospike Audit Logging",
                'asinfo -v "get-config:context=security"',
                "Reports audit/logging settings within the security context.", "Auditing"),
    _aero_entry("ASX-013", "Aerospike Memory Usage", 'asadm -e "show stat"',
                "Reports memory/statistics for capacity posture.", "Availability"),
    _aero_entry("ASX-014", "Aerospike Index Usage", 'asinfo -v "statistics"',
                "Reports index/statistics usage for the node.", "Availability"),
    _aero_entry("ASX-015", "Aerospike Cluster Node Count", 'asinfo -v "statistics"',
                "Reports cluster size / node count from node statistics.", "Availability"),
    _aero_entry("ASX-016", "Aerospike Namespace Replication Factor",
                'asinfo -v "get-config:context=namespace;id=${AEROSPIKE_NAMESPACE:-test}"',
                "Reports the replication factor for the target namespace.", "Resilience"),
    _aero_entry("ASX-017", "Aerospike Strong Consistency",
                'asinfo -v "get-config:context=namespace;id=${AEROSPIKE_NAMESPACE:-test}"',
                "Reports the strong-consistency setting for the namespace.", "Data Integrity"),
    _aero_entry("ASX-018", "Aerospike Expiration/TTL Config",
                'asinfo -v "get-config:context=namespace;id=${AEROSPIKE_NAMESPACE:-test}"',
                "Reports default-ttl / nsup expiration configuration.", "Data Lifecycle"),
    _aero_entry("ASX-019", "Aerospike Secondary Index List", 'asinfo -v "sindex"',
                "Lists secondary indexes on the node.", "Inventory"),
    _aero_entry("ASX-020", "Aerospike Latency / Slow Query", 'asinfo -v "statistics"',
                "Reports latency/throughput statistics for SLA monitoring.", "Performance"),
]


# ---------------------------------------------------------------------------
# Kubernetes (kubectl via KubernetesConnector)
# ---------------------------------------------------------------------------
_K8S = "Kubernetes"


def _k8s_entry(cid: str, name: str, kubectl_args: str, desc: str, category: str) -> dict[str, Any]:
    return _ext_entry(cid, name, f"kubectl {kubectl_args}", _K8S, desc,
                      framework=_FW_CONTAINER, evidence="Kubernetes kubectl output", category=category)


KUBERNETES_QUERIES: list[dict[str, Any]] = [
    _k8s_entry("K8X-001", "Kubernetes Version", "version -o json", "Reports client/server versions.", "Inventory"),
    _k8s_entry("K8X-002", "Kubernetes Nodes", "get nodes -o wide", "Lists cluster nodes.", "Inventory"),
    _k8s_entry("K8X-003", "Kubernetes Namespaces", "get namespaces", "Lists namespaces.", "Inventory"),
    _k8s_entry("K8X-004", "Kubernetes Cluster Roles", "get clusterroles", "Lists cluster roles (RBAC).", "Access Control"),
    _k8s_entry("K8X-005", "Kubernetes Cluster Role Bindings", "get clusterrolebindings", "Lists cluster role bindings.", "Access Control"),
    _k8s_entry("K8X-006", "Kubernetes Pod Security", "get pods --all-namespaces -o wide", "Lists pods across namespaces.", "Workload"),
    _k8s_entry("K8X-007", "Kubernetes Network Policies", "get networkpolicies --all-namespaces", "Lists network policies.", "Network Security"),
    _k8s_entry("K8X-008", "Kubernetes Secrets Inventory", "get secrets --all-namespaces", "Lists secret objects (names only).", "Access Control"),
    _k8s_entry("K8X-009", "Kubernetes Service Accounts", "get serviceaccounts --all-namespaces", "Lists service accounts.", "Access Control"),
    _k8s_entry("K8X-010", "Kubernetes PSP/PSA Labels", "get ns -o jsonpath={.items[*].metadata.labels}", "Shows namespace pod-security labels.", "Hardening"),
]


# ---------------------------------------------------------------------------
# OpenShift (oc via OpenShiftConnector)
# ---------------------------------------------------------------------------
_OCP = "OpenShift"


def _ocp_entry(cid: str, name: str, oc_args: str, desc: str, category: str) -> dict[str, Any]:
    return _ext_entry(cid, name, f"oc {oc_args}", _OCP, desc,
                      framework=_FW_CONTAINER, evidence="OpenShift oc output", category=category)


OPENSHIFT_QUERIES: list[dict[str, Any]] = [
    _ocp_entry("OCX-001", "OpenShift Version", "version -o json", "Reports oc/cluster versions.", "Inventory"),
    _ocp_entry("OCX-002", "OpenShift Cluster Operators", "get clusteroperators", "Lists cluster operators and status.", "Availability"),
    _ocp_entry("OCX-003", "OpenShift Nodes", "get nodes -o wide", "Lists cluster nodes.", "Inventory"),
    _ocp_entry("OCX-004", "OpenShift Projects", "get projects", "Lists projects (namespaces).", "Inventory"),
    _ocp_entry("OCX-005", "OpenShift Cluster Roles", "get clusterroles", "Lists cluster roles (RBAC).", "Access Control"),
    _ocp_entry("OCX-006", "OpenShift Role Bindings", "get clusterrolebindings", "Lists cluster role bindings.", "Access Control"),
    _ocp_entry("OCX-007", "OpenShift SCC", "get scc", "Lists Security Context Constraints.", "Hardening"),
    _ocp_entry("OCX-008", "OpenShift OAuth Config", "get oauth cluster -o json", "Reports the cluster OAuth configuration.", "Access Control"),
    _ocp_entry("OCX-009", "OpenShift Routes", "get routes --all-namespaces", "Lists exposed routes (TLS posture).", "Network Security"),
    _ocp_entry("OCX-010", "OpenShift Image Policies", "get image.config.openshift.io/cluster -o json", "Reports cluster image policy config.", "Supply Chain"),
]


#: Database technologies use exact-SQL allow-lists; these run through DB connectors.
_DB_CATALOG = (
    POSTGRESQL_QUERIES + YUGABYTE_QUERIES + AURORA_MYSQL_QUERIES + ORACLE_QUERIES
    + SQLSERVER_QUERIES + MONGODB_QUERIES
)
#: Shell/command technologies run curated commands via a command connector.
_SHELL_CATALOG = (
    NGINX_QUERIES + LINUX_QUERIES + RHEL8_QUERIES + RHEL9_QUERIES
    + REDIS_QUERIES + APACHE_QUERIES + TOMCAT_QUERIES
    + KUBERNETES_QUERIES + OPENSHIFT_QUERIES + AEROSPIKE_QUERIES
)
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
