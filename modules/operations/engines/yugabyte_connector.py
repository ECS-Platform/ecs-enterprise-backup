"""YugabyteDB (YSQL) connector for predefined query execution.

YugabyteDB's YSQL API is PostgreSQL-wire compatible, so this connector reuses the
PostgreSQL execution path (``psycopg2``) verbatim and only differs in:
  * configuration source (ECS_YB_* env vars / predefined_query_targets.yugabyte)
  * default listener port (5433)
  * technology label ("YugabyteDB") used in audit records

Keeping it a thin subclass avoids a duplicate SQL execution engine while still
routing Yugabyte separately from PostgreSQL. Read-only, credential-externalised,
never logs passwords.
"""

from __future__ import annotations

import os
from typing import Any

from modules.operations.engines.postgresql_connector import (
    DEFAULT_TIMEOUT_SEC,
    PostgreSQLConnector,
    _clean,
    _safe_int,
)

# Yugabyte YSQL default port (PostgreSQL-wire compatible).
DEFAULT_YB_PORT = 5433


def get_yugabyte_config() -> dict[str, Any]:
    """YugabyteDB (YSQL) target for predefined query execution.

    Resolution order per field: active-environment YAML
    (predefined_query_targets.yugabyte) -> ECS_YB_* env var -> default. No
    endpoints or credentials are hard-coded; production values come from the
    environment.
    """
    from modules.operations.engines.query_connectors import get_predefined_target

    cfg = get_predefined_target("yugabyte")
    password_env = str(cfg.get("password_env") or "ECS_YB_PASSWORD")
    return {
        "host": _clean(cfg.get("host")) or os.environ.get("ECS_YB_HOST", "localhost"),
        "port": _safe_int(cfg.get("port") or os.environ.get("ECS_YB_PORT"), DEFAULT_YB_PORT),
        "database": _clean(cfg.get("database")) or os.environ.get("ECS_YB_DATABASE", "yugabyte"),
        "user": _clean(cfg.get("user")) or os.environ.get("ECS_YB_USER", "yugabyte"),
        "password": os.environ.get(password_env) or os.environ.get("ECS_YB_PASSWORD", ""),
        "sslmode": _clean(cfg.get("sslmode")) or os.environ.get("ECS_YB_SSLMODE", ""),
        "timeout_sec": _safe_int(
            cfg.get("timeout_sec")
            or os.environ.get("ECS_YB_TIMEOUT_SECONDS")
            or os.environ.get("ECS_YB_TIMEOUT_SEC"),
            DEFAULT_TIMEOUT_SEC,
        ),
    }


class YugabyteConnector(PostgreSQLConnector):
    """Live YugabyteDB (YSQL) execution — reuses the PostgreSQL psycopg2 path."""

    technology = "YugabyteDB"

    def __init__(
        self,
        host: str = "localhost",
        port: int = DEFAULT_YB_PORT,
        database: str = "yugabyte",
        user: str = "yugabyte",
        password: str = "",
        sslmode: str = "",
        timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    ):
        super().__init__(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            sslmode=sslmode,
            timeout_sec=timeout_sec,
        )
