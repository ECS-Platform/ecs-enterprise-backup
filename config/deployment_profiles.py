"""ECS Deployment Profiles.

A *deployment profile* is a secret-safe, structured summary of a fully-resolved
environment configuration — one consistent view per deployment target
(LOCAL / UAT / PRODUCTION / DR) covering application, database, storage, LLM,
connectors, scheduler, logging, caching, security and monitoring.

It is READ-ONLY: it reads the merged config via ``environment_loader`` and never
mutates anything, never performs I/O, and never reveals secret values (secrets are
shown as SET / MISSING). It powers the config helper scripts, deployment docs, and
CI environment checks so teams can compare environments at a glance.

CLI::

    python -m config.deployment_profiles            # active env profile
    python -m config.deployment_profiles prod       # a named env
    python -m config.deployment_profiles --all      # every env with a YAML
    python -m config.deployment_profiles --json prod
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from config.environment_loader import (
    VALID_ENVIRONMENTS,
    available_environments,
    get_environment_config,
)

#: The canonical deployment targets (subset of VALID_ENVIRONMENTS that map to a
#: real deployment tier). dev/sit are lower test tiers, still profileable.
DEPLOYMENT_TARGETS: tuple[str, ...] = ("local", "uat", "prod", "dr")


def _mask_env(env_var: str | None) -> str:
    """SET / MISSING for a secret env var (never the value)."""
    if not env_var:
        return "n/a"
    return "SET" if os.environ.get(env_var, "").strip() else "MISSING"


def _get(cfg: dict[str, Any], *path: str, default: Any = None) -> Any:
    cur: Any = cfg
    for key in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
    return cur if cur is not None else default


def build_profile(env: str | None = None) -> dict[str, Any]:
    """Build the secret-safe deployment profile for one environment."""
    cfg = get_environment_config(env=env)
    name = str(cfg.get("environment") or env or "active")

    connectors = cfg.get("connectors") or {}
    enabled_connectors = sorted(
        cname for cname, cval in connectors.items()
        if isinstance(cval, dict) and _truthy(cval.get("enabled"))
    )

    return {
        "environment": name,
        "tenant": cfg.get("tenant", ""),
        "region": cfg.get("region", ""),
        "application": {
            "host": _get(cfg, "application", "host"),
            "port": _get(cfg, "application", "port"),
            "public_url": _get(cfg, "application", "public_url"),
            "base_url": _get(cfg, "application", "base_url"),
            "workers": _get(cfg, "application", "workers"),
        },
        "database": {
            "host": _get(cfg, "databases", "postgres", "host"),
            "port": _get(cfg, "databases", "postgres", "port"),
            "database": _get(cfg, "databases", "postgres", "database"),
            "user": _get(cfg, "databases", "postgres", "user"),
            "password": _mask_env(_get(cfg, "databases", "postgres", "password_env")),
        },
        "storage": {
            "provider": _get(cfg, "storage", "object_store", "provider"),
            "endpoint": _get(cfg, "storage", "object_store", "endpoint"),
            "bucket": _get(cfg, "storage", "object_store", "bucket"),
            "secure": _get(cfg, "storage", "object_store", "secure"),
            "access_key": _mask_env(_get(cfg, "storage", "object_store", "access_key_env")),
            "secret_key": _mask_env(_get(cfg, "storage", "object_store", "secret_key_env")),
        },
        "redis": {
            "host": _get(cfg, "redis", "host"),
            "port": _get(cfg, "redis", "port"),
            "ssl": _get(cfg, "redis", "ssl"),
            "password": _mask_env(_get(cfg, "redis", "password_env")),
        },
        "llm": {
            "provider": _get(cfg, "llm", "provider"),
            "model": _get(cfg, "llm", "model"),
            "base_url": _get(cfg, "llm", "base_url"),
        },
        "vector_store": {
            "provider": _get(cfg, "vector_store", "provider"),
            "host": _get(cfg, "vector_store", "host"),
            "port": _get(cfg, "vector_store", "port"),
        },
        "connectors": {
            "enabled_count": len(enabled_connectors),
            "enabled": enabled_connectors,
            "execution": {
                "enabled": _get(cfg, "connector_execution", "enabled"),
                "timeout_sec": _get(cfg, "connector_execution", "timeout_sec"),
                "max_retries": _get(cfg, "connector_execution", "max_retries"),
                "ssl_verify": _get(cfg, "connector_execution", "ssl_verify"),
            },
        },
        "scheduler": {
            "enabled": _get(cfg, "scheduler", "enabled"),
            "worker_count": _get(cfg, "scheduler", "worker_count"),
            "timeout_sec": _get(cfg, "scheduler", "timeout_sec"),
            "max_retries": _get(cfg, "scheduler", "max_retries"),
        },
        "caching": {
            "enabled": _get(cfg, "caching", "enabled"),
            "backend": _get(cfg, "caching", "backend"),
            "ttl_seconds": _get(cfg, "caching", "ttl_seconds"),
        },
        "logging": {
            "level": _get(cfg, "logging", "level"),
            "format": _get(cfg, "logging", "format"),
            "mask_secrets": _get(cfg, "logging", "mask_secrets"),
        },
        "security": {
            "auth_enabled": _get(cfg, "security", "auth_enabled"),
            "local_auth_bypass": _get(cfg, "security", "local_auth_bypass"),
            "force_https": _get(cfg, "security", "force_https"),
            "sso_enabled": _get(cfg, "authentication", "sso", "enabled"),
        },
        "monitoring": {
            "enabled": _get(cfg, "monitoring", "enabled"),
            "health_path": _get(cfg, "monitoring", "health_path"),
            "metrics_path": _get(cfg, "monitoring", "metrics_path"),
        },
    }


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def build_all_profiles() -> dict[str, dict[str, Any]]:
    """Profiles for every environment that has a YAML file present."""
    return {env: build_profile(env) for env in available_environments()}


def diff_profiles(env_a: str, env_b: str) -> dict[str, Any]:
    """Compare two profiles field-by-field; returns only the differing leaf paths."""
    a = build_profile(env_a)
    b = build_profile(env_b)
    diffs: dict[str, dict[str, Any]] = {}

    def walk(pa: Any, pb: Any, prefix: str = "") -> None:
        if isinstance(pa, dict) and isinstance(pb, dict):
            for key in sorted(set(pa) | set(pb)):
                walk(pa.get(key), pb.get(key), f"{prefix}.{key}" if prefix else key)
        else:
            if pa != pb:
                diffs[prefix] = {env_a: pa, env_b: pb}

    walk(a, b)
    return {"env_a": env_a, "env_b": env_b, "differences": diffs, "diff_count": len(diffs)}


def _render(profile: dict[str, Any]) -> str:
    lines = [
        f"Deployment Profile: {profile['environment'].upper()}",
        "=" * (20 + len(profile["environment"])),
        f"  tenant={profile['tenant']}  region={profile['region']}",
        "",
        "  Application:",
        f"    bind {profile['application']['host']}:{profile['application']['port']}  "
        f"public={profile['application']['public_url']}",
        "  Database (PostgreSQL evidence repo):",
        f"    {profile['database']['host']}:{profile['database']['port']}/"
        f"{profile['database']['database']}  password={profile['database']['password']}",
        "  Storage:",
        f"    {profile['storage']['provider']} {profile['storage']['endpoint']} "
        f"bucket={profile['storage']['bucket']} secure={profile['storage']['secure']}",
        "  Redis:",
        f"    {profile['redis']['host']}:{profile['redis']['port']} ssl={profile['redis']['ssl']}",
        "  LLM:",
        f"    {profile['llm']['provider']} {profile['llm']['base_url']} model={profile['llm']['model']}",
        "  Vector store:",
        f"    {profile['vector_store']['provider']} @ {profile['vector_store']['host']}",
        "  Connectors:",
        f"    {profile['connectors']['enabled_count']} enabled: "
        f"{', '.join(profile['connectors']['enabled']) or '(none)'}",
        "  Scheduler:",
        f"    enabled={profile['scheduler']['enabled']} workers={profile['scheduler']['worker_count']}",
        "  Security:",
        f"    auth={profile['security']['auth_enabled']} https={profile['security']['force_https']} "
        f"sso={profile['security']['sso_enabled']}",
        "  Logging/Monitoring:",
        f"    level={profile['logging']['level']} format={profile['logging']['format']} "
        f"monitoring={profile['monitoring']['enabled']}",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in argv
    if "--all" in argv:
        profiles = build_all_profiles()
        if as_json:
            print(json.dumps(profiles, indent=2, default=str))
        else:
            print("\n\n".join(_render(p) for p in profiles.values()))
        return 0
    env = next((a for a in argv if not a.startswith("-")), None)
    profile = build_profile(env)
    print(json.dumps(profile, indent=2, default=str) if as_json else _render(profile))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
