"""PostgreSQL connector for predefined query execution."""

from __future__ import annotations

import os
import time
from typing import Any

import psycopg2

from modules.operations.engines.query_connectors import ConnectorResult

DEFAULT_TIMEOUT_SEC = 30


def get_postgresql_config() -> dict[str, Any]:
    """PostgreSQL target for predefined query execution.

    Resolution order per field: active-environment YAML
    (predefined_query_targets.postgresql) -> ECS_PG_* env var -> historical
    default. The YAML values already honour the env vars, so behaviour is
    identical when no env file overrides are present.
    """
    from modules.operations.engines.query_connectors import get_predefined_target

    cfg = get_predefined_target("postgresql")
    password_env = str(cfg.get("password_env") or "ECS_PG_PASSWORD")
    return {
        "host": cfg.get("host") or os.environ.get("ECS_PG_HOST", "localhost"),
        "port": int(cfg.get("port") or os.environ.get("ECS_PG_PORT", "5432")),
        "database": cfg.get("database") or os.environ.get("ECS_PG_DATABASE", "ecs_demo"),
        "user": cfg.get("user") or os.environ.get("ECS_PG_USER", "ecs_user"),
        "password": os.environ.get(password_env) or os.environ.get("ECS_PG_PASSWORD", "ecs_password"),
        "timeout_sec": int(cfg.get("timeout_sec") or os.environ.get("ECS_PG_TIMEOUT_SEC", str(DEFAULT_TIMEOUT_SEC))),
    }


def _friendly_error(exc: Exception) -> tuple[str, str]:
    message = str(exc).strip()
    lower = message.lower()
    if "timeout" in lower or "timed out" in lower:
        return "timeout", "Query timed out. Check database availability and try again."
    if "password authentication failed" in lower or "authentication failed" in lower:
        return "authentication_failure", "Authentication failed. Verify database credentials."
    if "could not connect" in lower or "connection refused" in lower or "no route to host" in lower:
        return "connection_failure", "Could not connect to PostgreSQL. Ensure postgres-demo is running (docker compose up -d)."
    if "does not exist" in lower or "syntax error" in lower or "permission denied" in lower:
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


class PostgreSQLConnector:
    """Live PostgreSQL execution for predefined demo queries."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "ecs_demo",
        user: str = "ecs_user",
        password: str = "ecs_password",
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
            self._conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                dbname=self.database,
                user=self.user,
                password=self.password,
                connect_timeout=self.timeout_sec,
            )
            self._conn.autocommit = True
            with self._conn.cursor() as cur:
                cur.execute("SET statement_timeout = %s", (f"{self.timeout_sec}s",))
            return True
        except Exception as exc:
            _, self._last_error = _friendly_error(exc)
            self._conn = None
            return False

    def execute(self, query: str) -> ConnectorResult:
        if not self._conn:
            return ConnectorResult(
                success=False,
                error_message=self._last_error or "Not connected to PostgreSQL",
            )
        started = time.perf_counter()
        try:
            with self._conn.cursor() as cur:
                cur.execute(query)
                if cur.description:
                    columns = [col[0] for col in cur.description]
                    rows = cur.fetchall()
                    output = _format_result(columns, rows)
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
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            _, friendly = _friendly_error(exc)
            return ConnectorResult(
                success=False,
                error_message=friendly,
                duration_ms=duration_ms,
                metadata={"error_type": _friendly_error(exc)[0]},
            )

    def disconnect(self) -> None:
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
        self._conn = None
