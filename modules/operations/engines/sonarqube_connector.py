"""SonarQube connector — REST API execution."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import base64
from typing import Any

from modules.operations.engines.query_connectors import ConnectorResult

DEFAULT_TIMEOUT_SEC = 30


def get_sonarqube_config() -> dict[str, Any]:
    """SonarQube target for predefined query execution.

    Resolution: active-environment YAML (predefined_query_targets.sonarqube) ->
    ECS_SONAR_* env var -> historical default.
    """
    from modules.operations.engines.query_connectors import get_predefined_target

    cfg = get_predefined_target("sonarqube")
    token_env = str(cfg.get("token_env") or "ECS_SONAR_TOKEN")
    password_env = str(cfg.get("password_env") or "ECS_SONAR_PASSWORD")
    base_url = cfg.get("base_url") or os.environ.get("ECS_SONAR_URL", "http://sonarqube-demo:9000")
    return {
        "base_url": str(base_url).rstrip("/"),
        "token": os.environ.get(token_env) or os.environ.get("ECS_SONAR_TOKEN", ""),
        "user": cfg.get("user") or os.environ.get("ECS_SONAR_USER", "admin"),
        "password": os.environ.get(password_env) or os.environ.get("ECS_SONAR_PASSWORD", "admin"),
        "timeout_sec": int(cfg.get("timeout_sec") or os.environ.get("ECS_SONAR_TIMEOUT_SEC", str(DEFAULT_TIMEOUT_SEC))),
    }


class SonarQubeConnector:
    def __init__(
        self,
        base_url: str = "http://sonarqube-demo:9000",
        token: str = "",
        user: str = "admin",
        password: str = "admin",
        timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.user = user
        self.password = password
        self.timeout_sec = timeout_sec
        self._last_error = ""

    def connect(self) -> bool:
        try:
            self._request("/api/system/status")
            return True
        except Exception as exc:
            self._last_error = (
                f"SonarQube is not reachable at {self.base_url}. "
                f"Start with: docker compose --profile demo-connectors up -d sonarqube-demo ({exc})"
            )
            return False

    def _request(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        query = f"?{urllib.parse.urlencode(params)}" if params else ""
        url = f"{self.base_url}{path}{query}"
        req = urllib.request.Request(url, method="GET")
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        else:
            auth = base64.b64encode(f"{self.user}:{self.password}".encode()).decode()
            req.add_header("Authorization", f"Basic {auth}")
        with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def execute(self, query: str) -> ConnectorResult:
        started = time.perf_counter()
        mode = query.strip().lower()
        try:
            if mode in ("projects", "project count", "app-001"):
                data = self._request("/api/projects/search", {"ps": "1", "p": "1"})
                count = int(data.get("paging", {}).get("total", 0))
                output = f"SonarQube Project Count: {count}"
            elif mode in ("issues", "open issues", "app-002"):
                data = self._request("/api/issues/search", {"resolved": "false", "ps": "1", "p": "1"})
                count = int(data.get("total", 0))
                output = f"SonarQube Open Issues Count: {count}"
            else:
                duration_ms = int((time.perf_counter() - started) * 1000)
                return ConnectorResult(
                    success=False,
                    error_message=f"Unsupported SonarQube execution mode: {query}",
                    duration_ms=duration_ms,
                    metadata={"error_type": "unsupported_query", "rows_returned": 0},
                )
            duration_ms = int((time.perf_counter() - started) * 1000)
            return ConnectorResult(
                success=True,
                output=output,
                duration_ms=duration_ms,
                metadata={"rows_returned": 1},
            )
        except urllib.error.HTTPError as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            body = exc.read().decode("utf-8", errors="replace")[:300]
            return ConnectorResult(
                success=False,
                error_message=f"SonarQube API error ({exc.code}): {body}",
                duration_ms=duration_ms,
                metadata={"error_type": "query_failure", "rows_returned": 0},
            )
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            return ConnectorResult(
                success=False,
                error_message=f"SonarQube execution failed: {exc}",
                duration_ms=duration_ms,
                metadata={"error_type": "connection_failure", "rows_returned": 0},
            )

    def disconnect(self) -> None:
        return None
