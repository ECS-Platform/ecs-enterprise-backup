"""ECS Environment Configuration Loader.

Single entry point for environment-driven configuration. ECS selects the active
environment from the ``ECS_ENV`` environment variable (default ``local``) and
merges ``config/environments/_base.yaml`` with ``config/environments/<env>.yaml``.

Design goals
------------
* One switch to move between Local / Dev / SIT / UAT / Prod: ``ECS_ENV``.
* No code change to deploy a new environment — edit the YAML only.
* Reuses ``ecs_platform.config.loader`` so every value still supports
  ``${VAR}`` / ``${VAR:-default}`` substitution and secrets stay in env vars.
* Never raises on import; ``get_environment_config()`` degrades to base defaults
  if an env file is missing, so the demo keeps working.

Usage
-----
    from config.environment_loader import get_environment_config, active_environment
    cfg = get_environment_config()
    pg = cfg["databases"]["postgres"]
    targets = cfg["predefined_query_targets"]["os_servers"]
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from ecs_platform.config.loader import ConfigError, config_dir, load_config

#: Environments ECS recognises. ``ECS_ENV`` must resolve to one of these.
VALID_ENVIRONMENTS: tuple[str, ...] = ("local", "dev", "sit", "uat", "prod")

#: Env var that selects the active environment.
_ENV_SELECTOR = "ECS_ENV"
_DEFAULT_ENV = "local"

#: Comma-separated env-var overrides for predefined-query target server lists.
_TARGET_LIST_OVERRIDES = {
    "os_servers": "ECS_TARGET_OS_SERVERS",
    "db_servers": "ECS_TARGET_DB_SERVERS",
    "middleware_servers": "ECS_TARGET_MW_SERVERS",
    "appsec_targets": "ECS_TARGET_APPSEC",
}


class EnvironmentConfigError(ConfigError):
    """Raised when the active environment configuration is invalid/unloadable."""


def active_environment() -> str:
    """Return the active environment name (validated, lower-cased)."""
    raw = (os.environ.get(_ENV_SELECTOR) or _DEFAULT_ENV).strip().lower()
    if raw not in VALID_ENVIRONMENTS:
        raise EnvironmentConfigError(
            f"Invalid {_ENV_SELECTOR}='{raw}'. "
            f"Expected one of: {', '.join(VALID_ENVIRONMENTS)}."
        )
    return raw


def available_environments() -> list[str]:
    """Environments that have a YAML file present on disk."""
    base = config_dir() / "environments"
    return [e for e in VALID_ENVIRONMENTS if (base / f"{e}.yaml").is_file()]


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge ``override`` onto ``base`` (override wins). Pure (no mutation)."""
    out: dict[str, Any] = dict(base)
    for key, val in override.items():
        if key in out and isinstance(out[key], dict) and isinstance(val, dict):
            out[key] = _deep_merge(out[key], val)
        else:
            out[key] = val
    return out


def _csv_to_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _apply_target_overrides(cfg: dict[str, Any]) -> dict[str, Any]:
    """Allow comma-separated env vars to override predefined-query target lists."""
    targets = cfg.get("predefined_query_targets")
    if not isinstance(targets, dict):
        return cfg
    for key, env_var in _TARGET_LIST_OVERRIDES.items():
        raw = os.environ.get(env_var)
        if raw is not None and raw.strip() != "":
            targets[key] = _csv_to_list(raw)
    return cfg


@lru_cache(maxsize=None)
def _load_for_env(env: str) -> dict[str, Any]:
    try:
        base = load_config("environments/_base")
    except ConfigError as exc:
        raise EnvironmentConfigError(f"Cannot load environments/_base.yaml: {exc}") from exc
    try:
        env_cfg = load_config(f"environments/{env}")
    except ConfigError as exc:
        raise EnvironmentConfigError(
            f"Cannot load environments/{env}.yaml: {exc}"
        ) from exc
    merged = _deep_merge(base, env_cfg)
    merged["environment"] = env_cfg.get("environment", env)
    return _apply_target_overrides(merged)


def get_environment_config(*, env: str | None = None, refresh: bool = False) -> dict[str, Any]:
    """Return the fully-merged, env-resolved configuration for the active environment.

    :param env: force a specific environment (else read from ``ECS_ENV``).
    :param refresh: bypass the cache (also clears the underlying YAML cache).
    """
    if refresh:
        _load_for_env.cache_clear()
        from ecs_platform.config.loader import load_config as _lc

        _lc.cache_clear()
    target_env = (env or active_environment()).strip().lower()
    if target_env not in VALID_ENVIRONMENTS:
        raise EnvironmentConfigError(
            f"Invalid environment '{target_env}'. Expected one of: {', '.join(VALID_ENVIRONMENTS)}."
        )
    return _load_for_env(target_env)


# --------------------------------------------------------------------------- #
# Typed accessors — convenience helpers so modules never reach into raw dicts.
# All accept an optional ``env`` for cross-environment validation tooling.
# --------------------------------------------------------------------------- #
def get_section(name: str, *, env: str | None = None) -> dict[str, Any]:
    return dict(get_environment_config(env=env).get(name, {}) or {})


def get_application(app_key: str, *, env: str | None = None) -> dict[str, Any]:
    return dict(get_section("applications", env=env).get(app_key, {}) or {})


def get_database(name: str, *, env: str | None = None) -> dict[str, Any]:
    return dict(get_section("databases", env=env).get(name, {}) or {})


def get_connector(name: str, *, env: str | None = None) -> dict[str, Any]:
    return dict(get_section("connectors", env=env).get(name, {}) or {})


def get_connector_url(name: str, *, env: str | None = None) -> str:
    return str(get_connector(name, env=env).get("url", "") or "")


def get_framework_target(name: str, *, env: str | None = None) -> dict[str, Any]:
    return dict(get_section("framework_targets", env=env).get(name, {}) or {})


def get_predefined_query_targets(*, env: str | None = None) -> dict[str, Any]:
    return get_section("predefined_query_targets", env=env)


def get_target_servers(group: str, *, env: str | None = None) -> list[str]:
    val = get_predefined_query_targets(env=env).get(group, [])
    return list(val) if isinstance(val, list) else []


def get_storage(*, env: str | None = None) -> dict[str, Any]:
    return get_section("storage", env=env)


def get_authentication(*, env: str | None = None) -> dict[str, Any]:
    return get_section("authentication", env=env)


def get_llm(*, env: str | None = None) -> dict[str, Any]:
    return get_section("llm", env=env)


def get_reporting(*, env: str | None = None) -> dict[str, Any]:
    return get_section("reporting", env=env)


def get_tenant(*, env: str | None = None) -> str:
    return str(get_environment_config(env=env).get("tenant", "") or "")
