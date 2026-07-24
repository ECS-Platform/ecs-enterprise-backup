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


def _running_inside_container() -> bool:
    """True when the process is inside a Docker/OCI container."""
    if Path("/.dockerenv").exists():
        return True
    try:
        cgroup = Path("/proc/1/cgroup")
        if cgroup.is_file() and "docker" in cgroup.read_text(encoding="utf-8", errors="ignore"):
            return True
    except Exception:  # noqa: BLE001
        pass
    return False


def _rewrite_compose_dns_for_host() -> dict[str, str]:
    """Rewrite compose service DNS to localhost published ports for host uvicorn.

    Docker Compose injects names like ``postgres`` / ``minio:9000`` for the
    in-network ``ecs`` container. Host-side ``uvicorn`` cannot resolve those
    names, so repository init, MinIO custody, and PGVector appear skipped.
    No-op inside a container. Never overrides an already-correct localhost value.
    """
    applied: dict[str, str] = {}
    if _running_inside_container():
        return applied

    repo_host = str(os.environ.get("ECS_REPO_PG_HOST", "")).strip().lower()
    if not repo_host or repo_host in {"postgres", "postgres-demo"}:
        os.environ["ECS_REPO_PG_HOST"] = "localhost"
        applied["ECS_REPO_PG_HOST"] = "localhost"
        if str(os.environ.get("ECS_REPO_PG_PORT", "")).strip() in {"", "5432"}:
            # Compose publishes repository Postgres on host 5433.
            os.environ["ECS_REPO_PG_PORT"] = "5433"
            applied["ECS_REPO_PG_PORT"] = "5433"
    elif (
        repo_host in {"localhost", "127.0.0.1"}
        and str(os.environ.get("DEMO_MODE", "")).strip().lower() in _TRUTHY
        and str(os.environ.get("ECS_REPO_PG_PORT", "")).strip() in {"", "5432"}
    ):
        # Demo host uvicorn: .env.example uses 5432 but compose publishes 5433.
        os.environ["ECS_REPO_PG_PORT"] = "5433"
        applied["ECS_REPO_PG_PORT"] = "5433"

    vector_host = str(os.environ.get("ECS_VECTOR_PG_HOST", "")).strip().lower()
    if not vector_host or vector_host == "pgvector":
        os.environ["ECS_VECTOR_PG_HOST"] = "localhost"
        applied["ECS_VECTOR_PG_HOST"] = "localhost"
        if str(os.environ.get("ECS_VECTOR_PG_PORT", "")).strip() in {"", "5432"}:
            os.environ["ECS_VECTOR_PG_PORT"] = "5434"
            applied["ECS_VECTOR_PG_PORT"] = "5434"
    elif (
        vector_host in {"localhost", "127.0.0.1"}
        and str(os.environ.get("DEMO_MODE", "")).strip().lower() in _TRUTHY
        and str(os.environ.get("ECS_VECTOR_PG_PORT", "")).strip() in {"", "5432"}
    ):
        os.environ["ECS_VECTOR_PG_PORT"] = "5434"
        applied["ECS_VECTOR_PG_PORT"] = "5434"

    minio_ep = str(os.environ.get("MINIO_ENDPOINT", "")).strip().lower()
    if not minio_ep or minio_ep.startswith("minio:") or minio_ep == "minio":
        # Compose publishes MinIO API on host 9002.
        os.environ["MINIO_ENDPOINT"] = "localhost:9002"
        applied["MINIO_ENDPOINT"] = "localhost:9002"

    # Compose injects MinIO credentials only into the ``ecs`` container env.
    # Host uvicorn must use the same defaults or object-store silently falls
    # back to LocalObjectStore (no MinIO uploads / no MinIO startup activity).
    if not str(os.environ.get("MINIO_ACCESS_KEY", "")).strip():
        os.environ["MINIO_ACCESS_KEY"] = "ecs_minio"
        applied["MINIO_ACCESS_KEY"] = "ecs_minio"
    if not str(os.environ.get("MINIO_SECRET_KEY", "")).strip():
        os.environ["MINIO_SECRET_KEY"] = "ecs_minio_secret"
        applied["MINIO_SECRET_KEY"] = "(set)"

    # Demo host uvicorn: align empty/placeholder repo passwords with compose.
    if str(os.environ.get("DEMO_MODE", "")).strip().lower() in _TRUTHY:
        repo_pw = str(os.environ.get("ECS_REPO_PG_PASSWORD", "")).strip()
        if not repo_pw or repo_pw == "change-me":
            os.environ["ECS_REPO_PG_PASSWORD"] = "ecs_password"
            applied["ECS_REPO_PG_PASSWORD"] = "(compose-default)"
        vector_pw = str(os.environ.get("ECS_VECTOR_PG_PASSWORD", "")).strip()
        if not vector_pw or vector_pw == "change-me":
            os.environ["ECS_VECTOR_PG_PASSWORD"] = "ecs_password"
            applied["ECS_VECTOR_PG_PASSWORD"] = "(compose-default)"

    redis_url = str(os.environ.get("REDIS_URL", "")).strip()
    if not redis_url or "://redis:" in redis_url or redis_url.startswith("redis://redis/"):
        os.environ["REDIS_URL"] = "redis://localhost:6379/0"
        applied["REDIS_URL"] = os.environ["REDIS_URL"]

    # Compose / .env may set OLLAMA_URL to docker DNS (ollama:11434) or
    # host.docker.internal (container→host). Host uvicorn must use localhost or
    # post-persist embedding (nomic-embed-text → PGVector) fails with connection refused.
    ollama_url = str(os.environ.get("OLLAMA_URL", "")).strip()
    ollama_host = ollama_url.lower().replace("https://", "").replace("http://", "")
    if (
        not ollama_url
        or ollama_host.startswith("ollama:")
        or ollama_host == "ollama"
        or ollama_host.startswith("host.docker.internal")
    ):
        os.environ["OLLAMA_URL"] = "http://localhost:11434"
        applied["OLLAMA_URL"] = os.environ["OLLAMA_URL"]

    # repository.yaml is lru-cached after first resolve — clear so MinIO endpoint
    # / postgres host pick up the host-side remaps above.
    if applied:
        try:
            from ecs_platform.config.loader import load_config

            load_config.cache_clear()
        except Exception:  # noqa: BLE001
            pass
        try:
            from ecs_platform.storage import reset_object_store

            reset_object_store()
        except Exception:  # noqa: BLE001
            pass
        # Drop cached Ollama/pgvector clients so post-persist embedding uses the
        # remapped localhost endpoints (not compose DNS names).
        try:
            from ecs_platform.evidence_indexing import reset_indexing_clients

            reset_indexing_clients()
        except Exception:  # noqa: BLE001
            pass

    return applied


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

    host_endpoints = _rewrite_compose_dns_for_host()

    return {
        "loaded": env_path.exists(),
        "path": str(env_path),
        "parser": used,
        "DEMO_MODE": os.environ.get("DEMO_MODE", ""),
        "ECS_AUTH_ENABLED": os.environ.get("ECS_AUTH_ENABLED", ""),
        "host_compose_endpoints": host_endpoints,
    }


def demo_mode_enabled() -> bool:
    return str(os.environ.get("DEMO_MODE", "")).strip().lower() in _TRUTHY


def auth_enabled() -> bool:
    return str(os.environ.get("ECS_AUTH_ENABLED", "")).strip().lower() in _TRUTHY


# Load immediately on import so import order alone guarantees env availability.
ENV_STATUS = load_env()
