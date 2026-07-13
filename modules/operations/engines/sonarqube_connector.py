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


def _classify_http_error(exc: urllib.error.HTTPError, base_url: str) -> tuple[str, str]:
    body = exc.read().decode("utf-8", errors="replace")[:300]
    code = exc.code
    if code == 401:
        return (
            "authentication_failure",
            f"SonarQube authentication failed at {base_url} (HTTP 401). "
            "Verify ECS_SONAR_TOKEN or ECS_SONAR_USER/ECS_SONAR_PASSWORD.",
        )
    if code == 403:
        return ("query_failure", f"SonarQube authorization denied (HTTP 403): {body}")
    if code == 404:
        return ("query_failure", f"SonarQube endpoint not found (HTTP 404): {body}")
    if code >= 500:
        return ("remote_service_failure", f"SonarQube server error (HTTP {code}): {body}")
    return ("query_failure", f"SonarQube API error (HTTP {code}): {body}")


def _classify_url_error(exc: urllib.error.URLError, base_url: str) -> tuple[str, str]:
    reason = str(exc.reason).lower()
    if "timed out" in reason or "timeout" in reason:
        return ("connection_failure", f"SonarQube connection timed out at {base_url}.")
    return ("connection_failure", f"SonarQube is not reachable at {base_url}. ({exc.reason})")


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
        self._last_error_type = "execution_failure"

    def _auth_headers(self) -> dict[str, str]:
        # SonarQube user tokens authenticate as Basic username with an empty password.
        if self.token:
            encoded = base64.b64encode(f"{self.token}:".encode("utf-8")).decode("ascii")
            return {"Authorization": f"Basic {encoded}"}
        if self.user or self.password:
            auth = base64.b64encode(f"{self.user}:{self.password}".encode()).decode()
            return {"Authorization": f"Basic {auth}"}
        return {}

    def connect(self) -> bool:
        try:
            # /api/system/status is anonymous; omit auth so a bad token/password
            # cannot make a healthy instance appear unreachable.
            self._request("/api/system/status", auth=False)
            self._last_error = ""
            self._last_error_type = ""
            return True
        except urllib.error.HTTPError as exc:
            self._last_error_type, self._last_error = _classify_http_error(exc, self.base_url)
            return False
        except urllib.error.URLError as exc:
            self._last_error_type, self._last_error = _classify_url_error(exc, self.base_url)
            return False
        except json.JSONDecodeError as exc:
            self._last_error_type = "response_validation_failure"
            self._last_error = f"SonarQube health response was not valid JSON at {self.base_url}: {exc}"
            return False
        except Exception as exc:  # noqa: BLE001 - last-resort guard
            self._last_error_type = "connection_failure"
            self._last_error = f"SonarQube is not reachable at {self.base_url}. ({exc})"
            return False

    def _request(self, path: str, params: dict[str, str] | None = None, *, auth: bool = True) -> dict[str, Any]:
        query = f"?{urllib.parse.urlencode(params)}" if params else ""
        url = f"{self.base_url}{path}{query}"
        req = urllib.request.Request(url, method="GET")
        if auth:
            for key, value in self._auth_headers().items():
                req.add_header(key, value)
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
            error_type, error_message = _classify_http_error(exc, self.base_url)
            return ConnectorResult(
                success=False,
                error_message=error_message,
                duration_ms=duration_ms,
                metadata={"error_type": error_type, "rows_returned": 0},
            )
        except urllib.error.URLError as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            error_type, error_message = _classify_url_error(exc, self.base_url)
            return ConnectorResult(
                success=False,
                error_message=error_message,
                duration_ms=duration_ms,
                metadata={"error_type": error_type, "rows_returned": 0},
            )
        except json.JSONDecodeError as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            return ConnectorResult(
                success=False,
                error_message=f"SonarQube response was not valid JSON: {exc}",
                duration_ms=duration_ms,
                metadata={"error_type": "response_validation_failure", "rows_returned": 0},
            )
        except Exception as exc:  # noqa: BLE001
            duration_ms = int((time.perf_counter() - started) * 1000)
            return ConnectorResult(
                success=False,
                error_message=f"SonarQube execution failed: {exc}",
                duration_ms=duration_ms,
                metadata={"error_type": "query_failure", "rows_returned": 0},
            )

    def disconnect(self) -> None:
        return None
