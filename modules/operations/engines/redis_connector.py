"""Redis connector for predefined query execution.

Redis checks run ``redis-cli`` inside the Redis container, so this reuses the
existing docker-exec ``LinuxConnector`` rather than adding a redis-py dependency
or duplicating connector logic. If a password is configured it is injected via
``-a`` at execution time (kept out of the catalog command text and never logged).

Read-only: only INFO / CONFIG GET commands are in the catalog.
"""

from __future__ import annotations

import os
from typing import Any

from modules.operations.engines.linux_connector import LinuxConnector, _timeout_from
from modules.operations.engines.query_connectors import ConnectorResult

DEFAULT_TIMEOUT_SEC = 30


def get_redis_config() -> dict[str, Any]:
    """Redis target for predefined query execution (env / YAML driven).

    Execution is via ``docker exec <container> redis-cli ...``. Host/port are
    carried for diagnostics/future TCP mode; the password is read from env and
    used only to build the ``-a`` flag at execution time (never logged).
    """
    from modules.operations.engines.query_connectors import get_predefined_target

    cfg = get_predefined_target("redis")
    password_env = str(cfg.get("password_env") or "ECS_REDIS_PASSWORD")
    container = (
        cfg.get("container")
        or os.environ.get("ECS_REDIS_CONTAINER")
        or "redis"
    )
    return {
        "container": container,
        "host": (str(cfg.get("host")) if cfg.get("host") else None) or os.environ.get("ECS_REDIS_HOST", "localhost"),
        "port": int(cfg.get("port") or os.environ.get("ECS_REDIS_PORT", "6379") or 6379),
        "password": os.environ.get(password_env) or os.environ.get("ECS_REDIS_PASSWORD", ""),
        "timeout_sec": _timeout_from(cfg, "ECS_REDIS_TIMEOUT_SECONDS", "ECS_REDIS_TIMEOUT_SEC"),
    }


class RedisConnector(LinuxConnector):
    """Live Redis execution via redis-cli inside the Redis container.

    Subclasses LinuxConnector (docker exec) — no duplicate execution logic. The
    catalog command starts with ``redis-cli``; when a password is set, this
    connector rewrites it to ``redis-cli -a <pw>`` before running (credential is
    added here, not stored in the catalog).
    """

    technology = "Redis"

    def __init__(self, container: str = "redis", host: str = "localhost", port: int = 6379,
                 password: str = "", timeout_sec: int = DEFAULT_TIMEOUT_SEC):
        super().__init__(container=container, timeout_sec=timeout_sec)
        self.host = host
        self.port = port
        self.password = password

    def execute(self, query: str) -> ConnectorResult:
        cmd = (query or "").strip()
        if self.password and cmd.startswith("redis-cli"):
            # Insert auth + suppress the "-a" warning; never printed in the catalog.
            cmd = cmd.replace(
                "redis-cli", f"redis-cli --no-auth-warning -a '{self.password}'", 1
            )
        return super().execute(cmd)
