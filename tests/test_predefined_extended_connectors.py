"""Connector tests for the extended technologies.

Redis / Apache / Tomcat routing (via LinuxConnector), SQL Server (mocked pyodbc),
MongoDB (mocked pymongo), Kubernetes/OpenShift (kubectl/oc unavailable handling).
No live targets, no image pulls, no real drivers required.
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import sys
import types

import pytest

from modules.operations.engines import predefined_queries_engine as engine
from modules.operations.engines.query_connectors import ConnectorResult, connector_for_technology


# --------------------------------------------------------------------------- #
# Routing
# --------------------------------------------------------------------------- #
def test_routing_extended_technologies():
    assert type(connector_for_technology("Redis")).__name__ == "RedisConnector"
    assert type(connector_for_technology("Apache HTTPD")).__name__ == "LinuxConnector"
    assert type(connector_for_technology("Tomcat")).__name__ == "LinuxConnector"
    assert type(connector_for_technology("Kubernetes")).__name__ == "KubernetesConnector"
    assert type(connector_for_technology("OpenShift")).__name__ == "OpenShiftConnector"
    # DB connectors present when drivers installed; otherwise None (graceful).
    mssql = connector_for_technology("SQL Server")
    if mssql is not None:
        assert type(mssql).__name__ == "SQLServerConnector"
    mongo = connector_for_technology("MongoDB")
    if mongo is not None:
        assert type(mongo).__name__ == "MongoDBConnector"


def test_redis_is_linux_subclass():
    from modules.operations.engines.linux_connector import LinuxConnector
    from modules.operations.engines.redis_connector import RedisConnector

    assert issubclass(RedisConnector, LinuxConnector)
    assert RedisConnector().technology == "Redis"


def test_apache_tomcat_container_config(monkeypatch):
    monkeypatch.setenv("ECS_APACHE_CONTAINER", "my-apache")
    monkeypatch.setenv("ECS_TOMCAT_CONTAINER", "my-tomcat")
    _clear_cache()
    from modules.operations.engines.linux_connector import get_apache_config, get_tomcat_config

    assert get_apache_config()["container"] == "my-apache"
    assert get_tomcat_config()["container"] == "my-tomcat"
    _clear_cache()


# --------------------------------------------------------------------------- #
# Redis auth injection (never in the catalog command)
# --------------------------------------------------------------------------- #
def test_redis_injects_auth_without_leaking_catalog():
    from modules.operations.engines.redis_connector import RedisConnector

    conn = RedisConnector(container="redis", password="s3cr3t")
    captured = {}

    def _fake_super_execute(self, cmd):
        captured["cmd"] = cmd
        return ConnectorResult(success=True, output="ok", metadata={"rows_returned": 1})

    # Patch the parent LinuxConnector.execute to capture the final command.
    from modules.operations.engines.linux_connector import LinuxConnector
    orig = LinuxConnector.execute
    LinuxConnector.execute = _fake_super_execute
    try:
        conn.execute("redis-cli INFO server")
    finally:
        LinuxConnector.execute = orig
    assert "s3cr3t" in captured["cmd"]  # auth injected at execution time
    assert "--no-auth-warning" in captured["cmd"]


# --------------------------------------------------------------------------- #
# SQL Server (mocked pyodbc)
# --------------------------------------------------------------------------- #
def test_sqlserver_missing_driver(monkeypatch):
    monkeypatch.setitem(sys.modules, "pyodbc", None)
    from modules.operations.engines.sqlserver_connector import SQLServerConnector

    conn = SQLServerConnector(host="h", password="p")
    assert conn.connect() is False
    assert "pyodbc" in conn._last_error.lower() or "odbc" in conn._last_error.lower()


def test_sqlserver_execute_normalizes(monkeypatch):
    from modules.operations.engines.sqlserver_connector import SQLServerConnector

    class _Cur:
        description = [("name",), ("state",)]

        def execute(self, q):
            return None

        def fetchall(self):
            return [("db1", "ONLINE"), ("db2", "OFFLINE")]

        def close(self):
            return None

    conn = SQLServerConnector()
    conn._conn = types.SimpleNamespace(cursor=lambda: _Cur())
    res = conn.execute("SELECT name, state FROM sys.databases;")
    assert res.success is True
    assert res.metadata["rows_returned"] == 2
    assert "db1 | ONLINE" in res.output


def test_run_sqlserver_rejects_non_allowlisted(monkeypatch):
    engine.load_predefined_queries(force=True)
    fake = {"control_id": "MSX-BAD", "technology": "SQL Server", "query": "DROP TABLE t;",
            "predefined": True, "frameworks": ["DB Baselining"], "framework_coverage": "DB Baselining"}
    monkeypatch.setattr(engine, "get_control_by_id", lambda cid: fake if cid == "MSX-BAD" else None)
    res = engine.run_sqlserver_query("MSX-BAD", "tester")
    assert res["ok"] is False
    assert res["error_type"] == "unsupported_query"


# --------------------------------------------------------------------------- #
# MongoDB (mocked pymongo)
# --------------------------------------------------------------------------- #
def test_mongodb_missing_driver(monkeypatch):
    monkeypatch.setitem(sys.modules, "pymongo", None)
    from modules.operations.engines.mongodb_connector import MongoDBConnector

    conn = MongoDBConnector()
    assert conn.connect() is False
    assert "pymongo" in conn._last_error.lower()


def test_mongodb_execute_allowlisted_command():
    from modules.operations.engines.mongodb_connector import MongoDBConnector

    class _DB:
        def command(self, cmd):
            return {"version": "7.0.0", "ok": 1}

    class _Client:
        def __getitem__(self, name):
            return _DB()

        def close(self):
            return None

    conn = MongoDBConnector()
    conn._client = _Client()
    res = conn.execute("buildInfo")
    assert res.success is True
    assert "7.0.0" in res.output


def test_mongodb_rejects_unknown_command():
    from modules.operations.engines.mongodb_connector import MongoDBConnector

    conn = MongoDBConnector()
    conn._client = object()  # connected sentinel
    res = conn.execute("dropDatabase")  # not in the allow-list
    assert res.success is False
    assert res.metadata["error_type"] == "unsupported_query"


# --------------------------------------------------------------------------- #
# Kubernetes / OpenShift graceful handling (no cluster)
# --------------------------------------------------------------------------- #
def test_kubernetes_missing_binary(monkeypatch):
    from modules.operations.engines import kubernetes_connector as kc

    monkeypatch.setattr(kc, "which", lambda b: None)
    conn = kc.KubernetesConnector(binary="kubectl-nonexistent")
    assert conn.connect() is False
    assert "not installed" in conn._last_error.lower()


def test_openshift_missing_binary(monkeypatch):
    from modules.operations.engines import kubernetes_connector as kc

    monkeypatch.setattr(kc, "which", lambda b: None)
    conn = kc.OpenShiftConnector(binary="oc-nonexistent")
    assert conn.connect() is False
    assert "not installed" in conn._last_error.lower()


def test_kubernetes_cluster_unavailable(monkeypatch):
    from modules.operations.engines import kubernetes_connector as kc

    class _R:
        returncode = 1
        stdout = ""
        stderr = "Unable to connect to the server: dial tcp: i/o timeout"

    monkeypatch.setattr(kc.subprocess, "run", lambda *a, **k: _R())
    conn = kc.KubernetesConnector(binary="kubectl")
    res = conn.execute("kubectl get nodes")
    assert res.success is False
    assert res.metadata["error_type"] == "connection_failure"


def test_kubernetes_configuration_required(monkeypatch):
    from modules.operations.engines import kubernetes_connector as kc

    class _R:
        returncode = 1
        stdout = ""
        stderr = "error loading config file: no such file or directory"

    monkeypatch.setattr(kc.subprocess, "run", lambda *a, **k: _R())
    conn = kc.OpenShiftConnector(binary="oc")
    res = conn.execute("oc get projects")
    assert res.success is False
    assert res.metadata["error_type"] == "configuration_required"


def test_kubernetes_success(monkeypatch):
    from modules.operations.engines import kubernetes_connector as kc

    class _R:
        returncode = 0
        stdout = "node-1 Ready\nnode-2 Ready"
        stderr = ""

    monkeypatch.setattr(kc.subprocess, "run", lambda *a, **k: _R())
    conn = kc.KubernetesConnector(binary="kubectl")
    res = conn.execute("kubectl get nodes")
    assert res.success is True
    assert res.metadata["rows_returned"] == 2


# --------------------------------------------------------------------------- #
# Capability / dependency gating
# --------------------------------------------------------------------------- #
def test_shell_technologies_ready():
    engine.load_predefined_queries(force=True)
    for cid in ("RDX-001", "APX-001", "TCX-001", "K8X-001", "OCX-001"):
        ctrl = engine.get_control_by_id(cid)
        assert engine.assess_execution_capability(ctrl)["status"] == "Ready"


def test_db_dependency_gating(monkeypatch):
    engine.load_predefined_queries(force=True)
    monkeypatch.setattr(engine, "_dependency_available",
                        lambda tech: tech not in ("SQL Server", "MongoDB"))
    assert engine.assess_execution_capability(engine.get_control_by_id("MSX-001"))["status"] == "Dependency Missing"
    assert engine.assess_execution_capability(engine.get_control_by_id("MGX-001"))["status"] == "Dependency Missing"


def _clear_cache():
    try:
        from ecs_platform.config.loader import load_config
        load_config.cache_clear()
    except Exception:  # noqa: BLE001
        pass
    try:
        from config.environment_loader import _load_for_env
        _load_for_env.cache_clear()
    except Exception:  # noqa: BLE001
        pass
