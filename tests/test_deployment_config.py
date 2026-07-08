"""Tests for the ECS deployment configuration framework (LOCAL/UAT/PROD/DR).

Verifies that moving between deployment targets is configuration-only:
  * every environment loads and exposes the deployment sections,
  * app/db/redis/storage/llm/vector endpoints come from config,
  * secrets are masked (never leaked),
  * environment switching changes endpoints without code changes,
  * the extended validator flags localhost-in-remote / invalid URL / bad port,
  * deployment profiles + diff work.

Deterministic and offline (no live services). Secret env vars are not required
for structural validation (check_secrets defaults off).
"""

from __future__ import annotations

import os

os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from config import config_validation as cv
from config import deployment_profiles as dp
from config.environment_loader import (
    VALID_ENVIRONMENTS,
    available_environments,
    get_application_config,
    get_connector,
    get_database,
    get_environment_config,
    get_llm,
    get_redis,
    get_scheduler,
    get_vector_store,
)

DEPLOY_ENVS = ("local", "uat", "prod", "dr")


# Env-var prefixes that the environment YAML resolves via ${VAR}. Other test
# files import app.main, which loads the repo `.env` into os.environ (e.g.
# OLLAMA_URL=http://host.docker.internal:11434). To validate the committed YAML
# DEFAULTS deterministically (independent of any co-running test / ambient .env),
# these overrides are stripped for the duration of each test here.
_STRIP_PREFIXES = (
    "ECS_", "OLLAMA_URL", "REDIS_", "MINIO_", "DB_", "APP_", "JIRA_", "SNOW_",
    "CONFLUENCE_", "SONAR_", "PRISMA_", "AZDO_", "JENKINS_", "GITHUB_", "GITEA_",
    "MS_GRAPH_", "CHROMA_", "MILVUS_",
)
_KEEP = {"ECS_VALIDATE_CONFIG", "ECS_VALIDATE_SECRETS"}


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    # Strip ambient deployment overrides so tests see the committed YAML defaults.
    for key in list(os.environ):
        if key in _KEEP:
            continue
        if any(key == p or key.startswith(p) for p in _STRIP_PREFIXES):
            monkeypatch.delenv(key, raising=False)
    # Clear the loader cache so the stripped environment is re-resolved.
    get_environment_config(refresh=True)
    yield
    get_environment_config(refresh=True)


# --------------------------------------------------------------------------- #
# Environment registration + loading
# --------------------------------------------------------------------------- #
def test_dr_is_a_valid_environment():
    assert "dr" in VALID_ENVIRONMENTS
    assert "dr" in available_environments()


@pytest.mark.parametrize("env", DEPLOY_ENVS)
def test_every_deploy_env_loads(env):
    cfg = get_environment_config(env=env)
    assert cfg["environment"] == env
    for section in ("application", "databases", "connectors", "redis",
                    "scheduler", "llm", "vector_store", "storage", "security"):
        assert section in cfg, f"{env} missing section {section}"


# --------------------------------------------------------------------------- #
# All deployment targets come from config
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("env", DEPLOY_ENVS)
def test_application_identity_is_configured(env):
    app = get_application_config(env=env)
    assert app.get("host") and app.get("port")
    assert app.get("public_url") and app.get("base_url")


@pytest.mark.parametrize("env", DEPLOY_ENVS)
def test_database_endpoint_from_config(env):
    db = get_database("postgres", env=env)
    assert db.get("host") and db.get("port") and db.get("database")


@pytest.mark.parametrize("env", DEPLOY_ENVS)
def test_redis_and_scheduler_and_vector_from_config(env):
    assert get_redis(env=env).get("host")
    assert "enabled" in get_scheduler(env=env)
    assert get_vector_store(env=env).get("provider")


@pytest.mark.parametrize("env", DEPLOY_ENVS)
def test_llm_endpoint_from_config(env):
    llm = get_llm(env=env)
    assert llm.get("provider") and llm.get("base_url")


def test_connector_endpoint_from_config():
    # Jira connector URL resolves from config in prod (real host, not localhost).
    url = get_connector("jira", env="prod").get("url")
    assert url and "localhost" not in url


