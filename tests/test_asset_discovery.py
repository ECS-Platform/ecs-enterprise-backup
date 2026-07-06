"""Tests for asset discovery + the asset service facade (M1, Module 2).

All sources are exercised offline: ServiceNow via a MOCK transport (never a real
call), manual import, docker-compose parsed from a temp file, and the existing
enterprise-GRC CMDB. No live Docker / network required.
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import textwrap

import pytest

from modules.audit_intelligence.engines import asset_discovery as disco
from modules.audit_intelligence.engines import technology_control_mapping as mapping
from modules.audit_intelligence.engines import technology_fingerprint as fp
from modules.audit_intelligence.models import Asset
from modules.audit_intelligence.services import asset_service as svc


@pytest.fixture(autouse=True)
def _fresh_cache():
    mapping.reset_cache()
    fp.reset_cache()
    yield
    mapping.reset_cache()
    fp.reset_cache()


# --------------------------------------------------------------------------- #
# Manual import
# --------------------------------------------------------------------------- #
def test_manual_discovery_normalizes_and_links_controls():
    records = [
        {"asset_id": "M1", "hostname": "oracle-prod-01", "technology": "Oracle",
         "environment": "Production", "owner": "DBA", "criticality": "Tier-1"},
        {"asset_id": "M2", "hostname": "web-01", "image": "nginx:1.25",
         "environment": "Production"},
    ]
    assets = disco.discover_from_manual(records)
    assert len(assets) == 2
    assert all(isinstance(a, Asset) for a in assets)

    oracle = next(a for a in assets if a.asset_id == "M1")
    assert oracle.technology == "Oracle"
    assert oracle.source == "manual"
    # Cross-linked to applicable controls/frameworks from Module 1.
    assert oracle.applicable_control_ids
    assert oracle.applicable_frameworks

    web = next(a for a in assets if a.asset_id == "M2")
    assert web.technology == "NGINX"
    assert web.version == "1.25"


def test_manual_unknown_tech_has_no_controls():
    assets = disco.discover_from_manual([{"asset_id": "X", "hostname": "mystery-box"}])
    assert assets[0].technology == ""  # unknown -> not linked
    assert assets[0].applicable_control_ids == ()


# --------------------------------------------------------------------------- #
# ServiceNow (mock transport — never a real call)
# --------------------------------------------------------------------------- #
def _servicenow_transport(method, url, headers, params):
    # Mimic ServiceNow table API response for cmdb_ci_server.
    return {
        "result": [
            {"sys_id": "SNOW-1", "name": "svc-nginx-lb", "sys_class_name": "cmdb_ci_server",
             "ip_address": "10.0.0.1", "used_for": "Production", "assigned_to": "InfraOps"},
            {"sys_id": "SNOW-2", "name": "db-postgres-01", "sys_class_name": "cmdb_ci_server",
             "ip_address": "10.0.0.2", "used_for": "UAT", "assigned_to": "DBA"},
        ]
    }


def test_servicenow_discovery_with_mock_transport(monkeypatch):
    # Provide a base_url so the skeleton considers itself configured.
    monkeypatch.setenv("ECS_SERVICENOW_BASE_URL", "https://uat.example.service-now.com")
    assets = disco.discover_from_servicenow(transport=_servicenow_transport)
    assert len(assets) == 2
    ids = {a.asset_id for a in assets}
    assert ids == {"SNOW-1", "SNOW-2"}
    nginx = next(a for a in assets if a.asset_id == "SNOW-1")
    assert nginx.technology == "NGINX"
    assert nginx.source == "servicenow_cmdb"
    assert nginx.environment == "Production"


def test_servicenow_not_configured_returns_empty(monkeypatch):
    monkeypatch.delenv("ECS_SERVICENOW_BASE_URL", raising=False)
    # No base_url + no transport -> skeleton raises IntegrationNotConfigured, handled.
    assert disco.discover_from_servicenow() == []


# --------------------------------------------------------------------------- #
# docker-compose (offline parse of a temp file)
# --------------------------------------------------------------------------- #
def test_docker_compose_discovery_offline(tmp_path):
    compose = tmp_path / "docker-compose.yml"
    compose.write_text(
        textwrap.dedent(
            """
            services:
              postgres-demo:
                image: postgres:16
                container_name: postgres-demo
                ports: ["15432:5432"]
              redis:
                image: redis:7.2
                ports: ["16379:6379"]
              mystery:
                image: some/unknown-image:1.0
            """
        ),
        encoding="utf-8",
    )
    assets = disco.discover_from_docker_compose(compose)
    by_id = {a.asset_id: a for a in assets}
    assert set(by_id) == {"postgres-demo", "redis", "mystery"}
    assert by_id["postgres-demo"].technology == "PostgreSQL"
    assert by_id["redis"].technology == "Redis"
    assert by_id["mystery"].technology == ""  # unknown image
    assert all(a.source == "docker_compose" for a in assets)
    assert all(a.environment == "Local Demo" for a in assets)


def test_docker_compose_missing_file_returns_empty(tmp_path):
    assert disco.discover_from_docker_compose(tmp_path / "nope.yml") == []


def test_real_repo_compose_parses_without_docker():
    """The repo's actual docker-compose.yml parses offline into assets."""
    assets = disco.discover_from_docker_compose()
    assert len(assets) > 5  # many demo services
    assert any(a.technology == "PostgreSQL" for a in assets)


