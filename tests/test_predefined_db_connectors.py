"""Unit tests for the predefined-query database connectors.

Covers PostgreSQL / YugabyteDB / Aurora MySQL:
  * config loading (env + defaults, sslmode/ssl, timeout)
  * supplementary query catalog loading
  * technology detection + connector routing
  * safe handling of an unavailable DB (no exceptions)
  * result normalization to ConnectorResult / pipe-delimited text

No live database is required. DB drivers are mocked, so these tests pass even
when psycopg2 / PyMySQL are not installed.
"""

from __future__ import annotations

import sys
import types

import pytest

from modules.operations.engines import predefined_queries_engine as engine
from modules.operations.engines import supplementary_query_catalog as catalog
from modules.operations.engines.query_connectors import ConnectorResult, connector_for_technology
from modules.operations.engines.postgresql_connector import (
    _format_result,
    _safe_int,
    _clean,
    get_postgresql_config,
)
from modules.operations.engines.yugabyte_connector import (
    YugabyteConnector,
    get_yugabyte_config,
    DEFAULT_YB_PORT,
)
from modules.operations.engines.mysql_connector import (
    MySQLConnector,
    get_mysql_config,
    DEFAULT_MYSQL_PORT,
    _as_bool,
)


# --------------------------------------------------------------------------- #
# Config loading
# --------------------------------------------------------------------------- #
def test_postgres_config_defaults():
    cfg = get_postgresql_config()
    assert cfg["port"] == 5432
    assert cfg["host"]
    assert "timeout_sec" in cfg and isinstance(cfg["timeout_sec"], int)
    assert "sslmode" in cfg


def test_yugabyte_config_defaults():
    cfg = get_yugabyte_config()
    assert cfg["port"] == DEFAULT_YB_PORT == 5433
    assert isinstance(cfg["timeout_sec"], int)
    assert "sslmode" in cfg


def test_mysql_config_defaults():
    cfg = get_mysql_config()
    assert cfg["port"] == DEFAULT_MYSQL_PORT == 3306
    assert isinstance(cfg["timeout_sec"], int)
    assert isinstance(cfg["ssl"], bool)


def _reset_config_cache():
    """Clear the cached YAML config so env-var overrides are re-read.

    The predefined_query_targets YAML block resolves ${ECS_*} placeholders at
    load time and is cached (lru_cache). Env vars set mid-process only take
    effect after clearing that cache — which mirrors a fresh process start.
    """
    try:
        from ecs_platform.config.loader import load_config

        load_config.cache_clear()
    except Exception:  # noqa: BLE001 - if unavailable, connector env-fallback still applies
        pass
    try:
        from config.environment_loader import _load_for_env

        _load_for_env.cache_clear()
    except Exception:  # noqa: BLE001
        pass


def test_yugabyte_config_env_override(monkeypatch):
    monkeypatch.setenv("ECS_YB_HOST", "yb.uat.internal")
    monkeypatch.setenv("ECS_YB_PORT", "5599")
    monkeypatch.setenv("ECS_YB_DATABASE", "prod_yb")
    monkeypatch.setenv("ECS_YB_TIMEOUT_SECONDS", "45")
    _reset_config_cache()
    try:
        cfg = get_yugabyte_config()
        assert cfg["host"] == "yb.uat.internal"
        assert cfg["port"] == 5599
        assert cfg["database"] == "prod_yb"
        assert cfg["timeout_sec"] == 45
    finally:
        _reset_config_cache()


def test_mysql_config_env_override(monkeypatch):
    monkeypatch.setenv("ECS_MYSQL_HOST", "aurora.uat.rds.amazonaws.com")
    monkeypatch.setenv("ECS_MYSQL_PORT", "3307")
    monkeypatch.setenv("ECS_MYSQL_SSL", "true")
    _reset_config_cache()
    try:
        cfg = get_mysql_config()
        assert cfg["host"] == "aurora.uat.rds.amazonaws.com"
        assert cfg["port"] == 3307
        assert cfg["ssl"] is True
    finally:
        _reset_config_cache()


