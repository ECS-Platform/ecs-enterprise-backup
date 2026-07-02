"""Shared helpers for Evidence Analytics engines (Phase 5.5).

Flag resolution, config loading, datetime/age math. No network/DB/RAG/LLM imports.
Config loading is best-effort and never raises.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Mapping

_TRUTHY = {"1", "true", "yes", "on"}


def env_flag(name: str) -> bool | None:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return None
    return raw.strip().lower() in _TRUTHY


def load_policy() -> dict[str, Any]:
    """Load the 'evidence_analytics' policy block from config. Never raises."""
    try:
        from ecs_platform.config.loader import load_config

        cfg = load_config("evidence_analytics") or {}
        block = cfg.get("evidence_analytics", cfg)
        return block if isinstance(block, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def flag_enabled(env_name: str, policy_key: str, *, default: bool = False) -> bool:
    env = env_flag(env_name)
    if env is not None:
        return env
    val = load_policy().get(policy_key, default)
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in _TRUTHY
    return default


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return low
    if v < low:
        return low
    if v > high:
        return high
    return round(v, 1)


def normalize_weights(weights: Mapping[str, float], fallback_keys: list[str]) -> dict[str, float]:
    w = {k: float(v) for k, v in weights.items()
         if isinstance(v, (int, float)) and v >= 0}
    total = sum(w.values())
    if total <= 0:
        if not fallback_keys:
            return {}
        return {k: 1.0 / len(fallback_keys) for k in fallback_keys}
    return {k: v / total for k, v in w.items()}


def parse_dt(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        text = value.strip().replace("Z", "+00:00").replace(" UTC", "")
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(text, fmt)
                    break
                except ValueError:
                    continue
            else:
                return None
    else:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def age_days(value: Any, *, now: datetime | None = None) -> float | None:
    dt = parse_dt(value)
    if dt is None:
        return None
    now = now or datetime.now(timezone.utc)
    return max(0.0, (now - dt).total_seconds() / 86400.0)


def merge_block(defaults: Mapping[str, Any], policy: Mapping[str, Any] | None,
                key: str) -> dict[str, Any]:
    out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in defaults.items()}
    block = (policy or {}).get(key) if isinstance(policy, Mapping) else None
    if isinstance(block, Mapping):
        for k, v in block.items():
            if isinstance(out.get(k), dict) and isinstance(v, dict):
                merged = dict(out[k]); merged.update(v); out[k] = merged
            elif v is not None:
                out[k] = v
    return out
