"""Centralised configuration for the functional framework.

Reads ``tests/functional/config/*.yaml``. ``${VAR:-default}`` placeholders are resolved with the SAME resolver
ECS itself uses (``ecs_platform.config.loader``) so behaviour is identical. Secrets are never stored: the YAML
holds env-var *names*; :meth:`FunctionalConfig.secret` reads the value at call time.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
REPO_ROOT = Path(__file__).resolve().parents[3]


def _resolve(obj: Any) -> Any:
    try:
        from ecs_platform.config.loader import _resolve as ecs_resolve  # reuse ECS placeholder semantics

        return ecs_resolve(obj)
    except Exception:  # noqa: BLE001 - repo root not importable: fall back to a minimal resolver
        import re

        pat = re.compile(r"\$\{([A-Z0-9_]+)(?::-([^}]*))?\}")

        def sub(v: Any) -> Any:
            if isinstance(v, dict):
                return {k: sub(x) for k, x in v.items()}
            if isinstance(v, list):
                return [sub(x) for x in v]
            if isinstance(v, str):
                s = pat.sub(lambda m: os.environ.get(m.group(1)) or (m.group(2) or ""), v)
                low = s.strip().lower()
                if low in {"true", "false"}:
                    return low == "true"
                return int(s) if re.fullmatch(r"-?\d+", s.strip()) else s
            return v

        return sub(obj)


def _load(name: str) -> dict[str, Any]:
    with open(CONFIG_DIR / name, encoding="utf-8") as fh:
        return _resolve(yaml.safe_load(fh) or {})


@dataclass
class FunctionalConfig:
    env_name: str
    env: dict[str, Any]
    test_data: dict[str, Any]
    thresholds: dict[str, Any]
    raw: dict[str, Any] = field(default_factory=dict)

    # ---- URLs -----------------------------------------------------------------
    @property
    def base_url(self) -> str:
        return str(self.env.get("base_url") or "").rstrip("/")

    @property
    def api_url(self) -> str:
        return (str(self.env.get("api_url") or "") or self.base_url).rstrip("/")

    @property
    def ui_url(self) -> str:
        return (str(self.env.get("ui_url") or "") or self.base_url).rstrip("/")

    # ---- generic accessors ---------------------------------------------------
    def get(self, dotted: str, default: Any = None) -> Any:
        cur: Any = self.env
        for part in dotted.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return default
            cur = cur[part]
        return cur

    def feature(self, name: str) -> bool:
        return bool((self.env.get("features") or {}).get(name))

    def threshold(self, dotted: str) -> Any:
        cur: Any = self.thresholds
        for part in dotted.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return None
            cur = cur[part]
        return cur

    def secret(self, env_var_name: str) -> str:
        """Read a secret from the environment by NAME. Returns '' when unset. Never logged."""
        return os.environ.get(env_var_name, "") if env_var_name else ""

    @property
    def timeout(self) -> float:
        return float(self.env.get("timeout_sec", 30))

    @property
    def poll_interval(self) -> float:
        return float(self.env.get("poll_interval_sec", 2))

    @property
    def long_timeout(self) -> float:
        return float(self.env.get("long_timeout_sec", 180))

    @property
    def catalog(self) -> dict[str, Any]:
        return self.test_data.get("catalog", {})

    @property
    def personas(self) -> dict[str, dict[str, str]]:
        return self.test_data.get("personas", {})


@lru_cache(maxsize=4)
def load_config(env_name: str | None = None) -> FunctionalConfig:
    name = env_name or os.environ.get("ECS_FT_ENV", "local")
    envs = _load("environments.yaml").get("environments", {})
    if name not in envs:
        raise KeyError(f"Unknown ECS_FT_ENV '{name}'. Defined: {sorted(envs)}")
    return FunctionalConfig(
        env_name=name,
        env=envs[name],
        test_data=_load("test_data.yaml"),
        thresholds=_load("thresholds.yaml"),
    )
