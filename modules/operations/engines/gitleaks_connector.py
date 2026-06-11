"""GitLeaks connector — docker run secret scan summary."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Any

from modules.operations.engines.query_connectors import ConnectorResult

DEFAULT_TIMEOUT_SEC = 120


def get_gitleaks_config() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[3]
    return {
        "scan_path": os.environ.get("ECS_GITLEAKS_SCAN_PATH", str(root / "demo-data" / "gitleaks-sample")),
        "timeout_sec": int(os.environ.get("ECS_GITLEAKS_TIMEOUT_SEC", str(DEFAULT_TIMEOUT_SEC))),
    }


class GitLeaksConnector:
    def __init__(self, scan_path: str = "", timeout_sec: int = DEFAULT_TIMEOUT_SEC):
        self.scan_path = scan_path
        self.timeout_sec = timeout_sec
        self._last_error = ""

    def connect(self) -> bool:
        if not self.scan_path or not Path(self.scan_path).is_dir():
            self._last_error = f"GitLeaks scan path not found: {self.scan_path}"
            return False
        try:
            proc = subprocess.run(
                ["docker", "image", "inspect", "zricethezav/gitleaks"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if proc.returncode != 0:
                self._last_error = "GitLeaks image not available locally. Pull zricethezav/gitleaks or start demo-connectors profile."
                return False
            return True
        except FileNotFoundError:
            self._last_error = "Docker CLI not available in ECS container."
            return False
        except Exception as exc:
            self._last_error = f"GitLeaks preflight failed: {exc}"
            return False

    def execute(self, query: str) -> ConnectorResult:
        started = time.perf_counter()
        try:
            proc = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    f"{self.scan_path}:/scan:ro",
                    "zricethezav/gitleaks",
                    "detect",
                    "--source=/scan",
                    "--no-git",
                    "--redact",
                ],
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
                check=False,
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
            output = (proc.stdout or "").strip()
            stderr = (proc.stderr or "").strip()
            findings = [ln for ln in (output + "\n" + stderr).splitlines() if "leaks found" in ln.lower() or "Secret" in ln or "Finding" in ln]
            if proc.returncode == 0:
                summary = stderr or output or "GitLeaks Secret Scan Summary: 0 leaks found"
            elif proc.returncode == 1 and ("leaks found" in stderr.lower() or "leaks found" in output.lower()):
                summary = stderr or output
            else:
                return ConnectorResult(
                    success=False,
                    error_message=stderr or output or f"GitLeaks failed with exit code {proc.returncode}",
                    duration_ms=duration_ms,
                    metadata={"error_type": "query_failure", "rows_returned": 0},
                )
            header = "GitLeaks Secret Scan Summary\n" + ("=" * 32)
            full_output = f"{header}\n{summary}"
            leak_count = 0
            for ln in summary.splitlines():
                if "leaks found" in ln.lower():
                    try:
                        leak_count = int("".join(ch for ch in ln if ch.isdigit()) or "0")
                    except ValueError:
                        leak_count = 1
            return ConnectorResult(
                success=True,
                output=full_output,
                duration_ms=duration_ms,
                metadata={"rows_returned": max(leak_count, len(findings), 1)},
            )
        except subprocess.TimeoutExpired:
            duration_ms = int((time.perf_counter() - started) * 1000)
            return ConnectorResult(
                success=False,
                error_message="GitLeaks scan timed out.",
                duration_ms=duration_ms,
                metadata={"error_type": "timeout", "rows_returned": 0},
            )
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            return ConnectorResult(
                success=False,
                error_message=f"GitLeaks execution failed: {exc}",
                duration_ms=duration_ms,
                metadata={"error_type": "execution_failure", "rows_returned": 0},
            )

    def disconnect(self) -> None:
        return None
