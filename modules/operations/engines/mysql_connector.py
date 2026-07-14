"""Aurora MySQL (MySQL-wire) connector for predefined query execution.

Uses PyMySQL (pure-Python, matching the project's dependency style — no system
libraries required). Aurora MySQL is AWS-managed; locally this same connector
validates against a MySQL 8-compatible container. Results are normalised to the
identical ``ConnectorResult`` + pipe-delimited text used by the PostgreSQL
connector, so downstream audit / evidence / API handling is unchanged.

Read-only, credential-externalised, never logs passwords.
"""

from __future__ import annotations

import os
import time
from typing import Any

from modules.operations.engines.postgresql_connector import _clean, _safe_int
from modules.operations.engines.query_connectors import ConnectorResult

DEFAULT_TIMEOUT_SEC = 30
DEFAULT_MYSQL_PORT = 3306

_TRUTHY = {"1", "true", "yes", "on", "require", "required"}


def _as_bool(value: Any) -> bool:
    if value is None:
        return False
    s = str(value).strip().lower()
    if s.startswith("${"):  # unresolved placeholder -> default off
        return False
    return s in _TRUTHY


def get_mysql_config() -> dict[str, Any]:
    """Aurora MySQL target for predefined query execution.

    Resolution order per field: active-environment YAML
    (predefined_query_targets.aurora_mysql) -> ECS_MYSQL_* env var -> default.
    Endpoints/credentials are never hard-coded; production values come from env.
    """
    from modules.operations.engines.query_connectors import get_predefined_target

    cfg = get_predefined_target("aurora_mysql")
    password_env = str(cfg.get("password_env") or "ECS_MYSQL_PASSWORD")
    ssl_raw = cfg.get("ssl")
    if ssl_raw is None:
        ssl_raw = os.environ.get("ECS_MYSQL_SSL", "")
    return {
        "host": _clean(cfg.get("host")) or os.environ.get("ECS_MYSQL_HOST", "localhost"),
        "port": _safe_int(cfg.get("port") or os.environ.get("ECS_MYSQL_PORT"), DEFAULT_MYSQL_PORT),
        "database": _clean(cfg.get("database")) or os.environ.get("ECS_MYSQL_DATABASE", "ecs_demo"),
        "user": _clean(cfg.get("user")) or os.environ.get("ECS_MYSQL_USER", "ecs_user"),
        "password": os.environ.get(password_env) or os.environ.get("ECS_MYSQL_PASSWORD", ""),
        "ssl": _as_bool(ssl_raw),
        "timeout_sec": _safe_int(
            cfg.get("timeout_sec")
            or os.environ.get("ECS_MYSQL_TIMEOUT_SECONDS")
            or os.environ.get("ECS_MYSQL_TIMEOUT_SEC"),
            DEFAULT_TIMEOUT_SEC,
        ),
    }


def _friendly_error(exc: Exception) -> tuple[str, str]:
    message = str(exc).strip()
    lower = message.lower()
    if "timeout" in lower or "timed out" in lower:
        return "timeout", "Query timed out. Check database availability and try again."
    if "requires secure connection" in lower or "insecure transport" in lower:
        return (
            "connection_failure",
            "Secure transport required. Set ECS_MYSQL_SSL=true or use TLS.",
        )
    if "(1045," in message or "access denied for user" in lower:
        return "authentication_failure", "Authentication failed. Verify MySQL credentials."
    if "can't connect" in lower or "connection refused" in lower or "no route to host" in lower or "cannot connect" in lower:
        return "connection_failure", "Could not connect to MySQL. Ensure the MySQL/Aurora endpoint is reachable."
    if (
        "denied to user" in lower
        or "command denied" in lower
        or ("access denied" in lower and "privilege" in lower)
        or ("access denied" in lower and "you need" in lower)
    ):
        return "query_failure", f"Query failed: {message}"
    if "unknown database" in lower or "syntax" in lower:
        return "query_failure", f"Query failed: {message}"
    return "query_failure", f"Database error: {message}"


def _format_result(columns: list[str], rows: list[tuple]) -> str:
    if not columns:
        return "(no output)"
    header = " | ".join(columns)
    sep = "-" * min(len(header), 120)
    lines = [header, sep]
    for row in rows:
        lines.append(" | ".join("" if v is None else str(v) for v in row))
    return "\n".join(lines)


class MySQLConnector:
    """Live Aurora MySQL / MySQL 8 execution for predefined queries."""

    technology = "Aurora MySQL"

    def __init__(
        self,
        host: str = "localhost",
        port: int = DEFAULT_MYSQL_PORT,
        database: str = "ecs_demo",
        user: str = "ecs_user",
        password: str = "",
        ssl: bool = False,
        timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.ssl = bool(ssl)
        self.timeout_sec = timeout_sec
        self._conn = None
        self._last_error = ""

    def connect(self) -> bool:
        try:
            import pymysql
        except ImportError:
            self._last_error = "MySQL driver (PyMySQL) is not installed in this environment."
            self._conn = None
            return False
        try:
            connect_kwargs: dict[str, Any] = dict(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                connect_timeout=self.timeout_sec,
                read_timeout=self.timeout_sec,
                write_timeout=self.timeout_sec,
                # Read-only intent: MySQL has no per-connection statement_timeout
                # equivalent as portable as PostgreSQL's; autocommit avoids leaving
                # open transactions for these SELECT/SHOW checks.
                autocommit=True,
                cursorclass=pymysql.cursors.Cursor,
            )
            if self.ssl:
                # Minimal TLS enablement; certificate policy is enforced by the
                # server / security group per bank policy. No secrets logged.
                connect_kwargs["ssl"] = {"ssl": {}}
            self._conn = pymysql.connect(**connect_kwargs)
            self._last_error = ""
            return True
        except Exception as exc:  # noqa: BLE001 - normalise to friendly error
            _, self._last_error = _friendly_error(exc)
            self._conn = None
            return False

    def execute(self, query: str) -> ConnectorResult:
        if not self._conn:
            return ConnectorResult(
                success=False,
                error_message=self._last_error or "Not connected to MySQL",
            )
        started = time.perf_counter()
        try:
            with self._conn.cursor() as cur:
                cur.execute(query)
                if cur.description:
                    columns = [col[0] for col in cur.description]
                    rows = cur.fetchall()
                    output = _format_result(columns, list(rows))
                    row_count = len(rows)
                else:
                    output = f"Command completed. Rows affected: {cur.rowcount}"
                    row_count = cur.rowcount
            duration_ms = int((time.perf_counter() - started) * 1000)
            return ConnectorResult(
                success=True,
                output=output,
                duration_ms=duration_ms,
                metadata={"rows_returned": row_count},
            )
        except Exception as exc:  # noqa: BLE001
            duration_ms = int((time.perf_counter() - started) * 1000)
            etype, friendly = _friendly_error(exc)
            return ConnectorResult(
                success=False,
                error_message=friendly,
                duration_ms=duration_ms,
                metadata={"error_type": etype},
            )

    def disconnect(self) -> None:
        if self._conn:
            try:
                self._conn.close()
            except Exception:  # noqa: BLE001
                pass
        self._conn = None
