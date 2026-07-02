"""Trivy connector — docker run vulnerability scan summary."""

from __future__ import annotations

import os
import subprocess
import time
from typing import Any

from modules.operations.engines.query_connectors import ConnectorResult

DEFAULT_TIMEOUT_SEC = 120
DEFAULT_IMAGE = "alpine:3.19"


def get_trivy_config() -> dict[str, Any]:
    """Trivy target for predefined query execution.

    Resolution: active-environment YAML (predefined_query_targets.trivy) ->
    ECS_TRIVY_* env var -> historical default.
    """
    from modules.operations.engines.query_connectors import get_predefined_target

    cfg = get_predefined_target("trivy")
    return {
        "image": cfg.get("image") or os.environ.get("ECS_TRIVY_IMAGE", DEFAULT_IMAGE),
        "timeout_sec": int(cfg.get("timeout_sec") or os.environ.get("ECS_TRIVY_TIMEOUT_SEC", str(DEFAULT_TIMEOUT_SEC))),
    }


class TrivyConnector:
    def __init__(self, image: str = DEFAULT_IMAGE, timeout_sec: int = DEFAULT_TIMEOUT_SEC):
        self.image = image
        self.timeout_sec = timeout_sec
        self._last_error = ""

    def connect(self) -> bool:
        try:
            proc = subprocess.run(
                ["docker", "image", "inspect", "aquasec/trivy"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if proc.returncode != 0:
                self._last_error = "Trivy image not available locally. Pull aquasec/trivy or start demo-connectors profile."
                return False
            return True
        except FileNotFoundError:
            self._last_error = "Docker CLI not available in ECS container."
            return False
        except Exception as exc:
            self._last_error = f"Trivy preflight failed: {exc}"
            return False

    def execute(self, query: str) -> ConnectorResult:
        started = time.perf_counter()
        target = self.image
        parts = query.split()
        if len(parts) >= 3 and parts[0].lower() == "trivy" and parts[1].lower() == "image":
            target = parts[2]
        try:
            proc = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    "/var/run/docker.sock:/var/run/docker.sock",
                    "aquasec/trivy",
                    "image",
                    "--scanners",
                    "vuln",
                    "--format",
                    "table",
                    target,
                ],
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
                check=False,
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
            output = (proc.stdout or "").strip()
            if proc.stderr:
                output = f"{output}\n{proc.stderr.strip()}".strip()
            if proc.returncode != 0 and not output:
                return ConnectorResult(
                    success=False,
                    error_message=f"Trivy scan failed with exit code {proc.returncode}",
                    duration_ms=duration_ms,
                    metadata={"error_type": "query_failure", "rows_returned": 0},
                )
            summary_lines = [ln for ln in output.splitlines() if ln.strip()]
            summary = "\n".join(summary_lines[:25])
            if len(summary_lines) > 25:
                summary += f"\n… ({len(summary_lines)} lines total)"
            header = f"Trivy Image Scan Summary — {target}\n{'=' * 48}"
            full_output = f"{header}\n{summary or '(no vulnerabilities reported)'}"
            vuln_rows = sum(1 for ln in summary_lines if "CVE-" in ln or "Total:" in ln)
            return ConnectorResult(
                success=True,
                output=full_output,
                duration_ms=duration_ms,
                metadata={"rows_returned": max(vuln_rows, 1)},
            )
        except subprocess.TimeoutExpired:
            duration_ms = int((time.perf_counter() - started) * 1000)
            return ConnectorResult(
                success=False,
                error_message="Trivy scan timed out.",
                duration_ms=duration_ms,
                metadata={"error_type": "timeout", "rows_returned": 0},
            )
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            return ConnectorResult(
                success=False,
                error_message=f"Trivy execution failed: {exc}",
                duration_ms=duration_ms,
                metadata={"error_type": "execution_failure", "rows_returned": 0},
            )

    def disconnect(self) -> None:
        return None