def test_safe_int_tolerates_unresolved_placeholder():
    assert _safe_int("${ECS_PG_TIMEOUT_SECONDS:-30}", 30) == 30
    assert _safe_int("", 30) == 30
    assert _safe_int(None, 30) == 30
    assert _safe_int("45", 30) == 45


def test_clean_strips_unresolved_placeholder():
    assert _clean("${ECS_PG_HOST}") == ""
    assert _clean("  host  ") == "host"
    assert _clean(None) == ""


def test_as_bool_variants():
    assert _as_bool("true") is True
    assert _as_bool("1") is True
    assert _as_bool("require") is True
    assert _as_bool("false") is False
    assert _as_bool("${ECS_MYSQL_SSL:-false}") is False
    assert _as_bool(None) is False


# --------------------------------------------------------------------------- #
# Supplementary catalog
# --------------------------------------------------------------------------- #
def test_supplementary_catalog_counts():
    sup = catalog.supplementary_controls()
    pg = [c for c in sup if c["technology"] == "PostgreSQL"]
    yb = [c for c in sup if c["technology"] == "YugabyteDB"]
    my = [c for c in sup if c["technology"] == "Aurora MySQL"]
    assert len(pg) == 13
    assert len(yb) == 11
    assert len(my) == 14
    # DB technologies contribute 38 supplementary controls (this file is DB-scoped;
    # infrastructure controls — Oracle/NGINX/Linux/RHEL — are covered separately).
    assert len(pg) + len(yb) + len(my) == 38


def test_supplementary_entries_have_required_fields():
    for c in catalog.supplementary_controls():
        for field in ("control_id", "control_name", "query", "technology", "framework_coverage"):
            assert c.get(field), f"{c.get('control_id')} missing {field}"


def test_supplementary_ids_unique():
    ids = [c["control_id"] for c in catalog.supplementary_controls()]
    assert len(ids) == len(set(ids))


def test_engine_merges_supplementary_controls():
    engine.load_predefined_queries(force=True)
    for cid in ("PGX-001", "YBX-001", "MYX-001", "MYX-010"):
        ctrl = engine.get_control_by_id(cid)
        assert ctrl is not None, f"{cid} not merged"
        assert ctrl["predefined"] is True


def test_every_supplementary_query_in_allowlist():
    allow = {
        "PostgreSQL": engine.ALLOWED_POSTGRESQL_QUERIES,
        "YugabyteDB": engine.ALLOWED_YUGABYTE_QUERIES,
        "Aurora MySQL": engine.ALLOWED_MYSQL_QUERIES,
    }
    # DB-scoped: only the SQL database technologies use exact-SQL allow-lists here.
    for c in catalog.supplementary_controls():
        if c["technology"] not in allow:
            continue
        norm = engine._normalize_query_allowlist(c["query"])
        assert norm in allow[c["technology"]], f"{c['control_id']} not in allow-list"


# --------------------------------------------------------------------------- #
# Technology detection + routing
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "query, expected",
    [
        ("SELECT * FROM yb_servers();", "YugabyteDB"),
        ("SHOW VARIABLES LIKE 'have_ssl';", "Aurora MySQL"),
        ("SELECT user, host, plugin FROM mysql.user;", "Aurora MySQL"),
        ("SHOW DATABASES;", "Aurora MySQL"),
        ("SHOW PROCESSLIST;", "Aurora MySQL"),
        ("SELECT extname, extversion FROM pg_extension;", "PostgreSQL"),
        ("SELECT * FROM pg_stat_replication;", "PostgreSQL"),
        ("SHOW ssl;", "PostgreSQL"),
    ],
)
def test_detect_technology(query, expected):
    assert engine.detect_technology(query) == expected