# --------------------------------------------------------------------------- #
# enterprise-GRC CMDB reuse
# --------------------------------------------------------------------------- #
def test_enterprise_grc_discovery_reuses_existing_inventory():
    assets = disco.discover_from_enterprise_grc()
    assert assets  # existing CMDB has rows
    assert all(a.source == "enterprise_grc_cmdb" for a in assets)


# --------------------------------------------------------------------------- #
# Aggregate discover() + de-dup
# --------------------------------------------------------------------------- #
def test_discover_aggregates_and_dedupes():
    manual = [{"asset_id": "postgres-demo", "hostname": "postgres-demo", "image": "postgres:16"}]
    # Same asset_id will appear from both manual and docker-compose -> de-duped.
    assets = disco.discover(manual_records=manual, include_docker_compose=True)
    ids = [a.asset_id for a in assets]
    assert ids.count("postgres-demo") == 1  # de-duplicated (manual wins)


def test_discover_default_is_noop():
    assert disco.discover() == []


# --------------------------------------------------------------------------- #
# Service facade
# --------------------------------------------------------------------------- #
def test_service_inventory_and_rollups():
    manual = [
        {"asset_id": "A1", "hostname": "pg-1", "image": "postgres:16", "environment": "Production"},
        {"asset_id": "A2", "hostname": "pg-2", "image": "postgres:15", "environment": "UAT"},
        {"asset_id": "A3", "hostname": "mystery", "environment": "UAT"},
    ]
    assets = svc.discover_assets(manual_records=manual)

    inv = svc.inventory(assets)
    assert len(inv) == 3 and isinstance(inv[0], dict)

    tech_inv = svc.technology_inventory(assets)
    pg = next(r for r in tech_inv if r["technology"] == "PostgreSQL")
    assert pg["asset_count"] == 2
    assert set(pg["environments"]) == {"Production", "UAT"}

    report = svc.fingerprint_report(assets)
    assert report["total"] == 3
    assert sum(report["confidence_banding"].values()) == 3

    cov = svc.coverage_summary(assets)
    assert cov["total_assets"] == 3
    assert cov["identified_assets"] == 2
    assert cov["unidentified_assets"] == 1
    assert 0.0 <= cov["identification_rate"] <= 1.0


def test_service_coverage_links_frameworks():
    assets = svc.discover_assets(
        manual_records=[{"asset_id": "N", "hostname": "nginx-1", "image": "nginx:1.25"}]
    )
    cov = svc.coverage_summary(assets)
    assert "PCI DSS" in cov["applicable_frameworks"]
    assert cov["applicable_control_count"] > 0
