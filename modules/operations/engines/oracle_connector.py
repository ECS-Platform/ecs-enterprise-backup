"""Oracle Database connector for predefined query execution.

Uses python-oracledb in **thin mode** (pure-Python, no Oracle Instant Client
libraries required), matching the project's pure-Python driver style (psycopg2 /
PyMySQL). Read-only, credential-externalised, never logs passwords. Results are
normalised to the same ``ConnectorResult`` + pipe-delimited text used by the
PostgreSQL/MySQL connectors so downstream audit/evidence/API handling is
identical.

Oracle is AWS/on-prem managed; there is no lightweight default local container,
so live execution requires an external Oracle endpoint (or an optional Oracle XE
container on a 16/20 GB machine). See the developer docs.
"""

from __future__ import annotations

import os
import time
from typing import Any

from modules.operations.engines.query_connectors import ConnectorResult

DEFAULT_TIMEOUT_SEC = 30
DEFAULT_ORACLE_PORT = 1521


def _safe_int(value: Any, default: int) -> int:
    """Coerce a value to int, tolerating unresolved ``${...}`` placeholders/blanks."""
    try:
        s = str(value).strip()
        if not s or s.startswith("${"):
            return default
        return int(s)
    except (TypeError, ValueError):
        return default


def _clean(value: Any) -> str:
    """Return a string, treating unresolved ``${...}`` placeholders as empty."""
    s = str(value).strip() if value is not None else ""
    return "" if s.startswith("${") else s


def get_oracle_config() -> dict[str, Any]:
    """Oracle target for predefined query execution.

    Resolution per field: active-environment YAML
    (predefined_query_targets.oracle) -> ECS_ORACLE_* env var -> default.
    Endpoints/credentials are never hard-coded; production values come from env.
    """
    from modules.operations.engines.query_connectors import get_predefined_target

    cfg = get_predefined_target("oracle")
    password_env = str(cfg.get("password_env") or "ECS_ORACLE_PASSWORD")
    return {
        "host": _clean(cfg.get("host")) or os.environ.get("ECS_ORACLE_HOST", "localhost"),
        "port": _safe_int(cfg.get("port") or os.environ.get("ECS_ORACLE_PORT"), DEFAULT_ORACLE_PORT),
        "service_name": _clean(cfg.get("service_name")) or os.environ.get("ECS_ORACLE_SERVICE_NAME", "XEPDB1"),
        "user": _clean(cfg.get("user")) or os.environ.get("ECS_ORACLE_USER", "ecs_user"),
        "password": os.environ.get(password_env) or os.environ.get("ECS_ORACLE_PASSWORD", ""),
        "timeout_sec": _safe_int(
            cfg.get("timeout_sec")
            or os.environ.get("ECS_ORACLE_TIMEOUT_SECONDS")
            or os.environ.get("ECS_ORACLE_TIMEOUT_SEC"),
            DEFAULT_TIMEOUT_SEC,
        ),
    }


def _friendly_error(exc: Exception) -> tuple[str, str]:
    message = str(exc).strip()
    lower = message.lower()
    if "timeout" in lower or "timed out" in lower:
        return "timeout", "Query timed out. Check database availability and try again."
    if "invalid username" in lower or "logon denied" in lower or "ora-01017" in lower:
        return "authentication_failure", "Authentication failed. Verify Oracle credentials."
    if "listener" in lower or "could not connect" in lower or "connection refused" in lower \
            or "no route" in lower or "ora-12541" in lower or "ora-12514" in lower:
        return "connection_failure", "Could not connect to Oracle. Ensure the listener/service is reachable."
    if "table or view does not exist" in lower or "ora-00942" in lower or "insufficient privileges" in lower:
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


class OracleConnector:
    """Live Oracle execution for predefined queries (python-oracledb thin mode)."""

    technology = "Oracle"

    def __init__(
        self,
        host: str = "localhost",
        port: int = DEFAULT_ORACLE_PORT,
        service_name: str = "XEPDB1",
        user: str = "ecs_user",
        password: str = "",
        timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    ):
        self.host = host
        self.port = port
        self.service_name = service_name
        self.user = user
        self.password = password
        self.timeout_sec = timeout_sec
        self._conn = None
        self._last_error = ""

    def connect(self) -> bool:
        try:
            import oracledb
        except ImportError:
            self._last_error = "Oracle driver (python-oracledb) is not installed in this environment."
            self._conn = None
            return False
        try:
            dsn = oracledb.makedsn(self.host, self.port, service_name=self.service_name)
            self._conn = oracledb.connect(
                user=self.user,
                password=self.password,
                dsn=dsn,
                # thin mode is the default; keep connect bounded.
                tcp_connect_timeout=min(self.timeout_sec, 30),
            )
            try:
                self._conn.call_timeout = int(self.timeout_sec) * 1000  # ms
            except Exception:  # noqa: BLE001 - not all versions expose call_timeout
                pass
            return True
        except Exception as exc:  # noqa: BLE001
            _, self._last_error = _friendly_error(exc)
            self._conn = None
            return False

    def execute(self, query: str) -> ConnectorResult:
        if not self._conn:
            return ConnectorResult(
                success=False,
                error_message=self._last_error or "Not connected to Oracle",
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
                    output = "Command completed."
                    row_count = 0
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
