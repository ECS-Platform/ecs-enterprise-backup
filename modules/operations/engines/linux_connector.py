"""Linux connector — docker exec against ubuntu-demo."""

from __future__ import annotations

import os
import subprocess
import time
from typing import Any

from modules.operations.engines.query_connectors import ConnectorResult

DEFAULT_TIMEOUT_SEC = 30

LINUX_CONTROL_COMMANDS: dict[str, str] = {
    "OS-001": "hostname",
    "OS-002": "uptime",
}


def get_linux_config() -> dict[str, Any]:
    """Linux target for predefined query execution.

    Resolution: active-environment YAML (predefined_query_targets.linux) ->
    ECS_LINUX_* env var -> historical default.
    """
    from modules.operations.engines.query_connectors import get_predefined_target

    cfg = get_predefined_target("linux")
    return {
        "container": cfg.get("container") or os.environ.get("ECS_LINUX_CONTAINER", "ubuntu-demo"),
        "timeout_sec": int(cfg.get("timeout_sec") or os.environ.get("ECS_LINUX_TIMEOUT_SEC", str(DEFAULT_TIMEOUT_SEC))),
    }


class LinuxConnector:
    def __init__(self, container: str = "ubuntu-demo", timeout_sec: int = DEFAULT_TIMEOUT_SEC):
        self.container = container
        self.timeout_sec = timeout_sec
        self._last_error = ""

    def connect(self) -> bool:
        try:
            proc = subprocess.run(
                ["docker", "exec", self.container, "true"],
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
                check=False,
            )
            if proc.returncode != 0:
                self._last_error = (
                    f"Linux demo container '{self.container}' is not reachable. "
                    "Start with: docker compose --profile demo-connectors up -d ubuntu-demo"
                )
                return False
            return True
        except FileNotFoundError:
            self._last_error = "Docker CLI not available in ECS container."
            return False
        except subprocess.TimeoutExpired:
            self._last_error = "Timed out connecting to Linux demo container."
            return False
        except Exception as exc:
            self._last_error = f"Linux connection failed: {exc}"
            return False

    def execute(self, query: str) -> ConnectorResult:
        started = time.perf_counter()
        try:
            proc = subprocess.run(
                ["docker", "exec", self.container, "sh", "-c", query],
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
                check=False,
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
            output = (proc.stdout or "").strip()
            if proc.stderr:
                output = f"{output}\n{proc.stderr.strip()}".strip()
            if proc.returncode != 0:
                return ConnectorResult(
                    success=False,
                    error_message=output or f"Command failed with exit code {proc.returncode}",
                    duration_ms=duration_ms,
                    metadata={"error_type": "query_failure", "rows_returned": 0},
                )
            lines = [line for line in output.splitlines() if line.strip()]
            return ConnectorResult(
                success=True,
                output=output or "(no output)",
                duration_ms=duration_ms,
                metadata={"rows_returned": max(len(lines), 1)},
            )
        except subprocess.TimeoutExpired:
            duration_ms = int((time.perf_counter() - started) * 1000)
            return ConnectorResult(
                success=False,
                error_message="Command timed out.",
                duration_ms=duration_ms,
                metadata={"error_type": "timeout", "rows_returned": 0},
            )
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            return ConnectorResult(
                success=False,
                error_message=f"Linux execution failed: {exc}",
                duration_ms=duration_ms,
                metadata={"error_type": "execution_failure", "rows_returned": 0},
            )

    def disconnect(self) -> None:
        return None
