"""YAML configuration loader with environment-variable resolution.

Supports ${VAR} and ${VAR:-default} placeholders. No secrets are stored in YAML;
every sensitive value resolves from the process environment at load time. This lets
tenants/credentials be onboarded later by setting env vars — no code change.
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

_PLACEHOLDER = re.compile(r"\$\{([A-Z0-9_]+)(?::-([^}]*))?\}")

_CONFIG_DIR_ENV = "ECS_CONFIG_DIR"
_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


class ConfigError(RuntimeError):
    """Raised when configuration cannot be loaded or parsed."""


def config_dir() -> Path:
    """Resolve the config directory (env override, else repo-root /config)."""
    override = os.environ.get(_CONFIG_DIR_ENV)
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / "config"


def _coerce(value: str) -> Any:
    low = value.strip().lower()
    if low in _TRUE:
        return True
    if low in _FALSE:
        return False
    if re.fullmatch(r"-?\d+", value.strip()):
        try:
            return int(value)
        except ValueError:
            return value
    return value


def _resolve_scalar(value: str) -> Any:
    """Replace ${VAR} / ${VAR:-default} placeholders, then coerce booleans/ints."""
    matches = list(_PLACEHOLDER.finditer(value))
    if not matches:
        return value

    # Whole-string single placeholder -> preserve type coercion.
    if len(matches) == 1 and matches[0].span() == (0, len(value)):
        var, default = matches[0].group(1), matches[0].group(2)
        env_val = os.environ.get(var)
        if env_val is not None and env_val != "":
            return _coerce(env_val)
        if default is not None:
            return _coerce(default)
        return ""

    def _sub(m: re.Match) -> str:
        var, default = m.group(1), m.group(2)
        env_val = os.environ.get(var)
        if env_val is not None and env_val != "":
            return env_val
        return default if default is not None else ""

    return _PLACEHOLDER.sub(_sub, value)


def _resolve(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _resolve(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve(v) for v in obj]
    if isinstance(obj, str):
        return _resolve_scalar(obj)
    return obj


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise ConfigError(
            "PyYAML is required to load ECS configuration (pip install pyyaml)"
        ) from exc
    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"Config root must be a mapping: {path}")
    return _resolve(data)


@lru_cache(maxsize=None)
def load_config(name: str) -> dict[str, Any]:
    """Load and env-resolve a named config file (cached). e.g. load_config('llm')."""
    return _read_yaml(config_dir() / f"{name}.yaml")


def get_config(name: str, *, refresh: bool = False) -> dict[str, Any]:
    if refresh:
        load_config.cache_clear()
    return load_config(name)


def load_integrations() -> dict[str, Any]:
    return load_config("integrations")


def load_llm_config() -> dict[str, Any]:
    return load_config("llm")


def load_rbac_config() -> dict[str, Any]:
    return load_config("rbac")


def load_repository_config() -> dict[str, Any]:
    return load_config("repository")


def load_vectorstore_config() -> dict[str, Any]:
    return load_config("vectorstore")


def load_auth_config() -> dict[str, Any]:
    return load_config("auth")


def resolve_secret(env_var: str) -> str:
    """Read a secret strictly from the environment. Never logged."""
    return os.environ.get(env_var, "")