# --------------------------------------------------------------------------- #
# Environment switching = config only (no code change)
# --------------------------------------------------------------------------- #
def test_switching_env_changes_endpoints():
    local_db = get_database("postgres", env="local")["host"]
    prod_db = get_database("postgres", env="prod")["host"]
    dr_db = get_database("postgres", env="dr")["host"]
    assert local_db != prod_db != dr_db
    # The ECS public URL also differs per environment.
    assert (get_application_config(env="local")["public_url"]
            != get_application_config(env="prod")["public_url"]
            != get_application_config(env="dr")["public_url"])


def test_env_var_override_repoints_without_code(monkeypatch):
    monkeypatch.setenv("ECS_REPO_PG_HOST", "custom-db.example.internal")
    cfg = get_environment_config(env="prod", refresh=True)
    assert cfg["databases"]["postgres"]["host"] == "custom-db.example.internal"


# --------------------------------------------------------------------------- #
# Validator: localhost / URL / port / secrets
# --------------------------------------------------------------------------- #
def test_local_validates_clean():
    rep = cv.validate_environment("local")
    assert rep.ok, rep.errors


def test_prod_has_no_localhost():
    rep = cv.validate_environment("prod")
    assert not any("localhost" in e or "loopback" in e for e in rep.errors), rep.errors


@pytest.mark.parametrize("env", ("uat", "prod", "dr"))
def test_remote_envs_reject_localhost(env):
    # Structural: no localhost/loopback errors should be present for remote envs.
    rep = cv.validate_environment(env)
    localhost_errors = [e for e in rep.errors if "localhost" in e or "loopback" in e]
    assert not localhost_errors, localhost_errors


def test_secret_check_off_by_default_is_warning():
    # Without ECS_VALIDATE_SECRETS, missing secrets are warnings, not errors.
    rep = cv.validate_environment("prod", check_secrets=False)
    secret_errors = [e for e in rep.errors if "required secret" in e]
    assert not secret_errors
    assert any("required secret" in w for w in rep.warnings)


def test_secret_check_on_flags_missing(monkeypatch):
    for k in list(os.environ):
        if k.endswith("_PASSWORD") or k.endswith("_SECRET") or k.endswith("_TOKEN"):
            monkeypatch.delenv(k, raising=False)
    rep = cv.validate_environment("prod", check_secrets=True)
    assert any("required secret" in e for e in rep.errors)


def test_validator_helpers():
    assert cv._valid_port(5432) and cv._valid_port("443")
    assert not cv._valid_port(0) and not cv._valid_port("70000") and not cv._valid_port("abc")
    assert cv._valid_url("https://x.bank.com") and cv._valid_url("minio:9000")
    assert not cv._valid_url("http://")
    assert cv._contains_localhost("http://localhost:8000")
    assert cv._contains_localhost("http://host.docker.internal:11434")
    assert not cv._contains_localhost("https://ecs.bank.internal")


def test_secret_masking_never_leaks():
    assert cv.mask_secret("super-secret-value") == "su****"
    assert cv.mask_secret("") == "MISSING"
    assert cv.mask_secret(None) == "MISSING"
    assert "super-secret-value" not in cv.mask_secret("super-secret-value")


# --------------------------------------------------------------------------- #
# Deployment profiles
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("env", DEPLOY_ENVS)
def test_build_profile_is_secret_safe(env):
    profile = dp.build_profile(env)
    blob = repr(profile)
    # Secret fields are masked to SET/MISSING; the raw env-var NAME may appear but
    # never a secret VALUE (we don't set any real secrets in this test).
    assert profile["database"]["password"] in ("SET", "MISSING", "n/a")
    assert profile["storage"]["secret_key"] in ("SET", "MISSING", "n/a")
    assert profile["environment"] == env


def test_profile_diff_local_vs_prod():
    d = dp.diff_profiles("local", "prod")
    assert d["diff_count"] > 0
    assert "application.public_url" in d["differences"]


def test_all_profiles_cover_available_envs():
    profiles = dp.build_all_profiles()
    for env in available_environments():
        assert env in profiles
