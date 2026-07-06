"""SQL Server connector for predefined query execution.

Uses pyodbc (isolated, optional dependency — the connector degrades gracefully to
a friendly "driver not installed" message if pyodbc / an ODBC driver is absent).
Read-only, credential-externalised, never logs passwords. Results normalised to
the same ``ConnectorResult`` + pipe-delimited text used by the other DB connectors.

SQL Server is heavy/Windows-oriented; there is no default local container (an
optional `sqlserver-demo` profile exists but never starts by default).
"""

from __future__ import annotations

import os
import time
from typing import Any

from modules.operations.engines.query_connectors import ConnectorResult

DEFAULT_TIMEOUT_SEC = 30
DEFAULT_MSSQL_PORT = 1433


def _safe_int(value: Any, default: int) -> int:
    try:
        s = str(value).strip()
        if not s or s.startswith("${"):
            return default
        return int(s)
    except (TypeError, ValueError):
        return default


def _clean(value: Any) -> str:
    s = str(value).strip() if value is not None else ""
    return "" if s.startswith("${") else s


def get_sqlserver_config() -> dict[str, Any]:
    """SQL Server target for predefined query execution (env / YAML driven)."""
    from modules.operations.engines.query_connectors import get_predefined_target

    cfg = get_predefined_target("sqlserver")
    password_env = str(cfg.get("password_env") or "ECS_SQLSERVER_PASSWORD")
    return {
        "host": _clean(cfg.get("host")) or os.environ.get("ECS_SQLSERVER_HOST", "localhost"),
        "port": _safe_int(cfg.get("port") or os.environ.get("ECS_SQLSERVER_PORT"), DEFAULT_MSSQL_PORT),
        "database": _clean(cfg.get("database")) or os.environ.get("ECS_SQLSERVER_DATABASE", "master"),
        "user": _clean(cfg.get("user")) or os.environ.get("ECS_SQLSERVER_USERNAME", "sa"),
        "password": os.environ.get(password_env) or os.environ.get("ECS_SQLSERVER_PASSWORD", ""),
        "timeout_sec": _safe_int(
            cfg.get("timeout_sec")
            or os.environ.get("ECS_SQLSERVER_TIMEOUT_SECONDS")
            or os.environ.get("ECS_SQLSERVER_TIMEOUT_SEC"),
            DEFAULT_TIMEOUT_SEC,
        ),
    }


def _friendly_error(exc: Exception) -> tuple[str, str]:
    message = str(exc).strip()
    lower = message.lower()
    if "timeout" in lower or "timed out" in lower:
        return "timeout", "Query timed out. Check database availability and try again."
    if "login failed" in lower or "authentication" in lower or "password" in lower:
        return "authentication_failure", "Authentication failed. Verify SQL Server credentials."
    if "could not open" in lower or "unable to connect" in lower or "server is not found" in lower \
            or "connection refused" in lower or "no route" in lower:
        return "connection_failure", "Could not connect to SQL Server. Ensure the endpoint is reachable."
    if "invalid object name" in lower or "permission" in lower or "syntax" in lower:
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


def _build_conn_str(cfg: dict[str, Any], driver: str) -> str:
    return (
        f"DRIVER={{{driver}}};SERVER={cfg['host']},{cfg['port']};"
        f"DATABASE={cfg['database']};UID={cfg['user']};PWD={cfg['password']};"
        f"Connection Timeout={min(int(cfg.get('timeout_sec', 30)), 30)};TrustServerCertificate=yes"
    )


class SQLServerConnector:
    """Live SQL Server execution for predefined queries (pyodbc)."""

    technology = "SQL Server"

    def __init__(
        self,
        host: str = "localhost",
        port: int = DEFAULT_MSSQL_PORT,
        database: str = "master",
        user: str = "sa",
        password: str = "",
        timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.timeout_sec = timeout_sec
        self._conn = None
        self._last_error = ""

    def connect(self) -> bool:
        try:
            import pyodbc
        except ImportError:
            self._last_error = "SQL Server driver (pyodbc + an ODBC driver) is not installed in this environment."
            self._conn = None
            return False
        cfg = {
            "host": self.host, "port": self.port, "database": self.database,
            "user": self.user, "password": self.password, "timeout_sec": self.timeout_sec,
        }
        # Try common driver names; fail gracefully if none are installed.
        drivers = ["ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server", "FreeTDS"]
        last_exc: Exception | None = None
        for drv in drivers:
            try:
                self._conn = pyodbc.connect(
                    _build_conn_str(cfg, drv), timeout=min(self.timeout_sec, 30)
                )
                return True
            except Exception as exc:  # noqa: BLE001 - try next driver
                last_exc = exc
                continue
        _, self._last_error = _friendly_error(last_exc or Exception("No ODBC driver available"))
        self._conn = None
        return False

    def execute(self, query: str) -> ConnectorResult:
        if not self._conn:
            return ConnectorResult(
                success=False,
                error_message=self._last_error or "Not connected to SQL Server",
            )
        started = time.perf_counter()
        try:
            cur = self._conn.cursor()
            cur.execute(query)
            if cur.description:
                columns = [col[0] for col in cur.description]
                rows = cur.fetchall()
                output = _format_result(columns, [tuple(r) for r in rows])
                row_count = len(rows)
            else:
                output = "Command completed."
                row_count = 0
            cur.close()
            duration_ms = int((time.perf_counter() - started) * 1000)
            return ConnectorResult(
                success=True, output=output, duration_ms=duration_ms,
                metadata={"rows_returned": row_count},
            )
        except Exception as exc:  # noqa: BLE001
            duration_ms = int((time.perf_counter() - started) * 1000)
            etype, friendly = _friendly_error(exc)
            return ConnectorResult(
                success=False, error_message=friendly, duration_ms=duration_ms,
                metadata={"error_type": etype},
            )

    def disconnect(self) -> None:
        if self._conn:
            try:
                self._conn.close()
            except Exception:  # noqa: BLE001
                pass
        self._conn = None
