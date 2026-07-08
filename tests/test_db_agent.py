"""Tests for the DB Agent prototype.

Verifies the prototype-security contract:
  * the agent starts and serves with NO enterprise security infra configured;
  * no mTLS / JWT / OIDC / OAuth / Vault / certificates / PKI required;
  * /healthz is always ok; /readyz reports degraded (503) without blocking;
  * config resolves from env/YAML with secrets MASKED and no hardcoded creds;
  * all ENABLE_* security flags default OFF (and toggle on when set);
  * connectivity checks degrade gracefully (never raise) with no/unreachable
    targets, reusing the ECS database connector.

Fully offline. Env is isolated per test.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

_AGENT_ENV = [
    "DB_HOST", "DB_PORT", "DB_NAME", "DB_USERNAME", "DB_PASSWORD", "DB_SSLMODE",
    "DB_TIMEOUT_SEC", "SSH_HOST", "SSH_PORT", "SSH_USERNAME", "SSH_PASSWORD",
    "SSH_TIMEOUT_SEC", "DB_AGENT_HOST", "DB_AGENT_PORT", "DB_AGENT_CONFIG",
    "ENABLE_MTLS", "ENABLE_JWT", "ENABLE_VAULT", "ENABLE_OIDC", "ENABLE_CERT_AUTH",
]


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    for name in _AGENT_ENV:
        monkeypatch.delenv(name, raising=False)
    # Point YAML at a non-existent path so tests never pick up config/db_agent.yaml.
    monkeypatch.setenv("DB_AGENT_CONFIG", str(tmp_path / "none.yaml"))
    yield


@pytest.fixture
def client():
    from db_agent.app import app
    return TestClient(app)


# --------------------------------------------------------------------------- #
# Startup / liveness / readiness (no security infra)
# --------------------------------------------------------------------------- #
def test_agent_starts_and_serves_without_any_security(client):
    # The mere fact that TestClient(app) built + serves proves startup needs no
    # mTLS/JWT/OIDC/Vault/certs. Root advertises prototype status.
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["prototype"] is True
    assert body["production_secure"] is False


def test_healthz_always_ok(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_readyz_degraded_does_not_block(client):
    # With nothing configured, readiness is degraded (503) but the agent serves.
    r = client.get("/readyz")
    assert r.status_code == 503
    assert r.json()["status"] == "degraded"
    # Agent is still fully responsive on other routes.
    assert client.get("/healthz").status_code == 200


def test_prototype_mode_header_present(client):
    assert client.get("/healthz").headers.get("X-DB-Agent-Mode") == "prototype"


# --------------------------------------------------------------------------- #
# Config: env/YAML resolution, masking, no hardcoded creds
# --------------------------------------------------------------------------- #
def test_config_masks_secrets(client, monkeypatch):
    monkeypatch.setenv("DB_HOST", "db.internal")
    monkeypatch.setenv("DB_NAME", "appdb")
    monkeypatch.setenv("DB_USERNAME", "ro_user")
    monkeypatch.setenv("DB_PASSWORD", "super-secret-value")
    cfg = client.get("/config").json()
    # Password/username are reported as SET/MISSING — never the raw value.
    assert cfg["db"]["password"] == "SET"
    assert cfg["db"]["username"] == "SET"
    assert "super-secret-value" not in str(cfg)
    assert cfg["db"]["host"] == "db.internal"
    assert cfg["db"]["configured"] is True


def test_config_unset_is_missing_not_hardcoded(client):
    cfg = client.get("/config").json()
    assert cfg["db"]["username"] == "MISSING"
    assert cfg["db"]["password"] == "MISSING"
    assert cfg["db"]["host"] == "(unset)"
    assert cfg["db"]["configured"] is False


def test_config_loads_from_yaml(monkeypatch, tmp_path):
    yaml_path = tmp_path / "db_agent.yaml"
    yaml_path.write_text(
        "db:\n  host: yaml-db\n  name: yamldb\n  username: yamluser\n"
        "ssh:\n  host: yaml-ssh\n  username: yamlssh\n"
        "agent:\n  port: 9191\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("DB_AGENT_CONFIG", str(yaml_path))
    from db_agent.config import load_config

    cfg = load_config()
    assert cfg.db.host == "yaml-db"
    assert cfg.db.name == "yamldb"
    assert cfg.ssh.host == "yaml-ssh"
    assert cfg.port == 9191


def test_env_overrides_yaml(monkeypatch, tmp_path):
    yaml_path = tmp_path / "db_agent.yaml"
    yaml_path.write_text("db:\n  host: yaml-db\n", encoding="utf-8")
    monkeypatch.setenv("DB_AGENT_CONFIG", str(yaml_path))
    monkeypatch.setenv("DB_HOST", "env-db")
    from db_agent.config import load_config

    assert load_config().db.host == "env-db"


# --------------------------------------------------------------------------- #
# Security extension points: all OFF by default; optional
# --------------------------------------------------------------------------- #
def test_all_security_flags_default_off(client):
    sec = client.get("/security").json()
    assert sec["prototype"] is True
    assert sec["production_secure"] is False
    assert sec["any_enabled"] is False
    for flag in ("ENABLE_MTLS", "ENABLE_JWT", "ENABLE_VAULT", "ENABLE_OIDC",
                 "ENABLE_CERT_AUTH"):
        assert sec["optional_features"][flag] is False


def test_security_flags_toggle_on_when_set(monkeypatch):
    from db_agent import security
    assert security.mtls_enabled() is False
    monkeypatch.setenv("ENABLE_MTLS", "true")
    assert security.mtls_enabled() is True
    monkeypatch.setenv("ENABLE_JWT", "1")
    assert security.jwt_enabled() is True


def test_tls_context_is_none_in_prototype(monkeypatch):
    from db_agent import security
    assert security.tls_context() is None
    # Even with the flag on, the prototype stub returns None (not implemented) —
    # so enabling it never crashes startup before real wiring exists.
    monkeypatch.setenv("ENABLE_MTLS", "true")
    assert security.tls_context() is None


def test_authenticate_allows_in_prototype(monkeypatch):
    from db_agent import security
    ok, reason = security.authenticate_request({})
    assert ok is True and "disabled" in reason
    # With JWT enabled but unimplemented, prototype still allows (hook pending).
    monkeypatch.setenv("ENABLE_JWT", "true")
    ok2, reason2 = security.authenticate_request({})
    assert ok2 is True


def test_resolve_secret_reads_env(monkeypatch):
    from db_agent import security
    monkeypatch.setenv("SOME_SECRET", "abc")
    assert security.resolve_secret("SOME_SECRET") == "abc"
    assert security.resolve_secret("MISSING_SECRET", "fallback") == "fallback"


# --------------------------------------------------------------------------- #
# Connectivity: graceful degradation, never raises
# --------------------------------------------------------------------------- #
def test_connectivity_unconfigured_is_not_configured(client):
    r = client.get("/connectivity").json()
    assert r["database"]["status"] == "not_configured"
    assert r["database"]["configured"] is False
    assert r["ssh"]["status"] == "not_configured"
    assert r["summary"]["targets_configured"] == 0


def test_connectivity_unreachable_target_fails_gracefully(client, monkeypatch):
    # TEST-NET-3 (203.0.113.0/24) is reserved + unroutable -> guaranteed failure.
    monkeypatch.setenv("DB_HOST", "203.0.113.10")
    monkeypatch.setenv("DB_NAME", "x")
    monkeypatch.setenv("DB_USERNAME", "u")
    monkeypatch.setenv("DB_PASSWORD", "p")
    monkeypatch.setenv("DB_TIMEOUT_SEC", "2")
    db = client.get("/connectivity/database").json()
    assert db["configured"] is True
    assert db["ok"] is False          # failed, but no exception/crash
    assert db["status"] == "error"


def test_ssh_check_is_tcp_probe(client, monkeypatch):
    monkeypatch.setenv("SSH_HOST", "203.0.113.10")
    monkeypatch.setenv("SSH_USERNAME", "u")
    monkeypatch.setenv("SSH_PORT", "22")
    monkeypatch.setenv("SSH_TIMEOUT_SEC", "2")
    ssh = client.get("/connectivity/ssh").json()
    assert ssh["configured"] is True
    assert ssh["mode"] == "tcp_probe"
    assert ssh["ok"] is False


def test_check_db_tcp_fallback_when_driver_missing(monkeypatch):
    # Force the psycopg2 import inside check_db to fail -> TCP fallback path.
    import builtins
    from db_agent import connectivity
    from db_agent.config import DbTarget

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "modules.operations.engines.postgresql_connector":
            raise ImportError("simulated missing driver")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    res = connectivity.check_db(DbTarget(host="203.0.113.10", port=5432,
                                         name="x", username="u", password="p",
                                         timeout_sec=2))
    assert res["engine"] == "tcp_fallback"
    assert res["ok"] is False  # unreachable, but graceful


# --------------------------------------------------------------------------- #
# Isolation: the agent does not touch ECS platform security
# --------------------------------------------------------------------------- #
def test_agent_does_not_import_ecs_auth():
    # The DB Agent must be independent of ECS's security framework. It reuses the
    # DB connector only; it must not pull in app.auth.* at import time.
    import importlib
    import sys

    for mod in ("db_agent", "db_agent.app", "db_agent.config",
                "db_agent.security", "db_agent.connectivity"):
        importlib.import_module(mod)
    # No ECS auth module should have been imported as a side effect of db_agent.
    assert not any(m.startswith("app.auth") for m in sys.modules
                   if sys.modules.get(m) is not None and m.startswith("app.auth")
                   and "db_agent" in str(sys.modules.get(m, ""))), \
        "db_agent must not depend on app.auth"
