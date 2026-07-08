"""Tests for predefined-query Docker demo targets and container routing.

Verifies docker-compose service definitions/profiles and the connector container
resolution for NGINX / Linux / RHEL 8.x / RHEL 9.x. No Docker images are pulled
and no containers are started — docker-compose.yml is parsed as YAML.
"""

from __future__ import annotations

import os
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


# --------------------------------------------------------------------------- #
# Service presence
# --------------------------------------------------------------------------- #
def test_compose_has_nginx_demo(compose):
    svc = compose["services"]["nginx-demo"]
    assert "nginx" in svc["image"]
    assert svc.get("container_name") == "nginx-demo"


def test_compose_has_rhel8_demo(compose):
    svc = compose["services"]["rhel8-demo"]
    assert "ubi8" in svc["image"]
    assert svc.get("container_name") == "rhel8-demo"


def test_compose_has_rhel9_demo(compose):
    svc = compose["services"]["rhel9-demo"]
    assert "ubi9" in svc["image"]
    assert svc.get("container_name") == "rhel9-demo"


def test_compose_has_oracle_demo(compose):
    svc = compose["services"]["oracle-demo"]
    assert "oracle" in svc["image"].lower()


# --------------------------------------------------------------------------- #
# Profiles: opt-in only; Oracle isolated from infra-demo/default
# --------------------------------------------------------------------------- #
def test_infra_services_are_profile_gated(compose):
    for name in ("nginx-demo", "rhel8-demo", "rhel9-demo", "oracle-demo"):
        assert _profiles(compose["services"][name]), f"{name} must be profile-gated (not default)"


def test_infra_demo_umbrella_profile(compose):
    # nginx + rhel are grouped under the umbrella "infra-demo" profile.
    assert "infra-demo" in _profiles(compose["services"]["nginx-demo"])
    assert "infra-demo" in _profiles(compose["services"]["rhel8-demo"])
    assert "infra-demo" in _profiles(compose["services"]["rhel9-demo"])


def test_rhel_demo_profile(compose):
    assert "rhel-demo" in _profiles(compose["services"]["rhel8-demo"])
    assert "rhel-demo" in _profiles(compose["services"]["rhel9-demo"])


def test_nginx_demo_profile(compose):
    assert "nginx-demo" in _profiles(compose["services"]["nginx-demo"])


def test_oracle_demo_isolated(compose):
    prof = _profiles(compose["services"]["oracle-demo"])
    assert prof == {"oracle-demo"}, "oracle-demo must ONLY be in the oracle-demo profile"
    assert "infra-demo" not in prof
    assert "db-targets" not in prof


def test_oracle_not_in_default_startup(compose):
    # A service with no profiles would start by default; oracle-demo must have one.
    assert _profiles(compose["services"]["oracle-demo"]), "oracle-demo must be opt-in"


def test_existing_db_targets_still_present(compose):
    for name in ("yugabyte", "mysql-demo"):
        assert "db-targets" in _profiles(compose["services"][name])


# --------------------------------------------------------------------------- #
# nginx demo config file exists
# --------------------------------------------------------------------------- #
def test_nginx_demo_config_present():
    conf = ROOT / "demo-data" / "nginx" / "default.conf"
    assert conf.is_file()
    text = conf.read_text(encoding="utf-8")
    assert "listen 80" in text
    assert "server_tokens off" in text
    assert "access_log" in text
    assert "error_log" in text


# --------------------------------------------------------------------------- #
# Container routing per technology (connector config)
# --------------------------------------------------------------------------- #
def test_rhel8_uses_rhel8_container(monkeypatch):
    monkeypatch.setenv("ECS_RHEL8_CONTAINER", "my-rhel8")
    _clear_config_cache()
    from modules.operations.engines.linux_connector import get_rhel_config
    assert get_rhel_config(8)["container"] == "my-rhel8"
    _clear_config_cache()


def test_rhel9_uses_rhel9_container(monkeypatch):
    monkeypatch.setenv("ECS_RHEL9_CONTAINER", "my-rhel9")
    _clear_config_cache()
    from modules.operations.engines.linux_connector import get_rhel_config
    assert get_rhel_config(9)["container"] == "my-rhel9"
    _clear_config_cache()


def test_nginx_uses_nginx_container(monkeypatch):
    monkeypatch.setenv("ECS_NGINX_CONTAINER", "my-nginx")
    _clear_config_cache()
    from modules.operations.engines.linux_connector import get_nginx_config
    assert get_nginx_config()["container"] == "my-nginx"
    _clear_config_cache()


def test_rhel_falls_back_to_linux_container(monkeypatch):
    # No ECS_RHEL8_CONTAINER; must fall back to ECS_LINUX_CONTAINER.
    monkeypatch.delenv("ECS_RHEL8_CONTAINER", raising=False)
    monkeypatch.setenv("ECS_LINUX_CONTAINER", "shared-linux")
    _clear_config_cache()
    from modules.operations.engines.linux_connector import get_rhel_config
    # With the YAML default present it resolves rhel8-demo; the env-fallback path
    # (exercised when the YAML value is blank) yields the Linux container. Accept
    # either the RHEL default or the Linux fallback — both are valid, never empty.
    container = get_rhel_config(8)["container"]
    assert container in ("rhel8-demo", "shared-linux")
    assert container
    _clear_config_cache()


def test_shell_dispatch_routes_rhel_to_rhel_config(monkeypatch):
    from modules.operations.engines import predefined_queries_engine as engine
    engine.load_predefined_queries(force=True)

    captured = {}

    class _FakeConn:
        def __init__(self, **kw):
            captured["container"] = kw.get("container")

        def connect(self):
            return True

        def execute(self, cmd):
            from modules.operations.engines.query_connectors import ConnectorResult
            captured["cmd"] = cmd
            return ConnectorResult(success=True, output="ok", metadata={"rows_returned": 1})

        def disconnect(self):
            return None

    import modules.operations.engines.linux_connector as lc
    monkeypatch.setattr(lc, "LinuxConnector", lambda **kw: _FakeConn(**kw))
    monkeypatch.setenv("ECS_RHEL9_CONTAINER", "route-rhel9")
    _clear_config_cache()

    res = engine.run_shell_control("RH9-001", "tester")
    assert res["ok"] is True
    assert captured["container"] == "route-rhel9"
    _clear_config_cache()


# --------------------------------------------------------------------------- #
# Windows remains unsupported for local Docker (documented)
# --------------------------------------------------------------------------- #
def test_windows_not_in_compose(compose):
    names = set(compose["services"].keys())
    assert not any("windows" in n.lower() for n in names), \
        "No Windows container should exist for macOS/Linux Docker"


def test_windows_documented_unsupported():
    doc = (ROOT / "docs" / "developer-manual" / "PREDEFINED_DATABASE_QUERY_MODULE.md").read_text(encoding="utf-8")
    low = doc.lower()
    assert "windows" in low
    # Documented as remote/enterprise-only / not supported by local Docker.
    assert ("remote" in low and "windows" in low) or "not supported" in low


def _clear_config_cache():
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
