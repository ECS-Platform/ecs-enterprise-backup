"""Docker-compose tests for the extended technology demo targets.

Parses docker-compose.yml (no image pulls, no containers). Verifies apache-demo,
tomcat-demo, mongodb-demo are present and profile-gated; sqlserver-demo is
optional/isolated and not in any umbrella profile or default; existing Oracle
remains optional-only; existing infra-demo behavior is not broken.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
COMPOSE = ROOT / "docker-compose.yml"


@pytest.fixture(scope="module")
def compose() -> dict:
    with COMPOSE.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _profiles(svc: dict) -> set[str]:
    return set(svc.get("profiles", []) or [])


def test_apache_demo_present_and_gated(compose):
    svc = compose["services"]["apache-demo"]
    assert "httpd" in svc["image"]
    assert "apache-demo" in _profiles(svc)
    assert "infra-demo-extended" in _profiles(svc)


def test_tomcat_demo_present_and_gated(compose):
    svc = compose["services"]["tomcat-demo"]
    assert "tomcat" in svc["image"]
    assert "tomcat-demo" in _profiles(svc)
    assert "infra-demo-extended" in _profiles(svc)


def test_mongodb_demo_present_and_gated(compose):
    svc = compose["services"]["mongodb-demo"]
    assert "mongo" in svc["image"]
    assert "mongodb-demo" in _profiles(svc)
    assert "db-demo-extended" in _profiles(svc)


def test_sqlserver_demo_optional_and_isolated(compose):
    svc = compose["services"]["sqlserver-demo"]
    assert "mssql" in svc["image"].lower() or "sql" in svc["image"].lower()
    prof = _profiles(svc)
    assert prof == {"sqlserver-demo"}, "SQL Server must ONLY be in the sqlserver-demo profile"
    assert "infra-demo" not in prof
    assert "infra-demo-extended" not in prof
    assert "db-demo-extended" not in prof
    assert "db-targets" not in prof


def test_sqlserver_not_in_default(compose):
    assert _profiles(compose["services"]["sqlserver-demo"]), "sqlserver-demo must be opt-in"


def test_oracle_remains_optional_only(compose):
    prof = _profiles(compose["services"]["oracle-demo"])
    assert prof == {"oracle-demo"}


def test_extended_services_are_opt_in(compose):
    for name in ("apache-demo", "tomcat-demo", "mongodb-demo", "sqlserver-demo"):
        assert _profiles(compose["services"][name]), f"{name} must be profile-gated (not default)"


def test_existing_infra_demo_not_broken(compose):
    # The base infra-demo profile still groups nginx + rhel.
    assert "infra-demo" in _profiles(compose["services"]["nginx-demo"])
    assert "infra-demo" in _profiles(compose["services"]["rhel8-demo"])
    assert "infra-demo" in _profiles(compose["services"]["rhel9-demo"])
    # ...and does NOT accidentally include the extended/optional services.
    for name in ("apache-demo", "tomcat-demo", "mongodb-demo", "sqlserver-demo", "oracle-demo"):
        assert "infra-demo" not in _profiles(compose["services"][name])


def test_redis_service_reused(compose):
    # Redis checks reuse the existing redis service (no new redis-demo needed).
    assert "redis" in compose["services"]
    assert "redis" in compose["services"]["redis"]["image"]


def test_existing_db_targets_intact(compose):
    for name in ("yugabyte", "mysql-demo"):
        assert "db-targets" in _profiles(compose["services"][name])
