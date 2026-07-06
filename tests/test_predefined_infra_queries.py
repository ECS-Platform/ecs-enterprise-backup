"""Tests for the infrastructure predefined queries: Oracle, NGINX, Linux, RHEL 8.x/9.x.

No live Oracle or SSH/Docker is required — connectors/drivers are mocked where a
connection would be attempted. Covers catalog presence, exact technology labels,
run-enablement, connector routing, and frontend Technology-filter inclusion.
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import sys
import types

import pytest

from modules.operations.engines import predefined_queries_engine as engine
from modules.operations.engines import supplementary_query_catalog as catalog
from modules.operations.engines.query_connectors import connector_for_technology

ORX = [f"ORX-0{i:02d}" for i in range(1, 11)]  # ORX-001..010
NGX = [f"NGX-00{i}" for i in range(1, 9)]       # NGX-001..008
LNX = [f"LNX-00{i}" for i in range(1, 9)]       # LNX-001..008
RH8 = [f"RH8-00{i}" for i in range(1, 9)]       # RH8-001..008
RH9 = [f"RH9-00{i}" for i in range(1, 9)]       # RH9-001..008

ORACLE = "Oracle"
NGINX = "NGINX"
LINUX = "Linux"
RHEL8 = "Red Hat Enterprise Linux 8.x"
RHEL9 = "Red Hat Enterprise Linux 9.x"


# --------------------------------------------------------------------------- #
# Catalog presence + counts
# --------------------------------------------------------------------------- #
def test_infra_catalog_counts():
    sup = catalog.supplementary_controls()
    by_tech = {}
    for c in sup:
        by_tech.setdefault(c["technology"], []).append(c["control_id"])
    assert len(by_tech[ORACLE]) == 10
    assert len(by_tech[NGINX]) == 8
    assert len(by_tech[LINUX]) == 8
    assert len(by_tech[RHEL8]) == 8
    assert len(by_tech[RHEL9]) == 8


@pytest.mark.parametrize("ids", [ORX, NGX, LNX, RH8, RH9])
def test_infra_ids_present_in_engine(ids):
    engine.load_predefined_queries(force=True)
    for cid in ids:
        ctrl = engine.get_control_by_id(cid)
        assert ctrl is not None, f"{cid} not merged into engine"
        assert ctrl["predefined"] is True
        assert ctrl["query"], f"{cid} has no command/query"


def test_total_controls_include_infra():
    rep = engine.load_predefined_queries(force=True)
    # 37 Excel + at least the 68 base supplementary (26 DB + 42 infra). Later
    # expansions only add more, so assert the floor rather than an exact total.
    assert rep["controls_loaded"] >= 105
    for cid in ("ORX-001", "NGX-001", "LNX-001", "RH8-001", "RH9-001"):
        assert engine.get_control_by_id(cid) is not None


# --------------------------------------------------------------------------- #
# Exact technology labels
# --------------------------------------------------------------------------- #
def test_exact_technology_labels():
    engine.load_predefined_queries(force=True)
    assert engine.get_control_by_id("ORX-001")["technology"] == "Oracle"
    assert engine.get_control_by_id("NGX-001")["technology"] == "NGINX"
    assert engine.get_control_by_id("LNX-001")["technology"] == "Linux"
    assert engine.get_control_by_id("RH8-001")["technology"] == "Red Hat Enterprise Linux 8.x"
    assert engine.get_control_by_id("RH9-001")["technology"] == "Red Hat Enterprise Linux 9.x"


# --------------------------------------------------------------------------- #
# Run-enablement (capability) — with/without Oracle driver
# --------------------------------------------------------------------------- #
def test_shell_controls_ready_and_live():
    engine.load_predefined_queries(force=True)
    for cid in ["NGX-001", "LNX-001", "RH8-001", "RH9-001"]:
        ctrl = engine.get_control_by_id(cid)
        cap = engine.assess_execution_capability(ctrl)
        assert cap["status"] == "Ready"
        assert engine.is_live_execution_enabled(ctrl) is True


def test_oracle_capability_depends_on_driver(monkeypatch):
    engine.load_predefined_queries(force=True)
    ctrl = engine.get_control_by_id("ORX-001")

    # Driver present -> Ready.
    monkeypatch.setattr(engine, "_dependency_available", lambda tech: True)
    assert engine.assess_execution_capability(ctrl)["status"] == "Ready"

    # Driver missing -> Dependency Missing (not runnable).
    monkeypatch.setattr(engine, "_dependency_available",
                        lambda tech: False if tech == "Oracle" else True)
    cap = engine.assess_execution_capability(ctrl)
    assert cap["status"] == "Dependency Missing"
    assert "python-oracledb" in cap["reason"]
    assert engine.is_live_execution_enabled(ctrl) is False


def test_windows_remains_connector_missing():
    # Windows is still a generic (non-runnable) connector -> Connector Missing.
    ctrl = {"predefined": True, "technology": "Windows", "control_id": "OS-001", "query": "get-hotfix"}
    cap = engine.assess_execution_capability(ctrl)
    assert cap["status"] == "Connector Missing"


# --------------------------------------------------------------------------- #
# Connector routing
# --------------------------------------------------------------------------- #
def test_routing_infra_technologies():
    assert type(connector_for_technology("NGINX")).__name__ == "LinuxConnector"
    assert type(connector_for_technology("Linux")).__name__ == "LinuxConnector"
    assert type(connector_for_technology(RHEL8)).__name__ == "LinuxConnector"
    assert type(connector_for_technology(RHEL9)).__name__ == "LinuxConnector"
    # Oracle routes to OracleConnector when oracledb is importable; else None.
    conn = connector_for_technology("Oracle")
    if conn is not None:
        assert type(conn).__name__ == "OracleConnector"
        assert conn.port == 1521


def test_nginx_uses_nginx_container(monkeypatch):
    monkeypatch.setenv("ECS_NGINX_CONTAINER", "nginx-demo")
    from modules.operations.engines.linux_connector import get_nginx_config

    cfg = get_nginx_config()
    assert cfg["container"] == "nginx-demo"


# --------------------------------------------------------------------------- #
# Allow-lists
# --------------------------------------------------------------------------- #
def test_oracle_allowlist_covers_catalog():
    for c in catalog.ORACLE_QUERIES:
        assert engine._normalize_query_allowlist(c["query"]) in engine.ALLOWED_ORACLE_QUERIES


def test_shell_control_ids_registered():
    for cid in NGX + LNX + RH8 + RH9:
        assert cid in catalog.SHELL_CONTROL_IDS


# --------------------------------------------------------------------------- #
# Dispatch (mocked; no live target)
# --------------------------------------------------------------------------- #
def test_run_oracle_missing_driver(monkeypatch):
    engine.load_predefined_queries(force=True)
    # Force ImportError on `import oracledb` inside the connector's connect().
    monkeypatch.setitem(sys.modules, "oracledb", None)
    res = engine.run_oracle_query("ORX-001", "tester")
    # Either the run reports failure, or capability blocks it — both are safe.
    assert res["ok"] is False


def test_run_shell_control_routes_and_reports(monkeypatch):
    engine.load_predefined_queries(force=True)

    calls = {}

    class _FakeConn:
        def __init__(self, **kw):
            calls["kw"] = kw

        def connect(self):
            return True

        def execute(self, cmd):
            calls["cmd"] = cmd
            from modules.operations.engines.query_connectors import ConnectorResult
            return ConnectorResult(success=True, output="ok", metadata={"rows_returned": 1})

        def disconnect(self):
            return None

    import modules.operations.engines.linux_connector as lc
    monkeypatch.setattr(lc, "LinuxConnector", lambda **kw: _FakeConn(**kw))
    res = engine.run_shell_control("RH9-001", "tester")
    assert res["ok"] is True
    assert calls["cmd"] == "cat /etc/redhat-release"


def test_run_shell_rejects_non_shell_control():
    engine.load_predefined_queries(force=True)
    res = engine.run_shell_control("PGX-001", "tester")  # a DB control
    assert res["ok"] is False
    assert res["error_type"] == "unsupported_technology"


# --------------------------------------------------------------------------- #
# Frontend Technology filter includes the new technologies
# --------------------------------------------------------------------------- #
def test_technology_filter_options_include_infra():
    dash = engine.get_predefined_queries_dashboard(per_page=1)
    opts = dash["technology_options"]
    for tech in ("Oracle", "NGINX", "Linux",
                 "Red Hat Enterprise Linux 8.x", "Red Hat Enterprise Linux 9.x"):
        assert tech in opts


@pytest.mark.parametrize("tech,prefix,count", [
    ("Oracle", "ORX", 10),
    ("NGINX", "NGX", 8),
    ("Red Hat Enterprise Linux 8.x", "RH8", 8),
    ("Red Hat Enterprise Linux 9.x", "RH9", 8),
])
def test_technology_filter_narrows_to_infra(tech, prefix, count):
    dash = engine.get_predefined_queries_dashboard(technology=tech, per_page=500)
    ids = [r["control_id"] for r in dash["rows"]]
    supplementary = [cid for cid in ids if cid.startswith(prefix)]
    assert len(supplementary) == count
    assert all((r.get("technology") or "") == tech for r in dash["rows"])
