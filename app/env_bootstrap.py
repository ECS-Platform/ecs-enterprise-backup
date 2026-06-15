"""Environment bootstrap — load .env into os.environ before anything else.

This module MUST be imported first (before any app/* or modules/* import) so
that flags such as ``DEMO_MODE`` and ``ECS_AUTH_ENABLED`` are present in the
process environment by the time authentication, RBAC and page guards
initialise. Without this, running ECS directly via uvicorn (not docker-compose,
which performs its own ${VAR} substitution) leaves these flags unset and a
browser refresh can trigger authentication failures in demo mode.

Behaviour:
  * Loads the repository-root ``.env`` if present, using python-dotenv when it
    is installed and falling back to a tiny built-in parser otherwise (so the
    platform never hard-depends on the package being importable).
  * Never overrides values already present in the real environment
    (``override=False``) so container / CI overrides still win.
  * Never raises — a missing or malformed .env degrades to a no-op.
"""

from __future__ import annotations

import os
from pathlib import Path

_TRUTHY = {"1", "true", "yes", "on"}
_LOADED = False


def _repo_root() -> Path:
    # app/env_bootstrap.py -> repo root is one level up from app/
    return Path(__file__).resolve().parent.parent


def _fallback_parse(env_path: Path) -> int:
    """Minimal .env parser used when python-dotenv is unavailable."""
    count = 0
    try:
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val
                count += 1
    except Exception:  # noqa: BLE001
        return count
    return count


def load_env() -> dict:
    """Load .env into os.environ exactly once. Returns a small status dict."""
    global _LOADED
    if _LOADED:
        return {"loaded": True, "cached": True}
    _LOADED = True

    env_path = _repo_root() / ".env"
    used = "none"
    if env_path.exists():
        try:
            from dotenv import load_dotenv  # type: ignore

            load_dotenv(dotenv_path=str(env_path), override=False)
            used = "python-dotenv"
        except Exception:  # noqa: BLE001 - package missing or failed
            _fallback_parse(env_path)
            used = "fallback-parser"

    return {
        "loaded": env_path.exists(),
        "path": str(env_path),
        "parser": used,
        "DEMO_MODE": os.environ.get("DEMO_MODE", ""),
        "ECS_AUTH_ENABLED": os.environ.get("ECS_AUTH_ENABLED", ""),
    }


def demo_mode_enabled() -> bool:
    return str(os.environ.get("DEMO_MODE", "")).strip().lower() in _TRUTHY


def auth_enabled() -> bool:
    return str(os.environ.get("ECS_AUTH_ENABLED", "")).strip().lower() in _TRUTHY


# Load immediately on import so import order alone guarantees env availability.
ENV_STATUS = load_env()