def test_routing_returns_expected_connectors():
    # These require the drivers; skip gracefully if a driver is missing.
    pg = connector_for_technology("PostgreSQL")
    yb = connector_for_technology("YugabyteDB")
    my = connector_for_technology("Aurora MySQL")
    # When drivers are installed, we get concrete connectors on the right ports.
    if pg is not None:
        assert pg.port == 5432
    if yb is not None:
        assert type(yb).__name__ == "YugabyteConnector"
        assert yb.port == 5433
    if my is not None:
        assert type(my).__name__ == "MySQLConnector"
        assert my.port == 3306


def test_yugabyte_is_postgres_wire_subclass():
    from modules.operations.engines.postgresql_connector import PostgreSQLConnector

    assert issubclass(YugabyteConnector, PostgreSQLConnector)
    assert YugabyteConnector().technology == "YugabyteDB"


# --------------------------------------------------------------------------- #
# Result normalization
# --------------------------------------------------------------------------- #
def test_format_result_pipe_delimited():
    out = _format_result(["col_a", "col_b"], [("v1", "v2"), ("v3", None)])
    lines = out.splitlines()
    assert lines[0] == "col_a | col_b"
    assert "v1 | v2" in out
    assert "v3 | " in out  # None rendered as empty


def test_format_result_empty_columns():
    assert _format_result([], []) == "(no output)"


class _FakeCursor:
    """Minimal DB-API cursor stand-in for mocking execute()."""

    def __init__(self, description, rows):
        self.description = description
        self._rows = rows
        self.rowcount = len(rows)

    def execute(self, query, *a, **k):
        return None

    def fetchall(self):
        return self._rows

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_mysql_execute_normalizes_rows():
    conn = MySQLConnector(host="h", port=3306, database="d", user="u", password="p")
    # Inject a fake pymysql connection with a cursor returning two rows.
    conn._conn = types.SimpleNamespace(
        cursor=lambda: _FakeCursor([("user",), ("host",)], [("root", "%"), ("app", "10.0.0.1")])
    )
    result = conn.execute("SELECT user, host FROM mysql.user;")
    assert isinstance(result, ConnectorResult)
    assert result.success is True
    assert result.metadata["rows_returned"] == 2
    assert "user | host" in result.output
    assert "root | %" in result.output


def test_mysql_execute_not_connected_returns_failure():
    conn = MySQLConnector()
    result = conn.execute("SELECT VERSION();")
    assert result.success is False
    assert result.error_message


# --------------------------------------------------------------------------- #
# Safe handling of unavailable DB / missing driver
# --------------------------------------------------------------------------- #
def test_mysql_connect_missing_driver(monkeypatch):
    """When PyMySQL is not importable, connect() returns False (no exception)."""
    monkeypatch.setitem(sys.modules, "pymysql", None)  # force ImportError on `import pymysql`
    conn = MySQLConnector(host="127.0.0.1", port=59997, timeout_sec=1)
    assert conn.connect() is False
    assert "PyMySQL" in conn._last_error or "driver" in conn._last_error.lower()


def test_run_mysql_query_missing_control():
    res = engine.run_mysql_query("NON-EXISTENT-CTRL", "tester")
    assert res["ok"] is False
    assert res["error_type"] == "missing_control"


def test_run_yugabyte_query_missing_control():
    res = engine.run_yugabyte_query("NON-EXISTENT-CTRL", "tester")
    assert res["ok"] is False
    assert res["error_type"] == "missing_control"


def test_run_mysql_query_rejects_non_allowlisted(monkeypatch):
    """A MySQL control whose query is not allow-listed is refused before connecting."""
    engine.load_predefined_queries(force=True)
    fake = {
        "control_id": "MYX-TEST",
        "technology": "Aurora MySQL",
        "query": "DROP TABLE users;",
        "predefined": True,
        "frameworks": ["DB Baselining"],
        "framework_coverage": "DB Baselining",
    }
    monkeypatch.setattr(engine, "get_control_by_id", lambda cid: fake if cid == "MYX-TEST" else None)
    res = engine.run_mysql_query("MYX-TEST", "tester")
    assert res["ok"] is False
    assert res["error_type"] == "unsupported_query"
