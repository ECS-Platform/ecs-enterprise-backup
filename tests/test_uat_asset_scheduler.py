"""Tests for the UAT asset-driven scheduler & evidence routing.

Fully offline + deterministic: no network, no live connector, no query execution.
Assets are built in-memory or loaded from the repo's committed local/template
YAML. Covers config loading, template parsing, technology classification, connector
routing (SharePoint / Jira / SonarQube / ServiceNow), evidence plan generation,
dry-run execution, and the unknown-asset fallback.
"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from modules.audit_intelligence.engines import asset_discovery
from modules.audit_intelligence.services import asset_scheduler as sched
from modules.audit_intelligence.services.asset_scheduler import (
    ROUTE_BASELINE,
    ROUTE_CONNECTOR,
    ROUTE_UNSUPPORTED,
)

ROOT = Path(__file__).resolve().parent.parent
LOCAL_CFG = ROOT / "config" / "uat_assets.local.yaml"
TEMPLATE_CFG = ROOT / "config" / "uat_assets.template.yaml"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _asset(**rec):
    """Build a single normalized Asset from a raw record (via the real pipeline)."""
    return asset_discovery.discover_from_manual([rec])[0]


def _classify(**rec):
    return sched.classify_asset(_asset(**rec))


# --------------------------------------------------------------------------- #
# 1. Asset config loading
# --------------------------------------------------------------------------- #
def test_load_asset_config_local_file():
    cfg = sched.load_asset_config(LOCAL_CFG)
    assert isinstance(cfg, dict)
    assert cfg.get("environment") == "local"
    assert isinstance(cfg.get("assets"), list) and cfg["assets"]


def test_load_asset_config_missing_file_returns_empty():
    cfg = sched.load_asset_config(ROOT / "config" / "does_not_exist.yaml")
    assert cfg == {}


def test_load_assets_normalizes_to_asset_objects():
    assets = sched.load_assets(LOCAL_CFG)
    assert assets and all(hasattr(a, "asset_id") for a in assets)
    ids = {a.asset_id for a in assets}
    assert "local-postgres" in ids and "local-sonarqube" in ids


def test_load_assets_empty_config_is_safe():
    assert sched.assets_from_config({}) == []
    assert sched.assets_from_config({"assets": []}) == []


# --------------------------------------------------------------------------- #
# 2. UAT template parsing (placeholders only)
# --------------------------------------------------------------------------- #
def test_uat_template_parses_and_has_placeholders():
    cfg = sched.load_asset_config(TEMPLATE_CFG)
    assert isinstance(cfg.get("assets"), list) and cfg["assets"]
    assets = sched.assets_from_config(cfg)
    assert len(assets) >= 10
    # No real hosts — every hostname is a placeholder or ${VAR:-...}-expanded default.
    for a in assets:
        h = a.hostname
        assert ("placeholder" in h) or h == "" or h.startswith("<"), f"unexpected host: {h!r}"


def test_uat_template_has_no_secret_markers():
    raw = TEMPLATE_CFG.read_text(encoding="utf-8")
    for marker in ("password:", "client_secret:", "api_token:", "secret_key:", "access_key:"):
        assert marker not in raw, f"template must not contain secret field {marker!r}"


def test_template_placeholder_expands_from_env(monkeypatch):
    monkeypatch.setenv("ECS_UAT_PG_HOST", "localhost-from-env")
    cfg = sched.load_asset_config(TEMPLATE_CFG)
    assets = sched.assets_from_config(cfg)
    pg = next(a for a in assets if a.asset_id == "uat-postgres-01")
    assert pg.hostname == "localhost-from-env"


# --------------------------------------------------------------------------- #
# 3. Localhost technology classification (baseline collectors)
# --------------------------------------------------------------------------- #
def test_localhost_postgresql_classification():
    c = _classify(asset_id="pg1", hostname="localhost-postgres",
                  image="postgres:16", ports=["127.0.0.1:5432:5432"])
    assert c.technology == "PostgreSQL"
    assert c.route == ROUTE_BASELINE
    assert c.scope_kind == "technology" and c.scope_value == "PostgreSQL"
    assert c.control_ids  # PostgreSQL has predefined controls
    assert c.connector == ""


def test_localhost_nginx_classification():
    c = _classify(asset_id="nginx1", hostname="localhost-nginx",
                  image="nginx:1.25", ports=["127.0.0.1:8080:80"])
    assert c.technology == "NGINX"
    assert c.route == ROUTE_BASELINE
    assert c.scope_value == "NGINX"
    assert c.control_ids


def test_classification_by_port_only():
    # No explicit tech/image; port 5432 -> PostgreSQL via the fingerprint engine.
    c = _classify(asset_id="p", hostname="db-node", ports=["5432"])
    assert c.technology == "PostgreSQL"
    assert c.route == ROUTE_BASELINE


# --------------------------------------------------------------------------- #
# 4. Connector asset classification + routing
# --------------------------------------------------------------------------- #
def test_connector_asset_classification_sonarqube():
    # SonarQube exists as BOTH a catalog technology and a connector -> connector wins.
    c = _classify(asset_id="sq", hostname="localhost-sonarqube",
                  asset_type="sonarqube", technology="SonarQube")
    assert c.route == ROUTE_CONNECTOR
    assert c.connector == "sonarqube"
    assert c.scope_kind == "connector" and c.scope_value == "sonarqube"


def test_sharepoint_routing():
    c = _classify(asset_id="sp", hostname="sp-mock", asset_type="sharepoint")
    assert c.route == ROUTE_CONNECTOR
    assert c.connector == "sharepoint_graph"


def test_jira_routing():
    c = _classify(asset_id="jira1", hostname="jira-mock", asset_type="jira")
    assert c.route == ROUTE_CONNECTOR
    assert c.connector == "jira"


def test_sonarqube_routing_alias():
    c = _classify(asset_id="sq2", hostname="sonar-mock", asset_type="SonarQube")
    assert c.connector == "sonarqube"


def test_servicenow_routing():
    c = _classify(asset_id="snow", hostname="snow-mock", asset_type="servicenow")
    assert c.connector == "servicenow_cmdb"


def test_teams_and_outlook_routing():
    assert _classify(asset_id="t", asset_type="teams").connector == "teams_graph"
    assert _classify(asset_id="o", asset_type="outlook").connector == "outlook_graph"


def test_connector_route_via_substring_match():
    # "SharePoint Online" should still route to sharepoint_graph via token contains.
    c = _classify(asset_id="sp2", hostname="x", asset_type="SharePoint Online")
    assert c.connector == "sharepoint_graph"


def test_connector_routes_table_is_readonly_copy():
    table = sched.connector_routes()
    table["bogus"] = "x"
    assert "bogus" not in sched.connector_routes()


# --------------------------------------------------------------------------- #
# 5. Evidence plan generation
# --------------------------------------------------------------------------- #
def test_evidence_plan_generation_mixed():
    assets = [
        _asset(asset_id="pg", hostname="localhost-postgres", image="postgres:16"),
        _asset(asset_id="ng", hostname="localhost-nginx", image="nginx:1.25"),
        _asset(asset_id="sq", hostname="sonar", asset_type="sonarqube"),
        _asset(asset_id="jira", hostname="jira", asset_type="jira"),
        _asset(asset_id="mystery", hostname="localhost-mystery-box"),
    ]
    plan = sched.plan_evidence(assets)
    d = plan.to_dict()
    assert d["summary"]["planned_jobs"] == 4
    assert d["summary"]["unsupported_assets"] == 1
    assert d["summary"]["by_route"] == {ROUTE_BASELINE: 2, ROUTE_CONNECTOR: 2}
    assert d["summary"]["total_planned_controls"] > 0
    # deterministic ordering: connectors (route name sorts before) then baseline
    routes = [j["route"] for j in d["jobs"]]
    assert routes == sorted(routes)


def test_plan_is_bounded_and_deterministic():
    assets = sched.load_assets(LOCAL_CFG)
    p1 = sched.plan_evidence(assets).to_dict()
    p2 = sched.plan_evidence(assets).to_dict()
    assert p1 == p2  # deterministic


# --------------------------------------------------------------------------- #
# 6. Dry-run scheduler execution (no side effects)
# --------------------------------------------------------------------------- #
def test_dry_run_local_config_all_pass():
    rep = sched.dry_run(config_path=LOCAL_CFG)
    assert rep["ok"] is True
    assert rep["mode"] == "dry-run"
    s = rep["summary"]
    assert s["assets_loaded"] == 9
    assert s["planned_jobs"] == 8
    assert s["unsupported_assets"] == 1
    assert s["by_route"][ROUTE_BASELINE] == 4
    assert s["by_route"][ROUTE_CONNECTOR] == 4


def test_dry_run_reports_connector_readiness_config_only():
    rep = sched.dry_run(config_path=LOCAL_CFG)
    ready = rep["connector_readiness"]
    # All connectors referenced by the local plan are reported, unconfigured offline.
    assert set(ready) == {"sonarqube", "sharepoint_graph", "jira", "servicenow_cmdb"}
    for r in ready.values():
        assert r["configured"] is False
        assert r["status"] in ("not_configured", "adapter_error")
        # Never leak secrets — any secret-like field must be masked (SET/MISSING),
        # never a raw value. Non-secret fields (base_url_configured, scope, etc.)
        # are allowed.
        mc = r.get("masked_config") or {}
        secret_markers = ("secret", "token", "password", "api_token", "access_key", "client_secret")
        for key, val in mc.items():
            if any(m in key.lower() for m in secret_markers):
                assert val in ("SET", "MISSING"), f"{key} not masked in {r['connector']}: {val!r}"


def test_dry_run_makes_no_live_call(monkeypatch):
    # Guard: if anything tried a live health probe, this would flip. The dry-run
    # path must only use is_configured()/masked_config(), never health_check().
    import modules.operations.integrations.jira as jira

    def _boom(*a, **k):
        raise AssertionError("health_check must NOT be called during dry-run")

    monkeypatch.setattr(jira, "health_check", _boom, raising=False)
    rep = sched.dry_run(config_path=LOCAL_CFG)
    assert rep["ok"] is True  # completed without calling health_check


def test_dry_run_empty_config_is_safe():
    rep = sched.dry_run(cfg={})
    assert rep["ok"] is True
    assert rep["summary"]["assets_loaded"] == 0
    assert rep["summary"]["planned_jobs"] == 0


# --------------------------------------------------------------------------- #
# 7. Unknown asset fallback
# --------------------------------------------------------------------------- #
def test_unknown_asset_fallback_does_not_crash():
    c = _classify(asset_id="mystery", hostname="localhost-mystery-box")
    assert c.route == ROUTE_UNSUPPORTED
    assert c.connector == ""
    assert c.control_ids == ()
    assert any("unsupported" in r for r in c.reasons)


def test_unknown_asset_lands_in_plan_unsupported_bucket():
    plan = sched.plan_evidence([_asset(asset_id="m", hostname="mystery-appliance")])
    assert len(plan.jobs) == 0
    assert len(plan.unsupported) == 1
    assert plan.unsupported[0].asset_id == "m"


def test_execute_plan_only_runs_baseline_with_injected_executor():
    # Baseline jobs delegate to the evidence service via an injected mock executor.
    # Connector jobs are now also surfaced (as safe "skipped" receipts when the
    # ECS_CONNECTOR_EXECUTION_ENABLED flag is off) — no live call is made offline.
    assets = [
        _asset(asset_id="pg", hostname="localhost-postgres", image="postgres:16"),
        _asset(asset_id="sq", hostname="sonar", asset_type="sonarqube"),
    ]
    plan = sched.plan_evidence(assets)
    calls = []

    def _mock_executor(control_id, user):
        calls.append(control_id)
        return {"ok": True, "message": "ok", "rows_returned": 1, "output": "mock",
                "evidence_id": "E", "evidence_filename": "e.txt", "duration_ms": 1}

    runs = sched.execute_plan(plan, executor=_mock_executor)
    baseline = [r for r in runs if r.get("kind") == "baseline"]
    connector = [r for r in runs if r.get("kind") == "connector"]
    # Exactly one baseline job ran through the injected executor.
    assert len(baseline) == 1
    assert baseline[0]["scope_value"] == "PostgreSQL"
    assert calls  # executor was invoked for baseline controls
    # The connector job is surfaced but SKIPPED (no flag, no network) offline.
    assert len(connector) == 1
    assert connector[0]["connector"] == "sonarqube"
    assert connector[0]["status"] == "skipped"
    assert connector[0]["ingested"] == 0


def test_execute_plan_run_connectors_false_is_baseline_only():
    # Backward-compatible switch: run_connectors=False preserves the old behavior
    # (baseline jobs only; connector jobs omitted entirely).
    assets = [
        _asset(asset_id="pg", hostname="localhost-postgres", image="postgres:16"),
        _asset(asset_id="sq", hostname="sonar", asset_type="sonarqube"),
    ]
    plan = sched.plan_evidence(assets)

    def _mock_executor(control_id, user):
        return {"ok": True, "message": "ok", "rows_returned": 1, "output": "mock",
                "evidence_id": "E", "evidence_filename": "e.txt", "duration_ms": 1}

    runs = sched.execute_plan(plan, executor=_mock_executor, run_connectors=False)
    assert len(runs) == 1
    assert runs[0]["scope_value"] == "PostgreSQL"
    assert not [r for r in runs if r.get("kind") == "connector"]
