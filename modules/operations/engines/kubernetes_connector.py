"""Kubernetes / OpenShift connectors for predefined query execution.

Both are thin CLI-execution abstractions that run ``kubectl`` / ``oc`` as
subprocesses against whatever kubeconfig the ECS host is configured with. No live
cluster is required for unit tests. They degrade gracefully:
  * binary not found        -> "kubectl/oc not installed"
  * no kubeconfig / no auth -> "not configured"
  * cluster unreachable     -> "cluster unavailable"

Read-only: the catalog only contains `get` / `version` style commands. Results
are normalised to ``ConnectorResult`` (plain CLI text). No secrets are logged.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import time
from shutil import which
from typing import Any

from modules.operations.engines.query_connectors import ConnectorResult

DEFAULT_TIMEOUT_SEC = 30


def _safe_int(value: Any, default: int) -> int:
    try:
        s = str(value).strip()
        if not s or s.startswith("${"):
            return default
        return int(s)
    except (TypeError, ValueError):
        return default


def _clean(value: Any) -> str:
    s = str(value).strip() if value is not None else ""
    return "" if s.startswith("${") else s


def get_kubernetes_config() -> dict[str, Any]:
    from modules.operations.engines.query_connectors import get_predefined_target

    cfg = get_predefined_target("kubernetes")
    return {
        "binary": _clean(cfg.get("binary")) or os.environ.get("ECS_KUBECTL_PATH", "kubectl"),
        "kubeconfig": _clean(cfg.get("kubeconfig")) or os.environ.get("ECS_KUBECONFIG", ""),
        "timeout_sec": _safe_int(
            cfg.get("timeout_sec") or os.environ.get("ECS_K8S_TIMEOUT_SECONDS"), DEFAULT_TIMEOUT_SEC,
        ),
    }


def get_openshift_config() -> dict[str, Any]:
    from modules.operations.engines.query_connectors import get_predefined_target

    cfg = get_predefined_target("openshift")
    return {
        "binary": _clean(cfg.get("binary")) or os.environ.get("ECS_OC_PATH", "oc"),
        "kubeconfig": _clean(cfg.get("kubeconfig")) or os.environ.get("ECS_OPENSHIFT_KUBECONFIG", ""),
        "timeout_sec": _safe_int(
            cfg.get("timeout_sec") or os.environ.get("ECS_OPENSHIFT_TIMEOUT_SECONDS"), DEFAULT_TIMEOUT_SEC,
        ),
    }


def _classify(stdout: str, stderr: str) -> tuple[str, str]:
    text = f"{stdout}\n{stderr}".lower()
    if "was refused" in text or "connection refused" in text or "unable to connect to the server" in text \
            or "timed out" in text or "no route to host" in text or "i/o timeout" in text:
        return "connection_failure", "Cluster unavailable — could not reach the API server."
    if "not configured" in text or "no configuration" in text or "invalid configuration" in text \
            or "no such file" in text or "please enter username" in text or "you must be logged in" in text \
            or "error loading config" in text:
        return "configuration_required", "Cluster not configured — set a valid kubeconfig / log in."
    if "forbidden" in text or "cannot list" in text or "unauthorized" in text:
        return "authentication_failure", "Access denied — the current context lacks permission."
    return "query_failure", (stderr.strip() or stdout.strip() or "Command failed.")


class _CliClusterConnector:
    """Shared kubectl/oc subprocess connector."""

    technology = ""
    _tool = "kubectl"

    def __init__(self, binary: str = "", kubeconfig: str = "", timeout_sec: int = DEFAULT_TIMEOUT_SEC):
        self.binary = binary or self._tool
        self.kubeconfig = kubeconfig
        self.timeout_sec = timeout_sec
        self._last_error = ""

    def connect(self) -> bool:
        # No persistent connection; verify the binary exists so callers get a
        # clean "not installed" instead of a raw FileNotFoundError.
        if which(self.binary) is None and not os.path.isfile(self.binary):
            self._last_error = f"{self._tool} not installed / not on PATH ({self.binary})."
            return False
        return True

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        if self.kubeconfig:
            env["KUBECONFIG"] = self.kubeconfig
        return env

    def execute(self, query: str) -> ConnectorResult:
        # The catalog command starts with the tool name (e.g. "kubectl get nodes").
        parts = shlex.split(query or "")
        if parts and parts[0] in ("kubectl", "oc"):
            parts = parts[1:]
        argv = [self.binary, *parts]
        started = time.perf_counter()
        try:
            proc = subprocess.run(
                argv, capture_output=True, text=True,
                timeout=self.timeout_sec, check=False, env=self._env(),
            )
        except FileNotFoundError:
            return ConnectorResult(
                success=False,
                error_message=f"{self._tool} not installed / not on PATH ({self.binary}).",
                metadata={"error_type": "configuration_required"},
            )
        except subprocess.TimeoutExpired:
            return ConnectorResult(
                success=False, error_message="Command timed out (cluster unavailable?).",
                metadata={"error_type": "timeout"},
            )
        except Exception as exc:  # noqa: BLE001
            return ConnectorResult(
                success=False, error_message=f"{self._tool} execution failed: {exc}",
                metadata={"error_type": "execution_failure"},
            )
        duration_ms = int((time.perf_counter() - started) * 1000)
        out = (proc.stdout or "").strip()
        if proc.returncode == 0:
            lines = [ln for ln in out.splitlines() if ln.strip()]
            return ConnectorResult(
                success=True, output=out or "(no output)", duration_ms=duration_ms,
                metadata={"rows_returned": max(len(lines), 1)},
            )
        etype, friendly = _classify(out, proc.stderr or "")
        return ConnectorResult(
            success=False, error_message=friendly, duration_ms=duration_ms,
            metadata={"error_type": etype},
        )

    def disconnect(self) -> None:
        return None


class KubernetesConnector(_CliClusterConnector):
    technology = "Kubernetes"
    _tool = "kubectl"


class OpenShiftConnector(_CliClusterConnector):
    technology = "OpenShift"
    _tool = "oc"
